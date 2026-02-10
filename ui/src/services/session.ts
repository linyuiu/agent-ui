export const SESSION_KEYS = {
  accessToken: 'access_token',
  email: 'user_email',
  role: 'user_role',
  username: 'user_name',
  account: 'user_account',
  permissions: 'user_permissions',
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
  access_token?: string
  user?: LoginUserPayload
}

const getItem = (key: string) => localStorage.getItem(key) || ''

export const getSessionToken = (): string => getItem(SESSION_KEYS.accessToken)

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
  if (payload.access_token) {
    localStorage.setItem(SESSION_KEYS.accessToken, payload.access_token)
  }
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
}

export const setSessionPermissions = (permissions: unknown): void => {
  localStorage.setItem(SESSION_KEYS.permissions, JSON.stringify(permissions))
}
