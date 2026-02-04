from pydantic import BaseModel, EmailStr, Field


class _PasswordBase(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(_PasswordBase):
    email: EmailStr


class RegisterRequest(_PasswordBase):
    email: EmailStr


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


class ModuleSummary(BaseModel):
    id: str
    title: str
    subtitle: str
    total: int
    active: int
    description: str


class AgentSummary(BaseModel):
    id: str
    name: str
    status: str
    owner: str
    last_run: str
    description: str
    url: str


class AgentDetail(AgentSummary):
    tools: list[str]
    tags: list[str]


class ModelSummary(BaseModel):
    id: str
    name: str
    provider: str
    status: str
    context_length: int
    description: str


class ModelDetail(ModelSummary):
    pricing: str
    release: str
    tags: list[str]


class PolicyBase(BaseModel):
    name: str
    effect: str
    actions: list[str]
    resource_type: str
    resource_id: str | None = None
    subject_attrs: dict
    resource_attrs: dict
    enabled: bool = True


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(PolicyBase):
    pass


class PolicyOut(PolicyBase):
    id: int


class AgentImportRequest(BaseModel):
    api_url: str
    ak: str
    sk: str


class AgentImportResponse(BaseModel):
    imported: int
    agents: list[AgentDetail]


class ModelCreate(BaseModel):
    id: str
    name: str
    provider: str
    status: str
    context_length: int
    description: str
    pricing: str
    release: str
    tags: list[str]
