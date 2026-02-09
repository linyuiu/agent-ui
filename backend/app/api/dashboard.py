from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import (
    can_view_agent,
    can_view_menu,
    can_view_model,
    get_user_access,
    is_super_admin,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/modules", response_model=list[schemas.ModuleSummary])
def get_modules(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.ModuleSummary]:
    if is_super_admin(current_user):
        agent_total, agent_active = db.query(
            func.count(models.Agent.id),
            func.coalesce(
                func.sum(case((models.Agent.status.in_(["active", "enabled"]), 1), else_=0)),
                0,
            ),
        ).one()
        model_total, model_active = db.query(
            func.count(models.Model.id),
            func.coalesce(
                func.sum(case((models.Model.status.in_(["active", "enabled"]), 1), else_=0)),
                0,
            ),
        ).one()
        return [
            schemas.ModuleSummary(
                id="agents",
                title="智能体",
                subtitle="管理与调度",
                total=int(agent_total or 0),
                active=int(agent_active or 0),
                description="管理智能体实例与运行状态。",
            ),
            schemas.ModuleSummary(
                id="models",
                title="模型",
                subtitle="能力与成本",
                total=int(model_total or 0),
                active=int(model_active or 0),
                description="查看模型版本与推理指标。",
            ),
            schemas.ModuleSummary(
                id="admin",
                title="系统管理",
                subtitle="用户、权限与同步",
                total=0,
                active=0,
                description="管理用户角色、权限策略与智能体同步。",
            ),
        ]

    agents = db.query(
        models.Agent.id,
        models.Agent.status,
        models.Agent.group_name,
        models.Agent.groups,
    ).all()
    models_list = db.query(models.Model.id, models.Model.status).all()

    access = get_user_access(db, current_user)

    allowed_agent_total = 0
    allowed_agent_active = 0
    for item in agents:
        groups = list(item.groups or [])
        if not groups and item.group_name:
            groups = [item.group_name]
        if not can_view_agent(access, str(item.id), groups):
            continue
        allowed_agent_total += 1
        if item.status in {"active", "enabled"}:
            allowed_agent_active += 1

    allowed_model_total = 0
    allowed_model_active = 0
    for item in models_list:
        if not can_view_model(access, str(item.id)):
            continue
        allowed_model_total += 1
        if item.status in {"active", "enabled"}:
            allowed_model_active += 1

    menu_defs = [
        {
            "id": "agents",
            "title": "智能体",
            "subtitle": "管理与调度",
            "total": allowed_agent_total,
            "active": allowed_agent_active,
            "description": "管理智能体实例与运行状态。",
        },
        {
            "id": "models",
            "title": "模型",
            "subtitle": "能力与成本",
            "total": allowed_model_total,
            "active": allowed_model_active,
            "description": "查看模型版本与推理指标。",
        },
        {
            "id": "admin",
            "title": "系统管理",
            "subtitle": "用户、权限与同步",
            "total": 0,
            "active": 0,
            "description": "管理用户角色、权限策略与智能体同步。",
        },
    ]

    result: list[schemas.ModuleSummary] = []
    for item in menu_defs:
        if can_view_menu(access, item["id"]):
            result.append(schemas.ModuleSummary(**item))

    return result
