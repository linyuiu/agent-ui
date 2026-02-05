import { apiGet, apiPost, apiPut } from './http'

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

export const fetchAgents = () => apiGet<AgentSummary[]>('/agents')
export const fetchAgent = (id: string) => apiGet<AgentDetail>(`/agents/${id}`)

export const createAgent = (payload: AgentCreate) => apiPost<AgentDetail>('/admin/agents', payload)
export const updateAgent = (id: string, payload: AgentUpdate) =>
  apiPut<AgentDetail>(`/admin/agents/${id}`, payload)
