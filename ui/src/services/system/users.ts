import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type { AdminUser, AdminUserCreate, AdminUserUpdate } from './types'

export const fetchUsers = () => apiGet<AdminUser[]>('/admin/users')
export const createUser = (payload: AdminUserCreate) => apiPost<AdminUser>('/admin/users', payload)
export const updateUser = (userId: number, payload: AdminUserUpdate) =>
  apiPut<AdminUser>(`/admin/users/${userId}`, payload)
export const resetUserPassword = (userId: number) =>
  apiPost<{ status: string; password: string }>(`/admin/users/${userId}/reset-password`)
export const deleteUser = (userId: number) => apiDelete(`/admin/users/${userId}`)
