from app import models
from app.permissions.permissions import (
    build_view_access,
    can_view_agent,
    can_view_menu,
    has_permission_from_grants,
)


def _grant(
    *,
    subject_type: str = "role",
    subject_id: str = "user",
    scope: str,
    resource_type: str,
    resource_id: str | None,
    action: str,
) -> models.PermissionGrant:
    return models.PermissionGrant(
        subject_type=subject_type,
        subject_id=subject_id,
        scope=scope,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
    )


def test_manage_implies_edit_and_view() -> None:
    grants = [
        _grant(
            scope="resource",
            resource_type="agent",
            resource_id="agent-1",
            action="manage",
        )
    ]
    assert has_permission_from_grants(
        grants,
        action="view",
        scope="resource",
        resource_type="agent",
        resource_id="agent-1",
    )
    assert has_permission_from_grants(
        grants,
        action="edit",
        scope="resource",
        resource_type="agent",
        resource_id="agent-1",
    )
    assert has_permission_from_grants(
        grants,
        action="manage",
        scope="resource",
        resource_type="agent",
        resource_id="agent-1",
    )


def test_menu_permission_with_wildcard_applies_to_each_menu() -> None:
    grants = [
        _grant(
            scope="menu",
            resource_type="menu",
            resource_id=None,
            action="view",
        )
    ]
    access = build_view_access(grants)
    assert can_view_menu(access, "agents")
    assert can_view_menu(access, "models")
    assert can_view_menu(access, "admin")


def test_agent_group_permission_allows_group_members() -> None:
    grants = [
        _grant(
            scope="resource",
            resource_type="agent_group",
            resource_id="ops",
            action="view",
        )
    ]
    access = build_view_access(grants)
    assert can_view_agent(access, "agent-x", ["ops"])
    assert not can_view_agent(access, "agent-x", ["sales"])

