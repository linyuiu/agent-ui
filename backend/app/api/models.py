from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..permissions.dependencies import require_menu_user
from ..permissions import can_view_model, get_user_access, is_super_admin
from ..services.serializers import model_detail, model_summary

router = APIRouter(prefix="/models", tags=["models"])


def _list_models_sync(db: Session, current_user: models.User) -> list[schemas.ModelSummary]:
    models_list = db.query(models.Model).all()

    if is_super_admin(current_user):
        return [model_summary(model) for model in models_list]

    access = get_user_access(db, current_user)
    allowed = [
        model_summary(model)
        for model in models_list
        if can_view_model(access, str(model.id))
    ]
    return allowed


def _get_model_sync(db: Session, model_id: str, current_user: models.User) -> schemas.ModelDetail:
    model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not is_super_admin(current_user):
        access = get_user_access(db, current_user)
        if not can_view_model(access, str(model.id)):
            raise HTTPException(status_code=403, detail="Forbidden")

    return model_detail(model)


@router.get("", response_model=list[schemas.ModelSummary])
async def list_models(
    current_user: models.User = Depends(require_menu_user(action="view", menu_id="models")),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.ModelSummary]:
    return await db.run_sync(lambda sync_db: _list_models_sync(sync_db, current_user))


@router.get("/{model_id}", response_model=schemas.ModelDetail)
async def get_model(
    model_id: str,
    current_user: models.User = Depends(require_menu_user(action="view", menu_id="models")),
    db: AsyncSession = Depends(get_db),
) -> schemas.ModelDetail:
    return await db.run_sync(lambda sync_db: _get_model_sync(sync_db, model_id, current_user))
