import { apiDelete, apiGet, apiPost, apiPut } from './http'
import type { AgentDetail } from './agents'

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
  status: string
  source: string
  workspace: string
  created_at: string
}

export type AdminUserCreate = {
  account: string
  username: string
  email: string
  password: string
  role: string
  status?: string
  source?: string
  workspace?: string
}

export type AdminUserUpdate = {
  account?: string
  username?: string
  email?: string
  role?: string
  status?: string
  source?: string
  workspace?: string
  password?: string
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

export const fetchRoles = () => apiGet<Role[]>('/admin/roles')
export const createRole = (payload: RoleCreate) => apiPost<Role>('/admin/roles', payload)
export const deleteRole = (roleId: number) => apiDelete(`/admin/roles/${roleId}`)

export const fetchPermissionGrants = () => apiGet<PermissionGrant[]>('/admin/permissions')
export const createPermissionGrant = (payload: PermissionGrantCreate) =>
  apiPost<PermissionGrant>('/admin/permissions', payload)
export const deletePermissionGrant = (grantId: number) => apiDelete(`/admin/permissions/${grantId}`)
export const fetchSubjectPermissions = (params: {
  subject_type: 'user' | 'role'
  subject_id: string
  scope: 'menu' | 'resource'
}) =>
  apiGet<PermissionSubjectSummary>(
    `/admin/permissions/subject?subject_type=${params.subject_type}&subject_id=${encodeURIComponent(
      params.subject_id
    )}&scope=${params.scope}`
  )
export const updateSubjectPermissions = (payload: PermissionSubjectUpdate) =>
  apiPut<PermissionSubjectSummary>('/admin/permissions/subject', payload)

export const fetchUsers = () => apiGet<AdminUser[]>('/admin/users')
export const createUser = (payload: AdminUserCreate) => apiPost<AdminUser>('/admin/users', payload)
export const updateUser = (userId: number, payload: AdminUserUpdate) =>
  apiPut<AdminUser>(`/admin/users/${userId}`, payload)
export const resetUserPassword = (userId: number) =>
  apiPost<{ status: string; password: string }>(`/admin/users/${userId}/reset-password`)
export const deleteUser = (userId: number) => apiDelete(`/admin/users/${userId}`)

export const importAgents = (payload: AgentImportRequest) =>
  apiPost<AgentImportResponse>('/admin/agents/import', payload)

export const fetchAgentGroups = () => apiGet<AgentGroup[]>('/admin/agent-groups')
export const createAgentGroup = (payload: AgentGroupCreate) =>
  apiPost<AgentGroup>('/admin/agent-groups', payload)
export const updateAgentGroup = (id: number, payload: AgentGroupUpdate) =>
  apiPut<AgentGroup>(`/admin/agent-groups/${id}`, payload)
export const deleteAgentGroup = (id: number) => apiDelete(`/admin/agent-groups/${id}`)
