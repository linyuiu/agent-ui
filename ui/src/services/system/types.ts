import type { AgentDetail, Fit2CloudSyncResponse } from '../agents'

export type Role = {
  id: number
  name: string
  description: string
}

export type RoleCreate = {
  name: string
  description?: string
}

export type PermissionGrant = {
  id: number
  subject_type: 'user' | 'role'
  subject_id: string
  scope: 'menu' | 'resource'
  resource_type: string
  resource_id: string | null
  action: 'view' | 'edit' | 'manage'
  created_at: string
}

export type PermissionGrantCreate = Omit<PermissionGrant, 'id' | 'created_at'>

export type PermissionSubjectItem = {
  resource_type: string
  resource_id: string | null
  actions: Array<'view' | 'edit' | 'manage'>
}

export type PermissionSubjectMatrixItem = PermissionSubjectItem & {
  inherited_actions?: Array<'view' | 'edit' | 'manage'>
}

export type PermissionSubjectSummary = {
  subject_type: 'user' | 'role'
  subject_id: string
  scope: 'menu' | 'resource'
  role?: string | null
  roles?: string[]
  read_only?: boolean
  items: PermissionSubjectMatrixItem[]
}

export type PermissionSubjectUpdate = {
  subject_type: 'user' | 'role'
  subject_id: string
  scope: 'menu' | 'resource'
  items: PermissionSubjectItem[]
}

export type AdminUser = {
  id: number
  username: string
  account: string
  email: string
  role: string
  roles?: string[]
  status: string
  source: string
  source_provider?: string
  source_subject?: string
  workspace: string
  created_at: string
}

export type AdminUserCreate = {
  account: string
  username: string
  email: string
  password: string
  role?: string
  roles?: string[]
  status?: string
  source?: string
  source_provider?: string
  workspace?: string
}

export type AdminUserUpdate = {
  account?: string
  username?: string
  email?: string
  role?: string
  roles?: string[]
  status?: string
  source?: string
  source_provider?: string
  workspace?: string
  password?: string
}

export type SsoProviderProtocol = 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'

export type SsoProvider = {
  id: number
  key: string
  name: string
  protocol: SsoProviderProtocol
  enabled: boolean
  auto_create_user: boolean
  default_role: string
  default_workspace: string
  config: Record<string, unknown>
  attribute_mapping: Record<string, unknown>
  created_at: string
}

export type SsoProviderCreate = {
  key: string
  name: string
  protocol: SsoProviderProtocol
  enabled?: boolean
  auto_create_user?: boolean
  default_role?: string
  default_workspace?: string
  config?: Record<string, unknown>
  attribute_mapping?: Record<string, unknown>
}

export type SsoProviderUpdate = Partial<SsoProviderCreate>

export type SsoProviderTestRequest = {
  protocol: SsoProviderProtocol
  config?: Record<string, unknown>
  attribute_mapping?: Record<string, unknown>
}

export type SsoProviderTestResponse = {
  status: string
  message: string
}

export type SsoProviderPublic = {
  key: string
  name: string
  protocol: SsoProviderProtocol
  login_mode: 'redirect' | 'password'
}

export type AgentImportRequest = {
  api_url: string
  ak: string
  sk: string
}

export type AgentImportResponse = {
  imported: number
  agents: AgentDetail[]
}

export type AgentGroup = {
  id: number
  name: string
  description: string
  created_at: string
}

export type AgentGroupCreate = {
  name: string
  description?: string
}

export type AgentGroupUpdate = {
  name?: string
  description?: string
}

export type AgentApiConfig = {
  id: number
  base_url: string
  token_hint: string
  created_at: string
}

export type AgentApiConfigCreate = {
  base_url: string
  token: string
}

export type AgentApiConfigUpdate = {
  base_url?: string
  token?: string
}

export type Fit2CloudWorkspace = {
  id: string
  name: string
}

export type Fit2CloudApplication = {
  id: string
  name: string
}

export type Fit2CloudSyncByConfigRequest = {
  workspace_id: string
  workspace_name?: string
  application_ids?: string[]
  sync_all?: boolean
}

export type { Fit2CloudSyncResponse }
