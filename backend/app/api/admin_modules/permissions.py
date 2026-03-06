from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import (
    ACTION_ORDER,
    expand_agent_group_permissions_async,
    expand_resource_wildcards_async,
    get_user_role_names_async,
    is_super_admin,
    require_manage_menu_async,
    require_menu_action_async,
)
from .common import (
    assert_permission_editable,
    build_permission_items,
    collect_actions,
    expand_actions,
)

router = APIRouter()


def _permission_grant_out(grant: models.PermissionGrant) -> schemas.PermissionGrantOut:
    return schemas.PermissionGrantOut(
        id=grant.id,
        subject_type=grant.subject_type,
        subject_id=grant.subject_id,
        scope=grant.scope,
        resource_type=grant.resource_type,
        resource_id=grant.resource_id,
        action=grant.action,
        created_at=grant.created_at,
    )


async def _build_subject_permissions_summary(
    *,
    subject_type: str,
    subject_id: str,
    scope: str,
    current_user: models.User,
    db: AsyncSession,
) -> schemas.PermissionSubjectSummary:
    if subject_type not in {"user", "role"}:
        raise HTTPException(status_code=400, detail="Invalid subject type")
    if scope not in {"menu", "resource"}:
        raise HTTPException(status_code=400, detail="Invalid scope")

    read_only = False
    role_name: str | None = None
    role_names: list[str] = []

    if subject_type == "user":
        try:
            user_id = int(subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = await db.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        role_names = await get_user_role_names_async(db, user)
        role_name = role_names[0] if role_names else None
        if user.account == "admin" and not is_super_admin(current_user):
            read_only = True

        clause = [
            (models.PermissionGrant.subject_type == "user")
            & (models.PermissionGrant.subject_id == str(user_id))
            & (models.PermissionGrant.scope == scope)
        ]
        if role_names:
            clause.append(
                (models.PermissionGrant.subject_type == "role")
                & (models.PermissionGrant.subject_id.in_(role_names))
                & (models.PermissionGrant.scope == scope)
            )
        grants = (await db.execute(select(models.PermissionGrant).where(or_(*clause)))).scalars().all()
        user_grants = [grant for grant in grants if grant.subject_type == "user"]
        role_grants = [grant for grant in grants if grant.subject_type == "role"]

        direct_map = collect_actions(user_grants)
        inherited_map = collect_actions(role_grants)

        if scope == "resource":
            direct_map = await expand_resource_wildcards_async(db, direct_map)
            inherited_map = await expand_resource_wildcards_async(db, inherited_map)
            direct_map = {key: set(actions) for key, actions in direct_map.items() if key[1] is not None}
            inherited_map = {
                key: set(actions) for key, actions in inherited_map.items() if key[1] is not None
            }

        effective_map: dict[tuple[str, str | None], set[str]] = {}
        for key, actions in inherited_map.items():
            effective_map.setdefault(key, set()).update(actions)
        for key, actions in direct_map.items():
            effective_map.setdefault(key, set()).update(actions)

        if scope == "resource":
            derived_from_direct = await expand_agent_group_permissions_async(db, direct_map)
            derived_from_inherited = await expand_agent_group_permissions_async(db, inherited_map)
            for key, actions in derived_from_direct.items():
                effective_map.setdefault(key, set()).update(actions)
            for key, actions in derived_from_inherited.items():
                effective_map.setdefault(key, set()).update(actions)

            inherited_display: dict[tuple[str, str | None], set[str]] = {}
            for key, actions in inherited_map.items():
                inherited_display.setdefault(key, set()).update(actions)
            for key, actions in derived_from_inherited.items():
                inherited_display.setdefault(key, set()).update(actions)
            items = build_permission_items(effective_map, inherited_display)
        else:
            items = build_permission_items(effective_map, inherited_map)
    else:
        role = (
            await db.execute(select(models.Role).where(models.Role.name == subject_id))
        ).scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        role_name = subject_id
        role_names = [subject_id]
        if subject_id == "user":
            read_only = True
        elif subject_id == "admin" and not is_super_admin(current_user):
            read_only = True

        role_grants = (
            await db.execute(
                select(models.PermissionGrant).where(
                    models.PermissionGrant.subject_type == "role",
                    models.PermissionGrant.subject_id == subject_id,
                    models.PermissionGrant.scope == scope,
                )
            )
        ).scalars().all()
        effective_map = collect_actions(role_grants)
        if scope == "resource":
            effective_map = await expand_resource_wildcards_async(db, effective_map)
            effective_map = {
                key: set(actions) for key, actions in effective_map.items() if key[1] is not None
            }
            derived_from_groups = await expand_agent_group_permissions_async(db, effective_map)
            for key, actions in derived_from_groups.items():
                effective_map.setdefault(key, set()).update(actions)
            items = build_permission_items(effective_map, derived_from_groups)
        else:
            items = build_permission_items(effective_map, {})

    if scope == "resource":
        items = [item for item in items if item.resource_id is not None]

    return schemas.PermissionSubjectSummary(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        role=role_name,
        roles=role_names,
        read_only=read_only,
        items=items,
    )


@router.get("/permissions", response_model=list[schemas.PermissionGrantOut])
async def list_permission_grants(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.PermissionGrantOut]:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    grants = (
        await db.execute(select(models.PermissionGrant).order_by(models.PermissionGrant.id.desc()))
    ).scalars().all()
    return [_permission_grant_out(grant) for grant in grants]


@router.get("/permissions/subject", response_model=schemas.PermissionSubjectSummary)
async def get_subject_permissions(
    subject_type: str,
    subject_id: str,
    scope: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionSubjectSummary:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    return await _build_subject_permissions_summary(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        current_user=current_user,
        db=db,
    )


@router.put("/permissions/subject", response_model=schemas.PermissionSubjectSummary)
async def update_subject_permissions(
    payload: schemas.PermissionSubjectUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionSubjectSummary:
    await require_manage_menu_async(db, current_user)
    subject_type = payload.subject_type
    subject_id = payload.subject_id
    scope = payload.scope

    if subject_type == "user":
        try:
            user_id = int(subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = await db.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        assert_permission_editable(current_user, target_user=user)
        role_names = await get_user_role_names_async(db, user)
        role_grants = []
        if role_names:
            role_grants = (
                await db.execute(
                    select(models.PermissionGrant).where(
                        models.PermissionGrant.subject_type == "role",
                        models.PermissionGrant.subject_id.in_(role_names),
                        models.PermissionGrant.scope == scope,
                    )
                )
            ).scalars().all()
        role_map_raw = collect_actions(role_grants)
        if scope == "resource":
            role_map_raw = await expand_resource_wildcards_async(db, role_map_raw)
            role_map_raw = {
                key: set(actions) for key, actions in role_map_raw.items() if key[1] is not None
            }
            role_map_effective = {key: set(actions) for key, actions in role_map_raw.items()}
            derived_from_role = await expand_agent_group_permissions_async(db, role_map_effective)
            for key, actions in derived_from_role.items():
                role_map_effective.setdefault(key, set()).update(actions)
        else:
            role_map_effective = role_map_raw
    else:
        role = (
            await db.execute(select(models.Role).where(models.Role.name == subject_id))
        ).scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        assert_permission_editable(current_user, target_role=subject_id)
        role_map_raw = {}
        role_map_effective = {}

    desired_map: dict[tuple[str, str | None], set[str]] = {}
    for item in payload.items:
        actions = {action for action in item.actions if action in ACTION_ORDER}
        actions = expand_actions(actions)
        if not actions:
            continue
        if scope == "menu" and item.resource_type != "menu":
            raise HTTPException(status_code=400, detail="Menu scope requires resource_type=menu")
        if scope == "menu" and item.resource_id not in {"agents", "models", "admin"}:
            raise HTTPException(status_code=400, detail="Invalid menu id")
        if scope == "resource" and item.resource_type not in {"agent", "model", "agent_group"}:
            raise HTTPException(status_code=400, detail="Invalid resource type")
        if scope == "resource" and not item.resource_id:
            raise HTTPException(status_code=400, detail="Resource scope requires resource_id")
        desired_map[(item.resource_type, item.resource_id)] = actions

    direct_map: dict[tuple[str, str | None], set[str]] = {}
    group_derived_from_desired = (
        await expand_agent_group_permissions_async(db, desired_map) if scope == "resource" else {}
    )

    for key, actions in desired_map.items():
        resource_type, resource_id = key
        remaining = set(actions)

        if subject_type == "user":
            inherited_actions = set(role_map_effective.get(key, set()))
            if resource_id is None:
                inherited_actions.update(role_map_raw.get((resource_type, None), set()))
            remaining -= inherited_actions

        if scope == "resource" and resource_type == "agent":
            remaining -= group_derived_from_desired.get(key, set())

        if remaining:
            direct_map[key] = remaining

    existing = (
        await db.execute(
            select(models.PermissionGrant).where(
                models.PermissionGrant.subject_type == subject_type,
                models.PermissionGrant.subject_id == subject_id,
                models.PermissionGrant.scope == scope,
            )
        )
    ).scalars().all()
    existing_keys = {(grant.resource_type, grant.resource_id, grant.action): grant for grant in existing}

    desired_keys: set[tuple[str, str | None, str]] = set()
    for (resource_type, resource_id), actions in direct_map.items():
        for action in actions:
            desired_keys.add((resource_type, resource_id, action))

    for key, grant in existing_keys.items():
        if key not in desired_keys:
            await db.delete(grant)

    for resource_type, resource_id, action in desired_keys:
        if (resource_type, resource_id, action) in existing_keys:
            continue
        db.add(
            models.PermissionGrant(
                subject_type=subject_type,
                subject_id=subject_id,
                scope=scope,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
            )
        )

    await db.commit()

    return await _build_subject_permissions_summary(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        current_user=current_user,
        db=db,
    )


@router.post("/permissions", response_model=schemas.PermissionGrantOut, status_code=201)
async def create_permission_grant(
    payload: schemas.PermissionGrantCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionGrantOut:
    await require_manage_menu_async(db, current_user)
    if payload.scope == "menu" and payload.resource_type != "menu":
        raise HTTPException(status_code=400, detail="Menu scope requires resource_type=menu")
    if payload.scope == "menu" and payload.resource_id not in {"agents", "models", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid menu id")
    if payload.scope == "resource" and payload.resource_type not in {"agent", "model", "agent_group"}:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    if payload.scope == "resource" and not payload.resource_id:
        raise HTTPException(status_code=400, detail="Resource scope requires resource_id")
    if payload.resource_type == "agent_group" and payload.resource_id:
        group = (
            await db.execute(select(models.AgentGroup).where(models.AgentGroup.name == payload.resource_id))
        ).scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Agent group not found")
    if payload.subject_type == "role":
        role = (
            await db.execute(select(models.Role.id).where(models.Role.name == payload.subject_id))
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=400, detail="Role not found")
        assert_permission_editable(current_user, target_role=payload.subject_id)
    if payload.subject_type == "user":
        try:
            user_id = int(payload.subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = await db.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        assert_permission_editable(current_user, target_user=user)

    existing = (
        await db.execute(
            select(models.PermissionGrant).where(
                models.PermissionGrant.subject_type == payload.subject_type,
                models.PermissionGrant.subject_id == payload.subject_id,
                models.PermissionGrant.scope == payload.scope,
                models.PermissionGrant.resource_type == payload.resource_type,
                models.PermissionGrant.resource_id == payload.resource_id,
                models.PermissionGrant.action == payload.action,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Permission already granted")

    grant = models.PermissionGrant(**payload.model_dump())
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return _permission_grant_out(grant)


@router.delete("/permissions/{grant_id}")
async def delete_permission_grant(
    grant_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    grant = await db.get(models.PermissionGrant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Permission grant not found")
    if grant.subject_type == "role":
        assert_permission_editable(current_user, target_role=grant.subject_id)
    if grant.subject_type == "user":
        try:
            target_id = int(grant.subject_id)
        except ValueError:
            target_id = None
        if target_id is not None:
            target_user = await db.get(models.User, target_id)
            if target_user:
                assert_permission_editable(current_user, target_user=target_user)
    await db.delete(grant)
    await db.commit()
    return {"status": "deleted"}
