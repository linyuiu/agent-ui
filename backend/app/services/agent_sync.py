from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..db import AsyncSessionLocal
from ..services.chat_user_sync import create_agent_chat_user_sync_task
from ..tasks.chat_user_sync import enqueue_agent_chat_user_sync
from ..api.admin_modules.common import (
    compact_fit2cloud_source_payload,
    fit2cloud_fetch_async,
    new_proxy_id,
    set_agent_upstream_chat_link,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_fit2cloud_agent_sync_task(
    db: AsyncSession,
    *,
    current_user: models.User,
    config_id: int,
    workspace_id: str,
    workspace_name: str,
    application_id: str,
    application_name: str,
    sync_chat_users: bool,
) -> models.SyncTask:
    task = models.SyncTask(
        task_type="fit2cloud_agent_sync",
        status="pending",
        config_id=config_id,
        agent_name=application_name or "智能体同步任务",
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        external_id=application_id,
        total_steps=4 if sync_chat_users else 3,
        completed_steps=0,
        created_by=current_user.id,
        message="等待同步",
        payload={"sync_chat_users": bool(sync_chat_users)},
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


async def _ensure_agent_group(db: AsyncSession, group_name: str) -> None:
    if not group_name:
        return
    existing = (
        await db.execute(select(models.AgentGroup).where(models.AgentGroup.name == group_name))
    ).scalar_one_or_none()
    if existing:
        return
    db.add(models.AgentGroup(name=group_name, description=""))
    await db.flush()


async def _sync_single_fit2cloud_agent(
    db: AsyncSession,
    *,
    config: models.AgentApiConfig,
    workspace_id: str,
    workspace_name: str,
    application_id: str,
    application_name: str,
) -> tuple[models.Agent, str]:
    base_url = config.base_url.rstrip("/")
    detail_resp, token_resp = await asyncio.gather(
        fit2cloud_fetch_async(
            base_url,
            config.token,
            f"/admin/api/workspace/{workspace_id}/application/{application_id}",
        ),
        fit2cloud_fetch_async(
            base_url,
            config.token,
            f"/admin/api/workspace/{workspace_id}/application/{application_id}/access_token",
        ),
    )
    detail = detail_resp.get("data") or {}
    token_data = token_resp.get("data") or {}
    access_token = str(token_data.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=400, detail="Upstream missing access_token")

    await _ensure_agent_group(db, workspace_name)
    existing = (
        await db.execute(
            select(models.Agent).where(
                models.Agent.is_synced.is_(True),
                models.Agent.workspace_id == workspace_id,
                models.Agent.external_id == application_id,
            )
        )
    ).scalar_one_or_none()

    description = detail.get("desc") or detail.get("prologue") or ""
    owner = detail.get("nick_name") or detail.get("user") or "external"
    last_run = detail.get("update_time") or detail.get("create_time") or ""
    status_value = "active" if token_data.get("is_active") else "paused"
    source_payload = compact_fit2cloud_source_payload(
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        app={"id": application_id, "name": application_name},
        detail=detail,
        token_data=token_data,
    )

    if not existing:
        existing = models.Agent(
            id=uuid4().hex,
            name=str(detail.get("name") or application_name or "Agent"),
            status=status_value,
            owner=str(owner),
            last_run=str(last_run),
            proxy_id=new_proxy_id(),
            upstream_base_url=base_url,
            upstream_token=access_token,
            url="",
            description=str(description),
            group_name=workspace_name,
            groups=[workspace_name] if workspace_name else [],
            source_payload=source_payload,
            source_type="fit2cloud",
            is_synced=True,
            external_id=application_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            sync_config_id=config.id,
        )
        set_agent_upstream_chat_link(
            existing,
            upstream_base_url=base_url,
            upstream_token=access_token,
        )
        db.add(existing)
        await db.flush()
        return existing, "imported"

    existing.name = str(detail.get("name") or application_name or existing.name)
    existing.status = status_value
    existing.owner = str(owner)
    existing.last_run = str(last_run)
    existing.description = str(description)
    existing.group_name = workspace_name
    existing.groups = [workspace_name] if workspace_name else []
    existing.source_payload = source_payload
    existing.source_type = "fit2cloud"
    existing.is_synced = True
    existing.external_id = application_id
    existing.workspace_id = workspace_id
    existing.workspace_name = workspace_name
    existing.sync_config_id = config.id
    set_agent_upstream_chat_link(
        existing,
        upstream_base_url=base_url,
        upstream_token=access_token,
    )
    await db.flush()
    return existing, "updated"


async def run_fit2cloud_agent_sync_task(task_id: str) -> None:
    async with AsyncSessionLocal() as db:
        task = await db.get(models.SyncTask, task_id)
        if not task:
            return

        config = await db.get(models.AgentApiConfig, task.config_id) if task.config_id else None
        if not config:
            await _mark_task_failed(db, task, "同步任务缺少 API 配置")
            return
        if not task.workspace_id or not task.external_id:
            await _mark_task_failed(db, task, "同步任务缺少工作空间或应用标识")
            return

        task.status = "running"
        task.started_at = _now()
        task.updated_at = _now()
        task.message = "正在同步智能体"
        task.error = ""
        await db.commit()

        try:
            agent, result = await _sync_single_fit2cloud_agent(
                db,
                config=config,
                workspace_id=task.workspace_id,
                workspace_name=task.workspace_name or task.workspace_id,
                application_id=task.external_id,
                application_name=task.agent_name,
            )
            task.agent_id = agent.id
            task.completed_steps = 3
            task.total_records = 1
            task.processed_records = 1
            task.message = f"智能体已{ '新增' if result == 'imported' else '更新' }"
            task.updated_at = _now()
            await db.commit()

            if bool((task.payload or {}).get("sync_chat_users")):
                chat_task = await create_agent_chat_user_sync_task(
                    db,
                    current_user=models.User(id=task.created_by or 0),
                    agent=agent,
                    config_id=int(config.id),
                )
                await db.commit()
                try:
                    chat_task.celery_task_id = enqueue_agent_chat_user_sync(chat_task.id)
                    await db.commit()
                except Exception as exc:
                    chat_task.status = "failed"
                    chat_task.error = str(exc)
                    chat_task.message = str(exc)
                    await db.commit()
                payload = dict(task.payload or {})
                payload["chat_sync_task_id"] = chat_task.id
                task.payload = payload
                task.completed_steps = task.total_steps
                task.message = f"{task.message}，已创建对话用户同步任务"
            else:
                task.completed_steps = task.total_steps

            task.status = "completed"
            task.finished_at = _now()
            task.updated_at = _now()
            await db.commit()
        except Exception as exc:  # pragma: no cover - task failure path
            await _mark_task_failed(db, task, str(exc))
