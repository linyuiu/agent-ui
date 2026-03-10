from __future__ import annotations

import asyncio

from .celery_app import celery_app
from ..services.agent_sync import run_fit2cloud_agent_sync_task


def _run_sync(task_id: str) -> None:
    asyncio.run(run_fit2cloud_agent_sync_task(task_id))


if celery_app is not None:  # pragma: no branch
    @celery_app.task(name="agent_ui.sync_fit2cloud_agent")
    def sync_fit2cloud_agent_task(task_id: str) -> None:  # pragma: no cover - celery worker path
        _run_sync(task_id)
else:  # pragma: no cover - optional dependency branch
    def sync_fit2cloud_agent_task(task_id: str) -> None:
        _run_sync(task_id)


def enqueue_fit2cloud_agent_sync(task_id: str) -> str:
    if celery_app is not None:  # pragma: no branch
        try:
            result = sync_fit2cloud_agent_task.delay(task_id)
            return str(result.id)
        except Exception:
            pass

    loop = asyncio.get_running_loop()
    loop.create_task(run_fit2cloud_agent_sync_task(task_id))
    return f"local-{task_id}"


__all__ = ["enqueue_fit2cloud_agent_sync", "sync_fit2cloud_agent_task"]
