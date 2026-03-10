from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas, security
from ...auth import get_current_user
from ...db import get_db
from ...permissions import get_user_role_names_async, require_manage_menu_async, require_menu_action_async
from .common import normalize_roles

router = APIRouter()


def _admin_user_out(user: models.User, roles: list[str], bound_providers: list[str]) -> schemas.AdminUserOut:
    return schemas.AdminUserOut(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        roles=roles,
        status=user.status,
        source=user.source,
        source_provider=user.source_provider or "local",
        workspace=user.workspace,
        bound_providers=bound_providers,
        created_at=user.created_at,
    )


async def _fetch_user_roles_map(db: AsyncSession, user_ids: list[int]) -> dict[int, list[str]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(models.UserRole.user_id, models.UserRole.role_name)
            .where(models.UserRole.user_id.in_(user_ids))
            .order_by(models.UserRole.user_id.asc(), models.UserRole.role_name.asc())
        )
    ).all()
    grouped: dict[int, list[str]] = {user_id: [] for user_id in user_ids}
    for user_id, role_name in rows:
        grouped.setdefault(int(user_id), []).append(str(role_name))
    return grouped


async def _fetch_bound_providers_map(db: AsyncSession, user_ids: list[int]) -> dict[int, list[str]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(models.UserSsoBinding.user_id, models.UserSsoBinding.provider_key)
            .where(models.UserSsoBinding.user_id.in_(user_ids))
            .order_by(models.UserSsoBinding.user_id.asc(), models.UserSsoBinding.provider_key.asc())
        )
    ).all()
    grouped: dict[int, list[str]] = {user_id: [] for user_id in user_ids}
    for user_id, provider_key in rows:
        grouped.setdefault(int(user_id), []).append(str(provider_key))
    return grouped


async def _ensure_roles_exist(db: AsyncSession, role_names: list[str]) -> None:
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")
    existing = set(
        (
            await db.execute(
                select(models.Role.name).where(models.Role.name.in_(role_names))
            )
        ).scalars().all()
    )
    missing = [name for name in role_names if name not in existing]
    if missing:
        raise HTTPException(status_code=400, detail=f"Role not found: {', '.join(missing)}")


