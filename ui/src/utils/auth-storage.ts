export type AuthUserSnapshot = {
  email?: string
  username?: string
  account?: string
  role?: string
}

export type PersistAuthSessionParams = {
  user?: AuthUserSnapshot
  permissions?: unknown
  sessionExpiresAt?: string
}

const AUTH_KEYS = [
  'access_token',
  'user_email',
  'user_name',
  'user_account',
  'user_role',
  'user_permissions',
  'session_expires_at',
] as const

export const clearAuthStorage = () => {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key))
}

export const clearAuthSession = clearAuthStorage

export const persistAuthSession = ({ user, permissions, sessionExpiresAt }: PersistAuthSessionParams) => {
  if (user?.email) {
    localStorage.setItem('user_email', user.email)
  }

  if (user?.username) {
    localStorage.setItem('user_name', user.username)
  }

  if (user?.account) {
    localStorage.setItem('user_account', user.account)
  }

  if (user?.role) {
    localStorage.setItem('user_role', user.role)
  }

  if (typeof permissions !== 'undefined') {
    localStorage.setItem('user_permissions', JSON.stringify(permissions))
  }

  if (sessionExpiresAt) {
    localStorage.setItem('session_expires_at', sessionExpiresAt)
  }
}
