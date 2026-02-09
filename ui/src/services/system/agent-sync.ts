import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type {
  AgentApiConfig,
  AgentApiConfigCreate,
  AgentApiConfigUpdate,
  AgentImportRequest,
  AgentImportResponse,
  Fit2CloudApplication,
  Fit2CloudSyncByConfigRequest,
  Fit2CloudSyncResponse,
  Fit2CloudWorkspace,
} from './types'

export const importAgents = (payload: AgentImportRequest) =>
  apiPost<AgentImportResponse>('/admin/agents/import', payload)

export const fetchAgentApiConfigs = () => apiGet<AgentApiConfig[]>('/admin/agent-sync-configs')
export const createAgentApiConfig = (payload: AgentApiConfigCreate) =>
  apiPost<AgentApiConfig>('/admin/agent-sync-configs', payload)
export const updateAgentApiConfig = (id: number, payload: AgentApiConfigUpdate) =>
  apiPut<AgentApiConfig>(`/admin/agent-sync-configs/${id}`, payload)
export const deleteAgentApiConfig = (id: number) => apiDelete(`/admin/agent-sync-configs/${id}`)

export const fetchFit2CloudWorkspaces = (configId: number) =>
  apiGet<Fit2CloudWorkspace[]>(`/admin/agent-sync-configs/${configId}/workspaces`)

export const fetchFit2CloudApplications = (configId: number, workspaceId: string) =>
  apiGet<Fit2CloudApplication[]>(
    `/admin/agent-sync-configs/${configId}/workspaces/${encodeURIComponent(
      workspaceId
    )}/applications`
  )

export const syncFit2CloudByConfig = (configId: number, payload: Fit2CloudSyncByConfigRequest) =>
  apiPost<Fit2CloudSyncResponse>(`/admin/agent-sync-configs/${configId}/sync`, payload)
