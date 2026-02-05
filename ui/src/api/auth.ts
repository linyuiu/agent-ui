import { apiPost } from './http'

export type PasswordChangePayload = {
  current_password: string
  new_password: string
}

export const changePassword = (payload: PasswordChangePayload) =>
  apiPost<{ status: string }>('/auth/password', payload)
