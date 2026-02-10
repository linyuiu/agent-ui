from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ... import models, schemas, security
from ...auth import get_current_user
from ...db import get_db
from ...permissions import get_user_role_names
from .common import (
    ensure_role_exists,
    ensure_roles_exist,
    fetch_user_roles_map,
    normalize_roles,
    require_menu_manage,
    require_menu_view,
    set_user_roles,
)

router = APIRouter()


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AdminUserOut]:
    require_menu_view(current_user, db, "admin")
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    role_map = fetch_user_roles_map(db, [user.id for user in users])
    return [
        schemas.AdminUserOut(
            id=user.id,
            account=user.account,
            username=user.username,
            email=user.email,
            role=user.role,
            roles=role_map.get(user.id, [user.role] if user.role else []),
            status=user.status,
            source=user.source,
            source_provider=user.source_provider or "local",
            source_subject=user.source_subject or "",
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
    require_menu_manage(current_user, db)
    role_names = normalize_roles(role=payload.role, roles=payload.roles)
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")
    ensure_roles_exist(db, role_names)

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
        role=role_names[0],
        status=payload.status or "active",
        source=payload.source or "local",
        source_provider=payload.source_provider or payload.source or "local",
        source_subject="",
        workspace=payload.workspace or "default",
    )
    db.add(user)
    db.flush()
    set_user_roles(db, user, role_names)
    db.commit()
    db.refresh(user)
    assigned_roles = get_user_role_names(db, user)
    return schemas.AdminUserOut(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        roles=assigned_roles,
        status=user.status,
        source=user.source,
        source_provider=user.source_provider or "local",
        source_subject=user.source_subject or "",
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
    require_menu_manage(current_user, db)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.account and payload.account != user.account:
        existing = db.query(models.User).filter(models.User.account == payload.account).first()
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

    if payload.role is not None or payload.roles is not None:
        if user.account == "admin":
            requested_roles = ["admin"]
        else:
            requested_roles = normalize_roles(role=payload.role, roles=payload.roles)
            if not requested_roles:
                raise HTTPException(status_code=400, detail="At least one role is required")
        set_user_roles(db, user, requested_roles)

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
        user.password_hash = security.hash_password(payload.password)

    db.commit()
    db.refresh(user)
    assigned_roles = get_user_role_names(db, user)

    return schemas.AdminUserOut(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        roles=assigned_roles,
        status=user.status,
        source=user.source,
        source_provider=user.source_provider or "local",
        source_subject=user.source_subject or "",
        workspace=user.workspace,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_menu_manage(current_user, db)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.account == "admin":
        raise HTTPException(status_code=400, detail="Admin account cannot be deleted")
    db.query(models.PermissionGrant).filter(
        models.PermissionGrant.subject_type == "user",
        models.PermissionGrant.subject_id == str(user_id),
    ).delete(synchronize_session=False)
    db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete(
        synchronize_session=False
    )
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
    require_menu_manage(current_user, db)
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
    require_menu_view(current_user, db, "admin")
    roles = db.query(models.Role).order_by(models.Role.id.asc()).all()
    return [schemas.RoleOut(id=role.id, name=role.name, description=role.description) for role in roles]


@router.post("/roles", response_model=schemas.RoleOut, status_code=201)
def create_role(
    payload: schemas.RoleCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.RoleOut:
    require_menu_manage(current_user, db)
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
    require_menu_manage(current_user, db)
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Protected role cannot be deleted")

    affected_user_ids = [
        user_id
        for (user_id,) in db.query(models.UserRole.user_id)
        .filter(models.UserRole.role_name == role.name)
        .all()
    ]

    db.query(models.PermissionGrant).filter(
        models.PermissionGrant.subject_type == "role",
        models.PermissionGrant.subject_id == role.name,
    ).delete(synchronize_session=False)
    db.query(models.UserRole).filter(models.UserRole.role_name == role.name).delete(
        synchronize_session=False
    )
    db.query(models.User).filter(models.User.role == role.name).update(
        {models.User.role: "user"},
        synchronize_session=False,
    )

    if affected_user_ids:
        ensure_role_exists(db, "user")
        links = (
            db.query(models.UserRole.user_id, models.UserRole.role_name)
            .filter(models.UserRole.user_id.in_(affected_user_ids))
            .order_by(models.UserRole.user_id.asc(), models.UserRole.role_name.asc())
            .all()
        )
        role_map: dict[int, list[str]] = {user_id: [] for user_id in affected_user_ids}
        for user_id, role_name in links:
            role_map.setdefault(user_id, []).append(role_name)

        users = db.query(models.User).filter(models.User.id.in_(affected_user_ids)).all()
        for user in users:
            assigned = role_map.get(user.id, [])
            if user.account == "admin":
                if "admin" not in assigned:
                    db.add(models.UserRole(user_id=user.id, role_name="admin"))
                assigned = ["admin"]
            elif not assigned:
                assigned = ["user"]
                db.add(models.UserRole(user_id=user.id, role_name="user"))
            user.role = assigned[0]

    db.delete(role)
    db.commit()
    return {"status": "deleted"}


@router.get("/agent-groups", response_model=list[schemas.AgentGroupOut])
def list_agent_groups(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentGroupOut]:
    require_menu_view(current_user, db, "admin")
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
    require_menu_manage(current_user, db)
    existing = db.query(models.AgentGroup).filter(models.AgentGroup.name == payload.name).first()
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
    require_menu_manage(current_user, db)
    group = db.query(models.AgentGroup).filter(models.AgentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.name and payload.name != group.name:
        existing = db.query(models.AgentGroup).filter(models.AgentGroup.name == payload.name).first()
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
    require_menu_manage(current_user, db)
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
