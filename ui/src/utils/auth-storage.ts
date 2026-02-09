export type AuthUserSnapshot = {
  email?: string
  username?: string
  account?: string
  role?: string
}

export type PersistAuthSessionParams = {
  token?: string
  user?: AuthUserSnapshot
  permissions?: unknown
}

const AUTH_KEYS = [
  'access_token',
  'user_email',
  'user_name',
  'user_account',
  'user_role',
  'user_permissions',
] as const

export const clearAuthStorage = () => {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key))
}

export const persistAuthSession = ({ token, user, permissions }: PersistAuthSessionParams) => {
  if (token) {
    localStorage.setItem('access_token', token)
  }

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
}
