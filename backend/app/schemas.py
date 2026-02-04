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
