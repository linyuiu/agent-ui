from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..db import AsyncSessionLocal
from ..services.serializers import agent_detail
from ..api.admin_modules.common import fit2cloud_fetch_async, fit2cloud_request_async

_PAGE_SIZE = 100


def sync_task_out(task: models.SyncTask) -> schemas.SyncTaskOut:
    return schemas.SyncTaskOut(
        id=task.id,
        task_type=task.task_type,
        status=task.status,
        config_id=task.config_id,
        agent_id=task.agent_id,
        agent_name=task.agent_name,
        workspace_id=task.workspace_id,
        workspace_name=task.workspace_name,
        external_id=task.external_id,
        total_steps=task.total_steps,
        completed_steps=task.completed_steps,
        total_records=task.total_records,
        processed_records=task.processed_records,
        message=task.message,
        error=task.error,
        payload=dict(task.payload or {}),
        created_by=task.created_by,
        celery_task_id=task.celery_task_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_source(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_identity(value: str) -> str:
    return str(value or "").strip().lower()


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item or "").strip()]


async def _fetch_paged_records(
    base_url: str,
    token: str,
    path_builder,
) -> list[dict[str, Any]]:
    page = 1
    records: list[dict[str, Any]] = []
    while True:
        payload = await fit2cloud_fetch_async(base_url, token, path_builder(page, _PAGE_SIZE))
        data = payload.get("data") or {}
        if isinstance(data, list):
            page_items = [item for item in data if isinstance(item, dict)]
            records.extend(page_items)
            break
        page_items = data.get("records") or []
        if not isinstance(page_items, list):
            break
        page_items = [item for item in page_items if isinstance(item, dict)]
        records.extend(page_items)
        total = int(data.get("total") or len(records) or 0)
        size = int(data.get("size") or _PAGE_SIZE)
        current = int(data.get("current") or page)
        if not page_items or current * size >= total:
            break
        page += 1
    return records


async def fetch_all_chat_users(base_url: str, token: str) -> list[dict[str, Any]]:
    return await _fetch_paged_records(
        base_url,
        token,
        lambda page, size: f"/admin/api/system/chat_user/user_manage/{page}/{size}",
    )


async def fetch_all_chat_user_groups(base_url: str, token: str) -> list[dict[str, Any]]:
    payload = await fit2cloud_fetch_async(base_url, token, "/admin/api/system/group")
    data = payload.get("data") or []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


async def fetch_agent_group_chat_users(
    base_url: str,
    token: str,
    *,
    workspace_candidates: list[str],
    application_id: str,
    group_id: str,
) -> tuple[str, list[dict[str, Any]]]:
    errors: list[str] = []
    candidates = [candidate for candidate in workspace_candidates if candidate]
    if "default" not in candidates:
        candidates.append("default")
    seen: set[str] = set()
    ordered_candidates = [candidate for candidate in candidates if not (candidate in seen or seen.add(candidate))]

    for workspace_key in ordered_candidates:
        try:
            records = await _fetch_paged_records(
                base_url,
                token,
                lambda page, size: (
                    f"/admin/api/workspace/{workspace_key}/APPLICATION/{application_id}"
                    f"/user_group_id/{group_id}/{page}/{size}"
                ),
            )
            return workspace_key, records
        except HTTPException as exc:
            errors.append(f"{workspace_key}: {exc.detail}")
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"{workspace_key}: {exc}")
    raise HTTPException(status_code=400, detail="; ".join(errors) or "Failed to fetch agent chat users")


def _workspace_candidates_for_agent(agent: models.Agent) -> list[str]:
    source_payload = dict(agent.source_payload or {})
    workspace_info = source_payload.get("workspace") if isinstance(source_payload.get("workspace"), dict) else {}
    candidates = [
        str(workspace_info.get("slug") or "").strip(),
        str(workspace_info.get("path") or "").strip(),
        str(workspace_info.get("id") or "").strip(),
        str(agent.workspace_id or "").strip(),
        "default",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


async def push_agent_group_chat_user_accesses(
    *,
    base_url: str,
    token: str,
    agent: models.Agent,
    group_id: str,
    payload: list[dict[str, Any]],
) -> str:
    application_id = str(agent.external_id or "").strip()
    if not application_id:
        raise HTTPException(status_code=400, detail="Agent external application id is missing")

    errors: list[str] = []
    for workspace_key in _workspace_candidates_for_agent(agent):
        try:
            await fit2cloud_request_async(
                base_url,
                token,
                (
                    f"/admin/api/workspace/{workspace_key}/APPLICATION/{application_id}"
                    f"/user_group_id/{group_id}"
                ),
                method="PUT",
                json_body=payload,
            )
            return workspace_key
        except HTTPException as exc:
            errors.append(f"{workspace_key}: {exc.detail}")
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"{workspace_key}: {exc}")
    raise HTTPException(status_code=400, detail="; ".join(errors) or "Failed to update agent chat users")


