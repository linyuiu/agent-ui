import { apiDelete, apiGet, apiPost, apiPut } from '../http'
import type {
  PermissionGrant,
  PermissionGrantCreate,
  PermissionSubjectSummary,
  PermissionSubjectUpdate,
} from './types'

export const fetchPermissionGrants = () => apiGet<PermissionGrant[]>('/admin/permissions')
export const createPermissionGrant = (payload: PermissionGrantCreate) =>
  apiPost<PermissionGrant>('/admin/permissions', payload)
export const deletePermissionGrant = (grantId: number) => apiDelete(`/admin/permissions/${grantId}`)

export const fetchSubjectPermissions = (params: {
  subject_type: 'user' | 'role'
  subject_id: string
  scope: 'menu' | 'resource'
}) =>
  apiGet<PermissionSubjectSummary>(
    `/admin/permissions/subject?subject_type=${params.subject_type}&subject_id=${encodeURIComponent(
      params.subject_id
    )}&scope=${params.scope}`
  )

export const updateSubjectPermissions = (payload: PermissionSubjectUpdate) =>
  apiPut<PermissionSubjectSummary>('/admin/permissions/subject', payload)
