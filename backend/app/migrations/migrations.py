from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .. import models, security
from ..db import Base, engine
from ..services.chat_links import (
    build_proxy_chat_url,
    generate_proxy_id,
    parse_upstream_chat_url,
)


def _column_names(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _column_map(inspector, table: str) -> dict[str, dict]:
    return {col["name"]: col for col in inspector.get_columns(table)}


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
            if "source_provider" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN source_provider VARCHAR(64)"))
            if "source_subject" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN source_subject VARCHAR(255)"))
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
                    "SET source_provider = COALESCE(NULLIF(source_provider, ''), 'local') "
                    "WHERE source_provider IS NULL OR source_provider = ''"
                )
            )
            conn.execute(
                text(
                    "UPDATE users "
                    "SET source_subject = COALESCE(source_subject, '') "
                    "WHERE source_subject IS NULL"
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
            conn.execute(text("ALTER TABLE users ALTER COLUMN source_provider SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN source_subject SET NOT NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN workspace SET NOT NULL"))
            conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_account ON users (account)")
            )
            conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key"))

        if "agents" in tables:
            columns = _column_names(inspector, "agents")
            column_defs = _column_map(inspector, "agents")
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
            if "source_type" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN source_type VARCHAR(50)"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET source_type = COALESCE(source_type, '') "
                    "WHERE source_type IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN source_type SET NOT NULL"))
            if "is_synced" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN is_synced BOOLEAN"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET is_synced = (source_type IS NOT NULL AND source_type <> '') "
                    "WHERE is_synced IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN is_synced SET NOT NULL"))
            conn.execute(text("ALTER TABLE agents ALTER COLUMN is_synced SET DEFAULT FALSE"))
            if "external_id" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN external_id VARCHAR(255)"))
            if "workspace_id" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN workspace_id VARCHAR(255)"))
            if "proxy_id" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN proxy_id VARCHAR(64)"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET proxy_id = md5(random()::text || clock_timestamp()::text) "
                    "WHERE proxy_id IS NULL OR proxy_id = ''"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN proxy_id SET NOT NULL"))
            conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_agents_proxy_id ON agents (proxy_id)")
            )
            if "upstream_base_url" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN upstream_base_url VARCHAR(255)"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET upstream_base_url = COALESCE(upstream_base_url, '') "
                    "WHERE upstream_base_url IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN upstream_base_url SET NOT NULL"))
            if "upstream_token" not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN upstream_token VARCHAR(1024)"))
            conn.execute(
                text(
                    "UPDATE agents "
                    "SET upstream_token = COALESCE(upstream_token, '') "
                    "WHERE upstream_token IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE agents ALTER COLUMN upstream_token SET NOT NULL"))
            if "description" in columns:
                desc_type = str(column_defs["description"].get("type", "")).lower()
                # Fit2Cloud `desc/prologue` may exceed 1024 chars; keep full text instead of truncating.
                if "text" not in desc_type:
                    conn.execute(text("ALTER TABLE agents ALTER COLUMN description TYPE TEXT"))

        if "agent_api_configs" in tables:
            columns = _column_names(inspector, "agent_api_configs")
            if "base_url" not in columns:
                conn.execute(text("ALTER TABLE agent_api_configs ADD COLUMN base_url VARCHAR(255)"))
            if "token" not in columns:
                conn.execute(text("ALTER TABLE agent_api_configs ADD COLUMN token VARCHAR(1024)"))
            conn.execute(
                text(
                    "UPDATE agent_api_configs "
                    "SET token = COALESCE(token, '') "
                    "WHERE token IS NULL"
                )
            )

        if "models" in tables:
            columns = _column_names(inspector, "models")
            if "model_type" not in columns:
                conn.execute(text("ALTER TABLE models ADD COLUMN model_type VARCHAR(50)"))
            conn.execute(
                text(
                    "UPDATE models "
                    "SET model_type = COALESCE(NULLIF(model_type, ''), 'llm') "
                    "WHERE model_type IS NULL OR model_type = ''"
                )
            )
            conn.execute(text("ALTER TABLE models ALTER COLUMN model_type SET NOT NULL"))

            if "base_model" not in columns:
                conn.execute(text("ALTER TABLE models ADD COLUMN base_model VARCHAR(255)"))
            conn.execute(
                text(
                    "UPDATE models "
                    "SET base_model = COALESCE(base_model, '') "
                    "WHERE base_model IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE models ALTER COLUMN base_model SET NOT NULL"))

            if "api_url" not in columns:
                conn.execute(text("ALTER TABLE models ADD COLUMN api_url VARCHAR(1024)"))
            conn.execute(
                text(
                    "UPDATE models "
                    "SET api_url = COALESCE(api_url, '') "
                    "WHERE api_url IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE models ALTER COLUMN api_url SET NOT NULL"))

            if "api_key" not in columns:
                conn.execute(text("ALTER TABLE models ADD COLUMN api_key VARCHAR(1024)"))
            conn.execute(
                text(
                    "UPDATE models "
                    "SET api_key = COALESCE(api_key, '') "
                    "WHERE api_key IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE models ALTER COLUMN api_key SET NOT NULL"))

            if "parameters" not in columns:
                conn.execute(text("ALTER TABLE models ADD COLUMN parameters JSON"))
            conn.execute(text("UPDATE models SET parameters = '[]'::json WHERE parameters IS NULL"))
            conn.execute(text("ALTER TABLE models ALTER COLUMN parameters SET NOT NULL"))

    _backfill_agent_chat_links()
    _seed_roles()
    _seed_admin_user()
    _seed_admin_permissions()
    _seed_user_permissions()
    _seed_user_roles()
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


def _seed_admin_user() -> None:
    with Session(engine) as session:
        existing = session.query(models.User).filter(models.User.account == "admin").first()
        if existing:
            changed = False
            if existing.email.endswith(".local"):
                existing.email = "admin@example.com"
                changed = True
            if existing.role != "admin":
                existing.role = "admin"
                changed = True
            if (existing.source_provider or "") != "local":
                existing.source_provider = "local"
                changed = True
            if existing.source_subject is None:
                existing.source_subject = ""
                changed = True
            if changed:
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

            # include existing role links for this user, keep as union
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

            if user.account == "admin" or "admin" in target_roles:
                primary_role = "admin"
            else:
                primary_role = target_roles[0]
            if user.role != primary_role:
                user.role = primary_role
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
