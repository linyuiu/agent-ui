import os
from typing import Iterable
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import config  # noqa: F401
from . import models, schemas, security
from .auth import get_current_user
from .db import Base, engine, get_db
from .permissions import is_allowed

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


def _count_active(items: Iterable[object], key: str = "status") -> int:
    active_values = {"active", "enabled"}
    return sum(1 for item in items if getattr(item, key, None) in active_values)


def _agent_summary(agent: models.Agent) -> schemas.AgentSummary:
    return schemas.AgentSummary(
        id=agent.id,
        name=agent.name,
        status=agent.status,
        owner=agent.owner,
        last_run=agent.last_run,
        description=agent.description,
        url=agent.url,
    )


def _agent_detail(agent: models.Agent) -> schemas.AgentDetail:
    return schemas.AgentDetail(
        **_agent_summary(agent).model_dump(),
        tools=agent.tools or [],
        tags=agent.tags or [],
    )


def _model_summary(model: models.Model) -> schemas.ModelSummary:
    return schemas.ModelSummary(
        id=model.id,
        name=model.name,
        provider=model.provider,
        status=model.status,
        context_length=model.context_length,
        description=model.description,
    )


def _model_detail(model: models.Model) -> schemas.ModelDetail:
    return schemas.ModelDetail(
        **_model_summary(model).model_dump(),
        pricing=model.pricing,
        release=model.release,
        tags=model.tags or [],
    )


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


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
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserPublic(id=user.id, email=user.email, role=user.role)


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
        user=schemas.UserPublic(id=user.id, email=user.email, role=user.role),
    )


@app.get("/auth/me", response_model=schemas.UserPublic)
def me(current_user: models.User = Depends(get_current_user)) -> schemas.UserPublic:
    return schemas.UserPublic(id=current_user.id, email=current_user.email, role=current_user.role)


@app.get("/dashboard/modules", response_model=list[schemas.ModuleSummary])
def get_modules(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.ModuleSummary]:
    agents = db.query(models.Agent).all()
    models_list = db.query(models.Model).all()

    allowed_agents = [
        agent
        for agent in agents
        if is_allowed(
            db,
            current_user,
            action="view",
            resource_type="agent",
            resource_id=agent.id,
            resource_attrs={"owner": agent.owner, "status": agent.status, "tags": agent.tags},
        )
    ]
    allowed_models = [
        model
        for model in models_list
        if is_allowed(
            db,
            current_user,
            action="view",
            resource_type="model",
            resource_id=model.id,
            resource_attrs={"provider": model.provider, "status": model.status, "tags": model.tags},
        )
    ]

    menu_defs = [
        {
            "id": "agents",
            "title": "智能体",
            "subtitle": "管理与调度",
            "total": len(allowed_agents),
            "active": _count_active(allowed_agents),
            "description": "管理智能体实例与运行状态。",
        },
        {
            "id": "models",
            "title": "模型",
            "subtitle": "能力与成本",
            "total": len(allowed_models),
            "active": _count_active(allowed_models),
            "description": "查看模型版本与推理指标。",
        },
        {
            "id": "admin",
            "title": "权限管理",
            "subtitle": "策略与接入",
            "total": 0,
            "active": 0,
            "description": "配置访问策略与数据接入。",
        },
    ]

    result: list[schemas.ModuleSummary] = []
    for item in menu_defs:
        if is_allowed(
            db,
            current_user,
            action="view",
            resource_type="menu",
            resource_id=item["id"],
            resource_attrs={},
        ):
            result.append(schemas.ModuleSummary(**item))

    return result


@app.get("/agents", response_model=list[schemas.AgentSummary])
def list_agents(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AgentSummary]:
    agents = db.query(models.Agent).all()
    allowed = [
        _agent_summary(agent)
        for agent in agents
        if is_allowed(
            db,
            current_user,
            action="view",
            resource_type="agent",
            resource_id=agent.id,
            resource_attrs={"owner": agent.owner, "status": agent.status, "tags": agent.tags},
        )
    ]
    return allowed


