import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type {
  SsoProvider,
  SsoProviderCreate,
  SystemAuthSetting,
  SystemAuthSettingUpdate,
  SsoProviderTestRequest,
  SsoProviderTestResponse,
  SsoProviderUpdate,
} from './types'

export const fetchSsoProviders = () => apiGet<SsoProvider[]>('/admin/sso/providers')
export const fetchSystemAuthSettings = () => apiGet<SystemAuthSetting>('/admin/sso/settings')

export const fetchSsoProtocols = () => apiGet<{ protocols: string[] }>('/admin/sso/providers/protocols')

export const createSsoProvider = (payload: SsoProviderCreate) =>
  apiPost<SsoProvider>('/admin/sso/providers', payload)

export const updateSsoProvider = (providerId: number, payload: SsoProviderUpdate) =>
  apiPut<SsoProvider>(`/admin/sso/providers/${providerId}`, payload)

export const updateSystemAuthSettings = (payload: SystemAuthSettingUpdate) =>
  apiPut<SystemAuthSetting>('/admin/sso/settings', payload)

export const deleteSsoProvider = (providerId: number) => apiDelete(`/admin/sso/providers/${providerId}`)

export const testSsoProvider = (payload: SsoProviderTestRequest) =>
  apiPost<SsoProviderTestResponse>('/admin/sso/providers/test', payload)
