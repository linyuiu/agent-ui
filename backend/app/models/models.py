from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, UniqueConstraint, func

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    status = Column(String(50), nullable=False, default="active")
    source = Column(String(50), nullable=False, default="local")
    workspace = Column(String(100), nullable=False, default="default")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    url = Column(String(1024), nullable=False)
    description = Column(String(1024), nullable=False, default="")
    group_name = Column(String(255), nullable=False, default="")
    groups = Column(JSON, nullable=False, default=list)
    tools = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    source_payload = Column(JSON, nullable=False, default=dict)
    source_type = Column(String(50), nullable=False, default="")
    external_id = Column(String(255), nullable=True)
    workspace_id = Column(String(255), nullable=True)
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


class Model(Base):
    __tablename__ = "models"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False, default="")
    status = Column(String(50), nullable=False, default="enabled")
    context_length = Column(Integer, nullable=False, default=0)
    description = Column(String(1024), nullable=False, default="")
    pricing = Column(String(255), nullable=False, default="")
    release = Column(String(50), nullable=False, default="")
    tags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
