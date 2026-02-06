from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import has_permission, require_menu_action

router = APIRouter(prefix="/agent-groups", tags=["agent-groups"])


def _to_out(group: models.AgentGroup) -> schemas.AgentGroupOut:
    return schemas.AgentGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
    )


@router.get("", response_model=list[schemas.AgentGroupOut])
def list_agent_groups(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentGroupOut]:
    require_menu_action(db, current_user, action="view", menu_id="agents")
    groups = db.query(models.AgentGroup).order_by(models.AgentGroup.name.asc()).all()
    if current_user.role == "admin":
        return [_to_out(group) for group in groups]

    allowed: list[schemas.AgentGroupOut] = []
    for group in groups:
        if has_permission(
            db,
            current_user,
            action="view",
            scope="resource",
            resource_type="agent_group",
            resource_id=None,
        ) or has_permission(
            db,
            current_user,
            action="view",
            scope="resource",
            resource_type="agent_group",
            resource_id=group.name,
        ):
            allowed.append(_to_out(group))
    return allowed


@router.post("", response_model=schemas.AgentGroupOut, status_code=201)
def create_agent_group(
    payload: schemas.AgentGroupCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentGroupOut:
    require_menu_action(db, current_user, action="edit", menu_id="agents")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    existing = db.query(models.AgentGroup).filter(models.AgentGroup.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Group already exists")

    group = models.AgentGroup(name=name, description=payload.description or "")
    db.add(group)

    grant = models.PermissionGrant(
        subject_type="user",
        subject_id=str(current_user.id),
        scope="resource",
        resource_type="agent_group",
        resource_id=name,
        action="manage",
    )
    db.add(grant)

    db.commit()
    db.refresh(group)
    return _to_out(group)