async def sync_chat_user_catalog(
    db: AsyncSession,
    *,
    base_url: str,
    token: str,
) -> tuple[list[models.ChatUserGroup], list[models.ChatUser]]:
    group_payloads = await fetch_all_chat_user_groups(base_url, token)
    user_payloads = await fetch_all_chat_users(base_url, token)

    group_ids = {str(item.get("id") or "").strip() for item in group_payloads if item.get("id")}
    user_ids = {str(item.get("id") or "").strip() for item in user_payloads if item.get("id")}

    existing_groups = {
        item.id: item
        for item in (
            await db.execute(
                select(models.ChatUserGroup).where(models.ChatUserGroup.id.in_(group_ids or [""]))
            )
        ).scalars().all()
    }
    existing_users = {
        item.id: item
        for item in (
            await db.execute(select(models.ChatUser).where(models.ChatUser.id.in_(user_ids or [""])))
        ).scalars().all()
    }

    synced_at = _now()

    for payload in group_payloads:
        group_id = str(payload.get("id") or "").strip()
        if not group_id:
            continue
        group = existing_groups.get(group_id)
        if not group:
            group = models.ChatUserGroup(id=group_id)
            db.add(group)
            existing_groups[group_id] = group
        group.name = str(payload.get("name") or group_id)
        group.raw_payload = dict(payload)
        group.synced_at = synced_at

    for payload in user_payloads:
        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            continue
        chat_user = existing_users.get(user_id)
        if not chat_user:
            chat_user = models.ChatUser(id=user_id)
            db.add(chat_user)
            existing_users[user_id] = chat_user
        chat_user.username = str(payload.get("username") or "").strip()
        chat_user.email = str(payload.get("email") or "").strip()
        chat_user.phone = str(payload.get("phone") or "").strip()
        chat_user.is_active = bool(payload.get("is_active"))
        chat_user.nick_name = str(payload.get("nick_name") or "").strip()
        chat_user.source = str(payload.get("source") or "").strip()
        chat_user.create_time = str(payload.get("create_time") or "").strip()
        chat_user.update_time = str(payload.get("update_time") or "").strip()
        chat_user.user_group_ids = _string_list(payload.get("user_group_ids"))
        chat_user.user_group_names = _string_list(payload.get("user_group_names"))
        chat_user.raw_payload = dict(payload)
        chat_user.synced_at = synced_at

    if group_ids:
        await db.execute(delete(models.ChatUserGroup).where(models.ChatUserGroup.id.not_in(group_ids)))
    else:
        await db.execute(delete(models.ChatUserGroup))
    if user_ids:
        await db.execute(delete(models.ChatUser).where(models.ChatUser.id.not_in(user_ids)))
        await db.execute(delete(models.UserChatBinding).where(models.UserChatBinding.chat_user_id.not_in(user_ids)))
    else:
        await db.execute(delete(models.ChatUser))
        await db.execute(delete(models.UserChatBinding))

    await db.execute(delete(models.ChatUserGroupMember))
    membership_rows: list[models.ChatUserGroupMember] = []
    for chat_user in existing_users.values():
        group_ids_for_user = list(chat_user.user_group_ids or [])
        group_names_for_user = list(chat_user.user_group_names or [])
        name_map = {
            str(group_id): group_names_for_user[index]
            for index, group_id in enumerate(group_ids_for_user)
            if index < len(group_names_for_user)
        }
        for group_id in group_ids_for_user:
            membership_rows.append(
                models.ChatUserGroupMember(
                    group_id=group_id,
                    group_name=name_map.get(group_id) or existing_groups.get(group_id, models.ChatUserGroup(id="", name="")).name,
                    chat_user_id=chat_user.id,
                    synced_at=synced_at,
                )
            )
    if membership_rows:
        db.add_all(membership_rows)

    await db.flush()
    await sync_user_chat_bindings(db, chat_users=list(existing_users.values()))
    return list(existing_groups.values()), list(existing_users.values())


