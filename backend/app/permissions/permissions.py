from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..models import Agent, AgentGroup, Model, PermissionGrant, User, UserRole
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


def _session_info(db: Session | AsyncSession) -> dict:
    info = getattr(db, "info", None)
    if info is not None:
        return info
    return db.sync_session.info

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
    cached = _session_info(db).get(cache_key)
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

    _session_info(db)[cache_key] = role_names
    return role_names


async def get_user_role_names_async(db: AsyncSession, user: User) -> list[str]:
    cache_key = f"user_roles:{user.id}"
    info = _session_info(db)
    cached = info.get(cache_key)
    if cached is not None:
        return cached

    rows = (
        await db.execute(
            select(UserRole.role_name)
            .where(UserRole.user_id == user.id)
            .order_by(UserRole.role_name.asc())
        )
    ).all()
    role_names = _normalize_role_names(name for (name,) in rows)
    if not role_names:
        fallback = (user.role or "user").strip() or "user"
        role_names = [fallback]

    info[cache_key] = role_names
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
    cached = _session_info(db).get(cache_key)
    if cached is not None:
        return cached

    user_clause = (PermissionGrant.subject_type == "user") & (
        PermissionGrant.subject_id == str(user.id)
    )
    role_clause = (PermissionGrant.subject_type == "role") & (
        PermissionGrant.subject_id.in_(role_names)
    )
    grants = db.query(PermissionGrant).filter(or_(user_clause, role_clause)).all()
    _session_info(db)[cache_key] = grants
    return grants


async def get_user_grants_async(db: AsyncSession, user: User) -> list[PermissionGrant]:
    role_names = await get_user_role_names_async(db, user)
    role_key = ",".join(sorted(role_names))
    cache_key = f"perm_grants:{user.id}:{role_key}"
    info = _session_info(db)
    cached = info.get(cache_key)
    if cached is not None:
        return cached

    user_clause = (PermissionGrant.subject_type == "user") & (
        PermissionGrant.subject_id == str(user.id)
    )
    role_clause = (PermissionGrant.subject_type == "role") & (
        PermissionGrant.subject_id.in_(role_names)
    )
    grants = (await db.execute(select(PermissionGrant).where(or_(user_clause, role_clause)))).scalars().all()
    info[cache_key] = grants
    return grants


def get_user_access(db: Session, user: User) -> PermissionAccess:
    if is_super_admin(user):
        return {}

    role_names = get_user_role_names(db, user)
    role_key = ",".join(sorted(role_names))
    cache_key = f"perm_access:{user.id}:{role_key}"
    cached = _session_info(db).get(cache_key)
    if cached is not None:
        return cached

    grants = get_user_grants(db, user)
    access = _build_access_map(grants)
    _session_info(db)[cache_key] = access
    return access


async def get_user_access_async(db: AsyncSession, user: User) -> PermissionAccess:
    if is_super_admin(user):
        return {}

    role_names = await get_user_role_names_async(db, user)
    role_key = ",".join(sorted(role_names))
    cache_key = f"perm_access:{user.id}:{role_key}"
    info = _session_info(db)
    cached = info.get(cache_key)
    if cached is not None:
        return cached

    grants = await get_user_grants_async(db, user)
    access = _build_access_map(grants)
    info[cache_key] = access
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


async def evaluate_permission_async(
    db: AsyncSession,
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
        subject_roles=tuple(await get_user_role_names_async(db, user)),
        subject_attrs=subject_attrs or {},
        resource_attrs=resource_attrs or {},
    )
    engine = get_permission_engine()
    return engine.evaluate(
        request=request,
        grants=await get_user_grants_async(db, user),
        access=await get_user_access_async(db, user),
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


async def has_permission_async(
    db: AsyncSession,
    user: User,
    *,
    action: str,
    scope: str,
    resource_type: str,
    resource_id: str | None = None,
) -> bool:
    decision = await evaluate_permission_async(
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
            detail="访问需要权限",
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
            detail="访问需要权限",
        )


async def require_menu_action_async(
    db: AsyncSession,
    user: User,
    *,
    action: str,
    menu_id: str,
) -> None:
    if is_super_admin(user):
        return
    if menu_id not in MENU_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid menu",
        )
    decision = await evaluate_permission_async(
        db,
        user,
        action=action,
        scope="menu",
        resource_type="menu",
        resource_id=menu_id,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="访问需要权限",
        )


async def require_manage_menu_async(db: AsyncSession, user: User) -> None:
    await require_menu_action_async(db, user, action="manage", menu_id="admin")


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


