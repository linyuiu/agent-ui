from __future__ import annotations

import asyncio

from .celery_app import celery_app
from ..services.chat_user_sync import run_agent_chat_user_sync_task


def _run_sync(task_id: str) -> None:
    asyncio.run(run_agent_chat_user_sync_task(task_id))


if celery_app is not None:  # pragma: no branch
    @celery_app.task(name="agent_ui.sync_agent_chat_users")
    def sync_agent_chat_users_task(task_id: str) -> None:  # pragma: no cover - celery worker path
        _run_sync(task_id)
else:  # pragma: no cover - optional dependency branch
    def sync_agent_chat_users_task(task_id: str) -> None:
        _run_sync(task_id)


def enqueue_agent_chat_user_sync(task_id: str) -> str:
    if celery_app is not None:  # pragma: no branch
        try:
            result = sync_agent_chat_users_task.delay(task_id)
            return str(result.id)
        except Exception:
            pass

    loop = asyncio.get_running_loop()
    loop.create_task(run_agent_chat_user_sync_task(task_id))
    return f"local-{task_id}"


__all__ = ["enqueue_agent_chat_user_sync", "sync_agent_chat_users_task"]
