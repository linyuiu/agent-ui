const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
  access_token: string
  token_type: string
  user?: {
    email?: string
    username?: string
    account?: string
    role?: string
  }
}

export type SsoPasswordLoginResult =
  | { type: 'login'; payload: SsoLoginResponse }
  | { type: 'bind_required'; payload: SsoBindPending }

const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as { detail?: string }
  return payload?.detail || fallback
}

export const fetchEnabledSsoProviders = async (): Promise<SsoProviderPublic[]> => {
  const response = await fetch(`${API_BASE}/auth/sso/providers`)
  if (!response.ok) return []
  return (await response.json()) as SsoProviderPublic[]
}

export const ssoPasswordLogin = async (payload: {
  provider_key: string
  account: string
  password: string
}): Promise<SsoPasswordLoginResult> => {
  const response = await fetch(`${API_BASE}/auth/sso/password-login`, {
    method: 'POST',
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

export const bindSsoIdentity = async (token: string, bindToken: string) => {
  const response = await fetch(`${API_BASE}/auth/sso/bind`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ bind_token: bindToken }),
  })
  if (!response.ok) {
    throw new Error(await parseError(response, '绑定单点登录失败'))
  }
  return response.json()
}
