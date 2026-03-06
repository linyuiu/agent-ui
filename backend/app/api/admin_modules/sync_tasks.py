from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import require_manage_menu_async
from ...services.chat_user_sync import sync_task_out

router = APIRouter()


@router.get("/agent-sync-tasks", response_model=list[schemas.SyncTaskOut])
async def list_agent_sync_tasks(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SyncTaskOut]:
    await require_manage_menu_async(db, current_user)
    tasks = (
        await db.execute(
            select(models.SyncTask).order_by(models.SyncTask.created_at.desc()).limit(100)
        )
    ).scalars().all()
    return [sync_task_out(task) for task in tasks]
