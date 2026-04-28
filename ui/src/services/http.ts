const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const SESSION_EXPIRES_HEADER = 'x-session-expires-at'

type ApiError = {
  detail?: unknown
}

const AUTH_KEYS = [
  'access_token',
  'user_email',
  'user_role',
  'user_name',
  'user_account',
  'user_permissions',
  'session_expires_at',
] as const

const clearAuthKeys = () => {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key))
}

const handleUnauthorized = () => {
  clearAuthKeys()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as ApiError
  const detail = payload?.detail
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

const syncSessionHeaders = (response: Response) => {
  const expiresAt = response.headers.get(SESSION_EXPIRES_HEADER)
  if (expiresAt) {
    localStorage.setItem('session_expires_at', expiresAt)
  }
}

const parseResponse = async <T>(response: Response, fallback: string): Promise<T> => {
  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, fallback))
  }

  syncSessionHeaders(response)
  return (await response.json()) as T
}

export const apiGet = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  return parseResponse<T>(response, 'Request failed')
}

export const apiPost = async <T>(path: string, body?: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  return parseResponse<T>(response, 'Request failed')
}

export const apiPut = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  return parseResponse<T>(response, 'Request failed')
}

export const apiDelete = async (path: string): Promise<void> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, 'Request failed'))
  }
  syncSessionHeaders(response)
}

export type { ApiError }
