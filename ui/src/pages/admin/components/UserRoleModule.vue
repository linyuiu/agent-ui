<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>用户管理</h2>
        <p>管理账号、角色与权限分配。</p>
      </div>
    </div>

    <div class="panel user-panel">
      <div class="user-toolbar">
        <div ref="filterRef" class="search-box filter-box">
          <button class="filter-trigger" type="button" @click="toggleFilter">
            {{ userFilterField === 'username' ? '用户名' : '账号' }}
            <span class="caret" :class="{ open: filterOpen }"></span>
          </button>
          <transition name="slide-fade">
            <div v-if="filterOpen" class="filter-dropdown">
              <button class="filter-option" type="button" @click="selectFilter('username')">
                用户名
              </button>
              <button class="filter-option" type="button" @click="selectFilter('account')">
                账号
              </button>
            </div>
          </transition>
          <input
            v-model="userSearch"
            type="text"
            :placeholder="userFilterField === 'username' ? '搜索用户名' : '搜索账号'"
          />
        </div>
        <div class="toolbar-actions">
          <button class="ghost" type="button" @click="handleSyncUsers">同步用户</button>
          <button class="primary" type="button" @click="toggleUserForm">
            {{ showUserForm ? '收起' : '添加用户' }}
          </button>
        </div>
      </div>

      <div v-if="showUserForm" class="user-form-panel">
        <form class="form" @submit.prevent="handleCreateUser">
          <div class="field">
            <label>账号</label>
            <input v-model="userForm.account" type="text" placeholder="demo" required />
          </div>
          <div class="field">
            <label>用户名</label>
            <input v-model="userForm.username" type="text" placeholder="Demo User" required />
          </div>
          <div class="field">
            <label>邮箱</label>
            <input v-model="userForm.email" type="email" placeholder="user@example.com" required />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="userForm.password" type="password" placeholder="至少 6 位" required />
          </div>
          <div class="field">
            <label>角色</label>
            <div class="inline-dropdown" @click.stop>
              <button
                class="filter-trigger inline-trigger"
                type="button"
                @click.stop="toggleCreateRoleDropdown"
              >
                <span>{{ formatRoleList(userForm.roles) }}</span>
                <span class="caret" :class="{ open: createRoleDropdownOpen }"></span>
              </button>
              <div v-if="createRoleDropdownOpen" class="filter-dropdown inline-dropdown-panel">
                <button
                  v-for="role in roles"
                  :key="role.id"
                  class="filter-option"
                  type="button"
                  @click="toggleCreateUserRole(role.name)"
                >
                  <span>{{ userForm.roles.includes(role.name) ? '✓ ' : '' }}{{ role.name }}</span>
                </button>
                <button
                  v-if="!roles.length"
                  class="filter-option"
                  type="button"
                  @click="toggleCreateUserRole('user')"
                >
                  <span>{{ userForm.roles.includes('user') ? '✓ ' : '' }}user</span>
                </button>
              </div>
            </div>
          </div>
          <div class="field">
            <label>用户状态</label>
            <div class="inline-dropdown" @click.stop>
              <button
                class="filter-trigger inline-trigger"
                type="button"
                @click.stop="toggleCreateStatusDropdown"
              >
                <span>{{ userForm.status }}</span>
                <span class="caret" :class="{ open: createStatusDropdownOpen }"></span>
              </button>
              <div v-if="createStatusDropdownOpen" class="filter-dropdown inline-dropdown-panel">
                <button class="filter-option" type="button" @click="setCreateUserStatus('active')">
                  active
                </button>
                <button class="filter-option" type="button" @click="setCreateUserStatus('disabled')">
                  disabled
                </button>
              </div>
            </div>
          </div>
          <div class="field">
            <label>用户来源</label>
            <input v-model="userForm.source" type="text" placeholder="local" />
          </div>
          <div class="field">
            <label>工作空间</label>
            <input v-model="userForm.workspace" type="text" placeholder="default" />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="userLoading">
              {{ userLoading ? '创建中...' : '创建用户' }}
            </button>
          </div>
        </form>
      </div>

      <p v-if="userError" class="state error">{{ userError }}</p>
      <p v-if="userSuccess" class="state success">{{ userSuccess }}</p>

      <div class="table">
        <div class="table-head">
          <div class="col col-check"><input type="checkbox" disabled /></div>
          <div class="col col-name">用户名</div>
          <div class="col col-account">账号</div>
          <div class="col col-status">用户状态</div>
          <div class="col col-email">邮箱</div>
          <div class="col col-source">用户来源</div>
          <div class="col col-workspace">工作空间</div>
          <div class="col col-created">创建时间</div>
          <div class="col col-role">角色</div>
          <div class="col col-ops">操作</div>
        </div>

        <div v-if="usersLoading" class="state">加载用户中...</div>
        <div v-else-if="usersError" class="state error">{{ usersError }}</div>

        <div v-else-if="filteredUsers.length" class="table-body">
          <div v-for="(user, index) in filteredUsers" :key="user.id" class="table-row">
            <div class="col col-check"><input type="checkbox" /></div>
            <div class="col col-name">{{ user.username }}</div>
            <div class="col col-account">{{ user.account }}</div>
            <div class="col col-status">
              <div class="inline-dropdown" :class="{ 'drop-up': shouldOpenUserDropdownUp(index) }" @click.stop>
                <button
                  class="filter-trigger inline-trigger"
                  type="button"
                  :disabled="isAdminAccount(user.account)"
                  @click.stop="toggleStatusDropdown(user.id)"
                >
                  <span>{{ user.status }}</span>
                  <span class="caret" :class="{ open: statusOpenFor === user.id }"></span>
                </button>
                <div v-if="statusOpenFor === user.id" class="filter-dropdown inline-dropdown-panel">
                  <button class="filter-option" type="button" @click="setUserStatus(user, 'active')">
                    active
                  </button>
                  <button class="filter-option" type="button" @click="setUserStatus(user, 'disabled')">
                    disabled
                  </button>
                </div>
              </div>
            </div>
            <div class="col col-email">{{ user.email }}</div>
            <div class="col col-source">{{ user.source || 'local' }}</div>
            <div class="col col-workspace">{{ user.workspace || 'default' }}</div>
            <div class="col col-created">{{ new Date(user.created_at).toLocaleString() }}</div>
            <div class="col col-role">
              <div class="inline-dropdown" :class="{ 'drop-up': shouldOpenUserDropdownUp(index) }" @click.stop>
                <button
                  class="filter-trigger inline-trigger"
                  type="button"
                  :disabled="isAdminAccount(user.account)"
                  @click.stop="toggleRoleDropdown(user.id)"
                >
                  <span>{{ user.roles?.length ? user.roles.join(', ') : user.role }}</span>
                  <span class="caret" :class="{ open: roleOpenFor === user.id }"></span>
                </button>
                <div v-if="roleOpenFor === user.id" class="filter-dropdown inline-dropdown-panel">
                  <button
                    v-for="role in roles"
                    :key="role.id"
                    class="filter-option"
                    type="button"
                    @click="toggleUserRole(user, role.name)"
                  >
                    <span>{{ user.roles?.includes(role.name) ? '✓ ' : '' }}{{ role.name }}</span>
                  </button>
                  <button v-if="!roles.length" class="filter-option" type="button" @click="toggleUserRole(user, 'user')">
                    <span>{{ user.roles?.includes('user') ? '✓ ' : '' }}user</span>
                  </button>
                </div>
              </div>
            </div>
            <div class="col col-ops">
              <button
                class="ghost action-control"
                type="button"
                :disabled="isAdminAccount(user.account)"
                :title="isAdminAccount(user.account) ? 'admin 账号不可修改角色/状态' : ''"
                @click="handleUpdateUser(user)"
              >
                保存
              </button>
              <button class="ghost danger action-control" type="button" @click="openResetPassword(user)">
                重置密码
              </button>
              <button
                class="ghost danger action-control"
                type="button"
                :disabled="isAdminAccount(user.account)"
                :title="isAdminAccount(user.account) ? 'admin 账号不可删除' : ''"
                @click="openDeleteUser(user)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
        <div v-else class="state">暂无用户数据</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div>
        <h2>角色管理</h2>
        <p>创建角色并维护权限模板。</p>
      </div>
    </div>

    <div class="panel role-panel">
      <div class="user-toolbar">
        <div class="search-box">
          <input v-model="roleSearch" type="text" placeholder="搜索角色名称" />
        </div>
        <div class="toolbar-actions">
          <button class="primary" type="button" @click="showRoleForm = !showRoleForm">
            {{ showRoleForm ? '收起' : '新增角色' }}
          </button>
        </div>
      </div>

      <div v-if="showRoleForm" class="user-form-panel">
        <form class="form role-create-form" @submit.prevent="handleCreateRole">
          <div class="field">
            <label>角色名称</label>
            <input v-model="roleForm.name" type="text" placeholder="ops" required />
          </div>
          <div class="field">
            <label>角色描述</label>
            <input v-model="roleForm.description" type="text" placeholder="运营角色" />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="roleLoading">
              {{ roleLoading ? '保存中...' : '保存角色' }}
            </button>
          </div>
        </form>
      </div>

      <p v-if="roleError" class="state error">{{ roleError }}</p>
      <p v-if="roleSuccess" class="state success">{{ roleSuccess }}</p>

      <div v-if="rolesLoading" class="state">加载角色中...</div>
      <div v-else-if="rolesError" class="state error">{{ rolesError }}</div>
      <div v-else class="role-list">
        <div v-if="filteredRoleList.length" class="grid">
          <div v-for="role in filteredRoleList" :key="role.id" class="policy-card">
            <div>
              <h3>{{ role.name }}</h3>
              <p>{{ role.description || '暂无描述' }}</p>
            </div>
            <div class="policy-actions">
              <button
                class="ghost danger"
                type="button"
                :disabled="isProtectedRole(role.name)"
                @click="openDeleteRole(role)"
              >
                {{ isProtectedRole(role.name) ? '系统角色不可删除' : '删除角色' }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="state">暂无角色</div>
      </div>
    </div>
  </div>

  <div v-if="showResetModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>重置密码</h3>
        <button class="modal-close" type="button" @click="closeResetModal">✕</button>
      </div>
      <p class="modal-body">
        确认将 <strong>{{ resetTarget?.username }}</strong> 的密码重置为
        <code>agentui@2025</code> 吗？
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeResetModal">取消</button>
        <button class="primary" type="button" :disabled="resetting" @click="confirmResetPassword">
          {{ resetting ? '处理中...' : '确认重置' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="showDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除用户</h3>
        <button class="modal-close" type="button" @click="closeDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ deleteTarget?.username }}</strong> 吗？该用户的权限数据将一并删除。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="deleting" @click="confirmDeleteUser">
          {{ deleting ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="showRoleDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除角色</h3>
        <button class="modal-close" type="button" @click="closeRoleDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ roleDeleteTarget?.name }}</strong> 吗？该角色的权限数据将一并删除。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeRoleDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="roleDeleting" @click="confirmDeleteRole">
          {{ roleDeleting ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAdminSubjects } from '../../../composables/use-admin-subjects'
import { useDocumentClick } from '../../../composables/use-document-click'
import { includesKeyword, useSearchableList } from '../../../composables/use-searchable-list'
import {
  createRole,
  createUser,
  deleteRole,
  deleteUser,
  resetUserPassword,
  updateUser,
  type AdminUser,
  type Role,
} from '../../../services/admin'

const roleLoading = ref(false)
const roleError = ref('')
const roleSuccess = ref('')
const showRoleForm = ref(false)

const userLoading = ref(false)
const userError = ref('')
const userSuccess = ref('')
const userSearch = ref('')
const userFilterField = ref<'username' | 'account'>('username')
const showUserForm = ref(false)
const roleSearch = ref('')
const filterOpen = ref(false)
const filterRef = ref<HTMLElement | null>(null)
const statusOpenFor = ref<number | null>(null)
const roleOpenFor = ref<number | null>(null)
const createRoleDropdownOpen = ref(false)
const createStatusDropdownOpen = ref(false)

const showResetModal = ref(false)
const resetTarget = ref<AdminUser | null>(null)
const resetting = ref(false)
const showDeleteModal = ref(false)
const deleteTarget = ref<AdminUser | null>(null)
const deleting = ref(false)
const showRoleDeleteModal = ref(false)
const roleDeleteTarget = ref<Role | null>(null)
const roleDeleting = ref(false)

const roleForm = ref({
  name: '',
  description: '',
})

const userForm = ref({
  account: '',
  username: '',
  email: '',
  password: '',
  role: 'user',
  roles: ['user'] as string[],
  status: 'active',
  source: 'local',
  workspace: 'default',
})

const orderRoleNamesByCatalog = (roleNames: string[], catalog: string[] = []) => {
  const unique = Array.from(new Set(roleNames.map((item) => String(item || '').trim()).filter(Boolean)))

  return unique.sort((a, b) => {
    const ai = catalog.indexOf(a)
    const bi = catalog.indexOf(b)
    if (ai === -1 && bi === -1) return a.localeCompare(b)
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}

const normalizeRoleNamesByCatalog = (singleRole?: string, roleNames?: string[], catalog: string[] = []) => {
  const source = roleNames?.length ? roleNames : singleRole ? [singleRole] : []
  const ordered = orderRoleNamesByCatalog(source, catalog)
  if (ordered.length) return ordered
  return ['user']
}

const getPrimaryRole = (roleNames: string[]) => {
  if (roleNames.includes('admin')) return 'admin'
  return roleNames[0] || 'user'
}

const mapUsersWithRoles = (records: AdminUser[], roleCatalog: Role[]) => {
  const catalog = roleCatalog.map((item) => item.name)
  return records.map((item) => {
    const nextRoles = normalizeRoleNamesByCatalog(item.role, item.roles, catalog)
    return {
      ...item,
      role: getPrimaryRole(nextRoles),
      roles: nextRoles,
    }
  })
}

const { roles, users, usersLoading, usersError, rolesLoading, rolesError, loadUsers, loadRoles } =
  useAdminSubjects({ mapUsers: mapUsersWithRoles })

const roleCatalog = computed(() => roles.value.map((item) => item.name))

const normalizeRoleNames = (singleRole?: string, roleNames?: string[]) =>
  normalizeRoleNamesByCatalog(singleRole, roleNames, roleCatalog.value)

const formatRoleList = (roleNames?: string[]) => normalizeRoleNames(undefined, roleNames).join(', ')

const toggleRoleName = (roleNames: string[], targetRole: string) => {
  const next = [...normalizeRoleNames(undefined, roleNames)]
  const idx = next.indexOf(targetRole)
  if (idx >= 0) {
    if (next.length === 1) return next
    next.splice(idx, 1)
    return orderRoleNamesByCatalog(next, roleCatalog.value)
  }
  next.push(targetRole)
  return orderRoleNamesByCatalog(next, roleCatalog.value)
}

const { filtered: filteredUsers } = useSearchableList(users, userSearch, (user, keyword) =>
  includesKeyword(keyword, userFilterField.value === 'account' ? user.account : user.username),
)

const shouldOpenUserDropdownUp = (index: number) => {
  const threshold = 2
  return index >= Math.max(0, filteredUsers.value.length - threshold)
}

const { filtered: filteredRoleList } = useSearchableList(roles, roleSearch, (role, keyword) =>
  includesKeyword(keyword, role.name),
)

const protectedRoles = new Set(['admin', 'user'])
const isProtectedRole = (name: string) => protectedRoles.has(name)
const isAdminAccount = (account?: string) => String(account || '').trim().toLowerCase() === 'admin'

const handleCreateRole = async () => {
  roleLoading.value = true
  roleError.value = ''
  roleSuccess.value = ''
  try {
    await createRole(roleForm.value)
    roleSuccess.value = '角色已创建。'
    roleForm.value = { name: '', description: '' }
    await loadRoles()
  } catch (err) {
    roleError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    roleLoading.value = false
  }
}

const handleCreateUser = async () => {
  userLoading.value = true
  userError.value = ''
  userSuccess.value = ''

  try {
    const nextRoles = normalizeRoleNames(userForm.value.role, userForm.value.roles)
    await createUser({
      ...userForm.value,
      role: getPrimaryRole(nextRoles),
      roles: nextRoles,
    })
    userSuccess.value = '用户已创建。'
    userForm.value = {
      account: '',
      username: '',
      email: '',
      password: '',
      role: 'user',
      roles: ['user'],
      status: 'active',
      source: 'local',
      workspace: 'default',
    }
    createRoleDropdownOpen.value = false
    createStatusDropdownOpen.value = false
    showUserForm.value = false
    await loadUsers()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '创建失败'
  } finally {
    userLoading.value = false
  }
}

const toggleUserForm = () => {
  showUserForm.value = !showUserForm.value
  if (!showUserForm.value) {
    createRoleDropdownOpen.value = false
    createStatusDropdownOpen.value = false
  }
}

const toggleFilter = () => {
  filterOpen.value = !filterOpen.value
}

const selectFilter = (value: 'username' | 'account') => {
  userFilterField.value = value
  filterOpen.value = false
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node
  if (filterOpen.value && filterRef.value && !filterRef.value.contains(target)) {
    filterOpen.value = false
  }
  statusOpenFor.value = null
  roleOpenFor.value = null
  createRoleDropdownOpen.value = false
  createStatusDropdownOpen.value = false
}

const toggleStatusDropdown = (userId: number) => {
  roleOpenFor.value = null
  createRoleDropdownOpen.value = false
  createStatusDropdownOpen.value = false
  statusOpenFor.value = statusOpenFor.value === userId ? null : userId
}

const toggleRoleDropdown = (userId: number) => {
  statusOpenFor.value = null
  createRoleDropdownOpen.value = false
  createStatusDropdownOpen.value = false
  roleOpenFor.value = roleOpenFor.value === userId ? null : userId
}

const toggleCreateRoleDropdown = () => {
  statusOpenFor.value = null
  roleOpenFor.value = null
  createStatusDropdownOpen.value = false
  createRoleDropdownOpen.value = !createRoleDropdownOpen.value
}

const setUserStatus = (user: AdminUser, value: string) => {
  user.status = value
  statusOpenFor.value = null
}

const toggleCreateStatusDropdown = () => {
  statusOpenFor.value = null
  roleOpenFor.value = null
  createRoleDropdownOpen.value = false
  createStatusDropdownOpen.value = !createStatusDropdownOpen.value
}

const setCreateUserStatus = (value: 'active' | 'disabled') => {
  userForm.value.status = value
  createStatusDropdownOpen.value = false
}

const toggleCreateUserRole = (roleName: string) => {
  userForm.value.roles = toggleRoleName(userForm.value.roles, roleName)
  userForm.value.role = getPrimaryRole(userForm.value.roles)
}

const toggleUserRole = (user: AdminUser, roleName: string) => {
  const current = normalizeRoleNames(user.role, user.roles)
  const next = toggleRoleName(current, roleName)
  user.roles = next
  user.role = getPrimaryRole(next)
}

const handleSyncUsers = async () => {
  userError.value = ''
  userSuccess.value = ''
  try {
    await loadUsers()
    userSuccess.value = '同步功能暂未开放，已刷新用户列表。'
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '同步失败'
  }
}

const handleUpdateUser = async (user: AdminUser) => {
  userError.value = ''
  userSuccess.value = ''
  try {
    await updateUser(user.id, {
      role: user.role,
      roles: user.roles?.length ? user.roles : [user.role],
      status: user.status,
    })
    userSuccess.value = `用户 ${user.username} 已更新。`
    await loadUsers()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '更新失败'
  }
}

const openResetPassword = (user: AdminUser) => {
  resetTarget.value = user
  showResetModal.value = true
}

const closeResetModal = () => {
  showResetModal.value = false
  resetTarget.value = null
}

const confirmResetPassword = async () => {
  if (!resetTarget.value) return
  resetting.value = true
  userError.value = ''
  userSuccess.value = ''
  try {
    await resetUserPassword(resetTarget.value.id)
    userSuccess.value = `用户 ${resetTarget.value.username} 密码已重置为 agentui@2025。`
    closeResetModal()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '重置失败'
  } finally {
    resetting.value = false
  }
}

const openDeleteUser = (user: AdminUser) => {
  deleteTarget.value = user
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  deleteTarget.value = null
}

const confirmDeleteUser = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  userError.value = ''
  userSuccess.value = ''
  try {
    await deleteUser(deleteTarget.value.id)
    userSuccess.value = `用户 ${deleteTarget.value.username} 已删除。`
    closeDeleteModal()
    await loadUsers()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

const openDeleteRole = (role: Role) => {
  if (isProtectedRole(role.name)) {
    rolesError.value = '系统角色不可删除'
    return
  }
  roleDeleteTarget.value = role
  showRoleDeleteModal.value = true
}

const closeRoleDeleteModal = () => {
  showRoleDeleteModal.value = false
  roleDeleteTarget.value = null
}

const confirmDeleteRole = async () => {
  if (!roleDeleteTarget.value) return
  roleDeleting.value = true
  rolesError.value = ''
  roleSuccess.value = ''
  try {
    await deleteRole(roleDeleteTarget.value.id)
    roleSuccess.value = `角色 ${roleDeleteTarget.value.name} 已删除。`
    closeRoleDeleteModal()
    await Promise.all([loadRoles(), loadUsers()])
  } catch (err) {
    rolesError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    roleDeleting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadUsers()])
})

useDocumentClick(handleDocumentClick)
</script>

<style scoped src="./UserRoleModule.css"></style>
