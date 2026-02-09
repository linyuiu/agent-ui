from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from .common import (
    fit2cloud_fetch,
    get_agent_api_config,
    mask_token,
    require_menu_manage,
    sync_fit2cloud_workspace_agents,
)

router = APIRouter()


@router.get("/agent-sync-configs", response_model=list[schemas.AgentApiConfigOut])
def list_agent_api_configs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentApiConfigOut]:
    require_menu_manage(current_user, db)
    configs = db.query(models.AgentApiConfig).order_by(models.AgentApiConfig.created_at.desc()).all()
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
def create_agent_api_config(
    payload: schemas.AgentApiConfigCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentApiConfigOut:
    require_menu_manage(current_user, db)
    base_url = payload.base_url.strip().rstrip("/")
    token = payload.token.strip()
    if not base_url or not token:
        raise HTTPException(status_code=400, detail="API domain and token are required")

    config = models.AgentApiConfig(base_url=base_url, token=token)
    db.add(config)
    try:
        db.flush()
        created_at = config.created_at or datetime.now(timezone.utc)
        response = schemas.AgentApiConfigOut(
            id=config.id,
            base_url=config.base_url,
            token_hint=mask_token(config.token),
            created_at=created_at,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="API config already exists") from exc
    return response


@router.put("/agent-sync-configs/{config_id}", response_model=schemas.AgentApiConfigOut)
def update_agent_api_config(
    config_id: int,
    payload: schemas.AgentApiConfigUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentApiConfigOut:
    require_menu_manage(current_user, db)
    config = db.query(models.AgentApiConfig).filter(models.AgentApiConfig.id == config_id).first()
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
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="API config already exists") from exc

    return response


@router.delete("/agent-sync-configs/{config_id}")
def delete_agent_api_config(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_menu_manage(current_user, db)
    config = db.query(models.AgentApiConfig).filter(models.AgentApiConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(config)
    db.commit()
    return {"status": "deleted"}


@router.get(
    "/agent-sync-configs/{config_id}/workspaces",
    response_model=list[schemas.Fit2CloudWorkspace],
)
def list_fit2cloud_workspaces(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.Fit2CloudWorkspace]:
    require_menu_manage(current_user, db)
    config = get_agent_api_config(db, config_id)
    base_url = config.base_url.rstrip("/")
    try:
        workspace_resp = fit2cloud_fetch(base_url, config.token, "/admin/api/system/workspace")
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
def list_fit2cloud_applications(
    config_id: int,
    workspace_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.Fit2CloudApplication]:
    require_menu_manage(current_user, db)
    config = get_agent_api_config(db, config_id)
    base_url = config.base_url.rstrip("/")
    try:
        apps_resp = fit2cloud_fetch(base_url, config.token, f"/admin/api/workspace/{workspace_id}/application")
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
def sync_fit2cloud_agents_by_config(
    config_id: int,
    payload: schemas.Fit2CloudSyncByConfigRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentSyncResponse:
    require_menu_manage(current_user, db)
    config = get_agent_api_config(db, config_id)
    base_url = config.base_url.rstrip("/")
    workspace_id = payload.workspace_id

    try:
        apps_resp = fit2cloud_fetch(base_url, config.token, f"/admin/api/workspace/{workspace_id}/application")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch applications") from exc

    apps = apps_resp.get("data") or []
    if not isinstance(apps, list):
        raise HTTPException(status_code=400, detail="Unexpected application response format")

    selected_ids = set(payload.application_ids or [])
    if not payload.sync_all and not selected_ids:
        raise HTTPException(status_code=400, detail="No applications selected")

    if payload.sync_all:
        target_apps = [item for item in apps if isinstance(item, dict)]
    else:
        target_apps = [
            item for item in apps if isinstance(item, dict) and item.get("id") in selected_ids
        ]

    workspace_name = payload.workspace_name
    if not workspace_name:
        try:
            workspace_resp = fit2cloud_fetch(base_url, config.token, "/admin/api/system/workspace")
            workspaces = workspace_resp.get("data") or []
            for item in workspaces:
                if isinstance(item, dict) and item.get("id") == workspace_id:
                    workspace_name = item.get("name") or workspace_id
                    break
        except Exception:
            workspace_name = workspace_id
    workspace_name = workspace_name or workspace_id

    imported, updated, errors = sync_fit2cloud_workspace_agents(
        db,
        current_user,
        base_url=base_url,
        token=config.token,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        apps=target_apps,
    )

    db.commit()
    total = imported + updated
    return schemas.AgentSyncResponse(imported=imported, updated=updated, total=total, errors=errors)
