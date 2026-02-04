from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, func

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    effect = Column(String(20), nullable=False, default="allow")
    actions = Column(JSON, nullable=False, default=list)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=True)
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
    tools = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)
    source_payload = Column(JSON, nullable=False, default=dict)
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
