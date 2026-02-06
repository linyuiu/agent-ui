import { apiGet, apiPost } from './http'

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

export const fetchAgentGroups = () => apiGet<AgentGroup[]>('/agent-groups')
export const createAgentGroup = (payload: AgentGroupCreate) =>
  apiPost<AgentGroup>('/agent-groups', payload)
