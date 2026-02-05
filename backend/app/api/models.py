from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import has_permission, require_menu_action
from ..services.serializers import model_detail, model_summary

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[schemas.ModelSummary])
def list_models(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.ModelSummary]:
    require_menu_action(db, current_user, action="view", menu_id="models")
    models_list = db.query(models.Model).all()
    allowed = [
        model_summary(model)
        for model in models_list
        if has_permission(
            db,
            current_user,
            action="view",
            scope="resource",
            resource_type="model",
            resource_id=model.id,
        )
    ]
    return allowed


@router.get("/{model_id}", response_model=schemas.ModelDetail)
def get_model(
    model_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    require_menu_action(db, current_user, action="view", menu_id="models")
    model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not has_permission(
        db,
        current_user,
        action="view",
        scope="resource",
        resource_type="model",
        resource_id=model.id,
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    return model_detail(model)
