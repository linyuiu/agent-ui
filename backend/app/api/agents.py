from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import evaluate_permission_async, is_super_admin, require_menu_action_async
from ..services.chat_user_sync import build_agent_chat_user_view, user_can_view_synced_agent_async
from ..services.serializers import agent_detail, agent_summary

router = APIRouter(prefix="/agents", tags=["agents"])


def _resolve_agent_groups(agent: models.Agent) -> list[str]:
    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in groups:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


async def _can_view_agent_async(db: AsyncSession, user: models.User, agent: models.Agent) -> bool:
    if is_super_admin(user):
        return True
    groups = _resolve_agent_groups(agent)
    permission = await evaluate_permission_async(
        db,
        user,
        action="view",
        scope="resource",
        resource_type="agent",
        resource_id=str(agent.id),
        resource_attrs={"groups": groups},
    )
    if permission.allowed:
        return True
    if agent.is_synced:
        return await user_can_view_synced_agent_async(db, user=user, agent_id=str(agent.id))
    return False


async def _can_manage_agent_chat_users_async(
    db: AsyncSession,
    user: models.User,
    agent: models.Agent,
) -> bool:
    if is_super_admin(user):
        return True
    groups = _resolve_agent_groups(agent)
    permission = await evaluate_permission_async(
        db,
        user,
        action="manage",
        scope="resource",
        resource_type="agent",
        resource_id=str(agent.id),
        resource_attrs={"groups": groups},
    )
    return permission.allowed


@router.get("", response_model=list[schemas.AgentSummary])
async def list_agents(
    include_description: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.AgentSummary]:
    await require_menu_action_async(db, current_user, action="view", menu_id="agents")
    statement = select(models.Agent)
    if not include_description:
        statement = statement.options(
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
    agents = (await db.execute(statement.order_by(models.Agent.created_at.desc()))).scalars().all()
    if is_super_admin(current_user):
        return [agent_summary(agent, include_description=include_description) for agent in agents]

    visible: list[schemas.AgentSummary] = []
    for agent in agents:
        if await _can_view_agent_async(db, current_user, agent):
            visible.append(agent_summary(agent, include_description=include_description))
    return visible


@router.get("/{agent_id}", response_model=schemas.AgentDetail)
async def get_agent(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentDetail:
    await require_menu_action_async(db, current_user, action="view", menu_id="agents")
    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not await _can_view_agent_async(db, current_user, agent):
        raise HTTPException(status_code=403, detail="访问需要权限")
    return agent_detail(agent)


@router.get("/{agent_id}/chat-users", response_model=schemas.AgentChatUserView)
async def get_agent_chat_users(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.AgentChatUserView:
    agent = (await db.execute(select(models.Agent).where(models.Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not await _can_view_agent_async(db, current_user, agent):
        raise HTTPException(status_code=403, detail="访问需要权限")
    manageable = await _can_manage_agent_chat_users_async(db, current_user, agent)
    return await build_agent_chat_user_view(
        db,
        agent_id=agent_id,
        manageable=manageable,
        sync_supported=bool(agent.is_synced and agent.sync_config_id and agent.external_id),
    )