@app.get("/agents/{agent_id}", response_model=schemas.AgentDetail)
def get_agent(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentDetail:
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not is_allowed(
        db,
        current_user,
        action="view",
        resource_type="agent",
        resource_id=agent.id,
        resource_attrs={"owner": agent.owner, "status": agent.status, "tags": agent.tags},
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    return _agent_detail(agent)


@app.get("/models", response_model=list[schemas.ModelSummary])
def list_models(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.ModelSummary]:
    models_list = db.query(models.Model).all()
    allowed = [
        _model_summary(model)
        for model in models_list
        if is_allowed(
            db,
            current_user,
            action="view",
            resource_type="model",
            resource_id=model.id,
            resource_attrs={"provider": model.provider, "status": model.status, "tags": model.tags},
        )
    ]
    return allowed


@app.get("/models/{model_id}", response_model=schemas.ModelDetail)
def get_model(
    model_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not is_allowed(
        db,
        current_user,
        action="view",
        resource_type="model",
        resource_id=model.id,
        resource_attrs={"provider": model.provider, "status": model.status, "tags": model.tags},
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    return _model_detail(model)


@app.get("/admin/policies", response_model=list[schemas.PolicyOut])
def list_policies(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.PolicyOut]:
    _require_admin(current_user)
    policies = db.query(models.Policy).order_by(models.Policy.id.desc()).all()
    return [
        schemas.PolicyOut(
            id=policy.id,
            name=policy.name,
            effect=policy.effect,
            actions=policy.actions or [],
            resource_type=policy.resource_type,
            resource_id=policy.resource_id,
            subject_attrs=policy.subject_attrs or {},
            resource_attrs=policy.resource_attrs or {},
            enabled=policy.enabled,
        )
        for policy in policies
    ]


@app.post("/admin/policies", response_model=schemas.PolicyOut, status_code=201)
def create_policy(
    payload: schemas.PolicyCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PolicyOut:
    _require_admin(current_user)
    policy = models.Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return schemas.PolicyOut(
        id=policy.id,
        name=policy.name,
        effect=policy.effect,
        actions=policy.actions or [],
        resource_type=policy.resource_type,
        resource_id=policy.resource_id,
        subject_attrs=policy.subject_attrs or {},
        resource_attrs=policy.resource_attrs or {},
        enabled=policy.enabled,
    )


@app.put("/admin/policies/{policy_id}", response_model=schemas.PolicyOut)
def update_policy(
    policy_id: int,
    payload: schemas.PolicyUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PolicyOut:
    _require_admin(current_user)
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    for key, value in payload.model_dump().items():
        setattr(policy, key, value)

    db.commit()
    db.refresh(policy)
    return schemas.PolicyOut(
        id=policy.id,
        name=policy.name,
        effect=policy.effect,
        actions=policy.actions or [],
        resource_type=policy.resource_type,
        resource_id=policy.resource_id,
        subject_attrs=policy.subject_attrs or {},
        resource_attrs=policy.resource_attrs or {},
        enabled=policy.enabled,
    )


@app.delete("/admin/policies/{policy_id}")
def delete_policy(
    policy_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_admin(current_user)
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()
    return {"status": "deleted"}


@app.post("/admin/models", response_model=schemas.ModelDetail, status_code=201)
def create_model(
    payload: schemas.ModelCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ModelDetail:
    _require_admin(current_user)

    existing = db.query(models.Model).filter(models.Model.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")

    model = models.Model(**payload.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_detail(model)


@app.post("/admin/agents/import", response_model=schemas.AgentImportResponse)
def import_agents(
    payload: schemas.AgentImportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AgentImportResponse:
    _require_admin(current_user)

    try:
        response = httpx.post(
            payload.api_url,
            json={"ak": payload.ak, "sk": payload.sk},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to fetch agent data") from exc

    if isinstance(data, dict):
        items = data.get("data") or data.get("items") or data
    else:
        items = data

    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Unexpected response format")

    imported = 0
    result_agents: list[schemas.AgentDetail] = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url") or item.get("link")
        if not url:
            continue

        name = item.get("name") or item.get("title") or f"Agent {idx + 1}"
        status_value = item.get("status") or "active"
        owner = item.get("owner") or "external"
        description = item.get("description") or ""
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        tools = item.get("tools") if isinstance(item.get("tools"), list) else []
        last_run = item.get("last_run") or item.get("lastRun") or ""

        agent = db.query(models.Agent).filter(models.Agent.url == url).first()
        if not agent:
            agent = models.Agent(
                id=uuid4().hex,
                name=name,
                status=status_value,
                owner=owner,
                last_run=last_run,
                url=url,
                description=description,
                tags=tags,
                tools=tools,
                source_payload=item,
            )
            db.add(agent)
        else:
            agent.name = name
            agent.status = status_value
            agent.owner = owner
            agent.last_run = last_run
            agent.description = description
            agent.tags = tags
            agent.tools = tools
            agent.source_payload = item

        imported += 1
        result_agents.append(_agent_detail(agent))

    db.commit()

    return schemas.AgentImportResponse(imported=imported, agents=result_agents)


@app.post("/demo/agents")
def demo_agents(payload: dict) -> dict:
    ak = payload.get("ak")
    sk = payload.get("sk")
    if ak != "demo-ak" or sk != "demo-sk":
        raise HTTPException(status_code=401, detail="Invalid demo credentials")

    return {
        "items": [
            {
                "name": "Customer Success Agent",
                "status": "active",
                "owner": "CS",
                "last_run": "2026-02-04T10:00:00Z",
                "description": "Handles onboarding and routine check-ins.",
                "tags": ["onboarding", "email"],
                "tools": ["HubSpot", "Slack"],
                "url": "https://example.com/agents/cs",
            },
            {
                "name": "Ops Triage Agent",
                "status": "active",
                "owner": "Operations",
                "last_run": "2026-02-04T09:20:00Z",
                "description": "Monitors SLA breaches and escalations.",
                "tags": ["alerts", "sla"],
                "tools": ["PagerDuty", "Grafana"],
                "url": "https://example.com/agents/ops",
            },
            {
                "name": "Growth Research Agent",
                "status": "paused",
                "owner": "Growth",
                "last_run": "2026-02-03T16:45:00Z",
                "description": "Summarizes experiment results and insights.",
                "tags": ["experiments", "reporting"],
                "tools": ["Notion", "Sheets"],
                "url": "https://example.com/agents/growth",
            },
        ]
    }
