from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol

ACTION_ORDER = {
    "view": 1,
    "edit": 2,
    "manage": 3,
}

ACTION_BITS = {
    "view": 1,
    "edit": 2,
    "manage": 4,
}

IMPLIED_ACTION_MASK = {
    "view": 1,   # view
    "edit": 3,   # view + edit
    "manage": 7,  # view + edit + manage
}

PermissionAccess = dict[tuple[str, str, str | None], int]


class GrantLike(Protocol):
    scope: str
    resource_type: str
    resource_id: str | None
    action: str


@dataclass(slots=True)
class PermissionRequest:
    action: str
    scope: str
    resource_type: str
    resource_id: str | None = None
    subject_id: str | None = None
    subject_roles: tuple[str, ...] = ()
    subject_attrs: Mapping[str, Any] = field(default_factory=dict)
    resource_attrs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PermissionDecision:
    allowed: bool
    reason: str = ""
    matched_key: tuple[str, str, str | None] | None = None


def build_access_map(grants: Iterable[GrantLike]) -> PermissionAccess:
    access: PermissionAccess = {}
    for grant in grants:
        action = str(getattr(grant, "action", "") or "").strip()
        implied = IMPLIED_ACTION_MASK.get(action)
        if implied is None:
            continue
        key = (
            str(getattr(grant, "scope", "") or ""),
            str(getattr(grant, "resource_type", "") or ""),
            getattr(grant, "resource_id", None),
        )
        access[key] = access.get(key, 0) | implied
    return access


def access_allows(access: PermissionAccess, request: PermissionRequest) -> PermissionDecision:
    required = ACTION_BITS.get(request.action)
    if required is None:
        return PermissionDecision(allowed=False, reason=f"invalid action: {request.action}")

    specific_key = (request.scope, request.resource_type, request.resource_id)
    wildcard_key = (request.scope, request.resource_type, None)
    mask = access.get(specific_key, 0) | access.get(wildcard_key, 0)
    if mask & required:
        matched = specific_key if access.get(specific_key, 0) & required else wildcard_key
        return PermissionDecision(allowed=True, matched_key=matched)

    # Bridge for current group-based agent authorization path.
    if request.scope == "resource" and request.resource_type == "agent":
        groups = request.resource_attrs.get("groups")
        if isinstance(groups, list):
            wildcard_group_key = ("resource", "agent_group", None)
            group_mask = access.get(wildcard_group_key, 0)
            if group_mask & required:
                return PermissionDecision(allowed=True, matched_key=wildcard_group_key)
            for group in groups:
                group_key = ("resource", "agent_group", str(group))
                if access.get(group_key, 0) & required:
                    return PermissionDecision(allowed=True, matched_key=group_key)

    return PermissionDecision(allowed=False, reason="no matching permission grant")


class PermissionEngine(Protocol):
    name: str

    def evaluate(
        self,
        *,
        request: PermissionRequest,
        grants: Iterable[GrantLike],
        access: PermissionAccess,
        super_admin: bool = False,
    ) -> PermissionDecision:
        ...


class RbacAclPermissionEngine:
    name = "rbac_acl"

    def evaluate(
        self,
        *,
        request: PermissionRequest,
        grants: Iterable[GrantLike],
        access: PermissionAccess,
        super_admin: bool = False,
    ) -> PermissionDecision:
        if super_admin:
            return PermissionDecision(allowed=True, reason="super admin bypass")
        resolved_access = access or build_access_map(grants)
        return access_allows(resolved_access, request)


class HybridAbacBridgeEngine(RbacAclPermissionEngine):
    # Placeholder engine to make future ABAC migration a drop-in replacement.
    name = "hybrid_abac_bridge"

    def evaluate(
        self,
        *,
        request: PermissionRequest,
        grants: Iterable[GrantLike],
        access: PermissionAccess,
        super_admin: bool = False,
    ) -> PermissionDecision:
        decision = self.evaluate_abac(request=request)
        if decision is not None:
            return decision
        return super().evaluate(
            request=request,
            grants=grants,
            access=access,
            super_admin=super_admin,
        )

    def evaluate_abac(self, *, request: PermissionRequest) -> PermissionDecision | None:
        # This hook intentionally returns None by default.
        # Future ABAC implementation can read request.subject_attrs/resource_attrs here.
        return None


_ENGINE_REGISTRY: dict[str, PermissionEngine] = {
    "rbac_acl": RbacAclPermissionEngine(),
    "hybrid_abac_bridge": HybridAbacBridgeEngine(),
}


def get_permission_engine() -> PermissionEngine:
    configured = os.getenv("PERMISSION_ENGINE", "rbac_acl").strip().lower()
    return _ENGINE_REGISTRY.get(configured, _ENGINE_REGISTRY["rbac_acl"])
