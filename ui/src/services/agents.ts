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
}

export type AgentDetail = AgentSummary

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
}

export const fetchAgents = (options?: { includeDescription?: boolean }) => {
  const includeDescription = options?.includeDescription ?? true
  return apiGet<AgentSummary[]>(
    `/agents?include_description=${includeDescription ? 'true' : 'false'}`
  )
}
export const fetchAgent = (id: string) => apiGet<AgentDetail>(`/agents/${id}`)

export const createAgent = (payload: AgentCreate) => apiPost<AgentDetail>('/admin/agents', payload)
export const updateAgent = (id: string, payload: AgentUpdate) =>
  apiPut<AgentDetail>(`/admin/agents/${id}`, payload)
export const deleteAgent = (id: string) => apiDelete(`/admin/agents/${id}`)

export const syncFit2CloudAgents = (payload: Fit2CloudSyncRequest) =>
  apiPost<Fit2CloudSyncResponse>('/admin/agents/sync-fit2cloud', payload)
