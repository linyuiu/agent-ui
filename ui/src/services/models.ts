import { apiDelete, apiGet, apiPost, apiPut } from './http'

export type ModelParameterItem = {
  key: string
  label: string
  hint: string
  required: boolean
  component_type: string
  default_value: string
}

export type ModelSummary = {
  id: string
  name: string
  provider: string
  model_type: string
  base_model: string
  status: string
  context_length: number
  description: string
}

export type ModelDetail = ModelSummary & {
  api_url: string
  api_key_masked: string
  parameters: ModelParameterItem[]
  pricing: string
  release: string
  tags: string[]
}

export type ModelCreate = {
  id?: string
  name: string
  provider: string
  model_type: string
  base_model: string
  api_url: string
  api_key: string
  parameters: ModelParameterItem[]
  status: string
  context_length: number
  description: string
  pricing: string
  release: string
  tags: string[]
}

export type ModelUpdate = Partial<ModelCreate>

export const fetchModels = () => apiGet<ModelSummary[]>('/models')
export const fetchModel = (id: string) => apiGet<ModelDetail>(`/models/${id}`)

export const createModel = (payload: ModelCreate) => apiPost<ModelDetail>('/admin/models', payload)
export const updateModel = (id: string, payload: ModelUpdate) =>
  apiPut<ModelDetail>(`/admin/models/${id}`, payload)
export const deleteModel = (id: string) => apiDelete(`/admin/models/${id}`)
