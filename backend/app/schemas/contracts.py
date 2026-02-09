from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class _PasswordBase(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(_PasswordBase):
    account: str = Field(min_length=2, max_length=64)


class RegisterRequest(_PasswordBase):
    account: str = Field(min_length=2, max_length=64)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr


class UserPublic(BaseModel):
    id: int
    account: str
    username: str
    email: EmailStr
    role: str
    roles: list[str] = []
    status: str
    source: str
    workspace: str


class AdminUserCreate(_PasswordBase):
    account: str = Field(min_length=2, max_length=64)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    role: str | None = "user"
    roles: list[str] | None = None
    status: str = "active"
    source: str = "local"
    workspace: str = "default"


class AdminUserUpdate(BaseModel):
    account: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    roles: list[str] | None = None
    status: str | None = None
    source: str | None = None
    workspace: str | None = None
    password: str | None = None


class AdminUserOut(BaseModel):
    id: int
    account: str
    username: str
    email: EmailStr
    role: str
    roles: list[str] = []
    status: str
    source: str
    workspace: str
    created_at: datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: str | None = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: str


class PermissionGrantBase(BaseModel):
    subject_type: str = Field(pattern="^(user|role)$")
    subject_id: str
    scope: str = Field(pattern="^(menu|resource)$")
    resource_type: str
    resource_id: str | None = None
    action: str = Field(pattern="^(view|edit|manage)$")


class PermissionGrantCreate(PermissionGrantBase):
    pass


class PermissionGrantOut(PermissionGrantBase):
    id: int
    created_at: datetime


class MenuPermission(BaseModel):
    menu_id: str
    actions: list[str]


class ResourcePermission(BaseModel):
    resource_type: str
    resource_id: str | None = None
    actions: list[str]


class PermissionSummary(BaseModel):
    menus: list[MenuPermission]
    resources: list[ResourcePermission]


class PermissionSubjectItem(BaseModel):
    resource_type: str
    resource_id: str | None = None
    actions: list[str] = []


class PermissionSubjectMatrixItem(PermissionSubjectItem):
    inherited_actions: list[str] = []


class PermissionSubjectSummary(BaseModel):
    subject_type: str
    subject_id: str
    scope: str
    role: str | None = None
    roles: list[str] = []
    read_only: bool = False
    items: list[PermissionSubjectMatrixItem] = []


class PermissionSubjectUpdate(BaseModel):
    subject_type: str = Field(pattern="^(user|role)$")
    subject_id: str
    scope: str = Field(pattern="^(menu|resource)$")
    items: list[PermissionSubjectItem] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AdminResetPasswordRequest(BaseModel):
    password: str | None = None


class AgentGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class AgentGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AgentGroupOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime


class AgentApiConfigCreate(BaseModel):
    base_url: str = Field(min_length=1, max_length=255)
    token: str = Field(min_length=1, max_length=1024)


class AgentApiConfigUpdate(BaseModel):
    base_url: str | None = None
    token: str | None = None


class AgentApiConfigOut(BaseModel):
    id: int
    base_url: str
    token_hint: str
    created_at: datetime


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
    groups: list[str] = []
    editable: bool = True
    source_type: str = ""
    status_editable_only: bool = False


class AgentDetail(AgentSummary):
    pass


class Fit2CloudSyncRequest(BaseModel):
    base_url: str = Field(min_length=1, max_length=255)
    token: str = Field(min_length=1, max_length=1024)


class AgentSyncResponse(BaseModel):
    imported: int
    updated: int
    total: int
    errors: list[str] = []


class Fit2CloudWorkspace(BaseModel):
    id: str
    name: str


class Fit2CloudApplication(BaseModel):
    id: str
    name: str


class Fit2CloudWorkspaceSyncItem(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=255)
    workspace_name: str | None = None
    application_ids: list[str] | None = None
    sync_all: bool = False


class Fit2CloudSyncByConfigRequest(BaseModel):
    workspace_id: str | None = None
    workspace_name: str | None = None
    application_ids: list[str] | None = None
    sync_all: bool = False
    workspaces: list[Fit2CloudWorkspaceSyncItem] | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    status: str | None = None
    owner: str | None = None
    last_run: str | None = None
    description: str | None = None
    groups: list[str] | None = None


class AgentCreate(BaseModel):
    name: str
    url: str
    status: str = "active"
    owner: str = "system"
    last_run: str = ""
    description: str = ""
    groups: list[str] = []


class ModelSummary(BaseModel):
    id: str
    name: str
    provider: str
    model_type: str
    base_model: str
    status: str
    context_length: int
    description: str


class ModelParameterItem(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=64)
    hint: str = Field(default="", max_length=128)
    required: bool = False
    component_type: str = Field(default="input", max_length=32)
    default_value: str = Field(default="", max_length=255)


class ModelDetail(ModelSummary):
    api_url: str
    api_key_masked: str
    parameters: list[ModelParameterItem] = Field(default_factory=list)
    pricing: str
    release: str
    tags: list[str] = Field(default_factory=list)


class PolicyBase(BaseModel):
    name: str
    effect: str
    actions: list[str]
    scope: str = "resource"
    resource_type: str
    resource_id: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    subject_attrs: dict = Field(default_factory=dict)
    resource_attrs: dict = Field(default_factory=dict)
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
    id: str | None = None
    name: str = Field(min_length=1, max_length=255)
    provider: str = ""
    model_type: str = "llm"
    base_model: str = ""
    api_url: str = Field(min_length=1, max_length=1024)
    api_key: str = Field(min_length=1, max_length=1024)
    parameters: list[ModelParameterItem] = Field(default_factory=list)
    status: str = "enabled"
    context_length: int = 0
    description: str = ""
    pricing: str = ""
    release: str = ""
    tags: list[str] = Field(default_factory=list)


class ModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    model_type: str | None = None
    base_model: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    parameters: list[ModelParameterItem] | None = None
    status: str | None = None
    context_length: int | None = None
    description: str | None = None
    pricing: str | None = None
    release: str | None = None
    tags: list[str] | None = None
