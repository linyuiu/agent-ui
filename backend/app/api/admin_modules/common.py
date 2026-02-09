from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ... import models, schemas
from ...permissions import (
    ACTION_ORDER,
    has_permission,
    is_super_admin,
    require_manage_menu,
    require_menu_action,
)
from ...services.chat_links import build_proxy_chat_url, parse_upstream_chat_url


def require_menu_view(user: models.User, db: Session, menu_id: str) -> None:
    require_menu_action(db, user, action="view", menu_id=menu_id)


def require_menu_edit(user: models.User, db: Session, menu_id: str) -> None:
    require_menu_action(db, user, action="edit", menu_id=menu_id)


def require_menu_manage(user: models.User, db: Session) -> None:
    require_manage_menu(db, user)


def ensure_role_exists(db: Session, role_name: str) -> None:
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")


def ensure_roles_exist(db: Session, role_names: list[str]) -> None:
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")
    existing = {
        name
        for (name,) in db.query(models.Role.name).filter(models.Role.name.in_(role_names)).all()
    }
    missing = [name for name in role_names if name not in existing]
    if missing:
        raise HTTPException(status_code=400, detail=f"Role not found: {', '.join(missing)}")


def normalize_roles(role: str | None = None, roles: list[str] | None = None) -> list[str]:
    candidates: list[str] = []
    if roles:
        candidates.extend(roles)
    elif role is not None:
        candidates.append(role)

    seen: set[str] = set()
    cleaned: list[str] = []
    for item in candidates:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


def set_user_roles(db: Session, user: models.User, role_names: list[str]) -> list[str]:
    role_names = normalize_roles(roles=role_names)
    if user.account == "admin":
        role_names = ["admin"]
    if not role_names:
        raise HTTPException(status_code=400, detail="At least one role is required")

    ensure_roles_exist(db, role_names)

    existing_rows = db.query(models.UserRole).filter(models.UserRole.user_id == user.id).all()
    existing = {row.role_name for row in existing_rows}
    expected = set(role_names)

    for row in existing_rows:
        if row.role_name not in expected:
            db.delete(row)
    for role_name in role_names:
        if role_name in existing:
            continue
        db.add(models.UserRole(user_id=user.id, role_name=role_name))

    if user.account == "admin" or "admin" in role_names:
        primary = "admin"
    else:
        primary = role_names[0]
    user.role = primary
    return role_names


def fetch_user_roles_map(db: Session, user_ids: list[int]) -> dict[int, list[str]]:
    if not user_ids:
        return {}
    rows = (
        db.query(models.UserRole)
        .filter(models.UserRole.user_id.in_(user_ids))
        .order_by(models.UserRole.user_id.asc(), models.UserRole.role_name.asc())
        .all()
    )
    grouped: dict[int, list[str]] = {user_id: [] for user_id in user_ids}
    for row in rows:
        grouped.setdefault(row.user_id, []).append(row.role_name)
    return grouped


def sorted_actions(actions: set[str]) -> list[str]:
    return sorted(actions, key=lambda item: ACTION_ORDER.get(item, 0))


def expand_actions(actions: set[str]) -> set[str]:
    expanded: set[str] = set()
    if "manage" in actions:
        expanded.update({"manage", "edit", "view"})
    elif "edit" in actions:
        expanded.update({"edit", "view"})
    elif "view" in actions:
        expanded.add("view")
    return expanded


def collect_actions(grants: list[models.PermissionGrant]) -> dict[tuple[str, str | None], set[str]]:
    grouped: dict[tuple[str, str | None], set[str]] = {}
    for grant in grants:
        key = (grant.resource_type, grant.resource_id)
        grouped.setdefault(key, set()).add(grant.action)
    for key, actions in list(grouped.items()):
        grouped[key] = expand_actions(actions)
    return grouped


def build_permission_items(
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
                actions=sorted_actions(actions),
                inherited_actions=sorted_actions(inherited_actions),
            )
        )
    items.sort(key=lambda item: (item.resource_type, item.resource_id or ""))
    return items


