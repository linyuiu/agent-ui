from __future__ import annotations

from typing import Iterable

from .. import models, schemas


def count_active(items: Iterable[object], key: str = "status") -> int:
    active_values = {"active", "enabled"}
    return sum(1 for item in items if getattr(item, key, None) in active_values)


def agent_summary(agent: models.Agent, *, include_description: bool = True) -> schemas.AgentSummary:
    is_synced = bool(getattr(agent, "is_synced", False))
    editable = True
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
        source_type=agent.source_type or "",
        status_editable_only=is_synced,
    )


def agent_detail(agent: models.Agent) -> schemas.AgentDetail:
    return schemas.AgentDetail(**agent_summary(agent, include_description=True).model_dump())


def model_summary(model: models.Model) -> schemas.ModelSummary:
    return schemas.ModelSummary(
        id=model.id,
        name=model.name,
        provider=model.provider,
        model_type=model.model_type,
        base_model=model.base_model,
        status=model.status,
        context_length=model.context_length,
        description=model.description,
    )


def _mask_secret(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 4:
        return "*" * len(text)
    return f"{'*' * (len(text) - 4)}{text[-4:]}"


def model_detail(model: models.Model) -> schemas.ModelDetail:
    return schemas.ModelDetail(
        **model_summary(model).model_dump(),
        api_url=model.api_url,
        api_key_masked=_mask_secret(model.api_key),
        parameters=[
            schemas.ModelParameterItem(**item)
            for item in (model.parameters or [])
            if isinstance(item, dict)
        ],
        pricing=model.pricing,
        release=model.release,
        tags=model.tags or [],
    )
