const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type ApiError = {
  detail?: string
}

const normalizeToken = (raw: string) => raw.replace(/^bearer\s+/i, '').trim()

const handleUnauthorized = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_email')
  localStorage.removeItem('user_role')
  localStorage.removeItem('user_name')
  localStorage.removeItem('user_account')
  localStorage.removeItem('user_permissions')
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

const getAuthHeaders = () => {
  const raw = localStorage.getItem('access_token')
  if (!raw) return {}
  const token = normalizeToken(raw)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const parseError = async (response: Response, fallback: string) => {
  const payload = (await response.json().catch(() => ({}))) as ApiError
  return payload?.detail || fallback
}

export const apiGet = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, 'Request failed'))
  }

  return (await response.json()) as T
}

export const apiPost = async <T>(path: string, body?: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, 'Request failed'))
  }

  return (await response.json()) as T
}

export const apiPut = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, 'Request failed'))
  }

  return (await response.json()) as T
}

export const apiDelete = async (path: string): Promise<void> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (response.status === 401) {
    handleUnauthorized()
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    throw new Error(await parseError(response, 'Request failed'))
  }
}

export type { ApiError }
