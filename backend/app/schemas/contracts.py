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
    source_provider: str = "local"
    workspace: str
    bound_providers: list[str] = []


class AdminUserCreate(_PasswordBase):
    account: str = Field(min_length=2, max_length=64)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr
    role: str | None = "user"
    roles: list[str] | None = None
    status: str = "active"
    source: str = "local"
    source_provider: str = "local"
    workspace: str = "default"


class AdminUserUpdate(BaseModel):
    account: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    roles: list[str] | None = None
    status: str | None = None
    source: str | None = None
    source_provider: str | None = None
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
    source_provider: str = "local"
    workspace: str
    bound_providers: list[str] = []
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


class SsoProviderBase(BaseModel):
    protocol: str = Field(pattern="^(ldap|cas|oidc|oauth2|saml2)$")
    enabled: bool = True
    auto_create_user: bool = True
    default_role: str = "user"
    default_workspace: str = "default"
    config: dict = Field(default_factory=dict)
    field_mapping: dict = Field(default_factory=dict)


class SsoProviderCreate(SsoProviderBase):
    key: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)


class SsoProviderUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    protocol: str | None = Field(default=None, pattern="^(ldap|cas|oidc|oauth2|saml2)$")
    enabled: bool | None = None
    auto_create_user: bool | None = None
    default_role: str | None = None
    default_workspace: str | None = None
    config: dict | None = None
    field_mapping: dict | None = None


class SsoProviderOut(SsoProviderBase):
    id: int
    key: str
    name: str
    created_at: datetime


class SsoProviderPublic(BaseModel):
    key: str
    name: str
    protocol: str
    login_mode: str = Field(pattern="^(redirect|password)$")


class SsoPasswordLoginRequest(_PasswordBase):
    provider_key: str = Field(min_length=2, max_length=64)
    account: str = Field(min_length=1, max_length=255)


class SsoProviderTestRequest(BaseModel):
    protocol: str = Field(pattern="^(ldap|cas|oidc|oauth2|saml2)$")
    config: dict = Field(default_factory=dict)
    field_mapping: dict = Field(default_factory=dict)


class SsoProviderTestResponse(BaseModel):
    status: str
    message: str


class SsoBindPending(BaseModel):
    bind_token: str
    provider_key: str
    provider_name: str
    provider_protocol: str
    username: str
    message: str


class SsoBindRequest(BaseModel):
    bind_token: str = Field(min_length=16, max_length=4096)


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


class ChatUserSummary(BaseModel):
    id: str
    username: str
    email: str = ""
    phone: str = ""
    is_active: bool = True
    nick_name: str = ""
    source: str = ""
    create_time: str = ""
    update_time: str = ""
    user_group_ids: list[str] = Field(default_factory=list)
    user_group_names: list[str] = Field(default_factory=list)


class ChatUserGroupSummary(BaseModel):
    id: str
    name: str


class AgentChatUserEntry(BaseModel):
    id: str
    username: str
    email: str = ""
    phone: str = ""
    is_active: bool = True
    nick_name: str = ""
    source: str = ""
    create_time: str = ""
    update_time: str = ""
    user_group_ids: list[str] = Field(default_factory=list)
    user_group_names: list[str] = Field(default_factory=list)
    is_auth: bool = False


class AgentChatUserGroupView(BaseModel):
    id: str
    name: str
    users: list[AgentChatUserEntry] = Field(default_factory=list)


class AgentChatUserView(BaseModel):
    agent_id: str
    groups: list[AgentChatUserGroupView] = Field(default_factory=list)
    total_users: int = 0
    last_synced_at: datetime | None = None


class SyncTaskOut(BaseModel):
    id: str
    task_type: str
    status: str
    config_id: int | None = None
    agent_id: str | None = None
    agent_name: str = ""
    workspace_id: str = ""
    workspace_name: str = ""
    external_id: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    total_records: int = 0
    processed_records: int = 0
    message: str = ""
    error: str = ""
    created_by: int | None = None
    celery_task_id: str = ""
    created_at: datetime
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


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
    sync_task_status: str | None = None
    can_sync_users: bool = False


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
    tasks: list[SyncTaskOut] = Field(default_factory=list)


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
    sync_chat_users: bool = False


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