async def _ensure_role_exists(db: AsyncSession, role_name: str) -> None:
    role = (
        await db.execute(select(models.Role.id).where(models.Role.name == role_name))
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")


async def _set_user_roles(db: AsyncSession, user: models.User, role_names: list[str]) -> list[str]:
    role_names = normalize_roles(roles=role_names)
    if user.account == "admin":
        role_names = ["admin"]
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")

    await _ensure_roles_exist(db, role_names)

    existing_rows = (
        await db.execute(select(models.UserRole).where(models.UserRole.user_id == user.id))
    ).scalars().all()
    existing = {row.role_name for row in existing_rows}
    expected = set(role_names)

    for row in existing_rows:
        if row.role_name not in expected:
            await db.delete(row)
    for role_name in role_names:
        if role_name in existing:
            continue
        db.add(models.UserRole(user_id=user.id, role_name=role_name))

    user.role = "admin" if user.account == "admin" or "admin" in role_names else role_names[0]
    return role_names


@router.get("/users", response_model=list[schemas.AdminUserOut])
async def list_users(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AdminUserOut]:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    users = (await db.execute(select(models.User).order_by(models.User.id.asc()))).scalars().all()
    user_ids = [user.id for user in users]
    role_map = await _fetch_user_roles_map(db, user_ids)
    binding_map = await _fetch_bound_providers_map(db, user_ids)
    return [
        _admin_user_out(
            user,
            role_map.get(user.id, [user.role] if user.role else []),
            binding_map.get(user.id, []),
        )
        for user in users
    ]


@router.post("/users", response_model=schemas.AdminUserOut, status_code=201)
async def create_user(
    payload: schemas.AdminUserCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AdminUserOut:
    await require_manage_menu_async(db, current_user)
    role_names = normalize_roles(role=payload.role, roles=payload.roles)
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")
    await _ensure_roles_exist(db, role_names)

    existing = (
        await db.execute(select(models.User).where(models.User.account == payload.account))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Account already registered")

    email_existing = (
        await db.execute(select(models.User).where(models.User.email == payload.email))
    ).scalar_one_or_none()
    if email_existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    username_existing = (
        await db.execute(select(models.User).where(models.User.username == payload.username))
    ).scalar_one_or_none()
    if username_existing:
        raise HTTPException(status_code=409, detail="Username already registered")

    user = models.User(
        account=payload.account,
        username=payload.username,
        email=payload.email,
        password_hash=await security.hash_password_async(payload.password),
        role=role_names[0],
        status=payload.status or "active",
        source=payload.source or "local",
        source_provider=payload.source_provider or payload.source or "local",
        source_subject="",
        workspace=payload.workspace or "default",
    )
    db.add(user)
    await db.flush()
    assigned_roles = await _set_user_roles(db, user, role_names)
    await db.commit()
    await db.refresh(user)
    return _admin_user_out(user, assigned_roles, [])


@router.put("/users/{user_id}", response_model=schemas.AdminUserOut)
async def update_user(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AdminUserOut:
    await require_manage_menu_async(db, current_user)
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.account and payload.account != user.account:
        existing = (
            await db.execute(select(models.User).where(models.User.account == payload.account))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Account already registered")
        user.account = payload.account

    if payload.username and payload.username != user.username:
        existing = (
            await db.execute(select(models.User).where(models.User.username == payload.username))
        ).scalar_one_or_none()
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Username already registered")
        user.username = payload.username

    if payload.email and payload.email != user.email:
        existing = (
            await db.execute(select(models.User).where(models.User.email == payload.email))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        user.email = payload.email

    if payload.role is not None or payload.roles is not None:
        requested_roles = ["admin"] if user.account == "admin" else normalize_roles(
            role=payload.role, roles=payload.roles
        )
        if not requested_roles:
            raise HTTPException(status_code=400, detail="At least one role is required")
        await _set_user_roles(db, user, requested_roles)

    if payload.status:
        if user.account == "admin":
            raise HTTPException(status_code=400, detail="Admin status cannot be changed")
        user.status = payload.status

    if payload.source:
        user.source = payload.source
    if payload.source_provider:
        user.source_provider = payload.source_provider
    if payload.workspace:
        user.workspace = payload.workspace
    if payload.password:
        user.password_hash = await security.hash_password_async(payload.password)

    await db.commit()
    await db.refresh(user)
    bound_providers = (
        await db.execute(
            select(models.UserSsoBinding.provider_key)
            .where(models.UserSsoBinding.user_id == user.id)
            .order_by(models.UserSsoBinding.provider_key.asc())
        )
    ).scalars().all()
    return _admin_user_out(user, await get_user_role_names_async(db, user), [str(item) for item in bound_providers])


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.account == "admin":
        raise HTTPException(status_code=400, detail="Admin account cannot be deleted")

    await db.execute(
        delete(models.PermissionGrant).where(
            models.PermissionGrant.subject_type == "user",
            models.PermissionGrant.subject_id == str(user_id),
        )
    )
    await db.execute(delete(models.UserRole).where(models.UserRole.user_id == user_id))
    await db.execute(delete(models.UserSsoBinding).where(models.UserSsoBinding.user_id == user_id))
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    payload: schemas.AdminResetPasswordRequest | None = None,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = (payload.password if payload and payload.password else None) or "agentui@2025"
    user.password_hash = await security.hash_password_async(new_password)
    await db.commit()
    return {"status": "ok", "password": new_password}


@router.get("/roles", response_model=list[schemas.RoleOut])
async def list_roles(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.RoleOut]:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    roles = (await db.execute(select(models.Role).order_by(models.Role.id.asc()))).scalars().all()
    return [schemas.RoleOut(id=role.id, name=role.name, description=role.description) for role in roles]


@router.post("/roles", response_model=schemas.RoleOut, status_code=201)
async def create_role(
    payload: schemas.RoleCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleOut:
    await require_manage_menu_async(db, current_user)
    existing = (
        await db.execute(select(models.Role).where(models.Role.name == payload.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Role already exists")
    role = models.Role(name=payload.name, description=payload.description or "")
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return schemas.RoleOut(id=role.id, name=role.name, description=role.description)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    role = await db.get(models.Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Protected role cannot be deleted")

    affected_user_ids = list(
        (
            await db.execute(
                select(models.UserRole.user_id).where(models.UserRole.role_name == role.name)
            )
        ).scalars().all()
    )

    await db.execute(
        delete(models.PermissionGrant).where(
            models.PermissionGrant.subject_type == "role",
            models.PermissionGrant.subject_id == role.name,
        )
    )
    await db.execute(delete(models.UserRole).where(models.UserRole.role_name == role.name))

    if affected_user_ids:
        await _ensure_role_exists(db, "user")
        links = (
            await db.execute(
                select(models.UserRole.user_id, models.UserRole.role_name)
                .where(models.UserRole.user_id.in_(affected_user_ids))
                .order_by(models.UserRole.user_id.asc(), models.UserRole.role_name.asc())
            )
        ).all()
        role_map: dict[int, list[str]] = {user_id: [] for user_id in affected_user_ids}
        for user_id, role_name in links:
            role_map.setdefault(int(user_id), []).append(str(role_name))

        users = (
            await db.execute(select(models.User).where(models.User.id.in_(affected_user_ids)))
        ).scalars().all()
        for user in users:
            assigned = role_map.get(user.id, [])
            if user.account == "admin":
                if "admin" not in assigned:
                    db.add(models.UserRole(user_id=user.id, role_name="admin"))
                user.role = "admin"
                continue
            if not assigned:
                db.add(models.UserRole(user_id=user.id, role_name="user"))
                assigned = ["user"]
            user.role = assigned[0]

    await db.delete(role)
    await db.commit()
    return {"status": "deleted"}


@router.get("/agent-groups", response_model=list[schemas.AgentGroupOut])
async def list_agent_groups(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AgentGroupOut]:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    groups = (
        await db.execute(select(models.AgentGroup).order_by(models.AgentGroup.name.asc()))
    ).scalars().all()
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
async def create_agent_group(
    payload: schemas.AgentGroupCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentGroupOut:
    await require_manage_menu_async(db, current_user)
    existing = (
        await db.execute(select(models.AgentGroup).where(models.AgentGroup.name == payload.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Group already exists")
    group = models.AgentGroup(name=payload.name, description=payload.description or "")
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return schemas.AgentGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
    )


@router.put("/agent-groups/{group_id}", response_model=schemas.AgentGroupOut)
async def update_agent_group(
    group_id: int,
    payload: schemas.AgentGroupUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentGroupOut:
    await require_manage_menu_async(db, current_user)
    group = await db.get(models.AgentGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.name and payload.name != group.name:
        existing = (
            await db.execute(select(models.AgentGroup).where(models.AgentGroup.name == payload.name))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Group already exists")
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    await db.commit()
    await db.refresh(group)
    return schemas.AgentGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
    )


@router.delete("/agent-groups/{group_id}")
async def delete_agent_group(
    group_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    group = await db.get(models.AgentGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    group_name = group.name
    agents = (await db.execute(select(models.Agent))).scalars().all()
    for agent in agents:
        if group_name in (agent.groups or []):
            agent.groups = [g for g in (agent.groups or []) if g != group_name]
            agent.group_name = agent.groups[0] if agent.groups else ""
    await db.delete(group)
    await db.commit()
    return {"status": "deleted"}