async def summarize_permissions_async(db: AsyncSession, user: User) -> dict:
    role_names = await get_user_role_names_async(db, user)
    super_admin = is_super_admin(user)
    from ..services.chat_user_sync import list_user_synced_agent_ids_async

    if is_super_admin(user):
        return {
            "roles": role_names,
            "is_super_admin": True,
            "synced_agent_ids": await _resource_ids_async(db, "agent"),
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

    access = await get_user_access_async(db, user)

    menus: list[dict] = []
    for menu_id in sorted(MENU_IDS):
        specific_key = ("menu", "menu", menu_id)
        wildcard_key = ("menu", "menu", None)
        mask = access.get(specific_key, 0) | access.get(wildcard_key, 0)
        if mask:
            menus.append({"menu_id": menu_id, "actions": _mask_to_actions(mask)})

    resources: list[dict] = []
    resource_actions: dict[tuple[str, str | None], set[str]] = {}
    resource_items: dict[tuple[str, str | None], dict] = {}
    for (scope, resource_type, resource_id), mask in sorted(
        access.items(), key=lambda item: (item[0][1], item[0][2] or "")
    ):
        if scope != "resource" or resource_type not in RESOURCE_TYPES or not mask:
            continue
        actions = set(_mask_to_actions(mask))
        resource_actions[(resource_type, resource_id)] = actions
        item = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actions": sorted(actions, key=lambda action: ACTION_ORDER.get(action, 0)),
        }
        resource_items[(resource_type, resource_id)] = item
        resources.append(item)

    synced_agent_ids = await list_user_synced_agent_ids_async(db, user=user)
    if ("agent", None) not in resource_actions:
        for agent_id in synced_agent_ids:
            key = ("agent", agent_id)
            actions = resource_actions.setdefault(key, set())
            if "view" in actions:
                continue
            actions.add("view")
            item = resource_items.get(key)
            if item is None:
                item = {
                    "resource_type": "agent",
                    "resource_id": agent_id,
                    "actions": [],
                }
                resource_items[key] = item
                resources.append(item)
            item["actions"] = sorted(actions, key=lambda action: ACTION_ORDER.get(action, 0))

    return {
        "roles": role_names,
        "is_super_admin": super_admin,
        "synced_agent_ids": synced_agent_ids,
        "menus": menus,
        "resources": resources,
    }


async def _resource_ids_async(db: AsyncSession, resource_type: str) -> list[str]:
    cache_key = f"resource_ids:{resource_type}"
    info = _session_info(db)
    cached = info.get(cache_key)
    if cached is not None:
        return cached

    if resource_type == "agent":
        rows = (await db.execute(select(Agent.id))).scalars().all()
    elif resource_type == "model":
        rows = (await db.execute(select(Model.id))).scalars().all()
    elif resource_type == "agent_group":
        rows = (await db.execute(select(AgentGroup.name))).scalars().all()
    else:
        rows = []
    values = [str(item) for item in rows if item]
    info[cache_key] = values
    return values


async def _agent_group_map_async(db: AsyncSession) -> list[tuple[str, list[str]]]:
    cache_key = "agent_group_map"
    info = _session_info(db)
    cached = info.get(cache_key)
    if cached is not None:
        return cached

    rows = (await db.execute(select(Agent.id, Agent.groups, Agent.group_name))).all()
    result: list[tuple[str, list[str]]] = []
    for agent_id, groups, group_name in rows:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in list(groups or []) + ([group_name] if group_name else []):
            name = str(item or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            normalized.append(name)
        result.append((str(agent_id), normalized))
    info[cache_key] = result
    return result


async def expand_resource_wildcards_async(
    db: AsyncSession,
    action_map: dict[tuple[str, str | None], set[str]],
) -> dict[tuple[str, str | None], set[str]]:
    expanded: dict[tuple[str, str | None], set[str]] = {
        key: set(actions) for key, actions in action_map.items()
    }
    for resource_type in ("agent", "model", "agent_group"):
        wildcard_actions = expanded.pop((resource_type, None), None)
        if not wildcard_actions:
            continue
        ids = await _resource_ids_async(db, resource_type)
        if not ids:
            expanded[(resource_type, None)] = set(wildcard_actions)
            continue
        for resource_id in ids:
            expanded.setdefault((resource_type, resource_id), set()).update(wildcard_actions)
    return expanded


async def expand_agent_group_permissions_async(
    db: AsyncSession,
    action_map: dict[tuple[str, str | None], set[str]],
) -> dict[tuple[str, str | None], set[str]]:
    group_actions: dict[str | None, set[str]] = {}
    for (resource_type, resource_id), actions in action_map.items():
        if resource_type == "agent_group":
            group_actions[resource_id] = set(actions)

    if not group_actions:
        return {}

    all_group_actions = group_actions.get(None, set())
    derived: dict[tuple[str, str | None], set[str]] = {}
    for agent_id, groups in await _agent_group_map_async(db):
        actions_for_agent: set[str] = set(all_group_actions)
        for group in groups:
            if group in group_actions:
                actions_for_agent.update(group_actions[group])
        if actions_for_agent:
            derived[("agent", agent_id)] = actions_for_agent
    return derived


def _sorted_actions(actions: set[str]) -> list[str]:
    return sorted(actions, key=lambda item: ACTION_ORDER.get(item, 0))
