from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, load_only

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import (
    can_view_agent,
    get_user_access,
    is_super_admin,
    require_menu_action,
)
from ..services.serializers import agent_detail, agent_summary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[schemas.AgentSummary])
def list_agents(
    include_description: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentSummary]:
    require_menu_action(db, current_user, action="view", menu_id="agents")
    query = db.query(models.Agent)
    if not include_description:
        query = query.options(
            load_only(
                models.Agent.id,
                models.Agent.name,
                models.Agent.status,
                models.Agent.owner,
                models.Agent.last_run,
                models.Agent.url,
                models.Agent.group_name,
                models.Agent.groups,
                models.Agent.source_type,
                models.Agent.is_synced,
            )
    )
    agents = query.all()

    if is_super_admin(current_user):
        return [
            agent_summary(agent, include_description=include_description)
            for agent in agents
        ]

    access = get_user_access(db, current_user)
    allowed = []
    for agent in agents:
        groups = list(agent.groups or [])
        if not groups and agent.group_name:
            groups = [agent.group_name]
        if can_view_agent(access, str(agent.id), groups):
            allowed.append(agent_summary(agent, include_description=include_description))
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

    if is_super_admin(current_user):
        return agent_detail(agent)

    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    access = get_user_access(db, current_user)
    if not can_view_agent(access, str(agent.id), groups):
        raise HTTPException(status_code=403, detail="Forbidden")

    return agent_detail(agent)
