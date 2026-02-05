from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import models, security
from .db import Base, engine


def _column_names(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "users" in tables:
            columns = _column_names(inspector, "users")
            if "account" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN account VARCHAR(255)"))
            if "username" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(255)"))
            if "status" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(50)"))
            if "source" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN source VARCHAR(50)"))
            if "workspace" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN workspace VARCHAR(100)"))

            conn.execute(
                text(
                    "UPDATE users "
                    "SET username = COALESCE(NULLIF(username, ''), email) "
                    "WHERE username IS NULL OR username = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE users "
                    "SET account = COALESCE(NULLIF(account, ''), email) "
                    "WHERE account IS NULL OR account = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE users "
                    "SET status = COALESCE(NULLIF(status, ''), 'active') "
                    "WHERE status IS NULL OR status = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE users "
                    "SET source = COALESCE(NULLIF(source, ''), 'local') "
                    "WHERE source IS NULL OR source = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE users "
                    "SET workspace = COALESCE(NULLIF(workspace, ''), 'default') "
                    "WHERE workspace IS NULL OR workspace = ''"
                )
            )
            conn.execute(text("ALTER TABLE users ALTER COLUMN account SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN username SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN status SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN source SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN workspace SET NOT NULL"))
            conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_account ON users (account)")
            )
            conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key"))

        if "agents" in tables:
            columns = _column_names(inspector, "agents")
            if "group_name" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN group_name VARCHAR(255)"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET group_name = COALESCE(group_name, '') "
                    "WHERE group_name IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN group_name SET NOT NULL"))
            if "groups" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN groups JSON"))
            conn.execute(text("UPDATE agents SET groups = '[]'::json WHERE groups IS NULL"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET groups = json_build_array(group_name) "
                    "WHERE (groups IS NULL OR COALESCE(json_array_length(groups), 0) = 0) "
                    "AND group_name IS NOT NULL AND group_name <> ''"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN groups SET NOT NULL"))

    _seed_roles()
    _seed_admin_user()
    _seed_admin_permissions()
    _seed_agent_groups()


def _seed_roles() -> None:
    with Session(engine) as session:
        existing = {role.name for role in session.query(models.Role).all()}
        defaults = [
            ("admin", "系统管理员"),
            ("user", "普通用户"),
            ("ops", "运营角色"),
        ]
        created = False
        for name, desc in defaults:
            if name in existing:
                continue
            session.add(models.Role(name=name, description=desc))
            created = True
        if created:
            session.commit()


def _seed_admin_user() -> None:
    with Session(engine) as session:
        existing = session.query(models.User).filter(models.User.account == "admin").first()
        if existing:
            if existing.email.endswith(".local"):
                existing.email = "admin@example.com"
                session.commit()
            return
        admin_user = models.User(
            account="admin",
            username="admin",
            email="admin@example.com",
            password_hash=security.hash_password("agentui@2025"),
            role="admin",
            status="active",
            source="local",
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
