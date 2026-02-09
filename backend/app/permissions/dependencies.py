from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import User
from .permissions import evaluate_permission, require_menu_action


def require_menu_user(*, action: str, menu_id: str):
    def _dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        require_menu_action(db, current_user, action=action, menu_id=menu_id)
        return current_user

    return _dependency


def require_resource_user(
    *,
    action: str,
    resource_type: str,
    resource_id_param: str | None = None,
    resource_id: str | None = None,
    scope: str = "resource",
    resource_attrs_builder: Callable[[Request], dict] | None = None,
):
    def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        resolved_resource_id = resource_id
        if resolved_resource_id is None and resource_id_param:
            value = request.path_params.get(resource_id_param)
            resolved_resource_id = str(value) if value is not None else None
        resource_attrs = (
            resource_attrs_builder(request)
            if resource_attrs_builder is not None
            else None
        )
        decision = evaluate_permission(
            db,
            current_user,
            action=action,
            scope=scope,
            resource_type=resource_type,
            resource_id=resolved_resource_id,
            resource_attrs=resource_attrs,
        )
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return current_user

    return _dependency