async def sync_agent_chat_user_accesses(
    db: AsyncSession,
    *,
    agent: models.Agent,
    base_url: str,
    token: str,
    groups: list[models.ChatUserGroup],
) -> tuple[int, list[str]]:
    application_id = str(agent.external_id or "").strip()
    if not application_id:
        raise HTTPException(status_code=400, detail="Agent external application id is missing")

    workspace_candidates = _workspace_candidates_for_agent(agent)

    await db.execute(delete(models.AgentChatUserAccess).where(models.AgentChatUserAccess.agent_id == agent.id))

    total_records = 0
    errors: list[str] = []
    synced_at = _now()

    for group in groups:
        if not group.id:
            continue
        try:
            _, records = await fetch_agent_group_chat_users(
                base_url,
                token,
                workspace_candidates=workspace_candidates,
                application_id=application_id,
                group_id=group.id,
            )
        except HTTPException as exc:
            errors.append(f"{group.name or group.id}: {exc.detail}")
            continue

        for payload in records:
            chat_user_id = str(payload.get("id") or "").strip()
            if not chat_user_id:
                continue
            db.add(
                models.AgentChatUserAccess(
                    agent_id=agent.id,
                    chat_user_id=chat_user_id,
                    group_id=group.id,
                    group_name=group.name,
                    username=str(payload.get("username") or "").strip(),
                    nick_name=str(payload.get("nick_name") or "").strip(),
                    is_active=bool(payload.get("is_active")),
                    source=str(payload.get("source") or "").strip(),
                    create_time=str(payload.get("create_time") or "").strip(),
                    update_time=str(payload.get("update_time") or "").strip(),
                    is_auth=bool(payload.get("is_auth")),
                    raw_payload=dict(payload),
                    synced_at=synced_at,
                )
            )
            total_records += 1

    await db.flush()
    return total_records, errors


async def create_agent_chat_user_sync_task(
    db: AsyncSession,
    *,
    current_user: models.User,
    agent: models.Agent,
    config_id: int,
) -> models.SyncTask:
    task = models.SyncTask(
        task_type="agent_chat_user_sync",
        status="pending",
        config_id=config_id,
        agent_id=agent.id,
        agent_name=agent.name,
        workspace_id=str(agent.workspace_id or ""),
        workspace_name=str(agent.workspace_name or ""),
        external_id=str(agent.external_id or ""),
        created_by=current_user.id,
        message="等待同步",
    )
    db.add(task)
    await db.flush()
    return task


async def _mark_task_failed(db: AsyncSession, task: models.SyncTask, detail: str) -> None:
    task.status = "failed"
    task.error = detail
    task.message = detail
    task.finished_at = _now()
    task.updated_at = _now()
    await db.commit()


async def run_agent_chat_user_sync_task(task_id: str) -> None:
    async with AsyncSessionLocal() as db:
        task = await db.get(models.SyncTask, task_id)
        if not task:
            return

        agent = await db.get(models.Agent, task.agent_id) if task.agent_id else None
        config = await db.get(models.AgentApiConfig, task.config_id) if task.config_id else None
        if not agent or not config:
            await _mark_task_failed(db, task, "同步任务缺少智能体或 API 配置")
            return
        if not agent.is_synced:
            await _mark_task_failed(db, task, "仅同步创建的智能体支持同步对话用户")
            return

        task.status = "running"
        task.started_at = _now()
        task.updated_at = _now()
        task.message = "正在同步用户组"
        task.error = ""
        await db.commit()

        try:
            groups, users = await sync_chat_user_catalog(
                db,
                base_url=config.base_url.rstrip("/"),
                token=config.token,
            )
            task.total_steps = max(2 + len(groups), 2)
            task.completed_steps = 2
            task.total_records = len(users)
            task.processed_records = len(users)
            task.message = "正在同步智能体对话用户"
            task.updated_at = _now()
            await db.commit()

            access_count, errors = await sync_agent_chat_user_accesses(
                db,
                agent=agent,
                base_url=config.base_url.rstrip("/"),
                token=config.token,
                groups=groups,
            )
            task.completed_steps = task.total_steps
            task.processed_records = len(users) + access_count
            task.total_records = task.processed_records
            task.status = "completed"
            task.message = f"同步完成，共同步 {access_count} 条智能体对话用户记录"
            task.error = "；".join(errors[:10]) if errors else ""
            task.finished_at = _now()
            task.updated_at = _now()
            await db.commit()
        except Exception as exc:  # pragma: no cover - task failure path
            await _mark_task_failed(db, task, str(exc))


