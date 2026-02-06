from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import PermissionGrant, User

MENU_IDS = {"agents", "models", "admin"}
RESOURCE_TYPES = {"agent", "model", "agent_group"}

ACTION_ORDER = {
    "view": 1,
    "edit": 2,
    "manage": 3,
}


def _action_allows(granted: str, requested: str) -> bool:
    return ACTION_ORDER.get(granted, 0) >= ACTION_ORDER.get(requested, 0)


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


def _user_subject_ids(user: User) -> tuple[str, str | None]:
    return str(user.id), user.role


def get_user_grants(db: Session, user: User) -> Iterable[PermissionGrant]:
    user_id, role_name = _user_subject_ids(user)
    user_clause = (PermissionGrant.subject_type == "user") & (
        PermissionGrant.subject_id == user_id
    )
    if role_name:
        role_clause = (PermissionGrant.subject_type == "role") & (
            PermissionGrant.subject_id == role_name
        )
        return db.query(PermissionGrant).filter(or_(user_clause, role_clause)).all()
    return db.query(PermissionGrant).filter(user_clause).all()


def has_permission(
    db: Session,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> bool:
    if user.role == "admin":
        return True

    grants = get_user_grants(db, user)
    for grant in grants:
        if not _matches_resource(
            grant, scope=scope, resource_type=resource_type, resource_id=resource_id
        ):
            continue
        if _action_allows(grant.action, action):
            return True
    return False


def require_permission(
    db: Session,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> None:
    if not has_permission(
        db, user, action=action, scope=scope, resource_type=resource_type, resource_id=resource_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def require_manage_menu(db: Session, user: User) -> None:
    require_menu_action(db, user, action="manage", menu_id="admin")


def require_menu_action(db: Session, user: User, *, action: str, menu_id: str) -> None:
    if user.role == "admin":
        return
    if not has_permission(
        db, user, action=action, scope="menu", resource_type="menu", resource_id=menu_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def summarize_permissions(db: Session, user: User) -> dict:
    if user.role == "admin":
        return {
            "menus": [
                {"menu_id": menu_id, "actions": ["view", "edit", "manage"]}
                for menu_id in sorted(MENU_IDS)
            ],
            "resources": [
                {"resource_type": resource_type, "resource_id": None, "actions": ["view", "edit", "manage"]}
                for resource_type in sorted(RESOURCE_TYPES)
            ],
        }

    grants = get_user_grants(db, user)
    menu_actions: dict[str, set[str]] = {}
    resource_actions: dict[tuple[str, str | None], set[str]] = {}

    for grant in grants:
        if grant.scope == "menu" and grant.resource_type == "menu":
            menu_id = grant.resource_id or ""
            if menu_id:
                menu_actions.setdefault(menu_id, set()).add(grant.action)
            continue

        if grant.scope == "resource":
            key = (grant.resource_type, grant.resource_id)
            resource_actions.setdefault(key, set()).add(grant.action)

    menus = [
        {"menu_id": menu_id, "actions": _sorted_actions(actions)}
        for menu_id, actions in menu_actions.items()
        if menu_id in MENU_IDS
    ]
    resources = [
        {"resource_type": resource_type, "resource_id": resource_id, "actions": _sorted_actions(actions)}
        for (resource_type, resource_id), actions in resource_actions.items()
        if resource_type in RESOURCE_TYPES
    ]
    return {"menus": menus, "resources": resources}


def _sorted_actions(actions: set[str]) -> list[str]:
    return sorted(actions, key=lambda item: ACTION_ORDER.get(item, 0))
