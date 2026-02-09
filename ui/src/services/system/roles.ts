import { apiDelete, apiGet, apiPost } from '../http'
import type { Role, RoleCreate } from './types'

export const fetchRoles = () => apiGet<Role[]>('/admin/roles')
export const createRole = (payload: RoleCreate) => apiPost<Role>('/admin/roles', payload)
export const deleteRole = (roleId: number) => apiDelete(`/admin/roles/${roleId}`)
