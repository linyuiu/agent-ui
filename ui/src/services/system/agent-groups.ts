import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type { AgentGroup, AgentGroupCreate, AgentGroupUpdate } from './types'

export const fetchAgentGroups = () => apiGet<AgentGroup[]>('/admin/agent-groups')
export const createAgentGroup = (payload: AgentGroupCreate) =>
  apiPost<AgentGroup>('/admin/agent-groups', payload)
export const updateAgentGroup = (id: number, payload: AgentGroupUpdate) =>
  apiPut<AgentGroup>(`/admin/agent-groups/${id}`, payload)
export const deleteAgentGroup = (id: number) => apiDelete(`/admin/agent-groups/${id}`)
