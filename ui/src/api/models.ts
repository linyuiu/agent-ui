import { apiGet, apiPost, apiPut } from './http'

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

export type ModelUpdate = Partial<Omit<ModelCreate, 'id'>>

export const fetchModels = () => apiGet<ModelSummary[]>('/models')
export const fetchModel = (id: string) => apiGet<ModelDetail>(`/models/${id}`)

export const createModel = (payload: ModelCreate) => apiPost<ModelDetail>('/admin/models', payload)
export const updateModel = (id: string, payload: ModelUpdate) =>
  apiPut<ModelDetail>(`/admin/models/${id}`, payload)
