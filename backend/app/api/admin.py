from __future__ import annotations

from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..auth import get_current_user
from ..db import get_db
from ..permissions import ACTION_ORDER, has_permission, require_manage_menu, require_menu_action
from ..services.serializers import agent_detail, model_detail

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_menu_view(user: models.User, db: Session, menu_id: str) -> None:
    require_menu_action(db, user, action="view", menu_id=menu_id)


def _require_menu_edit(user: models.User, db: Session, menu_id: str) -> None:
    require_menu_action(db, user, action="edit", menu_id=menu_id)


def _require_menu_manage(user: models.User, db: Session) -> None:
    require_manage_menu(db, user)


def _ensure_role_exists(db: Session, role_name: str) -> None:
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")


def _sorted_actions(actions: set[str]) -> list[str]:
    return sorted(actions, key=lambda item: ACTION_ORDER.get(item, 0))


def _collect_actions(grants: list[models.PermissionGrant]) -> dict[tuple[str, str | None], set[str]]:
    grouped: dict[tuple[str, str | None], set[str]] = {}
    for grant in grants:
        key = (grant.resource_type, grant.resource_id)
        grouped.setdefault(key, set()).add(grant.action)
    return grouped


def _build_permission_items(
    effective: dict[tuple[str, str | None], set[str]],
    inherited: dict[tuple[str, str | None], set[str]] | None = None,
) -> list[schemas.PermissionSubjectMatrixItem]:
    items: list[schemas.PermissionSubjectMatrixItem] = []
    inherited = inherited or {}
    for (resource_type, resource_id), actions in effective.items():
        inherited_actions = inherited.get((resource_type, resource_id), set())
        items.append(
            schemas.PermissionSubjectMatrixItem(
                resource_type=resource_type,
                resource_id=resource_id,
                actions=_sorted_actions(actions),
                inherited_actions=_sorted_actions(inherited_actions),
            )
        )
    items.sort(key=lambda item: (item.resource_type, item.resource_id or ""))
    return items


def _expand_resource_wildcards(
    db: Session,
    action_map: dict[tuple[str, str | None], set[str]],
) -> dict[tuple[str, str | None], set[str]]:
    expanded: dict[tuple[str, str | None], set[str]] = {}
    for key, actions in action_map.items():
        expanded[key] = set(actions)

    for resource_type in ("agent", "model", "agent_group"):
        wildcard_actions = expanded.pop((resource_type, None), None)
        if not wildcard_actions:
            continue
        if resource_type == "agent":
            ids = [agent.id for agent in db.query(models.Agent.id).all()]
        elif resource_type == "model":
            ids = [model.id for model in db.query(models.Model.id).all()]
        else:
            ids = [group.name for group in db.query(models.AgentGroup.name).all()]

        if not ids:
            expanded[(resource_type, None)] = set(wildcard_actions)
            continue

        for resource_id in ids:
            expanded.setdefault((resource_type, resource_id), set()).update(wildcard_actions)

    return expanded


def _assert_permission_editable(
    current_user: models.User, target_user: models.User | None = None, *, target_role: str | None = None
) -> None:
    if target_user and target_user.account == "admin" and current_user.account != "admin":
        raise HTTPException(status_code=403, detail="Protected user permissions cannot be modified")
    if target_role == "admin" and current_user.account != "admin":
        raise HTTPException(status_code=403, detail="Protected role permissions cannot be modified")


def _normalize_groups(groups: list[str] | None) -> list[str]:
    if not groups:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in groups:
        name = str(item).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


def _ensure_agent_groups(db: Session, groups: list[str]) -> None:
    if not groups:
        return
    existing = {
        group.name
        for group in db.query(models.AgentGroup)
        .filter(models.AgentGroup.name.in_(groups))
        .all()
    }
    for name in groups:
        if name not in existing:
            db.add(models.AgentGroup(name=name, description=""))
            existing.add(name)


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AdminUserOut]:
    _require_menu_view(current_user, db, "admin")
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    return [
        schemas.AdminUserOut(
            id=user.id,
            account=user.account,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            source=user.source,
            workspace=user.workspace,
            created_at=user.created_at,
        )
        for user in users
    ]


