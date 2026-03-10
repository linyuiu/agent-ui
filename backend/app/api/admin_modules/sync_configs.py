from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...services.agent_sync import create_fit2cloud_agent_sync_task
from ...services.chat_user_sync import sync_task_out
from ...tasks import enqueue_fit2cloud_agent_sync
from .common import (
    fit2cloud_fetch_async,
    mask_token,
)
from ...permissions import require_manage_menu_async

router = APIRouter()


@router.get("/agent-sync-configs", response_model=list[schemas.AgentApiConfigOut])
async def list_agent_api_configs(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AgentApiConfigOut]:
    await require_manage_menu_async(db, current_user)
    configs = (
        await db.execute(select(models.AgentApiConfig).order_by(models.AgentApiConfig.created_at.desc()))
    ).scalars().all()
    return [
        schemas.AgentApiConfigOut(
            id=config.id,
            base_url=config.base_url,
            token_hint=mask_token(config.token),
            created_at=config.created_at,
        )
        for config in configs
    ]


@router.post("/agent-sync-configs", response_model=schemas.AgentApiConfigOut, status_code=201)
async def create_agent_api_config(
    payload: schemas.AgentApiConfigCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentApiConfigOut:
    await require_manage_menu_async(db, current_user)
    base_url = payload.base_url.strip().rstrip("/")
    token = payload.token.strip()
    if not base_url or not token:
        raise HTTPException(status_code=400, detail="API domain and token are required")

    config = models.AgentApiConfig(base_url=base_url, token=token)
    db.add(config)
    try:
        await db.flush()
        created_at = config.created_at or datetime.now(timezone.utc)
        response = schemas.AgentApiConfigOut(
            id=config.id,
            base_url=config.base_url,
            token_hint=mask_token(config.token),
            created_at=created_at,
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="API config already exists") from exc
    return response


@router.put("/agent-sync-configs/{config_id}", response_model=schemas.AgentApiConfigOut)
async def update_agent_api_config(
    config_id: int,
    payload: schemas.AgentApiConfigUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentApiConfigOut:
    await require_manage_menu_async(db, current_user)
    config = await db.get(models.AgentApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    if payload.base_url:
        normalized_base_url = payload.base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise HTTPException(status_code=400, detail="API domain is required")
        config.base_url = normalized_base_url
    if payload.token:
        normalized_token = payload.token.strip()
        if not normalized_token:
            raise HTTPException(status_code=400, detail="Token is required")
        config.token = normalized_token
    response = schemas.AgentApiConfigOut(
        id=config.id,
        base_url=config.base_url,
        token_hint=mask_token(config.token),
        created_at=config.created_at,
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="API config already exists") from exc

    return response


@router.delete("/agent-sync-configs/{config_id}")
async def delete_agent_api_config(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    config = await db.get(models.AgentApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted"}


@router.get("/agent-sync-configs/{config_id}/workspaces", response_model=list[schemas.Fit2CloudWorkspace])
async def list_fit2cloud_workspaces(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.Fit2CloudWorkspace]:
    await require_manage_menu_async(db, current_user)
    config = await db.get(models.AgentApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    base_url = config.base_url.rstrip("/")
    try:
        workspace_resp = await fit2cloud_fetch_async(base_url, config.token, "/admin/api/workspace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch workspaces") from exc
    workspaces = workspace_resp.get("data") or []
    if not isinstance(workspaces, list):
        raise HTTPException(status_code=400, detail="Unexpected workspace response format")
    results: list[schemas.Fit2CloudWorkspace] = []
    for item in workspaces:
        if not isinstance(item, dict):
            continue
        workspace_id = item.get("id")
        if not workspace_id:
            continue
        results.append(
            schemas.Fit2CloudWorkspace(id=str(workspace_id), name=item.get("name") or str(workspace_id))
        )
    return results


@router.get(
    "/agent-sync-configs/{config_id}/workspaces/{workspace_id}/applications",
    response_model=list[schemas.Fit2CloudApplication],
)
async def list_fit2cloud_applications(
    config_id: int,
    workspace_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.Fit2CloudApplication]:
    await require_manage_menu_async(db, current_user)
    config = await db.get(models.AgentApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    base_url = config.base_url.rstrip("/")
    try:
        apps_resp = await fit2cloud_fetch_async(
            base_url,
            config.token,
            f"/admin/api/workspace/{workspace_id}/application",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch applications") from exc
    apps = apps_resp.get("data") or []
    if not isinstance(apps, list):
        raise HTTPException(status_code=400, detail="Unexpected application response format")
    results: list[schemas.Fit2CloudApplication] = []
    for item in apps:
        if not isinstance(item, dict):
            continue
        app_id = item.get("id")
        if not app_id:
            continue
        results.append(schemas.Fit2CloudApplication(id=str(app_id), name=item.get("name") or str(app_id)))
    return results


@router.post(
    "/agent-sync-configs/{config_id}/sync",
    response_model=schemas.AgentSyncResponse,
)
async def sync_fit2cloud_agents_by_config(
    config_id: int,
    payload: schemas.Fit2CloudSyncByConfigRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentSyncResponse:
    await require_manage_menu_async(db, current_user)
    config = await db.get(models.AgentApiConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    base_url = config.base_url.rstrip("/")
    normalized_workspaces: list[schemas.Fit2CloudWorkspaceSyncItem] = []
    if payload.workspaces:
        normalized_workspaces = payload.workspaces
    elif payload.workspace_id:
        normalized_workspaces = [
            schemas.Fit2CloudWorkspaceSyncItem(
                workspace_id=payload.workspace_id,
                workspace_name=payload.workspace_name,
                application_ids=payload.application_ids,
                sync_all=payload.sync_all,
            )
        ]

    if not normalized_workspaces:
        raise HTTPException(status_code=400, detail="No workspaces selected")

    workspace_name_map: dict[str, str] = {}
    try:
        workspace_resp = await fit2cloud_fetch_async(base_url, config.token, "/admin/api/workspace")
        workspaces = workspace_resp.get("data") or []
        if isinstance(workspaces, list):
            for item in workspaces:
                if not isinstance(item, dict):
                    continue
                workspace_id = str(item.get("id") or "")
                if not workspace_id:
                    continue
                workspace_name_map[workspace_id] = str(item.get("name") or workspace_id)
    except Exception:
        workspace_name_map = {}

    imported_total = 0
    updated_total = 0
    all_errors: list[str] = []
    created_tasks: list[models.SyncTask] = []

    for workspace_item in normalized_workspaces:
        workspace_id = workspace_item.workspace_id
        try:
            apps_resp = await fit2cloud_fetch_async(
                base_url,
                config.token,
                f"/admin/api/workspace/{workspace_id}/application",
            )
        except Exception:
            all_errors.append(f"workspace {workspace_id}: failed to fetch applications")
            continue

        apps = apps_resp.get("data") or []
        if not isinstance(apps, list):
            all_errors.append(f"workspace {workspace_id}: unexpected application response format")
            continue

        selected_ids = set(workspace_item.application_ids or [])
        if workspace_item.sync_all:
            target_apps = [item for item in apps if isinstance(item, dict)]
        else:
            if not selected_ids:
                all_errors.append(f"workspace {workspace_id}: no applications selected")
                continue
            target_apps = [
                item for item in apps if isinstance(item, dict) and str(item.get("id")) in selected_ids
            ]

        if not target_apps:
            all_errors.append(f"workspace {workspace_id}: no applications to sync")
            continue

        workspace_name = (
            workspace_item.workspace_name
            or workspace_name_map.get(str(workspace_id))
            or str(workspace_id)
        )

        for app in target_apps:
            application_id = str(app.get("id") or "").strip()
            if not application_id:
                continue
            task = await create_fit2cloud_agent_sync_task(
                db,
                current_user=current_user,
                config_id=config.id,
                workspace_id=str(workspace_id),
                workspace_name=str(workspace_name),
                application_id=application_id,
                application_name=str(app.get("name") or application_id),
                sync_chat_users=bool(payload.sync_chat_users),
            )
            created_tasks.append(task)

    await db.commit()
    for task in created_tasks:
        try:
            celery_task_id = enqueue_fit2cloud_agent_sync(task.id)
            task.celery_task_id = celery_task_id
        except Exception as exc:  # pragma: no cover - defensive scheduling branch
            all_errors.append(f"task {task.id}: {exc}")
    if created_tasks:
        await db.commit()
    return schemas.AgentSyncResponse(
        imported=0,
        updated=0,
        total=len(created_tasks),
        errors=all_errors,
        tasks=[sync_task_out(task) for task in created_tasks],
    )
