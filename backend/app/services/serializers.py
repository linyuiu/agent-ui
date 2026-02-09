from __future__ import annotations

from typing import Iterable

from .. import models, schemas


def count_active(items: Iterable[object], key: str = "status") -> int:
    active_values = {"active", "enabled"}
    return sum(1 for item in items if getattr(item, key, None) in active_values)


def agent_summary(agent: models.Agent, *, include_description: bool = True) -> schemas.AgentSummary:
    editable = agent.source_type not in {"fit2cloud"}
    groups = list(agent.groups or [])
    if not groups and agent.group_name:
        groups = [agent.group_name]
    return schemas.AgentSummary(
        id=agent.id,
        name=agent.name,
        status=agent.status,
        owner=agent.owner,
        last_run=agent.last_run,
        description=agent.description if include_description else "",
        url=agent.url,
        groups=groups,
        editable=editable,
    )


def agent_detail(agent: models.Agent) -> schemas.AgentDetail:
    return schemas.AgentDetail(**agent_summary(agent, include_description=True).model_dump())


def model_summary(model: models.Model) -> schemas.ModelSummary:
    return schemas.ModelSummary(
        id=model.id,
        name=model.name,
        provider=model.provider,
        status=model.status,
        context_length=model.context_length,
        description=model.description,
    )


def model_detail(model: models.Model) -> schemas.ModelDetail:
    return schemas.ModelDetail(
        **model_summary(model).model_dump(),
        pricing=model.pricing,
        release=model.release,
        tags=model.tags or [],
    )
