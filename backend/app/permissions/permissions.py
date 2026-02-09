from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import PermissionGrant, User, UserRole
from .engine import (
    ACTION_BITS,
    ACTION_ORDER,
    PermissionAccess,
    PermissionDecision,
    PermissionRequest,
    access_allows as engine_access_allows,
    build_access_map as engine_build_access_map,
    get_permission_engine,
)

MENU_IDS = {"agents", "models", "admin"}
RESOURCE_TYPES = {"agent", "model", "agent_group"}
SUPER_ADMIN_ACCOUNT = "admin"

def is_super_admin(user: User) -> bool:
    return (user.account or "").strip() == SUPER_ADMIN_ACCOUNT


def _normalize_role_names(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


def get_user_role_names(db: Session, user: User) -> list[str]:
    cache_key = f"user_roles:{user.id}"
    cached = db.info.get(cache_key)
    if cached is not None:
        return cached

    rows = (
        db.query(UserRole.role_name)
        .filter(UserRole.user_id == user.id)
        .order_by(UserRole.role_name.asc())
        .all()
    )
    role_names = _normalize_role_names(name for (name,) in rows)
    if not role_names:
        fallback = (user.role or "user").strip() or "user"
        role_names = [fallback]

    db.info[cache_key] = role_names
    return role_names


def has_role(db: Session, user: User, role_name: str) -> bool:
    return role_name in set(get_user_role_names(db, user))


def _mask_to_actions(mask: int) -> list[str]:
    actions: list[str] = []
    if mask & ACTION_BITS["view"]:
        actions.append("view")
    if mask & ACTION_BITS["edit"]:
        actions.append("edit")
    if mask & ACTION_BITS["manage"]:
        actions.append("manage")
    return actions


def _build_access_map(grants: Iterable[PermissionGrant]) -> PermissionAccess:
    return engine_build_access_map(grants)


def _access_allows(
    access: PermissionAccess,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None,
) -> bool:
    request = PermissionRequest(
        action=action,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return engine_access_allows(access, request).allowed


def _matches_resource(
    grant: PermissionGrant,
    *,
    scope: str,
    resource_type: str,
    resource_id: str | None,
) -> bool:
    if grant.scope != scope:
        return False
    if grant.resource_type != resource_type:
        return False
    if grant.resource_id is None:
        return True
    return grant.resource_id == resource_id


def _action_allows(granted: str, requested: str) -> bool:
    return ACTION_ORDER.get(granted, 0) >= ACTION_ORDER.get(requested, 0)


def has_permission_from_grants(
    grants: Iterable[PermissionGrant],
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> bool:
    # Fast path: use the compact access map.
    access = _build_access_map(grants)
    if _access_allows(
        access,
        action=action,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
    ):
        return True

    # Backward compatible path for non-standard grant values.
    for grant in grants:
        if not _matches_resource(
            grant, scope=scope, resource_type=resource_type, resource_id=resource_id
        ):
            continue
        if _action_allows(grant.action, action):
            return True
    return False


def build_view_access(grants: Iterable[PermissionGrant]) -> PermissionAccess:
    return _build_access_map(grants)


def can_view_menu(access: PermissionAccess, menu_id: str) -> bool:
    return _access_allows(
        access,
        action="view",
        scope="menu",
        resource_type="menu",
        resource_id=menu_id,
    )


def can_view_agent(access: PermissionAccess, agent_id: str, groups: list[str]) -> bool:
    if _access_allows(
        access,
        action="view",
        scope="resource",
        resource_type="agent",
        resource_id=agent_id,
    ):
        return True

    if _access_allows(
        access,
        action="view",
        scope="resource",
        resource_type="agent_group",
        resource_id=None,
    ):
        return True

    for group in groups:
        if _access_allows(
            access,
            action="view",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        ):
            return True
    return False


def can_view_model(access: PermissionAccess, model_id: str) -> bool:
    return _access_allows(
        access,
        action="view",
        scope="resource",
        resource_type="model",
        resource_id=model_id,
    )


def get_user_grants(db: Session, user: User) -> list[PermissionGrant]:
    role_names = get_user_role_names(db, user)
    role_key = ",".join(sorted(role_names))
    cache_key = f"perm_grants:{user.id}:{role_key}"
    cached = db.info.get(cache_key)
    if cached is not None:
        return cached

    user_clause = (PermissionGrant.subject_type == "user") & (
        PermissionGrant.subject_id == str(user.id)
    )
    role_clause = (PermissionGrant.subject_type == "role") & (
        PermissionGrant.subject_id.in_(role_names)
    )
    grants = db.query(PermissionGrant).filter(or_(user_clause, role_clause)).all()
    db.info[cache_key] = grants
    return grants


def get_user_access(db: Session, user: User) -> PermissionAccess:
    if is_super_admin(user):
        return {}

    role_names = get_user_role_names(db, user)
    role_key = ",".join(sorted(role_names))
    cache_key = f"perm_access:{user.id}:{role_key}"
    cached = db.info.get(cache_key)
    if cached is not None:
        return cached

    grants = get_user_grants(db, user)
    access = _build_access_map(grants)
    db.info[cache_key] = access
    return access


def evaluate_permission(
    db: Session,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_attrs: dict | None = None,
    subject_attrs: dict | None = None,
) -> PermissionDecision:
    request = PermissionRequest(
        action=action,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
        subject_id=str(user.id),
        subject_roles=tuple(get_user_role_names(db, user)),
        subject_attrs=subject_attrs or {},
        resource_attrs=resource_attrs or {},
    )
    engine = get_permission_engine()
    return engine.evaluate(
        request=request,
        grants=get_user_grants(db, user),
        access=get_user_access(db, user),
        super_admin=is_super_admin(user),
    )


def has_permission(
    db: Session,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> bool:
    decision = evaluate_permission(
        db,
        user,
        action=action,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return decision.allowed


def require_permission(
    db: Session,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> None:
    decision = evaluate_permission(
        db,
        user,
        action=action,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def require_manage_menu(db: Session, user: User) -> None:
    require_menu_action(db, user, action="manage", menu_id="admin")


def require_menu_action(db: Session, user: User, *, action: str, menu_id: str) -> None:
    if is_super_admin(user):
        return
    if menu_id not in MENU_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid menu",
        )
    if not has_permission(
        db,
        user,
        action=action,
        scope="menu",
        resource_type="menu",
        resource_id=menu_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def summarize_permissions(db: Session, user: User) -> dict:
    if is_super_admin(user):
        return {
            "menus": [
                {"menu_id": menu_id, "actions": ["view", "edit", "manage"]}
                for menu_id in sorted(MENU_IDS)
            ],
            "resources": [
                {
                    "resource_type": resource_type,
                    "resource_id": None,
                    "actions": ["view", "edit", "manage"],
                }
                for resource_type in sorted(RESOURCE_TYPES)
            ],
        }

    access = get_user_access(db, user)

    menus: list[dict] = []
    for menu_id in sorted(MENU_IDS):
        specific_key = ("menu", "menu", menu_id)
        wildcard_key = ("menu", "menu", None)
        mask = access.get(specific_key, 0) | access.get(wildcard_key, 0)
        if mask:
            menus.append({"menu_id": menu_id, "actions": _mask_to_actions(mask)})

    resources: list[dict] = []
    for (scope, resource_type, resource_id), mask in sorted(
        access.items(), key=lambda item: (item[0][1], item[0][2] or "")
    ):
        if scope != "resource" or resource_type not in RESOURCE_TYPES or not mask:
            continue
        resources.append(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "actions": _mask_to_actions(mask),
            }
        )

    return {"menus": menus, "resources": resources}


def _sorted_actions(actions: set[str]) -> list[str]:
    return sorted(actions, key=lambda item: ACTION_ORDER.get(item, 0))
