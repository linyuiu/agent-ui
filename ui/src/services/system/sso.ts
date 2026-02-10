import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type {
  SsoProvider,
  SsoProviderCreate,
  SsoProviderTestRequest,
  SsoProviderTestResponse,
  SsoProviderUpdate,
} from './types'

export const fetchSsoProviders = () => apiGet<SsoProvider[]>('/admin/sso/providers')

export const fetchSsoProtocols = () => apiGet<{ protocols: string[] }>('/admin/sso/providers/protocols')

export const createSsoProvider = (payload: SsoProviderCreate) =>
  apiPost<SsoProvider>('/admin/sso/providers', payload)

export const updateSsoProvider = (providerId: number, payload: SsoProviderUpdate) =>
  apiPut<SsoProvider>(`/admin/sso/providers/${providerId}`, payload)

export const deleteSsoProvider = (providerId: number) => apiDelete(`/admin/sso/providers/${providerId}`)

export const testSsoProvider = (payload: SsoProviderTestRequest) =>
  apiPost<SsoProviderTestResponse>('/admin/sso/providers/test', payload)
