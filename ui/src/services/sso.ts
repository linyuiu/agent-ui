const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export type SsoProviderPublic = {
  key: string
  name: string
  protocol: 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'
  login_mode: 'redirect' | 'password'
}

export type SsoBindPending = {
  bind_token: string
  provider_key: string
  provider_name: string
  provider_protocol: 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'
  username: string
  message: string
}

export type SsoLoginResponse = {
  access_token?: string
  token_type: string
  permissions?: unknown
  session_expires_at?: string
  user?: {
    email?: string
    username?: string
    account?: string
    role?: string
  }
}

export type SsoLoginOptions = {
  enabled_methods: Array<'local' | 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'>
  default_login_method: 'local' | 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'
  providers: SsoProviderPublic[]
}

export type SsoPasswordLoginResult =
  | { type: 'login'; payload: SsoLoginResponse }
  | { type: 'bind_required'; payload: SsoBindPending }

const formatDetail = (detail: unknown, fallback: string) => {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        const location = Array.isArray(item?.loc) ? item.loc.join('.') : ''
        const message = typeof item?.msg === 'string' ? item.msg : ''
        return [location, message].filter(Boolean).join(': ')
      })
      .filter(Boolean)
      .join('; ') || fallback
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown; msg?: unknown })?.message || (detail as { msg?: unknown })?.msg
    if (typeof message === 'string' && message.trim()) return message
  }
  return fallback
}

const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as { detail?: unknown }
  return formatDetail(payload?.detail, fallback)
}

const syncSessionHeaders = (response: Response) => {
  const expiresAt = response.headers.get('x-session-expires-at')
  if (expiresAt) {
    localStorage.setItem('session_expires_at', expiresAt)
  }
}

export const fetchEnabledSsoProviders = async (): Promise<SsoProviderPublic[]> => {
  const response = await fetch(`${API_BASE}/auth/sso/providers`, { credentials: 'include' })
  if (!response.ok) return []
  return (await response.json()) as SsoProviderPublic[]
}

export const fetchSsoLoginOptions = async (): Promise<SsoLoginOptions> => {
  const response = await fetch(`${API_BASE}/auth/sso/options`, { credentials: 'include' })
  if (!response.ok) {
    return {
      enabled_methods: ['local'],
      default_login_method: 'local',
      providers: [],
    }
  }
  return (await response.json()) as SsoLoginOptions
}

export const ssoPasswordLogin = async (payload: {
  provider_key: string
  encrypted_payload: string
  key_id: string
}): Promise<SsoPasswordLoginResult> => {
  const response = await fetch(`${API_BASE}/auth/sso/password-login`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (response.status === 409) {
    return { type: 'bind_required', payload: (await response.json()) as SsoBindPending }
  }
  if (!response.ok) {
    throw new Error(await parseError(response, '登录失败'))
  }
  return { type: 'login', payload: (await response.json()) as SsoLoginResponse }
}

export const buildSsoStartUrl = (providerKey: string, redirectPath = '/home/agents') =>
  `${API_BASE}/auth/sso/start/${encodeURIComponent(providerKey)}?redirect=${encodeURIComponent(
    redirectPath
  )}`

export const bindSsoIdentity = async (bindToken: string) => {
  const response = await fetch(`${API_BASE}/auth/sso/bind`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ bind_token: bindToken }),
  })
  if (!response.ok) {
    throw new Error(await parseError(response, '绑定单点登录失败'))
  }
  syncSessionHeaders(response)
  return response.json()
}
