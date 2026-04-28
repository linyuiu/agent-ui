export const SESSION_KEYS = {
  email: 'user_email',
  role: 'user_role',
  username: 'user_name',
  account: 'user_account',
  permissions: 'user_permissions',
  expiresAt: 'session_expires_at',
  legacyAccessToken: 'access_token',
} as const

type SessionProfile = {
  email: string
  role: string
  username: string
  account: string
}

type LoginUserPayload = {
  email?: string
  role?: string
  username?: string
  account?: string
}

type LoginPayload = {
  user?: LoginUserPayload
  session_expires_at?: string
}

const getItem = (key: string) => localStorage.getItem(key) || ''

export const getSessionExpiresAt = (): string => getItem(SESSION_KEYS.expiresAt)

export const isSessionExpired = (): boolean => {
  const raw = getSessionExpiresAt()
  if (!raw) return false
  const value = Date.parse(raw)
  return Number.isFinite(value) && value <= Date.now()
}

export const getSessionProfile = (): SessionProfile => ({
  email: getItem(SESSION_KEYS.email),
  role: getItem(SESSION_KEYS.role),
  username: getItem(SESSION_KEYS.username),
  account: getItem(SESSION_KEYS.account),
})

export const getCurrentRole = (): string => getItem(SESSION_KEYS.role)

export const clearSession = (): void => {
  Object.values(SESSION_KEYS).forEach((key) => localStorage.removeItem(key))
}

export const setSessionFromLogin = (payload: LoginPayload): void => {
  if (payload.user?.email) {
    localStorage.setItem(SESSION_KEYS.email, payload.user.email)
  }
  if (payload.user?.username) {
    localStorage.setItem(SESSION_KEYS.username, payload.user.username)
  }
  if (payload.user?.account) {
    localStorage.setItem(SESSION_KEYS.account, payload.user.account)
  }
  if (payload.user?.role) {
    localStorage.setItem(SESSION_KEYS.role, payload.user.role)
  }
  if (payload.session_expires_at) {
    localStorage.setItem(SESSION_KEYS.expiresAt, payload.session_expires_at)
  }
}

export const setSessionPermissions = (permissions: unknown): void => {
  localStorage.setItem(SESSION_KEYS.permissions, JSON.stringify(permissions))
}