async def build_agent_chat_user_view(
    db: AsyncSession,
    *,
    agent_id: str,
    manageable: bool = False,
    sync_supported: bool = False,
) -> schemas.AgentChatUserView:
    groups = (
        await db.execute(
            select(models.AgentChatUserAccess.group_id, models.AgentChatUserAccess.group_name)
            .where(models.AgentChatUserAccess.agent_id == agent_id)
            .distinct()
            .order_by(models.AgentChatUserAccess.group_name.asc(), models.AgentChatUserAccess.group_id.asc())
        )
    ).all()

    access_rows = (
        await db.execute(
            select(models.AgentChatUserAccess, models.ChatUser)
            .outerjoin(models.ChatUser, models.ChatUser.id == models.AgentChatUserAccess.chat_user_id)
            .where(models.AgentChatUserAccess.agent_id == agent_id)
            .order_by(
                models.AgentChatUserAccess.group_name.asc(),
                models.AgentChatUserAccess.nick_name.asc(),
                models.AgentChatUserAccess.username.asc(),
            )
        )
    ).all()

    grouped: dict[str, list[schemas.AgentChatUserEntry]] = {}
    latest_synced_at = None
    for access, chat_user in access_rows:
        latest_synced_at = max(
            [item for item in (latest_synced_at, access.synced_at) if item is not None],
            default=latest_synced_at,
        )
        grouped.setdefault(access.group_id, []).append(
            schemas.AgentChatUserEntry(
                id=access.chat_user_id,
                username=chat_user.username if chat_user else access.username,
                email=chat_user.email if chat_user else "",
                phone=chat_user.phone if chat_user else "",
                is_active=chat_user.is_active if chat_user else access.is_active,
                nick_name=chat_user.nick_name if chat_user else access.nick_name,
                source=chat_user.source if chat_user else access.source,
                create_time=chat_user.create_time if chat_user else access.create_time,
                update_time=chat_user.update_time if chat_user else access.update_time,
                user_group_ids=list(chat_user.user_group_ids or []) if chat_user else [access.group_id],
                user_group_names=list(chat_user.user_group_names or []) if chat_user else [access.group_name],
                is_auth=bool(access.is_auth),
            )
        )

    group_views = []
    for group_id, group_name in groups:
        users = grouped.get(group_id, [])
        group_views.append(
            schemas.AgentChatUserGroupView(
                id=group_id,
                name=group_name or group_id,
                authorized_count=sum(1 for user in users if user.is_auth),
                users=users,
            )
        )
    total_users = sum(len(group.users) for group in group_views)
    return schemas.AgentChatUserView(
        agent_id=agent_id,
        groups=group_views,
        total_users=total_users,
        last_synced_at=latest_synced_at,
        manageable=manageable,
        sync_supported=sync_supported,
    )


