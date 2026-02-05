from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..db import get_db
from ..permissions import has_permission
from ..services.serializers import count_active

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/modules", response_model=list[schemas.ModuleSummary])
def get_modules(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.ModuleSummary]:
    agents = db.query(models.Agent).all()
    models_list = db.query(models.Model).all()

    allowed_agents = []
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
            allowed_agents.append(agent)
    allowed_models = [
        model
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

    menu_defs = [
        {
            "id": "agents",
            "title": "智能体",
            "subtitle": "管理与调度",
            "total": len(allowed_agents),
            "active": count_active(allowed_agents),
            "description": "管理智能体实例与运行状态。",
        },
        {
            "id": "models",
            "title": "模型",
            "subtitle": "能力与成本",
            "total": len(allowed_models),
            "active": count_active(allowed_models),
            "description": "查看模型版本与推理指标。",
        },
        {
            "id": "admin",
            "title": "权限管理",
            "subtitle": "策略与接入",
            "total": 0,
            "active": 0,
            "description": "配置访问策略与数据接入。",
        },
    ]

    result: list[schemas.ModuleSummary] = []
    for item in menu_defs:
        if has_permission(
            db,
            current_user,
            action="view",
            scope="menu",
            resource_type="menu",
            resource_id=item["id"],
        ):
            result.append(schemas.ModuleSummary(**item))

    return result
