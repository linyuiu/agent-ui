import { apiDelete, apiGet, apiPost, apiPut } from './http'

export type AgentSummary = {
  id: string
  name: string
  status: string
  owner: string
  last_run: string
  description: string
  url: string
  groups: string[]
  editable: boolean
  source_type?: string
  status_editable_only?: boolean
  sync_task_status?: string | null
  can_sync_users?: boolean
}

export type AgentDetail = AgentSummary

export type AgentChatUserEntry = {
  id: string
  username: string
  email: string
  phone: string
  is_active: boolean
  nick_name: string
  source: string
  create_time: string
  update_time: string
  user_group_ids: string[]
  user_group_names: string[]
  is_auth: boolean
}

export type AgentChatUserGroupView = {
  id: string
  name: string
  users: AgentChatUserEntry[]
}

export type AgentChatUserView = {
  agent_id: string
  groups: AgentChatUserGroupView[]
  total_users: number
  last_synced_at?: string | null
}

export type AgentCreate = {
  name: string
  url: string
  status: string
  owner: string
  last_run: string
  description: string
  groups: string[]
}

export type AgentUpdate = Partial<AgentCreate>

export type Fit2CloudSyncRequest = {
  base_url: string
  token: string
}

export type Fit2CloudSyncResponse = {
  imported: number
  updated: number
  total: number
  errors: string[]
  tasks?: Array<{
    id: string
    status: string
  }>
}

export const fetchAgents = (options?: { includeDescription?: boolean }) => {
  const includeDescription = options?.includeDescription ?? true
  return apiGet<AgentSummary[]>(
    `/agents?include_description=${includeDescription ? 'true' : 'false'}`
  )
}
export const fetchAgent = (id: string) => apiGet<AgentDetail>(`/agents/${id}`)
export const fetchAgentChatUsers = (id: string) => apiGet<AgentChatUserView>(`/agents/${id}/chat-users`)

export const createAgent = (payload: AgentCreate) => apiPost<AgentDetail>('/admin/agents', payload)
export const updateAgent = (id: string, payload: AgentUpdate) =>
  apiPut<AgentDetail>(`/admin/agents/${id}`, payload)
export const deleteAgent = (id: string) => apiDelete(`/admin/agents/${id}`)

export const syncFit2CloudAgents = (payload: Fit2CloudSyncRequest) =>
  apiPost<Fit2CloudSyncResponse>('/admin/agents/sync-fit2cloud', payload)
