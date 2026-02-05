import { apiGet } from './http'

export type ModuleSummary = {
  id: string
  title: string
  subtitle: string
  total: number
  active: number
  description: string
}

export const fetchModules = () => apiGet<ModuleSummary[]>('/dashboard/modules')