def expand_resource_wildcards(
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


def expand_agent_group_permissions(
    db: Session,
    action_map: dict[tuple[str, str | None], set[str]],
) -> dict[tuple[str, str | None], set[str]]:
    group_actions: dict[str | None, set[str]] = {}
    for (resource_type, resource_id), actions in action_map.items():
        if resource_type != "agent_group":
            continue
        group_actions[resource_id] = set(actions)

    if not group_actions:
        return {}

    all_group_actions = group_actions.get(None, set())
    derived: dict[tuple[str, str | None], set[str]] = {}

    agents = db.query(models.Agent).all()
    for agent in agents:
        groups = list(agent.groups or [])
        if not groups and agent.group_name:
            groups = [agent.group_name]
        actions_for_agent: set[str] = set(all_group_actions)
        for name in groups:
            if name in group_actions:
                actions_for_agent.update(group_actions[name])
        if actions_for_agent:
            derived.setdefault(("agent", agent.id), set()).update(actions_for_agent)
    return derived


def assert_permission_editable(
    current_user: models.User, target_user: models.User | None = None, *, target_role: str | None = None
) -> None:
    if target_user and target_user.account == "admin" and not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Protected user permissions cannot be modified")
    if target_role == "user":
        raise HTTPException(status_code=403, detail="Protected role permissions cannot be modified")
    if target_role == "admin" and not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Protected role permissions cannot be modified")


def normalize_groups(groups: list[str] | None) -> list[str]:
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


def ensure_agent_groups(db: Session, current_user: models.User, groups: list[str]) -> None:
    if not groups:
        return
    existing = {
        group.name
        for group in db.query(models.AgentGroup).filter(models.AgentGroup.name.in_(groups)).all()
    }
    for name in groups:
        if name in existing:
            continue
        db.add(models.AgentGroup(name=name, description=""))
        if not is_super_admin(current_user):
            db.add(
                models.PermissionGrant(
                    subject_type="user",
                    subject_id=str(current_user.id),
                    scope="resource",
                    resource_type="agent_group",
                    resource_id=name,
                    action="manage",
                )
            )
        existing.add(name)
    db.flush()


def assert_group_permissions(db: Session, current_user: models.User, groups: list[str]) -> None:
    if not groups:
        return
    if has_permission(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="agent",
        resource_id=None,
    ):
        return
    for group in groups:
        if not has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        ):
            raise HTTPException(status_code=403, detail="Forbidden")


def mask_token(token: str) -> str:
    token = token or ""
    if len(token) <= 4:
        return "****"
    return f"****{token[-4:]}"


def fit2cloud_auth_header(token: str) -> str:
    token = (token or "").strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def fit2cloud_fetch(base_url: str, token: str, path: str) -> dict:
    headers = {"accept": "application/json", "Authorization": fit2cloud_auth_header(token)}
    resp = httpx.get(f"{base_url}{path}", headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("code") == 200:
        return data
    raise HTTPException(status_code=400, detail=f"Upstream error: {data}")


def new_proxy_id() -> str:
    return uuid4().hex


def set_agent_upstream_chat_link(
    agent: models.Agent,
    *,
    upstream_base_url: str,
    upstream_token: str,
) -> None:
    proxy_id = (agent.proxy_id or "").strip() or new_proxy_id()
    agent.proxy_id = proxy_id
    agent.upstream_base_url = upstream_base_url.rstrip("/")
    agent.upstream_token = upstream_token.strip()
    agent.url = build_proxy_chat_url(proxy_id)


def parse_agent_chat_link(raw_url: str) -> tuple[str, str]:
    try:
        return parse_upstream_chat_url(raw_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def fit2cloud_sync_worker_count(task_count: int) -> int:
    raw = os.getenv("FIT2CLOUD_SYNC_WORKERS", "8")
    try:
        configured = int(raw)
    except ValueError:
        configured = 8
    configured = max(1, min(configured, 32))
    return min(max(task_count, 1), configured)


def compact_fit2cloud_source_payload(
    workspace_id: str,
    workspace_name: str,
    app: dict,
    detail: dict,
    token_data: dict,
) -> dict:
    return {
        "source": "fit2cloud",
        "workspace": {"id": workspace_id, "name": workspace_name},
        "application": {
            "id": app.get("id"),
            "name": app.get("name"),
            "user_id": app.get("user_id"),
            "nick_name": app.get("nick_name"),
        },
        "detail": {
            "id": detail.get("id") or app.get("id"),
            "name": detail.get("name") or app.get("name"),
            "user": detail.get("user"),
            "create_time": detail.get("create_time"),
            "update_time": detail.get("update_time"),
        },
        "token": {
            "is_active": token_data.get("is_active"),
        },
    }


def fetch_fit2cloud_app_payloads(
    base_url: str,
    token: str,
    workspace_id: str,
    apps: list[dict],
) -> tuple[list[dict], list[str]]:
    targets = [app for app in apps if isinstance(app, dict) and app.get("id")]
    if not targets:
        return [], []

    def _fetch_one(app: dict) -> dict:
        app_id = str(app.get("id"))
        try:
            detail_resp = fit2cloud_fetch(base_url, token, f"/admin/api/workspace/{workspace_id}/application/{app_id}")
            token_resp = fit2cloud_fetch(
                base_url,
                token,
                f"/admin/api/workspace/{workspace_id}/application/{app_id}/access_token",
            )
        except Exception:
            return {"error": f"application {app_id}: failed to fetch detail/token"}

        detail = detail_resp.get("data") or {}
        token_data = token_resp.get("data") or {}
        if not token_data.get("access_token"):
            return {"error": f"application {app_id}: missing access_token"}

        return {
            "app_id": app_id,
            "app": app,
            "detail": detail,
            "token_data": token_data,
        }

    workers = fit2cloud_sync_worker_count(len(targets))
    if workers == 1:
        collected = [_fetch_one(app) for app in targets]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_fetch_one, app) for app in targets]
            collected = [future.result() for future in as_completed(futures)]

    payloads: list[dict] = []
    errors: list[str] = []
    for item in collected:
        error = item.get("error")
        if error:
            errors.append(str(error))
            continue
        payloads.append(item)
    return payloads, errors


