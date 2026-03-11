from __future__ import annotations

from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import (
    evaluate_permission_async,
    has_permission,
    has_permission_async,
    is_super_admin,
    require_manage_menu_async,
    require_menu_action_async,
)
from ...services.chat_user_sync import create_agent_chat_user_sync_task, sync_task_out
from ...services.chat_user_sync import update_agent_chat_user_accesses
from ...services.serializers import agent_detail, model_detail
from ...tasks import enqueue_agent_chat_user_sync
from .common import (
    fit2cloud_fetch_async,
    new_proxy_id,
    normalize_groups,
    parse_agent_chat_link,
    set_agent_upstream_chat_link,
    sync_fit2cloud_workspace_agents_async,
)

router = APIRouter()


def _normalize_manual_agent_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Agent URL is required")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Agent URL must be an absolute http(s) URL")
    return candidate


async def _ensure_agent_groups_async(
    db: AsyncSession,
    current_user: models.User,
    groups: list[str],
) -> None:
    if not groups:
        return
    existing = set(
        (
            await db.execute(
                select(models.AgentGroup.name).where(models.AgentGroup.name.in_(groups))
            )
        ).scalars().all()
    )
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
    await db.flush()


async def _assert_group_permissions_async(
    db: AsyncSession,
    current_user: models.User,
    groups: list[str],
) -> None:
    if not groups:
        return
    if await has_permission_async(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="agent",
        resource_id=None,
    ):
        return
    for group in groups:
        if not await has_permission_async(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        ):
            raise HTTPException(status_code=403, detail="访问需要权限")


