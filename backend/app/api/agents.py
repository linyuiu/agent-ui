from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import has_permission, require_menu_action
from ..services.serializers import agent_detail, agent_summary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[schemas.AgentSummary])
def list_agents(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentSummary]:
    require_menu_action(db, current_user, action="view", menu_id="agents")
    agents = db.query(models.Agent).all()
    allowed = []
    for agent in agents:
        groups = list(agent.groups or [])
        if not groups and agent.group_name:
            groups = [agent.group_name]
        if has_permission(
            db,
            current_user,
            action="view",
            scope="resource",
            resource_type="agent",
            resource_id=agent.id,
        ) or any(
            has_permission(
                db,
                current_user,
                action="view",
                scope="resource",
                resource_type="agent_group",
                resource_id=group,
            )
            for group in groups
        ):
            allowed.append(agent_summary(agent))
    return allowed


@router.get("/{agent_id}", response_model=schemas.AgentDetail)
def get_agent(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    require_menu_action(db, current_user, action="view", menu_id="agents")
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    if not has_permission(
        db,
        current_user,
        action="view",
        scope="resource",
        resource_type="agent",
        resource_id=agent.id,
    ) and not any(
        has_permission(
            db,
            current_user,
            action="view",
            scope="resource",
            resource_type="agent_group",
            resource_id=group,
        )
        for group in groups
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    return agent_detail(agent)
