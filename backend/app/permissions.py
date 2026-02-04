from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import Policy, User


def _matches(expected: Any, actual: Any) -> bool:
    if expected is None:
        return True

    if isinstance(expected, list):
        if isinstance(actual, list):
            return bool(set(expected) & set(actual))
        return actual in expected

    return expected == actual


def _match_conditions(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        actual = context.get(key)
        if not _matches(expected, actual):
            return False
    return True


def is_allowed(
    db: Session,
    user: User,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_attrs: dict[str, Any] | None = None,
) -> bool:
    if user.role == "admin":
        return True

    subject_ctx = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
    }
    res_ctx = {"id": resource_id}
    if resource_attrs:
        res_ctx.update(resource_attrs)

    policies = db.query(Policy).filter(Policy.enabled.is_(True)).all()
    allowed = False

    for policy in policies:
        if policy.resource_type != resource_type:
            continue
        if policy.resource_id and policy.resource_id != resource_id:
            continue
        if action not in (policy.actions or []):
            continue
        if not _match_conditions(policy.subject_attrs or {}, subject_ctx):
            continue
        if not _match_conditions(policy.resource_attrs or {}, res_ctx):
            continue

        if policy.effect == "deny":
            return False
        if policy.effect == "allow":
            allowed = True

    return allowed