async def update_agent_chat_user_accesses(
    db: AsyncSession,
    *,
    agent: models.Agent,
    config: models.AgentApiConfig,
    group_id: str,
    updates: list[schemas.AgentChatUserAccessUpdateItem],
) -> schemas.AgentChatUserView:
    if not agent.is_synced:
        raise HTTPException(status_code=400, detail="仅同步创建的智能体支持授权对话用户")
    if not agent.external_id:
        raise HTTPException(status_code=400, detail="智能体缺少外部应用标识")

    access_rows = (
        await db.execute(
            select(models.AgentChatUserAccess)
            .where(
                models.AgentChatUserAccess.agent_id == agent.id,
                models.AgentChatUserAccess.group_id == group_id,
            )
            .order_by(models.AgentChatUserAccess.username.asc(), models.AgentChatUserAccess.chat_user_id.asc())
        )
    ).scalars().all()
    if not access_rows:
        raise HTTPException(status_code=404, detail="未找到该用户组的对话用户数据")

    updates_by_id = {item.chat_user_id: bool(item.is_auth) for item in updates}
    unknown_ids = sorted(set(updates_by_id) - {row.chat_user_id for row in access_rows})
    if unknown_ids:
        raise HTTPException(status_code=400, detail=f"存在无效的对话用户：{', '.join(unknown_ids[:5])}")

    synced_at = _now()
    for row in access_rows:
        if row.chat_user_id in updates_by_id:
            row.is_auth = updates_by_id[row.chat_user_id]
        payload = dict(row.raw_payload or {})
        payload["is_auth"] = bool(row.is_auth)
        row.raw_payload = payload
        row.synced_at = synced_at

    upstream_payload = [
        {"chat_user_id": row.chat_user_id, "is_auth": bool(row.is_auth)}
        for row in access_rows
    ]

    try:
        await push_agent_group_chat_user_accesses(
            base_url=config.base_url.rstrip("/"),
            token=config.token,
            agent=agent,
            group_id=group_id,
            payload=upstream_payload,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive branch
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"更新源系统失败：{exc}") from exc

    await db.commit()
    return await build_agent_chat_user_view(
        db,
        agent_id=agent.id,
        manageable=True,
        sync_supported=bool(agent.is_synced and agent.sync_config_id and agent.external_id),
    )


async def find_chat_user_by_identity(
    db: AsyncSession,
    *,
    username: str,
    source: str,
) -> models.ChatUser | None:
    normalized_username = _normalize_identity(username)
    normalized_source = _normalize_source(source)
    if not normalized_username or not normalized_source:
        return None

    chat_users = (
        await db.execute(select(models.ChatUser).where(models.ChatUser.username == username))
    ).scalars().all()
    for chat_user in chat_users:
        if _normalize_source(chat_user.source) == normalized_source:
            return chat_user
    return None


async def upsert_user_chat_binding(
    db: AsyncSession,
    *,
    user: models.User,
    chat_user: models.ChatUser,
    binding_source: str,
) -> models.UserChatBinding:
    existing = (
        await db.execute(
            select(models.UserChatBinding).where(models.UserChatBinding.chat_user_id == chat_user.id)
        )
    ).scalar_one_or_none()
    if existing:
        if existing.user_id != user.id and existing.binding_source != "matched":
            raise HTTPException(status_code=409, detail="该对话用户已绑定其他系统用户")
        existing.user_id = user.id
        existing.binding_source = binding_source
        await db.flush()
        return existing

    binding = models.UserChatBinding(
        user_id=user.id,
        chat_user_id=chat_user.id,
        binding_source=binding_source,
    )
    db.add(binding)
    await db.flush()
    return binding