def sync_fit2cloud_workspace_agents(
    db: Session,
    current_user: models.User,
    *,
    base_url: str,
    token: str,
    workspace_id: str,
    workspace_name: str,
    apps: list[dict],
) -> tuple[int, int, list[str]]:
    workspace_key = str(workspace_id)
    workspace_label = str(workspace_name or workspace_key)
    target_apps = [item for item in apps if isinstance(item, dict) and item.get("id")]
    if not target_apps:
        return 0, 0, []

    groups = normalize_groups([workspace_label])
    if groups:
        ensure_agent_groups(db, current_user, groups)

    app_ids = [str(item.get("id")) for item in target_apps]
    existing_agents = (
        db.query(models.Agent)
        .filter(
            models.Agent.is_synced.is_(True),
            models.Agent.source_type == "fit2cloud",
            models.Agent.workspace_id == workspace_key,
            models.Agent.external_id.in_(app_ids),
        )
        .all()
    )
    existing_by_external_id = {
        str(agent.external_id): agent for agent in existing_agents if agent.external_id
    }

    payloads, errors = fetch_fit2cloud_app_payloads(
        base_url=base_url,
        token=token,
        workspace_id=workspace_key,
        apps=target_apps,
    )

    imported = 0
    updated = 0

    for item in payloads:
        app_id = str(item["app_id"])
        app = item["app"]
        detail = item["detail"]
        token_data = item["token_data"]
        access_token = token_data.get("access_token")
        status_value = "active" if token_data.get("is_active") else "paused"
        description = detail.get("desc") or detail.get("prologue") or ""
        owner = app.get("nick_name") or app.get("user_id") or detail.get("user") or "external"
        last_run = detail.get("update_time") or detail.get("create_time") or ""
        source_payload = compact_fit2cloud_source_payload(
            workspace_id=workspace_key,
            workspace_name=workspace_label,
            app=app,
            detail=detail,
            token_data=token_data,
        )

        existing = existing_by_external_id.get(app_id)
        if not existing:
            new_agent = models.Agent(
                id=uuid4().hex,
                name=detail.get("name") or app.get("name") or "Agent",
                status=status_value,
                owner=owner,
                last_run=last_run,
                proxy_id=new_proxy_id(),
                upstream_base_url=base_url,
                upstream_token=str(access_token),
                url="",
                description=description,
                group_name=groups[0] if groups else "",
                groups=groups,
                source_payload=source_payload,
                source_type="fit2cloud",
                is_synced=True,
                external_id=app_id,
                workspace_id=workspace_key,
            )
            set_agent_upstream_chat_link(
                new_agent,
                upstream_base_url=base_url,
                upstream_token=str(access_token),
            )
            db.add(new_agent)
            imported += 1
            continue

        existing.name = detail.get("name") or app.get("name") or existing.name
        existing.status = status_value
        existing.owner = owner
        existing.last_run = last_run
        existing.description = description
        existing.group_name = groups[0] if groups else ""
        existing.groups = groups
        existing.source_payload = source_payload
        existing.source_type = "fit2cloud"
        existing.is_synced = True
        existing.external_id = app_id
        existing.workspace_id = workspace_key
        set_agent_upstream_chat_link(
            existing,
            upstream_base_url=base_url,
            upstream_token=str(access_token),
        )
        updated += 1

    return imported, updated, errors


def get_agent_api_config(db: Session, config_id: int) -> models.AgentApiConfig:
    config = db.query(models.AgentApiConfig).filter(models.AgentApiConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config
