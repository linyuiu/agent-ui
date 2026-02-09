from __future__ import annotations

from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import has_permission
from ...services.serializers import agent_detail, model_detail
from .common import (
    assert_group_permissions,
    ensure_agent_groups,
    fit2cloud_fetch,
    new_proxy_id,
    normalize_groups,
    parse_agent_chat_link,
    require_menu_edit,
    require_menu_manage,
    set_agent_upstream_chat_link,
    sync_fit2cloud_workspace_agents,
)

router = APIRouter()


@router.post("/models", response_model=schemas.ModelDetail, status_code=201)
def create_model(
    payload: schemas.ModelCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    require_menu_edit(current_user, db, "models")
    if not has_permission(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="model",
        resource_id=payload.id,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    existing = db.query(models.Model).filter(models.Model.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")

    model = models.Model(**payload.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    return model_detail(model)


@router.put("/models/{model_id}", response_model=schemas.ModelDetail)
def update_model(
    model_id: str,
    payload: schemas.ModelUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    require_menu_edit(current_user, db, "models")
    if not has_permission(
        db,
        current_user,
        action="edit",
        scope="resource",
        resource_type="model",
        resource_id=model_id,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if payload.name is not None:
        model.name = payload.name
    if payload.provider is not None:
        model.provider = payload.provider
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

    db.commit()
    db.refresh(model)
    return model_detail(model)


@router.post("/agents", response_model=schemas.AgentDetail, status_code=201)
def create_agent(
    payload: schemas.AgentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    require_menu_edit(current_user, db, "agents")
    upstream_base_url, upstream_token = parse_agent_chat_link(payload.url)
    groups = normalize_groups(payload.groups)
    if groups:
        ensure_agent_groups(db, current_user, groups)
        assert_group_permissions(db, current_user, groups)
    else:
        if not has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent",
            resource_id=None,
        ):
            raise HTTPException(status_code=403, detail="Forbidden")
    existing = (
        db.query(models.Agent)
        .filter(
            models.Agent.upstream_base_url == upstream_base_url,
            models.Agent.upstream_token == upstream_token,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = models.Agent(
        id=uuid4().hex,
        name=payload.name,
        status=payload.status,
        owner=payload.owner,
        last_run=payload.last_run,
        proxy_id=new_proxy_id(),
        upstream_base_url=upstream_base_url,
        upstream_token=upstream_token,
        url="",
        description=payload.description,
        group_name=groups[0] if groups else "",
        groups=groups,
        source_payload={},
    )
    set_agent_upstream_chat_link(
        agent,
        upstream_base_url=upstream_base_url,
        upstream_token=upstream_token,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent_detail(agent)


@router.put("/agents/{agent_id}", response_model=schemas.AgentDetail)
def update_agent(
    agent_id: str,
    payload: schemas.AgentUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    require_menu_edit(current_user, db, "agents")
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    has_group_permission = any(
        has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        )
        for group in groups
    )
    if not (
        has_permission(
            db,
            current_user,
            action="edit",
            scope="resource",
            resource_type="agent",
            resource_id=agent_id,
        )
        or has_group_permission
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.url and payload.url != agent.url:
        upstream_base_url, upstream_token = parse_agent_chat_link(payload.url)
        existing = (
            db.query(models.Agent)
            .filter(
                models.Agent.id != agent_id,
                models.Agent.upstream_base_url == upstream_base_url,
                models.Agent.upstream_token == upstream_token,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Agent url already exists")
        set_agent_upstream_chat_link(
            agent,
            upstream_base_url=upstream_base_url,
            upstream_token=upstream_token,
        )

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
            ensure_agent_groups(db, current_user, groups)
            assert_group_permissions(db, current_user, groups)
        else:
            if not has_permission(
                db,
                current_user,
                action="edit",
                scope="resource",
                resource_type="agent",
                resource_id=None,
            ):
                raise HTTPException(status_code=403, detail="Forbidden")
        agent.groups = groups
        agent.group_name = groups[0] if groups else ""

    db.commit()
    db.refresh(agent)
    return agent_detail(agent)


@router.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_menu_edit(current_user, db, "agents")
    if not has_permission(
        db,
        current_user,
        action="manage",
        scope="resource",
        resource_type="agent",
        resource_id=agent_id,
    ) and not has_permission(
        db,
        current_user,
        action="manage",
        scope="resource",
        resource_type="agent",
        resource_id=None,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.query(models.PermissionGrant).filter(
        models.PermissionGrant.scope == "resource",
        models.PermissionGrant.resource_type == "agent",
        models.PermissionGrant.resource_id == agent_id,
    ).delete(synchronize_session=False)

    db.delete(agent)
    db.commit()
    return {"status": "deleted"}


@router.post("/agents/import", response_model=schemas.AgentImportResponse)
def import_agents(
    payload: schemas.AgentImportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentImportResponse:
    require_menu_edit(current_user, db, "agents")
    try:
        response = httpx.post(
            payload.api_url,
            json={"ak": payload.ak, "sk": payload.sk},
            timeout=20,
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
        else:
            if not has_permission(
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
            set_agent_upstream_chat_link(
                agent,
                upstream_base_url=upstream_base_url,
                upstream_token=upstream_token,
            )

        imported += 1
        result_agents.append(agent_detail(agent))

    db.commit()

    return schemas.AgentImportResponse(imported=imported, agents=result_agents)


@router.post("/agents/sync-fit2cloud", response_model=schemas.AgentSyncResponse)
def sync_fit2cloud_agents(
    payload: schemas.Fit2CloudSyncRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentSyncResponse:
    require_menu_manage(current_user, db)

    base_url = payload.base_url.rstrip("/")
    token = payload.token.strip()

    def _fetch_json(path: str) -> dict:
        return fit2cloud_fetch(base_url, token, path)

    errors: list[str] = []
    imported = 0
    updated = 0

    try:
        workspace_resp = _fetch_json("/admin/api/system/workspace")
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
            apps_resp = _fetch_json(f"/admin/api/workspace/{workspace_id}/application")
        except Exception:
            errors.append(f"workspace {workspace_id}: failed to fetch applications")
            continue

        apps = apps_resp.get("data") or []
        if not isinstance(apps, list):
            continue

        workspace_imported, workspace_updated, workspace_errors = sync_fit2cloud_workspace_agents(
            db,
            current_user,
            base_url=base_url,
            token=token,
            workspace_id=str(workspace_id),
            workspace_name=str(workspace_name),
            apps=apps,
        )
        imported += workspace_imported
        updated += workspace_updated
        errors.extend(workspace_errors)

    db.commit()
    total = imported + updated
    return schemas.AgentSyncResponse(imported=imported, updated=updated, total=total, errors=errors)
