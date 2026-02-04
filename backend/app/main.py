import os
from typing import Iterable

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import config  # noqa: F401
from . import models, schemas, security
from .db import Base, engine, get_db

app = FastAPI(title="Agent UI API")


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


AGENTS = [
    {
        "id": "agent-ops",
        "name": "Ops Monitor",
        "status": "active",
        "owner": "Operations",
        "last_run": "2026-02-04T09:20:00Z",
        "description": "Monitors daily KPIs and sends alerts.",
        "tools": ["Slack", "Postgres", "Grafana"],
        "tags": ["alerts", "daily"],
    },
    {
        "id": "agent-growth",
        "name": "Growth Assistant",
        "status": "active",
        "owner": "Growth",
        "last_run": "2026-02-04T08:55:00Z",
        "description": "Summarizes experiment results and drafts reports.",
        "tools": ["Notion", "Sheets", "BigQuery"],
        "tags": ["experiments", "reporting"],
    },
    {
        "id": "agent-support",
        "name": "Support Triage",
        "status": "paused",
        "owner": "Support",
        "last_run": "2026-02-03T18:40:00Z",
        "description": "Routes incoming tickets and suggests responses.",
        "tools": ["Zendesk", "Slack"],
        "tags": ["support", "routing"],
    },
]

MODELS = [
    {
        "id": "model-core",
        "name": "Core LLM",
        "provider": "OpenAI",
        "status": "enabled",
        "context_length": 128000,
        "description": "Primary multi-purpose model for agents.",
        "pricing": "$0.00 placeholder",
        "release": "2025-10",
        "tags": ["multimodal", "fast"],
    },
    {
        "id": "model-reason",
        "name": "Reasoning Pro",
        "provider": "OpenAI",
        "status": "enabled",
        "context_length": 64000,
        "description": "Used for complex planning and evaluation.",
        "pricing": "$0.00 placeholder",
        "release": "2025-06",
        "tags": ["analysis", "accurate"],
    },
    {
        "id": "model-light",
        "name": "Fast Lite",
        "provider": "OpenAI",
        "status": "disabled",
        "context_length": 32000,
        "description": "Low-latency model for quick classification.",
        "pricing": "$0.00 placeholder",
        "release": "2024-11",
        "tags": ["cheap", "fast"],
    },
]


def _count_active(items: Iterable[dict], key: str = "status") -> int:
    active_values = {"active", "enabled"}
    return sum(1 for item in items if item.get(key) in active_values)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.UserPublic, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)) -> schemas.UserPublic:
    existing = (
        db.query(models.User)
        .filter(models.User.email == payload.email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        email=payload.email,
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserPublic(id=user.id, email=user.email)


@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user = (
        db.query(models.User)
        .filter(models.User.email == payload.email)
        .first()
    )

    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = security.create_access_token({"sub": str(user.id), "email": user.email})
    return schemas.LoginResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserPublic(id=user.id, email=user.email),
    )


@app.get("/dashboard/modules", response_model=list[schemas.ModuleSummary])
def get_modules() -> list[schemas.ModuleSummary]:
    return [
        schemas.ModuleSummary(
            id="agents",
            title="Agents",
            subtitle="Management & orchestration",
            total=len(AGENTS),
            active=_count_active(AGENTS),
            description="Manage agent instances and their workloads.",
        ),
        schemas.ModuleSummary(
            id="models",
            title="Models",
            subtitle="Capabilities & cost",
            total=len(MODELS),
            active=_count_active(MODELS),
            description="Track model versions, latency, and spend.",
        ),
    ]


@app.get("/agents", response_model=list[schemas.AgentSummary])
def list_agents() -> list[schemas.AgentSummary]:
    return [schemas.AgentSummary(**agent) for agent in AGENTS]


@app.get("/agents/{agent_id}", response_model=schemas.AgentDetail)
def get_agent(agent_id: str) -> schemas.AgentDetail:
    agent = next((item for item in AGENTS if item["id"] == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return schemas.AgentDetail(**agent)


@app.get("/models", response_model=list[schemas.ModelSummary])
def list_models() -> list[schemas.ModelSummary]:
    return [schemas.ModelSummary(**model) for model in MODELS]


@app.get("/models/{model_id}", response_model=schemas.ModelDetail)
def get_model(model_id: str) -> schemas.ModelDetail:
    model = next((item for item in MODELS if item["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return schemas.ModelDetail(**model)
