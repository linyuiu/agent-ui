from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, func

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    status = Column(String(50), nullable=False, default="active")
    source = Column(String(50), nullable=False, default="local")
    source_provider = Column(String(64), nullable=False, default="local")
    source_subject = Column(String(255), nullable=False, default="")
    workspace = Column(String(100), nullable=False, default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSsoBinding(Base):
    __tablename__ = "user_sso_bindings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider_key = Column(String(64), nullable=False, index=True)
    provider_protocol = Column(String(20), nullable=False, default="")
    external_subject = Column(String(255), nullable=False, index=True)
    external_username = Column(String(255), nullable=False, default="")
    external_email = Column(String(255), nullable=False, default="")
    raw_profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("provider_key", "external_subject", name="uq_user_sso_binding_subject"),
        UniqueConstraint("user_id", "provider_key", name="uq_user_sso_binding_provider"),
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, primary_key=True, nullable=False, index=True)
    role_name = Column(String(50), primary_key=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_name", name="uq_user_role"),
    )


class PermissionGrant(Base):
    __tablename__ = "permission_grants"

    id = Column(Integer, primary_key=True, index=True)
    subject_type = Column(String(20), nullable=False)
    subject_id = Column(String(255), nullable=False)
    scope = Column(String(20), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=True)
    action = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "scope",
            "resource_type",
            "resource_id",
            "action",
            name="uq_permission_grant",
        ),
    )


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    effect = Column(String(20), nullable=False, default="allow")
    actions = Column(JSON, nullable=False, default=list)
    scope = Column(String(50), nullable=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=True)
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(String(255), nullable=True)
    subject_attrs = Column(JSON, nullable=False, default=dict)
    resource_attrs = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    owner = Column(String(255), nullable=False, default="system")
    last_run = Column(String(50), nullable=False, default="")
    proxy_id = Column(String(64), unique=True, nullable=False, index=True, default=lambda: uuid4().hex)
    upstream_base_url = Column(String(255), nullable=False, default="")
    upstream_token = Column(String(1024), nullable=False, default="")
    url = Column(String(1024), nullable=False)
    description = Column(Text, nullable=False, default="")
    group_name = Column(String(255), nullable=False, default="")
    groups = Column(JSON, nullable=False, default=list)
    tools = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    source_payload = Column(JSON, nullable=False, default=dict)
    source_type = Column(String(50), nullable=False, default="")
    is_synced = Column(Boolean, nullable=False, default=False)
    external_id = Column(String(255), nullable=True)
    workspace_id = Column(String(255), nullable=True)
    workspace_name = Column(String(255), nullable=False, default="")
    sync_config_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentGroup(Base):
    __tablename__ = "agent_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentApiConfig(Base):
    __tablename__ = "agent_api_configs"

    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String(255), unique=True, nullable=False, index=True)
    token = Column(String(1024), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatUser(Base):
    __tablename__ = "chat_users"

    id = Column(String(255), primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, default="", index=True)
    phone = Column(String(255), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    nick_name = Column(String(255), nullable=False, default="")
    source = Column(String(64), nullable=False, default="", index=True)
    create_time = Column(String(64), nullable=False, default="")
    update_time = Column(String(64), nullable=False, default="")
    user_group_ids = Column(JSON, nullable=False, default=list)
    user_group_names = Column(JSON, nullable=False, default=list)
    raw_payload = Column(JSON, nullable=False, default=dict)
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChatUserGroup(Base):
    __tablename__ = "chat_user_groups"

    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    raw_payload = Column(JSON, nullable=False, default=dict)
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChatUserGroupMember(Base):
    __tablename__ = "chat_user_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(255), nullable=False, index=True)
    group_name = Column(String(255), nullable=False, default="")
    chat_user_id = Column(String(255), nullable=False, index=True)
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("group_id", "chat_user_id", name="uq_chat_user_group_member"),
    )


class AgentChatUserAccess(Base):
    __tablename__ = "agent_chat_user_accesses"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    chat_user_id = Column(String(255), nullable=False, index=True)
    group_id = Column(String(255), nullable=False, index=True)
    group_name = Column(String(255), nullable=False, default="")
    username = Column(String(255), nullable=False, default="")
    nick_name = Column(String(255), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    source = Column(String(64), nullable=False, default="", index=True)
    create_time = Column(String(64), nullable=False, default="")
    update_time = Column(String(64), nullable=False, default="")
    is_auth = Column(Boolean, nullable=False, default=False)
    raw_payload = Column(JSON, nullable=False, default=dict)
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "group_id", "chat_user_id", name="uq_agent_chat_user_access"),
    )


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    id = Column(String(64), primary_key=True, index=True, default=lambda: uuid4().hex)
    task_type = Column(String(64), nullable=False, default="agent_chat_user_sync")
    status = Column(String(32), nullable=False, default="pending", index=True)
    config_id = Column(Integer, nullable=True, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    agent_name = Column(String(255), nullable=False, default="")
    workspace_id = Column(String(255), nullable=False, default="")
    workspace_name = Column(String(255), nullable=False, default="")
    external_id = Column(String(255), nullable=False, default="")
    total_steps = Column(Integer, nullable=False, default=0)
    completed_steps = Column(Integer, nullable=False, default=0)
    total_records = Column(Integer, nullable=False, default=0)
    processed_records = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=False, default="")
    error = Column(Text, nullable=False, default="")
    celery_task_id = Column(String(255), nullable=False, default="")
    created_by = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class AuthProviderConfig(Base):
    __tablename__ = "auth_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    protocol = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    auto_create_user = Column(Boolean, nullable=False, default=True)
    default_role = Column(String(50), nullable=False, default="user")
    default_workspace = Column(String(100), nullable=False, default="default")
    config = Column(JSON, nullable=False, default=dict)
    field_mapping = Column("attribute_mapping", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def attribute_mapping(self) -> dict:
        return dict(self.field_mapping or {})

    @attribute_mapping.setter
    def attribute_mapping(self, value: dict | None) -> None:
        self.field_mapping = value or {}


class Model(Base):
    __tablename__ = "models"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False, default="")
    model_type = Column(String(50), nullable=False, default="llm")
    base_model = Column(String(255), nullable=False, default="")
    api_url = Column(String(1024), nullable=False, default="")
    api_key = Column(String(1024), nullable=False, default="")
    parameters = Column(JSON, nullable=False, default=list)
    status = Column(String(50), nullable=False, default="enabled")
    context_length = Column(Integer, nullable=False, default=0)
    description = Column(String(1024), nullable=False, default="")
    pricing = Column(String(255), nullable=False, default="")
    release = Column(String(50), nullable=False, default="")
    tags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