def _import_agents_sync(
    db: Session,
    current_user: models.User,
    items: list,
) -> schemas.AgentImportResponse:
    imported = 0
    result_agents: list[schemas.AgentDetail] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url") or item.get("link")
        if not url:
            continue
        upstream_base_url, upstream_token = parse_agent_chat_link(str(url))

        name = item.get("name") or item.get("title") or f"Agent {idx + 1}"
        status_value = item.get("status") or "active"
        owner = item.get("owner") or "external"
        description = item.get("description") or ""
        source_payload = dict(item)
        source_payload.pop("url", None)
        source_payload.pop("link", None)
        raw_groups = item.get("groups")
        if isinstance(raw_groups, list):
            groups = normalize_groups([str(group) for group in raw_groups])
        else:
            group_name = item.get("group") or item.get("group_name")
            if not group_name and isinstance(item.get("tags"), list) and item.get("tags"):
                group_name = item.get("tags")[0]
            groups = normalize_groups([str(group_name)]) if group_name else []
        last_run = item.get("last_run") or item.get("lastRun") or ""

        if groups:
            ensure_agent_groups(db, current_user, groups)
            assert_group_permissions(db, current_user, groups)
        elif not has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent",
            resource_id=None,
        ):
            raise HTTPException(status_code=403, detail="Forbidden")

        agent = (
            db.query(models.Agent)
            .filter(
                models.Agent.upstream_base_url == upstream_base_url,
                models.Agent.upstream_token == upstream_token,
            )
            .first()
        )
        if not agent:
            agent = models.Agent(
                id=uuid4().hex,
                name=name,
                status=status_value,
                owner=owner,
                last_run=last_run,
                proxy_id=new_proxy_id(),
                upstream_base_url=upstream_base_url,
                upstream_token=upstream_token,
                url="",
                description=description,
                group_name=groups[0] if groups else "",
                groups=groups,
                source_payload=source_payload,
                source_type="api_sync",
                is_synced=True,
            )
            set_agent_upstream_chat_link(
                agent,
                upstream_base_url=upstream_base_url,
                upstream_token=upstream_token,
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
            agent.source_payload = source_payload
            if not agent.source_type:
                agent.source_type = "api_sync"
            agent.is_synced = True
            set_agent_upstream_chat_link(
                agent,
                upstream_base_url=upstream_base_url,
                upstream_token=upstream_token,
            )

        imported += 1
        result_agents.append(agent_detail(agent))

    db.commit()
    return schemas.AgentImportResponse(imported=imported, agents=result_agents)


@router.post("/models", response_model=schemas.ModelDetail, status_code=201)
async def create_model(
    payload: schemas.ModelCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ModelDetail:
    await require_menu_action_async(db, current_user, action="edit", menu_id="models")
    model_id = (payload.id or "").strip() or f"model-{uuid4().hex[:12]}"
    if not await has_permission_async(
        db, current_user, action="edit", scope="resource", resource_type="model", resource_id=model_id
    ) and not await has_permission_async(
        db, current_user, action="edit", scope="resource", resource_type="model", resource_id=None
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")

    existing = (await db.execute(select(models.Model).where(models.Model.id == model_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")

    model = models.Model(
        id=model_id,
        name=payload.name,
        provider=payload.provider,
        model_type=payload.model_type,
        base_model=payload.base_model,
        api_url=payload.api_url,
        api_key=payload.api_key,
        parameters=[item.model_dump() for item in payload.parameters],
        status=payload.status,
        context_length=payload.context_length,
        description=payload.description,
        pricing=payload.pricing,
        release=payload.release,
        tags=payload.tags,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model_detail(model)


@router.put("/models/{model_id}", response_model=schemas.ModelDetail)
async def update_model(
    model_id: str,
    payload: schemas.ModelUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ModelDetail:
    await require_menu_action_async(db, current_user, action="edit", menu_id="models")
    if not await has_permission_async(
        db, current_user, action="edit", scope="resource", resource_type="model", resource_id=model_id
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")

    model = (await db.execute(select(models.Model).where(models.Model.id == model_id))).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if payload.name is not None:
        model.name = payload.name
    if payload.provider is not None:
        model.provider = payload.provider
    if payload.model_type is not None:
        model.model_type = payload.model_type
    if payload.base_model is not None:
        model.base_model = payload.base_model
    if payload.api_url is not None:
        normalized_url = payload.api_url.strip()
        if not normalized_url:
            raise HTTPException(status_code=400, detail="api_url cannot be empty")
        model.api_url = normalized_url
    if payload.api_key is not None:
        normalized_key = payload.api_key.strip()
        if not normalized_key:
            raise HTTPException(status_code=400, detail="api_key cannot be empty")
        model.api_key = normalized_key
    if payload.parameters is not None:
        model.parameters = [item.model_dump() for item in payload.parameters]
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

    await db.commit()
    await db.refresh(model)
    return model_detail(model)


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_menu_action_async(db, current_user, action="edit", menu_id="models")
    if not await has_permission_async(
        db, current_user, action="manage", scope="resource", resource_type="model", resource_id=model_id
    ) and not await has_permission_async(
        db, current_user, action="manage", scope="resource", resource_type="model", resource_id=None
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")

    model = (await db.execute(select(models.Model).where(models.Model.id == model_id))).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    await db.execute(
        delete(models.PermissionGrant).where(
            models.PermissionGrant.scope == "resource",
            models.PermissionGrant.resource_type == "model",
            models.PermissionGrant.resource_id == model_id,
        )
    )

    await db.delete(model)
    await db.commit()
    return {"status": "deleted"}


@router.post("/agents", response_model=schemas.AgentDetail, status_code=201)
async def create_agent(
    payload: schemas.AgentCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentDetail:
    await require_menu_action_async(db, current_user, action="edit", menu_id="agents")
    manual_url = _normalize_manual_agent_url(payload.url)
    groups = normalize_groups(payload.groups)
    if groups:
        await _ensure_agent_groups_async(db, current_user, groups)
        await _assert_group_permissions_async(db, current_user, groups)
    elif not await has_permission_async(
        db, current_user, action="edit", scope="resource", resource_type="agent", resource_id=None
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")
    existing = (
        await db.execute(
            select(models.Agent).where(
                models.Agent.is_synced.is_(False),
                models.Agent.url == manual_url,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = models.Agent(
        id=uuid4().hex,
        name=payload.name,
        status=payload.status,
        owner=payload.owner,
        last_run=payload.last_run,
        proxy_id=new_proxy_id(),
        upstream_base_url="",
        upstream_token="",
        url=manual_url,
        description=payload.description,
        group_name=groups[0] if groups else "",
        groups=groups,
        source_payload={},
        is_synced=False,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent_detail(agent)


@router.put("/agents/{agent_id}", response_model=schemas.AgentDetail)
async def update_agent(
    agent_id: str,
    payload: schemas.AgentUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentDetail:
    await require_menu_action_async(db, current_user, action="edit", menu_id="agents")
    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    is_synced_agent = bool(agent.is_synced)

    if is_synced_agent:
        if any(
            value is not None
            for value in (
                payload.name,
                payload.url,
                payload.owner,
                payload.last_run,
                payload.description,
                payload.groups,
            )
        ):
            raise HTTPException(
                status_code=400,
                detail="Synced agents only allow status updates",
            )

    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    has_group_permission = False
    for group in groups:
        if await has_permission_async(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        ):
            has_group_permission = True
            break
    if not (
        await has_permission_async(
            db, current_user, action="edit", scope="resource", resource_type="agent", resource_id=agent_id
        )
        or has_group_permission
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")

    if payload.url is not None and payload.url != agent.url:
        manual_url = _normalize_manual_agent_url(payload.url)
        existing = (
            await db.execute(
                select(models.Agent).where(
                    models.Agent.id != agent_id,
                    models.Agent.is_synced.is_(False),
                    models.Agent.url == manual_url,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Agent url already exists")
        agent.url = manual_url
        agent.upstream_base_url = ""
        agent.upstream_token = ""

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
        groups = normalize_groups(payload.groups)
        if groups:
            await _ensure_agent_groups_async(db, current_user, groups)
            await _assert_group_permissions_async(db, current_user, groups)
        elif not await has_permission_async(
            db, current_user, action="edit", scope="resource", resource_type="agent", resource_id=None
        ):
            raise HTTPException(status_code=403, detail="访问需要权限")
        agent.groups = groups
        agent.group_name = groups[0] if groups else ""

    await db.commit()
    await db.refresh(agent)
    return agent_detail(agent)


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_menu_action_async(db, current_user, action="edit", menu_id="agents")
    if not await has_permission_async(
        db, current_user, action="manage", scope="resource", resource_type="agent", resource_id=agent_id
    ) and not await has_permission_async(
        db, current_user, action="manage", scope="resource", resource_type="agent", resource_id=None
    ):
        raise HTTPException(status_code=403, detail="访问需要权限")

    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.execute(
        delete(models.PermissionGrant).where(
            models.PermissionGrant.scope == "resource",
            models.PermissionGrant.resource_type == "agent",
            models.PermissionGrant.resource_id == agent_id,
        )
    )
    await db.execute(delete(models.AgentChatUserAccess).where(models.AgentChatUserAccess.agent_id == agent_id))
    await db.execute(delete(models.SyncTask).where(models.SyncTask.agent_id == agent_id))

    await db.delete(agent)
    await db.commit()
    return {"status": "deleted"}


@router.post("/agents/{agent_id}/sync-chat-users", response_model=schemas.SyncTaskOut, status_code=202)
async def sync_agent_chat_users(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SyncTaskOut:
    await require_manage_menu_async(db, current_user)
    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.is_synced:
        raise HTTPException(status_code=400, detail="仅同步创建的智能体支持同步对话用户")
    if not agent.sync_config_id:
        raise HTTPException(status_code=400, detail="智能体缺少同步配置")
    if not agent.external_id:
        raise HTTPException(status_code=400, detail="智能体缺少外部应用标识")

    task = await create_agent_chat_user_sync_task(
        db,
        current_user=current_user,
        agent=agent,
        config_id=int(agent.sync_config_id),
    )
    await db.commit()
    try:
        task.celery_task_id = enqueue_agent_chat_user_sync(task.id)
        await db.commit()
    except Exception as exc:  # pragma: no cover - defensive scheduling branch
        task.status = "failed"
        task.error = str(exc)
        task.message = str(exc)
        await db.commit()
    return sync_task_out(task)


@router.put("/agents/{agent_id}/chat-users", response_model=schemas.AgentChatUserView)
async def update_agent_chat_users(
    agent_id: str,
    payload: schemas.AgentChatUserAccessUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentChatUserView:
    await require_menu_action_async(db, current_user, action="edit", menu_id="agents")

    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.is_synced:
        raise HTTPException(status_code=400, detail="仅同步创建的智能体支持授权对话用户")
    if not agent.sync_config_id:
        raise HTTPException(status_code=400, detail="智能体缺少同步配置")

    agent_groups = list(agent.groups or [])
    if not agent_groups and agent.group_name:
        agent_groups = [agent.group_name]
    decision = await evaluate_permission_async(
        db,
        current_user,
        action="manage",
        scope="resource",
        resource_type="agent",
        resource_id=agent_id,
        resource_attrs={"groups": agent_groups},
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="访问需要权限")

    config = await db.get(models.AgentApiConfig, int(agent.sync_config_id))
    if not config:
        raise HTTPException(status_code=400, detail="未找到同步配置")

    return await update_agent_chat_user_accesses(
        db,
        agent=agent,
        config=config,
        group_id=payload.group_id,
        updates=payload.users,
    )


@router.post("/agents/import", response_model=schemas.AgentImportResponse)
async def import_agents(
    payload: schemas.AgentImportRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentImportResponse:
    await require_menu_action_async(db, current_user, action="edit", menu_id="agents")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                payload.api_url,
                json={"ak": payload.ak, "sk": payload.sk},
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

    return await db.run_sync(lambda sync_db: _import_agents_sync(sync_db, current_user, items))


@router.post("/agents/sync-fit2cloud", response_model=schemas.AgentSyncResponse)
async def sync_fit2cloud_agents(
    payload: schemas.Fit2CloudSyncRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentSyncResponse:
    await require_manage_menu_async(db, current_user)

    base_url = payload.base_url.rstrip("/")
    token = payload.token.strip()

    errors: list[str] = []
    imported = 0
    updated = 0

    try:
        workspace_resp = await fit2cloud_fetch_async(base_url, token, "/admin/api/workspace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch workspaces") from exc

    workspaces = workspace_resp.get("data") or []
    if not isinstance(workspaces, list):
        raise HTTPException(status_code=400, detail="Unexpected workspace response format")

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        workspace_id = workspace.get("id")
        workspace_name = workspace.get("name") or workspace_id or "workspace"
        if not workspace_id:
            continue
        try:
            apps_resp = await fit2cloud_fetch_async(
                base_url,
                token,
                f"/admin/api/workspace/{workspace_id}/application",
            )
        except Exception:
            errors.append(f"workspace {workspace_id}: failed to fetch applications")
            continue

        apps = apps_resp.get("data") or []
        if not isinstance(apps, list):
            continue

        workspace_imported, workspace_updated, workspace_errors = await sync_fit2cloud_workspace_agents_async(
            db,
            current_user,
            base_url=base_url,
            token=token,
            config_id=None,
            workspace_id=str(workspace_id),
            workspace_name=str(workspace_name),
            apps=apps,
        )
        imported += workspace_imported
        updated += workspace_updated
        errors.extend(workspace_errors)

    await db.commit()
    total = imported + updated
    return schemas.AgentSyncResponse(imported=imported, updated=updated, total=total, errors=errors)