@router.post("/users", response_model=schemas.AdminUserOut, status_code=201)
def create_user(
    payload: schemas.AdminUserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AdminUserOut:
    _require_menu_manage(current_user, db)
    _ensure_role_exists(db, payload.role)
    existing = db.query(models.User).filter(models.User.account == payload.account).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account already registered")

    email_existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if email_existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        account=payload.account,
        username=payload.username,
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        role=payload.role or "user",
        status=payload.status or "active",
        source=payload.source or "local",
        workspace=payload.workspace or "default",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.AdminUserOut(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        source=user.source,
        workspace=user.workspace,
        created_at=user.created_at,
    )


@router.put("/users/{user_id}", response_model=schemas.AdminUserOut)
def update_user(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AdminUserOut:
    _require_menu_manage(current_user, db)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.account and payload.account != user.account:
        existing = (
            db.query(models.User)
            .filter(models.User.account == payload.account)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Account already registered")
        user.account = payload.account

    if payload.username and payload.username != user.username:
        user.username = payload.username

    if payload.email and payload.email != user.email:
        existing = db.query(models.User).filter(models.User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        user.email = payload.email

    if payload.role:
        _ensure_role_exists(db, payload.role)
        user.role = payload.role

    if payload.status:
        user.status = payload.status

    if payload.source:
        user.source = payload.source

    if payload.workspace:
        user.workspace = payload.workspace

    if payload.password:
        user.password_hash = security.hash_password(payload.password)

    db.commit()
    db.refresh(user)

    return schemas.AdminUserOut(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        source=user.source,
        workspace=user.workspace,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_menu_manage(current_user, db)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(models.PermissionGrant).filter(
        models.PermissionGrant.subject_type == "user",
        models.PermissionGrant.subject_id == str(user_id),
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"status": "deleted"}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: schemas.AdminResetPasswordRequest | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_menu_manage(current_user, db)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = (payload.password if payload and payload.password else None) or "agentui@2025"
    user.password_hash = security.hash_password(new_password)
    db.commit()
    return {"status": "ok", "password": new_password}


@router.get("/roles", response_model=list[schemas.RoleOut])
def list_roles(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.RoleOut]:
    _require_menu_view(current_user, db, "admin")
    roles = db.query(models.Role).order_by(models.Role.id.asc()).all()
    return [schemas.RoleOut(id=role.id, name=role.name, description=role.description) for role in roles]


@router.get("/agent-groups", response_model=list[schemas.AgentGroupOut])
def list_agent_groups(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentGroupOut]:
    _require_menu_view(current_user, db, "admin")
    groups = db.query(models.AgentGroup).order_by(models.AgentGroup.name.asc()).all()
    return [
        schemas.AgentGroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
        )
        for group in groups
    ]


@router.post("/agent-groups", response_model=schemas.AgentGroupOut, status_code=201)
def create_agent_group(
    payload: schemas.AgentGroupCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentGroupOut:
    _require_menu_manage(current_user, db)
    existing = (
        db.query(models.AgentGroup).filter(models.AgentGroup.name == payload.name).first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Group already exists")
    group = models.AgentGroup(name=payload.name, description=payload.description or "")
    db.add(group)
    db.commit()
    db.refresh(group)
    return schemas.AgentGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
    )


@router.put("/agent-groups/{group_id}", response_model=schemas.AgentGroupOut)
def update_agent_group(
    group_id: int,
    payload: schemas.AgentGroupUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentGroupOut:
    _require_menu_manage(current_user, db)
    group = db.query(models.AgentGroup).filter(models.AgentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.name and payload.name != group.name:
        existing = (
            db.query(models.AgentGroup).filter(models.AgentGroup.name == payload.name).first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Group already exists")
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    db.commit()
    db.refresh(group)
    return schemas.AgentGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
    )


@router.delete("/agent-groups/{group_id}")
def delete_agent_group(
    group_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_menu_manage(current_user, db)
    group = db.query(models.AgentGroup).filter(models.AgentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    group_name = group.name
    agents = db.query(models.Agent).all()
    for agent in agents:
        if group_name in (agent.groups or []):
            agent.groups = [g for g in agent.groups if g != group_name]
            agent.group_name = agent.groups[0] if agent.groups else ""
    db.delete(group)
    db.commit()
    return {"status": "deleted"}


@router.post("/roles", response_model=schemas.RoleOut, status_code=201)
def create_role(
    payload: schemas.RoleCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.RoleOut:
    _require_menu_manage(current_user, db)
    existing = db.query(models.Role).filter(models.Role.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Role already exists")
    role = models.Role(name=payload.name, description=payload.description or "")
    db.add(role)
    db.commit()
    db.refresh(role)
    return schemas.RoleOut(id=role.id, name=role.name, description=role.description)


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_menu_manage(current_user, db)
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Protected role cannot be deleted")
    db.delete(role)
    db.commit()
    return {"status": "deleted"}


@router.get("/permissions", response_model=list[schemas.PermissionGrantOut])
def list_permission_grants(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.PermissionGrantOut]:
    _require_menu_view(current_user, db, "admin")
    grants = db.query(models.PermissionGrant).order_by(models.PermissionGrant.id.desc()).all()
    return [
        schemas.PermissionGrantOut(
            id=grant.id,
            subject_type=grant.subject_type,
            subject_id=grant.subject_id,
            scope=grant.scope,
            resource_type=grant.resource_type,
            resource_id=grant.resource_id,
            action=grant.action,
            created_at=grant.created_at,
        )
        for grant in grants
    ]


@router.get("/permissions/subject", response_model=schemas.PermissionSubjectSummary)
def get_subject_permissions(
    subject_type: str,
    subject_id: str,
    scope: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PermissionSubjectSummary:
    _require_menu_view(current_user, db, "admin")
    if subject_type not in {"user", "role"}:
        raise HTTPException(status_code=400, detail="Invalid subject type")
    if scope not in {"menu", "resource"}:
        raise HTTPException(status_code=400, detail="Invalid scope")

    read_only = False
    role_name: str | None = None

    if subject_type == "user":
        try:
            user_id = int(subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        role_name = user.role
        if user.account == "admin" and current_user.account != "admin":
            read_only = True
        user_grants = (
            db.query(models.PermissionGrant)
            .filter(
                models.PermissionGrant.subject_type == "user",
                models.PermissionGrant.subject_id == str(user_id),
                models.PermissionGrant.scope == scope,
            )
            .all()
        )
        role_grants: list[models.PermissionGrant] = []
        if role_name:
            role_grants = (
                db.query(models.PermissionGrant)
                .filter(
                    models.PermissionGrant.subject_type == "role",
                    models.PermissionGrant.subject_id == role_name,
                    models.PermissionGrant.scope == scope,
                )
                .all()
            )
        direct_map = _collect_actions(user_grants)
        inherited_map = _collect_actions(role_grants)
        effective_map: dict[tuple[str, str | None], set[str]] = {}
        for key, actions in inherited_map.items():
            effective_map.setdefault(key, set()).update(actions)
        for key, actions in direct_map.items():
            effective_map.setdefault(key, set()).update(actions)
        if scope == "resource":
            inherited_map = _expand_resource_wildcards(db, inherited_map)
            effective_map = _expand_resource_wildcards(db, effective_map)
        items = _build_permission_items(effective_map, inherited_map)
    else:
        role = db.query(models.Role).filter(models.Role.name == subject_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if subject_id == "admin" and current_user.account != "admin":
            read_only = True
        role_grants = (
            db.query(models.PermissionGrant)
            .filter(
                models.PermissionGrant.subject_type == "role",
                models.PermissionGrant.subject_id == subject_id,
                models.PermissionGrant.scope == scope,
            )
            .all()
        )
        effective_map = _collect_actions(role_grants)
        if scope == "resource":
            effective_map = _expand_resource_wildcards(db, effective_map)
        items = _build_permission_items(effective_map, {})

    return schemas.PermissionSubjectSummary(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        role=role_name,
        read_only=read_only,
        items=items,
    )


@router.put("/permissions/subject", response_model=schemas.PermissionSubjectSummary)
def update_subject_permissions(
    payload: schemas.PermissionSubjectUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PermissionSubjectSummary:
    _require_menu_manage(current_user, db)
    subject_type = payload.subject_type
    subject_id = payload.subject_id
    scope = payload.scope

    if subject_type == "user":
        try:
            user_id = int(subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        _assert_permission_editable(current_user, target_user=user)
        role_name = user.role
        role_grants: list[models.PermissionGrant] = []
        if role_name:
            role_grants = (
                db.query(models.PermissionGrant)
                .filter(
                    models.PermissionGrant.subject_type == "role",
                    models.PermissionGrant.subject_id == role_name,
                    models.PermissionGrant.scope == scope,
                )
                .all()
            )
        role_map = _collect_actions(role_grants)
    else:
        role = db.query(models.Role).filter(models.Role.name == subject_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        _assert_permission_editable(current_user, target_role=subject_id)
        role_map = {}

    desired_map: dict[tuple[str, str | None], set[str]] = {}
    for item in payload.items:
        actions = {action for action in item.actions if action in ACTION_ORDER}
        if not actions:
            continue
        if scope == "menu" and item.resource_type != "menu":
            raise HTTPException(status_code=400, detail="Menu scope requires resource_type=menu")
        if scope == "menu" and item.resource_id not in {"agents", "models", "admin"}:
            raise HTTPException(status_code=400, detail="Invalid menu id")
        if scope == "resource" and item.resource_type not in {"agent", "model", "agent_group"}:
            raise HTTPException(status_code=400, detail="Invalid resource type")
        desired_map[(item.resource_type, item.resource_id)] = actions

    direct_map: dict[tuple[str, str | None], set[str]] = {}
    if subject_type == "user":
        for key, actions in desired_map.items():
            inherited_actions = role_map.get(key, set())
            remaining = set(actions) - set(inherited_actions)
            if remaining:
                direct_map[key] = remaining
    else:
        direct_map = desired_map

    existing = (
        db.query(models.PermissionGrant)
        .filter(
            models.PermissionGrant.subject_type == subject_type,
            models.PermissionGrant.subject_id == subject_id,
            models.PermissionGrant.scope == scope,
        )
        .all()
    )
    existing_keys = {(grant.resource_type, grant.resource_id, grant.action): grant for grant in existing}

    desired_keys: set[tuple[str, str | None, str]] = set()
    for (resource_type, resource_id), actions in direct_map.items():
        for action in actions:
            desired_keys.add((resource_type, resource_id, action))

    for key, grant in existing_keys.items():
        if key not in desired_keys:
            db.delete(grant)

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

    db.commit()

    return get_subject_permissions(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        current_user=current_user,
        db=db,
    )

@router.post("/permissions", response_model=schemas.PermissionGrantOut, status_code=201)
def create_permission_grant(
    payload: schemas.PermissionGrantCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PermissionGrantOut:
    _require_menu_manage(current_user, db)
    if payload.scope == "menu" and payload.resource_type != "menu":
        raise HTTPException(status_code=400, detail="Menu scope requires resource_type=menu")
    if payload.scope == "resource" and payload.resource_type not in {"agent", "model", "agent_group"}:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    if payload.resource_type == "agent_group" and payload.resource_id:
        group = (
            db.query(models.AgentGroup)
            .filter(models.AgentGroup.name == payload.resource_id)
            .first()
        )
        if not group:
            raise HTTPException(status_code=404, detail="Agent group not found")
    if payload.subject_type == "role":
        _ensure_role_exists(db, payload.subject_id)
        _assert_permission_editable(current_user, target_role=payload.subject_id)
    if payload.subject_type == "user":
        try:
            user_id = int(payload.subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user id") from exc
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        _assert_permission_editable(current_user, target_user=user)

    existing = (
        db.query(models.PermissionGrant)
        .filter(
            models.PermissionGrant.subject_type == payload.subject_type,
            models.PermissionGrant.subject_id == payload.subject_id,
            models.PermissionGrant.scope == payload.scope,
            models.PermissionGrant.resource_type == payload.resource_type,
            models.PermissionGrant.resource_id == payload.resource_id,
            models.PermissionGrant.action == payload.action,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Permission already granted")

    grant = models.PermissionGrant(**payload.model_dump())
    db.add(grant)
    db.commit()
    db.refresh(grant)
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


@router.delete("/permissions/{grant_id}")
def delete_permission_grant(
    grant_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_menu_manage(current_user, db)
    grant = db.query(models.PermissionGrant).filter(models.PermissionGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Permission grant not found")
    if grant.subject_type == "role":
        _assert_permission_editable(current_user, target_role=grant.subject_id)
    if grant.subject_type == "user":
        try:
            target_id = int(grant.subject_id)
        except ValueError:
            target_id = None
        if target_id is not None:
            target_user = db.query(models.User).filter(models.User.id == target_id).first()
            if target_user:
                _assert_permission_editable(current_user, target_user=target_user)
    db.delete(grant)
    db.commit()
    return {"status": "deleted"}


@router.post("/models", response_model=schemas.ModelDetail, status_code=201)
def create_model(
    payload: schemas.ModelCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    _require_menu_edit(current_user, db, "models")
    if not has_permission(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="model",
        resource_id=payload.id,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    existing = db.query(models.Model).filter(models.Model.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")

    model = models.Model(**payload.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    return model_detail(model)


@router.put("/models/{model_id}", response_model=schemas.ModelDetail)
def update_model(
    model_id: str,
    payload: schemas.ModelUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    _require_menu_edit(current_user, db, "models")
    if not has_permission(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="model",
        resource_id=model_id,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if payload.name is not None:
        model.name = payload.name
    if payload.provider is not None:
        model.provider = payload.provider
    if payload.status is not None:
        model.status = payload.status
    if payload.context_length is not None:
        model.context_length = payload.context_length
    if payload.description is not None:
        model.description = payload.description
    if payload.pricing is not None:
        model.pricing = payload.pricing
    if payload.release is not None:
        model.release = payload.release
    if payload.tags is not None:
        model.tags = payload.tags

    db.commit()
    db.refresh(model)
    return model_detail(model)


@router.post("/agents", response_model=schemas.AgentDetail, status_code=201)
def create_agent(
    payload: schemas.AgentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    _require_menu_edit(current_user, db, "agents")
    groups = _normalize_groups(payload.groups)
    _ensure_agent_groups(db, groups)
    if not (
        has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent",
            resource_id=None,
        )
        or any(
            has_permission(
                db,
                current_user,
                action="edit",
                scope="resource",
                resource_type="agent_group",
                resource_id=group,
            )
            for group in groups
        )
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    existing = db.query(models.Agent).filter(models.Agent.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = models.Agent(
        id=uuid4().hex,
        name=payload.name,
        status=payload.status,
        owner=payload.owner,
        last_run=payload.last_run,
        url=payload.url,
        description=payload.description,
        group_name=groups[0] if groups else "",
        groups=groups,
        source_payload={},
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent_detail(agent)


@router.put("/agents/{agent_id}", response_model=schemas.AgentDetail)
def update_agent(
    agent_id: str,
    payload: schemas.AgentUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    _require_menu_edit(current_user, db, "agents")
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    has_group_permission = any(
        has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        )
        for group in groups
    )
    if not (
        has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent",
            resource_id=agent_id,
        )
        or has_group_permission
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.url and payload.url != agent.url:
        existing = db.query(models.Agent).filter(models.Agent.url == payload.url).first()
        if existing:
            raise HTTPException(status_code=409, detail="Agent url already exists")
        agent.url = payload.url

    if payload.name is not None:
        agent.name = payload.name
    if payload.status is not None:
        agent.status = payload.status
    if payload.owner is not None:
        agent.owner = payload.owner
    if payload.last_run is not None:
        agent.last_run = payload.last_run
    if payload.description is not None:
        agent.description = payload.description
    if payload.groups is not None:
        groups = _normalize_groups(payload.groups)
        if groups:
            allowed = has_permission(
                db,
                current_user,
                action="edit",
                scope="resource",
                resource_type="agent",
                resource_id=None,
            ) or any(
                has_permission(
                    db,
                    current_user,
                    action="edit",
                    scope="resource",
                    resource_type="agent_group",
                    resource_id=group,
                )
                for group in groups
            )
        else:
            allowed = has_permission(
                db,
                current_user,
                action="edit",
                scope="resource",
                resource_type="agent",
                resource_id=None,
            )
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        _ensure_agent_groups(db, groups)
        agent.groups = groups
        agent.group_name = groups[0] if groups else ""

    db.commit()
    db.refresh(agent)
    return agent_detail(agent)


@router.post("/agents/import", response_model=schemas.AgentImportResponse)
def import_agents(
    payload: schemas.AgentImportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentImportResponse:
    _require_menu_edit(current_user, db, "agents")
    try:
        response = httpx.post(
            payload.api_url,
            json={"ak": payload.ak, "sk": payload.sk},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch agent data") from exc

    if isinstance(data, dict):
        items = data.get("data") or data.get("items") or data
    else:
        items = data

    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Unexpected response format")

    imported = 0
    result_agents: list[schemas.AgentDetail] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url") or item.get("link")
        if not url:
            continue

        name = item.get("name") or item.get("title") or f"Agent {idx + 1}"
        status_value = item.get("status") or "active"
        owner = item.get("owner") or "external"
        description = item.get("description") or ""
        raw_groups = item.get("groups")
        if isinstance(raw_groups, list):
            groups = _normalize_groups([str(group) for group in raw_groups])
        else:
            group_name = item.get("group") or item.get("group_name")
            if not group_name and isinstance(item.get("tags"), list) and item.get("tags"):
                group_name = item.get("tags")[0]
            groups = _normalize_groups([str(group_name)]) if group_name else []
        last_run = item.get("last_run") or item.get("lastRun") or ""

        if not (
            has_permission(
                db,
                current_user,
                action="edit",
                scope="resource",
                resource_type="agent",
                resource_id=None,
            )
            or any(
                has_permission(
                    db,
                    current_user,
                    action="edit",
                    scope="resource",
                    resource_type="agent_group",
                    resource_id=group,
                )
                for group in groups
            )
        ):
            raise HTTPException(status_code=403, detail="Forbidden")

        _ensure_agent_groups(db, groups)

        agent = db.query(models.Agent).filter(models.Agent.url == url).first()
        if not agent:
            agent = models.Agent(
                id=uuid4().hex,
                name=name,
                status=status_value,
                owner=owner,
                last_run=last_run,
                url=url,
                description=description,
                group_name=groups[0] if groups else "",
                groups=groups,
                source_payload=item,
            )
            db.add(agent)
        else:
            agent.name = name
            agent.status = status_value
            agent.owner = owner
            agent.last_run = last_run
            agent.description = description
            agent.group_name = groups[0] if groups else ""
            agent.groups = groups
            agent.source_payload = item

        imported += 1
        result_agents.append(agent_detail(agent))

    db.commit()

    return schemas.AgentImportResponse(imported=imported, agents=result_agents)