async def sync_user_chat_bindings(
    db: AsyncSession,
    *,
    chat_users: list[models.ChatUser] | None = None,
) -> int:
    target_chat_users = chat_users
    if target_chat_users is None:
        target_chat_users = (await db.execute(select(models.ChatUser))).scalars().all()
    if not target_chat_users:
        await db.execute(
            delete(models.UserChatBinding).where(models.UserChatBinding.binding_source == "matched")
        )
        await db.flush()
        return 0

    usernames = {
        username
        for chat_user in target_chat_users
        for username in {str(chat_user.username or "").strip()}
        if username
    }
    if not usernames:
        return 0

    users = (
        await db.execute(
            select(models.User).where(
                or_(models.User.username.in_(usernames), models.User.account.in_(usernames))
            )
        )
    ).scalars().all()
    users_by_identity: dict[tuple[str, str], models.User] = {}
    for user in users:
        source_key = _normalize_source(user.source)
        if not source_key:
            continue
        username_key = _normalize_identity(user.username)
        account_key = _normalize_identity(user.account)
        if username_key:
            users_by_identity.setdefault((username_key, source_key), user)
        if account_key:
            users_by_identity.setdefault((account_key, source_key), user)

    chat_user_ids = [chat_user.id for chat_user in target_chat_users if chat_user.id]
    existing_bindings = {
        binding.chat_user_id: binding
        for binding in (
            await db.execute(
                select(models.UserChatBinding).where(models.UserChatBinding.chat_user_id.in_(chat_user_ids))
            )
        ).scalars().all()
    }

    matched_count = 0
    matched_chat_ids: set[str] = set()
    for chat_user in target_chat_users:
        identity_key = (_normalize_identity(chat_user.username), _normalize_source(chat_user.source))
        if not identity_key[0] or not identity_key[1]:
            continue
        user = users_by_identity.get(identity_key)
        existing = existing_bindings.get(chat_user.id)
        if not user:
            if existing and existing.binding_source == "matched":
                await db.delete(existing)
            continue
        matched_chat_ids.add(chat_user.id)
        await upsert_user_chat_binding(db, user=user, chat_user=chat_user, binding_source="matched")
        matched_count += 1

    if chat_user_ids:
        stale_bindings = (
            await db.execute(
                select(models.UserChatBinding).where(
                    models.UserChatBinding.binding_source == "matched",
                    models.UserChatBinding.chat_user_id.in_(chat_user_ids),
                )
            )
        ).scalars().all()
        for binding in stale_bindings:
            if binding.chat_user_id not in matched_chat_ids:
                await db.delete(binding)

    await db.flush()
    return matched_count


async def list_user_synced_agent_ids_async(db: AsyncSession, *, user: models.User) -> list[str]:
    cache_key = f"chat_visible_agent_ids:{user.id}"
    cached = db.info.get(cache_key)
    if cached is not None:
        return cached

    rows = (
        await db.execute(
            select(models.AgentChatUserAccess.agent_id)
            .join(models.UserChatBinding, models.UserChatBinding.chat_user_id == models.AgentChatUserAccess.chat_user_id)
            .join(models.Agent, models.Agent.id == models.AgentChatUserAccess.agent_id)
            .where(
                models.UserChatBinding.user_id == user.id,
                models.AgentChatUserAccess.is_auth.is_(True),
                models.Agent.is_synced.is_(True),
            )
            .distinct()
        )
    ).scalars().all()
    values = [str(item) for item in rows if item]
    db.info[cache_key] = values
    return values


async def user_can_view_synced_agent_async(
    db: AsyncSession,
    *,
    user: models.User,
    agent_id: str,
) -> bool:
    visible_ids = await list_user_synced_agent_ids_async(db, user=user)
    return agent_id in set(visible_ids)


async def resolve_sso_chat_user_identity(
    db: AsyncSession,
    *,
    provider: models.AuthProviderConfig,
    identity: dict[str, str],
) -> models.ChatUser | None:
    username_candidates = {
        str(identity.get("username") or "").strip(),
        str(identity.get("account") or "").strip(),
    }
    username_candidates = {item for item in username_candidates if item}
    if not username_candidates:
        return None

    config = dict(provider.config or {})
    raw_source_candidates = {
        provider.key,
        provider.protocol,
        str(config.get("source") or "").strip(),
        str(config.get("source_key") or "").strip(),
        str(config.get("chat_user_source") or "").strip(),
    }
    source_candidates = {_normalize_source(item) for item in raw_source_candidates if item}

    chat_users = (
        await db.execute(select(models.ChatUser).where(models.ChatUser.username.in_(username_candidates)))
    ).scalars().all()
    for chat_user in chat_users:
        if _normalize_source(chat_user.source) in source_candidates:
            return chat_user
    return None


async def build_agent_summary_with_sync_status(
    db: AsyncSession,
    agent: models.Agent,
) -> schemas.AgentDetail:
    detail = agent_detail(agent)
    if not agent.is_synced:
        return detail
    latest_task = (
        await db.execute(
            select(models.SyncTask)
            .where(models.SyncTask.agent_id == agent.id)
            .order_by(models.SyncTask.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    payload = detail.model_dump()
    payload["sync_task_status"] = latest_task.status if latest_task else None
    payload["can_sync_users"] = bool(agent.is_synced and agent.sync_config_id and agent.external_id)
    return schemas.AgentDetail(**payload)
