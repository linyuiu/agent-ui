from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models, security
from ..config import settings
from ..db import Base, engine
from ..services.chat_links import (
    build_proxy_chat_url,
    generate_proxy_id,
    parse_upstream_chat_url,
)


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    if getattr(settings, "DB_SEED_ON_STARTUP", False):
        seed_bootstrap_defaults()


def seed_bootstrap_defaults() -> None:
    _seed_roles()
    _seed_system_auth_settings()
    _seed_admin_user()
    _seed_admin_permissions()
    _seed_user_permissions()
    _seed_user_roles()


def seed_defaults() -> None:
    seed_bootstrap_defaults()
    _backfill_agent_chat_links()
    _seed_agent_groups()


def _backfill_agent_chat_links() -> None:
    with Session(engine) as session:
        agents = session.query(models.Agent).all()
        changed = False
        for agent in agents:
            # Only synced agents should be accessed through backend proxy links.
            if not bool(agent.is_synced):
                continue
            if not agent.proxy_id:
                agent.proxy_id = generate_proxy_id()
                changed = True

            if not agent.upstream_base_url or not agent.upstream_token:
                try:
                    upstream_base_url, upstream_token = parse_upstream_chat_url(agent.url or "")
                except ValueError:
                    continue
                agent.upstream_base_url = upstream_base_url
                agent.upstream_token = upstream_token
                changed = True

            if agent.upstream_base_url and agent.upstream_token:
                proxy_url = build_proxy_chat_url(agent.proxy_id)
                if agent.url != proxy_url:
                    agent.url = proxy_url
                    changed = True

        if changed:
            session.commit()


def _seed_roles() -> None:
    with Session(engine) as session:
        existing = {role.name for role in session.query(models.Role).all()}
        defaults = [
            ("admin", "系统管理员"),
            ("user", "普通用户"),
        ]
        created = False
        for name, desc in defaults:
            if name in existing:
                continue
            session.add(models.Role(name=name, description=desc))
            created = True
        if created:
            session.commit()


def _seed_system_auth_settings() -> None:
    with Session(engine) as session:
        setting = session.query(models.SystemAuthSetting).order_by(models.SystemAuthSetting.id.asc()).first()
        if not setting:
            session.add(
                models.SystemAuthSetting(
                    enabled_methods=["local"],
                    default_login_method="local",
                    auto_create_user=True,
                    default_role="user",
                )
            )
            session.commit()


def _seed_admin_user() -> None:
    with Session(engine) as session:
        existing = session.query(models.User).filter(models.User.account == "admin").first()
        if existing:
            return
        admin_user = models.User(
            account="admin",
            username="admin",
            email="admin@example.com",
            password_hash=security.hash_password("agentui@2025"),
            role="admin",
            status="active",
            source="local",
            source_provider="local",
            source_subject="",
            workspace="default",
        )
        session.add(admin_user)
        session.commit()


def _seed_admin_permissions() -> None:
    with Session(engine) as session:
        role = session.query(models.Role).filter(models.Role.name == "admin").first()
        if not role:
            return

        desired: list[tuple[str, str, str | None, str]] = []
        for menu_id in ("agents", "models", "admin"):
            for action in ("view", "edit", "manage"):
                desired.append(("menu", "menu", menu_id, action))
        for resource_type in ("agent", "model", "agent_group"):
            for action in ("view", "edit", "manage"):
                desired.append(("resource", resource_type, None, action))

        existing = {
            (grant.scope, grant.resource_type, grant.resource_id, grant.action)
            for grant in session.query(models.PermissionGrant)
            .filter(
                models.PermissionGrant.subject_type == "role",
                models.PermissionGrant.subject_id == "admin",
            )
            .all()
        }
        created = False
        for scope, resource_type, resource_id, action in desired:
            key = (scope, resource_type, resource_id, action)
            if key in existing:
                continue
            session.add(
                models.PermissionGrant(
                    subject_type="role",
                    subject_id="admin",
                    scope=scope,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                )
            )
            created = True
        if created:
            session.commit()


def _seed_user_permissions() -> None:
    with Session(engine) as session:
        role = session.query(models.Role).filter(models.Role.name == "user").first()
        if not role:
            return

        desired: list[tuple[str, str, str | None, str]] = []
        for menu_id in ("agents", "models", "admin"):
            desired.append(("menu", "menu", menu_id, "view"))
        for resource_type in ("agent", "model", "agent_group"):
            desired.append(("resource", resource_type, None, "view"))

        existing = {
            (grant.scope, grant.resource_type, grant.resource_id, grant.action)
            for grant in session.query(models.PermissionGrant)
            .filter(
                models.PermissionGrant.subject_type == "role",
                models.PermissionGrant.subject_id == "user",
            )
            .all()
        }
        created = False
        for scope, resource_type, resource_id, action in desired:
            key = (scope, resource_type, resource_id, action)
            if key in existing:
                continue
            session.add(
                models.PermissionGrant(
                    subject_type="role",
                    subject_id="user",
                    scope=scope,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                )
            )
            created = True
        if created:
            session.commit()


def _seed_user_roles() -> None:
    with Session(engine) as session:
        all_links = session.query(models.UserRole).all()
        existing_pairs = {(row.user_id, row.role_name) for row in all_links}
        links_by_user: dict[int, list[str]] = {}
        for row in all_links:
            links_by_user.setdefault(row.user_id, []).append(row.role_name)

        valid_roles = {role.name for role in session.query(models.Role).all()}
        if "user" not in valid_roles:
            session.add(models.Role(name="user", description="普通用户"))
            session.flush()
            valid_roles.add("user")
        if "admin" not in valid_roles:
            session.add(models.Role(name="admin", description="系统管理员"))
            session.flush()
            valid_roles.add("admin")

        changed = False
        users = session.query(models.User).all()
        for user in users:
            target_roles: list[str] = []
            if user.account == "admin":
                target_roles = ["admin"]
            else:
                current = (user.role or "").strip()
                if current in valid_roles:
                    target_roles.append(current)

            for role_name in links_by_user.get(user.id, []):
                if role_name in valid_roles and role_name not in target_roles:
                    target_roles.append(role_name)

            if not target_roles:
                target_roles = ["user"]

            for role_name in target_roles:
                pair = (user.id, role_name)
                if pair in existing_pairs:
                    continue
                session.add(models.UserRole(user_id=user.id, role_name=role_name))
                existing_pairs.add(pair)
                changed = True

        if changed:
            session.commit()


def _seed_agent_groups() -> None:
    with Session(engine) as session:
        existing = {group.name for group in session.query(models.AgentGroup).all()}
        created = False
        agents = session.query(models.Agent).all()
        for agent in agents:
            groups = list(agent.groups or [])
            if not groups and agent.group_name:
                groups = [agent.group_name]
            for name in groups:
                name = str(name).strip()
                if not name or name in existing:
                    continue
                session.add(models.AgentGroup(name=name, description=""))
                existing.add(name)
                created = True
        if created:
            session.commit()


def main() -> None:
    seed_defaults()


if __name__ == "__main__":
    main()
