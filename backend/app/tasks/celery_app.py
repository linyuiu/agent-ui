from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from celery import Celery
except ImportError:  # pragma: no cover - optional dependency
    Celery = None

from ..config import settings

celery_app = None

if Celery is not None:  # pragma: no branch
    celery_app = Celery(
        "agent_ui",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=False,
    )

__all__ = ["celery_app", "Celery"]
