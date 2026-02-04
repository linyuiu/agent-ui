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

export const fetchModules = () => apiGet<ModuleSummary[]>('/dashboard/modules')
export const fetchAgents = () => apiGet<AgentSummary[]>('/agents')
export const fetchAgent = (id: string) => apiGet<AgentDetail>(`/agents/${id}`)
export const fetchModels = () => apiGet<ModelSummary[]>('/models')
export const fetchModel = (id: string) => apiGet<ModelDetail>(`/models/${id}`)
