from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import require_menu_action_async

router = APIRouter()


def _chat_user_catalog_item_from_row(
    chat_user: models.ChatUser,
    *,
    system_user_id: int | None,
    system_username: str | None,
    system_account: str | None,
    accessible_agent_count: int | None,
) -> schemas.ChatUserCatalogItem:
    return schemas.ChatUserCatalogItem(
        id=chat_user.id,
        username=chat_user.username,
        email=chat_user.email or "",
        phone=chat_user.phone or "",
        is_active=bool(chat_user.is_active),
        nick_name=chat_user.nick_name or "",
        source=chat_user.source or "",
        create_time=chat_user.create_time or "",
        update_time=chat_user.update_time or "",
        user_group_ids=list(chat_user.user_group_ids or []),
        user_group_names=list(chat_user.user_group_names or []),
        synced_at=chat_user.synced_at,
        is_bound=system_user_id is not None,
        system_user_id=system_user_id,
        system_username=system_username or "",
        system_account=system_account or "",
        accessible_agent_count=int(accessible_agent_count or 0),
    )


@router.get("/chat-users", response_model=schemas.ChatUserCatalogResponse)
async def list_chat_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str = Query(default=""),
    source: list[str] = Query(default_factory=list),
    binding: str = Query(default=""),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ChatUserCatalogResponse:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")

    binding_value = binding.strip().lower()
    if binding_value not in {"", "bound", "unbound"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid binding filter")

    keyword = q.strip()
    source_values = [item.strip() for item in source if item and item.strip()]

    binding_subquery = (
        select(
            models.UserChatBinding.chat_user_id.label("chat_user_id"),
            models.User.id.label("system_user_id"),
            models.User.username.label("system_username"),
            models.User.account.label("system_account"),
        )
        .join(models.User, models.User.id == models.UserChatBinding.user_id)
        .subquery()
    )
    access_subquery = (
        select(
            models.AgentChatUserAccess.chat_user_id.label("chat_user_id"),
            func.count(func.distinct(models.AgentChatUserAccess.agent_id)).label("accessible_agent_count"),
        )
        .where(models.AgentChatUserAccess.is_auth.is_(True))
        .group_by(models.AgentChatUserAccess.chat_user_id)
        .subquery()
    )

    filters = []
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                models.ChatUser.username.ilike(pattern),
                models.ChatUser.nick_name.ilike(pattern),
                models.ChatUser.email.ilike(pattern),
                models.ChatUser.phone.ilike(pattern),
                binding_subquery.c.system_username.ilike(pattern),
                binding_subquery.c.system_account.ilike(pattern),
            )
        )
    if source_values:
        filters.append(models.ChatUser.source.in_(source_values))
    if binding_value == "bound":
        filters.append(binding_subquery.c.system_user_id.is_not(None))
    elif binding_value == "unbound":
        filters.append(binding_subquery.c.system_user_id.is_(None))

    total_stmt = (
        select(func.count())
        .select_from(models.ChatUser)
        .outerjoin(binding_subquery, binding_subquery.c.chat_user_id == models.ChatUser.id)
    )
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = int((await db.execute(total_stmt)).scalar_one() or 0)

    query = (
        select(
            models.ChatUser,
            binding_subquery.c.system_user_id,
            binding_subquery.c.system_username,
            binding_subquery.c.system_account,
            access_subquery.c.accessible_agent_count,
        )
        .outerjoin(binding_subquery, binding_subquery.c.chat_user_id == models.ChatUser.id)
        .outerjoin(access_subquery, access_subquery.c.chat_user_id == models.ChatUser.id)
    )
    if filters:
        query = query.where(*filters)
    query = query.order_by(
        models.ChatUser.synced_at.desc(),
        models.ChatUser.username.asc(),
        models.ChatUser.id.asc(),
    ).offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(query)).all()
    source_rows = (
        await db.execute(
            select(models.ChatUser.source)
            .where(models.ChatUser.source.is_not(None), models.ChatUser.source != "")
            .distinct()
            .order_by(models.ChatUser.source.asc())
        )
    ).scalars().all()

    return schemas.ChatUserCatalogResponse(
        items=[
            _chat_user_catalog_item_from_row(
                row[0],
                system_user_id=row[1],
                system_username=row[2],
                system_account=row[3],
                accessible_agent_count=row[4],
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        sources=[str(value) for value in source_rows if str(value).strip()],
    )


@router.get("/chat-users/{chat_user_id}/agents", response_model=schemas.ChatUserAccessibleAgentsResponse)
async def get_chat_user_accessible_agents(
    chat_user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ChatUserAccessibleAgentsResponse:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")

    binding_subquery = (
        select(
            models.UserChatBinding.chat_user_id.label("chat_user_id"),
            models.User.id.label("system_user_id"),
            models.User.username.label("system_username"),
            models.User.account.label("system_account"),
        )
        .join(models.User, models.User.id == models.UserChatBinding.user_id)
        .subquery()
    )
    access_subquery = (
        select(
            models.AgentChatUserAccess.chat_user_id.label("chat_user_id"),
            func.count(func.distinct(models.AgentChatUserAccess.agent_id)).label("accessible_agent_count"),
        )
        .where(models.AgentChatUserAccess.is_auth.is_(True))
        .group_by(models.AgentChatUserAccess.chat_user_id)
        .subquery()
    )

    chat_user_row = (
        await db.execute(
            select(
                models.ChatUser,
                binding_subquery.c.system_user_id,
                binding_subquery.c.system_username,
                binding_subquery.c.system_account,
                access_subquery.c.accessible_agent_count,
            )
            .outerjoin(binding_subquery, binding_subquery.c.chat_user_id == models.ChatUser.id)
            .outerjoin(access_subquery, access_subquery.c.chat_user_id == models.ChatUser.id)
            .where(models.ChatUser.id == chat_user_id)
            .limit(1)
        )
    ).first()
    if not chat_user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat user not found")

    chat_user_item = _chat_user_catalog_item_from_row(
        chat_user_row[0],
        system_user_id=chat_user_row[1],
        system_username=chat_user_row[2],
        system_account=chat_user_row[3],
        accessible_agent_count=chat_user_row[4],
    )

    access_rows = (
        await db.execute(
            select(
                models.Agent.id,
                models.Agent.name,
                models.Agent.status,
                models.Agent.owner,
                models.Agent.workspace_name,
                models.Agent.source_type,
                models.Agent.last_run,
                models.AgentChatUserAccess.group_id,
                models.AgentChatUserAccess.group_name,
            )
            .join(
                models.Agent,
                and_(
                    models.Agent.id == models.AgentChatUserAccess.agent_id,
                    models.AgentChatUserAccess.is_auth.is_(True),
                ),
            )
            .where(models.AgentChatUserAccess.chat_user_id == chat_user_id)
            .order_by(models.Agent.name.asc(), models.AgentChatUserAccess.group_name.asc())
        )
    ).all()

    accessible_agents: OrderedDict[str, schemas.ChatUserAccessibleAgentItem] = OrderedDict()
    for row in access_rows:
        agent_id = str(row[0])
        item = accessible_agents.get(agent_id)
        if item is None:
            item = schemas.ChatUserAccessibleAgentItem(
                agent_id=agent_id,
                agent_name=str(row[1] or ""),
                agent_status=str(row[2] or ""),
                agent_owner=str(row[3] or ""),
                workspace_name=str(row[4] or ""),
                source_type=str(row[5] or ""),
                last_run=str(row[6] or ""),
            )
            accessible_agents[agent_id] = item
        group_id = str(row[7] or "")
        group_name = str(row[8] or "")
        if group_id and group_id not in item.group_ids:
            item.group_ids.append(group_id)
        if group_name and group_name not in item.group_names:
            item.group_names.append(group_name)

    return schemas.ChatUserAccessibleAgentsResponse(
        chat_user=chat_user_item,
        items=list(accessible_agents.values()),
    )
