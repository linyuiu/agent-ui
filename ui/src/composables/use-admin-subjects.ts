import { ref } from 'vue'
import { fetchRoles, fetchUsers, type AdminUser, type Role } from '../services/admin'

type UseAdminSubjectsOptions = {
  mapUsers?: (users: AdminUser[], roles: Role[]) => AdminUser[]
}

export const useAdminSubjects = ({ mapUsers }: UseAdminSubjectsOptions = {}) => {
  const roles = ref<Role[]>([])
  const users = ref<AdminUser[]>([])

  const usersLoading = ref(false)
  const usersError = ref('')
  const rolesLoading = ref(false)
  const rolesError = ref('')

  const loadUsers = async () => {
    usersLoading.value = true
    usersError.value = ''
    try {
      const fetched = await fetchUsers()
      users.value = mapUsers ? mapUsers(fetched, roles.value) : fetched
    } catch (err) {
      usersError.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      usersLoading.value = false
    }
  }

  const loadRoles = async () => {
    rolesLoading.value = true
    rolesError.value = ''
    try {
      roles.value = await fetchRoles()
    } catch (err) {
      rolesError.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      rolesLoading.value = false
    }
  }

  return {
    roles,
    users,
    usersLoading,
    usersError,
    rolesLoading,
    rolesError,
    loadUsers,
    loadRoles,
  }
}
