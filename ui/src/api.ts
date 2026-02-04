const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type ApiError = {
  detail?: string
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const apiGet = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  const payload = (await response.json().catch(() => ({}))) as ApiError

  if (!response.ok) {
    const message = payload?.detail || 'Request failed'
    throw new Error(message)
  }

  return payload as T
}

export type ModuleSummary = {
  id: string
  title: string
  subtitle: string
  total: number
  active: number
  description: string
}

export type AgentSummary = {
  id: string
  name: string
  status: string
  owner: string
  last_run: string
  description: string
  url: string
}

export type AgentDetail = AgentSummary & {
  tools: string[]
  tags: string[]
}

export type ModelSummary = {
  id: string
  name: string
  provider: string
  status: string
  context_length: number
  description: string
}

export type ModelDetail = ModelSummary & {
  pricing: string
  release: string
  tags: string[]
}

export type Policy = {
  id: number
  name: string
  effect: string
  actions: string[]
  resource_type: string
  resource_id: string | null
  subject_attrs: Record<string, unknown>
  resource_attrs: Record<string, unknown>
  enabled: boolean
}

export type PolicyCreate = Omit<Policy, 'id'>

export type AgentImportRequest = {
  api_url: string
  ak: string
  sk: string
}

export type AgentImportResponse = {
  imported: number
  agents: AgentDetail[]
}

export type ModelCreate = {
  id: string
  name: string
  provider: string
  status: string
  context_length: number
  description: string
  pricing: string
  release: string
  tags: string[]
}

export const fetchModules = () => apiGet<ModuleSummary[]>('/dashboard/modules')
export const fetchAgents = () => apiGet<AgentSummary[]>('/agents')
export const fetchAgent = (id: string) => apiGet<AgentDetail>(`/agents/${id}`)
export const fetchModels = () => apiGet<ModelSummary[]>('/models')
export const fetchModel = (id: string) => apiGet<ModelDetail>(`/models/${id}`)
export const fetchPolicies = () => apiGet<Policy[]>('/admin/policies')

export const createPolicy = async (policy: PolicyCreate) => {
  const response = await fetch(`${API_BASE}/admin/policies`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(policy),
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = payload?.detail || 'Failed to create policy'
    throw new Error(message)
  }

  return payload as Policy
}

export const updatePolicy = async (policyId: number, policy: PolicyCreate) => {
  const response = await fetch(`${API_BASE}/admin/policies/${policyId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(policy),
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = payload?.detail || 'Failed to update policy'
    throw new Error(message)
  }

  return payload as Policy
}

export const deletePolicy = async (policyId: number) => {
  const response = await fetch(`${API_BASE}/admin/policies/${policyId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = payload?.detail || 'Failed to delete policy'
    throw new Error(message)
  }

  return true
}

export const importAgents = async (payload: AgentImportRequest) => {
  const response = await fetch(`${API_BASE}/admin/agents/import`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = data?.detail || 'Failed to import agents'
    throw new Error(message)
  }

  return data as AgentImportResponse
}

export const createModel = async (payload: ModelCreate) => {
  const response = await fetch(`${API_BASE}/admin/models`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = data?.detail || 'Failed to create model'
    throw new Error(message)
  }

  return data as ModelDetail
}
