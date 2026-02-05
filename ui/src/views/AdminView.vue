<template>
  <div class="admin">
    <div class="section">
      <div class="section-header">
        <div>
          <h2>用户管理</h2>
          <p>管理账号、角色与权限分配。</p>
        </div>
      </div>

      <div class="panel user-panel">
        <div class="user-toolbar">
          <div class="search-box">
            <select v-model="userFilterField" class="filter-select">
              <option value="username">用户名</option>
              <option value="account">账号</option>
            </select>
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
              <select v-model="userForm.role">
                <option v-if="!roles.length" value="user">user</option>
                <option v-for="role in roles" :key="role.id" :value="role.name">
                  {{ role.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>用户状态</label>
              <select v-model="userForm.status">
                <option value="active">active</option>
                <option value="disabled">disabled</option>
              </select>
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
            <div class="col col-actions">操作</div>
          </div>

          <div v-if="usersLoading" class="state">加载用户中...</div>
          <div v-else-if="usersError" class="state error">{{ usersError }}</div>

          <div v-else-if="filteredUsers.length" class="table-body">
            <div v-for="user in filteredUsers" :key="user.id" class="table-row">
              <div class="col col-check"><input type="checkbox" /></div>
              <div class="col col-name">{{ user.username }}</div>
              <div class="col col-account">{{ user.account }}</div>
              <div class="col col-status">
                <select v-model="user.status">
                  <option value="active">active</option>
                  <option value="disabled">disabled</option>
                </select>
              </div>
              <div class="col col-email">{{ user.email }}</div>
              <div class="col col-source">{{ user.source || 'local' }}</div>
              <div class="col col-workspace">{{ user.workspace || 'default' }}</div>
              <div class="col col-created">
                {{ new Date(user.created_at).toLocaleString() }}
              </div>
              <div class="col col-actions">
                <select v-model="user.role" class="action-control">
                  <option v-if="!roles.length" value="user">user</option>
                  <option v-for="role in roles" :key="role.id" :value="role.name">
                    {{ role.name }}
                  </option>
                </select>
                <button class="ghost action-control" type="button" @click="handleUpdateUser(user)">
                  保存
                </button>
                <button
                  class="ghost danger action-control"
                  type="button"
                  @click="openResetPassword(user)"
                >
                  重置密码
                </button>
                <button
                  class="ghost danger action-control"
                  type="button"
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

    <div class="section">
      <div class="section-header">
        <div>
          <h2>权限管理</h2>
          <p>菜单权限与资源权限可直接勾选并保存。</p>
        </div>
      </div>

      <div class="panel permission-board">
        <div class="permission-header">
          <div class="tab-group">
            <button
              class="tab"
              :class="{ active: subjectTab === 'user' }"
              type="button"
              @click="subjectTab = 'user'"
            >
              用户
            </button>
            <button
              class="tab"
              :class="{ active: subjectTab === 'role' }"
              type="button"
              @click="subjectTab = 'role'"
            >
              角色
            </button>
          </div>
          <div class="tab-group">
            <button
              class="tab"
              :class="{ active: scopeTab === 'menu' }"
              type="button"
              @click="scopeTab = 'menu'"
            >
              菜单权限
            </button>
            <button
              class="tab"
              :class="{ active: scopeTab === 'resource' }"
              type="button"
              @click="scopeTab = 'resource'"
            >
              资源权限
            </button>
          </div>
          <button
            class="primary"
            type="button"
            :disabled="permissionSaving || !selectedSubjectId || subjectReadOnly || isAdminSubject"
            @click="handleSavePermissions"
          >
            {{ permissionSaving ? '保存中...' : '保存' }}
          </button>
        </div>

        <p v-if="permissionError" class="state error">{{ permissionError }}</p>
        <p v-if="permissionSuccess" class="state success">{{ permissionSuccess }}</p>
        <p v-if="isAdminSubject" class="state">admin 默认拥有全部权限，无需配置。</p>
        <p v-if="subjectReadOnly && !isAdminSubject" class="state">
          该用户为超级管理员，权限不可修改。
        </p>

        <div class="permission-body">
          <aside class="permission-column subject-column">
            <div class="column-title">{{ subjectTab === 'user' ? '用户' : '角色' }}</div>
          <div class="search-box compact">
            <input v-model="subjectSearch" type="text" placeholder="搜索" />
          </div>
          <p v-if="subjectTab === 'user' && usersLoading" class="state">加载用户中...</p>
          <p v-if="subjectTab === 'user' && usersError" class="state error">{{ usersError }}</p>
          <p v-if="subjectTab === 'role' && rolesLoading" class="state">加载角色中...</p>
          <p v-if="subjectTab === 'role' && rolesError" class="state error">{{ rolesError }}</p>
          <div v-if="subjectTab === 'user'" class="list">
            <button
              v-for="user in filteredSubjects"
              :key="user.id"
                class="list-item"
                :class="{ active: selectedSubjectId === String(user.id) }"
                type="button"
                @click="selectedSubjectId = String(user.id)"
              >
                <strong>{{ user.username }}</strong>
                <small>{{ user.account }}</small>
              </button>
            </div>
          <div v-else class="list">
            <button
              v-for="role in filteredSubjects"
              :key="role.id"
              class="list-item"
              :class="{ active: selectedSubjectId === role.name }"
              type="button"
              @click="selectedSubjectId = role.name"
            >
              <strong>{{ role.name }}</strong>
              <small>{{ role.description || '暂无描述' }}</small>
            </button>
          </div>

          <div v-if="subjectTab === 'role'" class="role-form">
            <div v-if="selectedRole" class="role-actions">
              <button
                class="ghost danger"
                type="button"
                :disabled="isProtectedRole(selectedRole.name)"
                @click="handleDeleteRole(selectedRole)"
              >
                {{ isProtectedRole(selectedRole.name) ? '系统角色不可删除' : '删除角色' }}
              </button>
            </div>
            <button class="ghost" type="button" @click="showRoleForm = !showRoleForm">
              {{ showRoleForm ? '收起角色表单' : '新增角色' }}
            </button>
              <form v-if="showRoleForm" class="form compact-form" @submit.prevent="handleCreateRole">
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
              <p v-if="roleError" class="state error">{{ roleError }}</p>
              <p v-if="roleSuccess" class="state success">{{ roleSuccess }}</p>
            </div>
          </aside>

          <aside class="permission-column scope-column">
            <div class="column-title">
              {{ scopeTab === 'menu' ? '菜单权限' : '资源分类' }}
            </div>
            <div class="list">
              <button
                v-for="item in scopeItems"
                :key="item.id"
                class="list-item"
                :class="{ active: selectedScopeId === item.id }"
                type="button"
                @click="selectedScopeId = item.id"
              >
                <strong>{{ item.label }}</strong>
                <small>{{ item.subLabel }}</small>
              </button>
            </div>
          </aside>

          <section class="permission-column table-column">
            <div class="table-toolbar">
              <input v-model="tableSearch" type="text" placeholder="搜索名称" />
            </div>

            <div v-if="permissionsLoading" class="state">加载授权中...</div>
            <div v-else-if="permissionsError" class="state error">{{ permissionsError }}</div>

            <div v-else class="table permission-grid">
              <div class="table-head permission-row">
                <div class="col col-name">资源名称</div>
                <div class="col col-action">查看</div>
                <div class="col col-action">编辑</div>
                <div class="col col-action">管理</div>
              </div>
              <div v-if="filteredRows.length" class="table-body">
                <div v-for="row in filteredRows" :key="row.key" class="table-row permission-row">
                  <div class="col col-name">
                    <span class="row-title">{{ row.label }}</span>
                    <small v-if="row.subLabel">{{ row.subLabel }}</small>
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'view')"
                      :checked="isRowChecked(row, 'view')"
                      @change="toggleRowAction(row, 'view', $event)"
                    />
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'edit')"
                      :checked="isRowChecked(row, 'edit')"
                      @change="toggleRowAction(row, 'edit', $event)"
                    />
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'manage')"
                      :checked="isRowChecked(row, 'manage')"
                      @change="toggleRowAction(row, 'manage', $event)"
                    />
                  </div>
                </div>
              </div>
              <div v-else class="state">暂无资源</div>
            </div>
          </section>
        </div>
      </div>

      <div class="panel">
        <div class="section-header">
          <div>
            <h3>智能体分组管理</h3>
            <p>创建与维护可用于授权的分组。</p>
          </div>
        </div>

        <form class="form" @submit.prevent="handleCreateGroup">
          <div class="field">
            <label>分组名称</label>
            <input v-model="groupForm.name" type="text" placeholder="operations" required />
          </div>
          <div class="field">
            <label>分组描述</label>
            <input v-model="groupForm.description" type="text" placeholder="运营团队" />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="groupLoading">
              {{ groupLoading ? '保存中...' : '新增分组' }}
            </button>
          </div>
        </form>

        <p v-if="groupError" class="state error">{{ groupError }}</p>
        <p v-if="groupSuccess" class="state success">{{ groupSuccess }}</p>
        <p v-if="groupsLoading" class="state">加载分组中...</p>
        <p v-if="groupsError" class="state error">{{ groupsError }}</p>

        <div v-if="groups.length" class="grid">
          <div v-for="group in groups" :key="group.id" class="policy-card">
            <div>
              <h3>{{ group.name }}</h3>
              <p>{{ group.description || '暂无描述' }}</p>
            </div>
            <div class="policy-actions">
              <button class="ghost danger" type="button" @click="handleDeleteGroup(group)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>智能体接入</h2>
          <p>填写 API 地址与 AK/SK，拉取并保存智能体数据。</p>
        </div>
      </div>

      <div class="panel">
        <form class="form" @submit.prevent="handleImport">
          <div class="field">
            <label>API 地址</label>
            <input v-model="importForm.api_url" type="text" placeholder="https://api.example.com/agents" required />
          </div>
          <div class="field">
            <label>AK</label>
            <input v-model="importForm.ak" type="text" placeholder="access key" required />
          </div>
          <div class="field">
            <label>SK</label>
            <input v-model="importForm.sk" type="password" placeholder="secret key" required />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="importLoading">
              {{ importLoading ? '拉取中...' : '拉取并保存' }}
            </button>
            <button class="ghost" type="button" @click="handleUseSampleImport">填充示例</button>
            <button class="ghost" type="button" @click="handleImportSample">一键导入示例</button>
          </div>
        </form>

        <p v-if="importError" class="state error">{{ importError }}</p>
        <p v-if="importSuccess" class="state success">{{ importSuccess }}</p>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>模型配置</h2>
          <p>新增模型并用于授权。</p>
        </div>
      </div>

      <div class="panel">
        <form class="form" @submit.prevent="handleCreateModel">
          <div class="field">
            <label>模型 ID</label>
            <input v-model="modelForm.id" type="text" placeholder="model-001" required />
          </div>
          <div class="field">
            <label>模型名称</label>
            <input v-model="modelForm.name" type="text" placeholder="Reasoning Pro" required />
          </div>
          <div class="field">
            <label>Provider</label>
            <input v-model="modelForm.provider" type="text" placeholder="OpenAI" />
          </div>
          <div class="field">
            <label>状态</label>
            <select v-model="modelForm.status">
              <option value="enabled">enabled</option>
              <option value="disabled">disabled</option>
            </select>
          </div>
          <div class="field">
            <label>上下文长度</label>
            <input v-model.number="modelForm.context_length" type="number" min="0" />
          </div>
          <div class="field">
            <label>描述</label>
            <input v-model="modelForm.description" type="text" placeholder="简短描述" />
          </div>
          <div class="field">
            <label>价格</label>
            <input v-model="modelForm.pricing" type="text" placeholder="$0.00" />
          </div>
          <div class="field">
            <label>版本</label>
            <input v-model="modelForm.release" type="text" placeholder="2026-02" />
          </div>
          <div class="field">
            <label>标签</label>
            <input v-model="modelForm.tags" type="text" placeholder="fast,accurate" />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="modelLoading">
              {{ modelLoading ? '保存中...' : '保存模型' }}
            </button>
            <button class="ghost" type="button" :disabled="modelSeedLoading" @click="handleSeedModels">
              {{ modelSeedLoading ? '填充中...' : '填充示例模型' }}
            </button>
          </div>
        </form>

        <p v-if="modelError" class="state error">{{ modelError }}</p>
        <p v-if="modelSuccess" class="state success">{{ modelSuccess }}</p>
        <p v-if="modelSeedSuccess" class="state success">{{ modelSeedSuccess }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { fetchAgents, type AgentSummary } from '../api/agents'
import { createModel, fetchModels, type ModelSummary } from '../api/models'
import {
  fetchUsers,
  createUser,
  updateUser,
  fetchRoles,
  createRole,
  deleteRole,
  fetchSubjectPermissions,
  updateSubjectPermissions,
  resetUserPassword,
  deleteUser,
  fetchAgentGroups,
  createAgentGroup,
  deleteAgentGroup,
  importAgents,
  type PermissionSubjectMatrixItem,
  type Role,
  type AdminUser,
  type AgentGroup,
} from '../api/admin'

type PermissionAction = 'view' | 'edit' | 'manage'
type PermissionActionState = Record<PermissionAction, boolean>

type PermissionRow = {
  key: string
  label: string
  subLabel?: string
  scope: 'menu' | 'resource'
  resourceType: string
  resourceId: string | null
}

type ScopeItem = {
  id: string
  label: string
  subLabel: string
}

const roles = ref<Role[]>([])
const users = ref<AdminUser[]>([])
const agents = ref<AgentSummary[]>([])
const models = ref<ModelSummary[]>([])
const groups = ref<AgentGroup[]>([])

const usersLoading = ref(false)
const usersError = ref('')
const rolesLoading = ref(false)
const rolesError = ref('')
const groupsLoading = ref(false)
const groupsError = ref('')
const permissionsLoading = ref(false)
const permissionsError = ref('')
const inheritedState = ref<Record<string, PermissionActionState>>({})
const subjectReadOnly = ref(false)

const roleLoading = ref(false)
const roleError = ref('')
const roleSuccess = ref('')
const showRoleForm = ref(false)

const groupLoading = ref(false)
const groupError = ref('')
const groupSuccess = ref('')

const showResetModal = ref(false)
const resetTarget = ref<AdminUser | null>(null)
const resetting = ref(false)
const showDeleteModal = ref(false)
const deleteTarget = ref<AdminUser | null>(null)
const deleting = ref(false)

const permissionSaving = ref(false)
const permissionError = ref('')
const permissionSuccess = ref('')

const importLoading = ref(false)
const importError = ref('')
const importSuccess = ref('')

const modelLoading = ref(false)
const modelError = ref('')
const modelSuccess = ref('')
const modelSeedLoading = ref(false)
const modelSeedSuccess = ref('')

const userLoading = ref(false)
const userError = ref('')
const userSuccess = ref('')
const userSearch = ref('')
const userFilterField = ref<'username' | 'account'>('username')
const showUserForm = ref(false)

const subjectTab = ref<'user' | 'role'>('user')
const scopeTab = ref<'menu' | 'resource'>('menu')
const subjectSearch = ref('')
const tableSearch = ref('')
const selectedSubjectId = ref('')
const selectedScopeId = ref('agents')
const permissionState = ref<Record<string, PermissionActionState>>({})

const roleForm = ref({
  name: '',
  description: '',
})

const groupForm = ref({
  name: '',
  description: '',
})

const modelForm = ref({
  id: '',
  name: '',
  provider: '',
  status: 'enabled',
  context_length: 0,
  description: '',
  pricing: '',
  release: '',
  tags: '',
})

const sampleImport = {
  api_url: 'http://localhost:8000/demo/agents',
  ak: 'demo-ak',
  sk: 'demo-sk',
}

const importForm = ref({
  api_url: sampleImport.api_url,
  ak: sampleImport.ak,
  sk: sampleImport.sk,
})

const userForm = ref({
  account: '',
  username: '',
  email: '',
  password: '',
  role: 'user',
  status: 'active',
  source: 'local',
  workspace: 'default',
})

const filteredUsers = computed(() => {
  const query = userSearch.value.trim().toLowerCase()
  if (!query) return users.value
  return users.value.filter((user) => {
    const field = userFilterField.value === 'account' ? user.account : user.username
    return String(field || '').toLowerCase().includes(query)
  })
})

const menuScopeItems: ScopeItem[] = [
  { id: 'all', label: '全部菜单', subLabel: '管理所有模块' },
  { id: 'agents', label: '智能体模块', subLabel: '管理与调度' },
  { id: 'models', label: '模型模块', subLabel: '能力与成本' },
  { id: 'admin', label: '权限模块', subLabel: '策略与接入' },
]

const resourceScopeItems: ScopeItem[] = [
  { id: 'agent', label: '智能体', subLabel: '具体智能体资源' },
  { id: 'agent_group', label: '智能体分组', subLabel: '按分组授权' },
  { id: 'model', label: '模型', subLabel: '具体模型资源' },
]

const scopeItems = computed(() => (scopeTab.value === 'menu' ? menuScopeItems : resourceScopeItems))

const filteredSubjects = computed(() => {
  const query = subjectSearch.value.trim().toLowerCase()
  if (subjectTab.value === 'user') {
    if (!query) return users.value
    return users.value.filter((user) => {
      const fields = [user.username, user.account, user.email]
      return fields.some((field) => String(field || '').toLowerCase().includes(query))
    })
  }

  if (!query) return roles.value
  return roles.value.filter((role) => {
    const fields = [role.name, role.description]
    return fields.some((field) => String(field || '').toLowerCase().includes(query))
  })
})

const protectedRoles = new Set(['admin', 'user'])
const isProtectedRole = (name: string) => protectedRoles.has(name)
const selectedRole = computed(() =>
  roles.value.find((role) => role.name === selectedSubjectId.value) || null
)
const selectedUser = computed(() =>
  users.value.find((user) => String(user.id) === selectedSubjectId.value) || null
)
const isAdminSubject = computed(() => subjectTab.value === 'role' && selectedSubjectId.value === 'admin')

const buildRowKey = (scope: string, resourceType: string, resourceId: string | null) =>
  `${scope}::${resourceType}::${resourceId ?? '*'}`

const allMenuRows = computed<PermissionRow[]>(() =>
  menuScopeItems
    .filter((item) => item.id !== 'all')
    .map((item) => ({
      key: buildRowKey('menu', 'menu', item.id),
      label: item.label,
      subLabel: item.subLabel,
      scope: 'menu',
      resourceType: 'menu',
      resourceId: item.id,
    }))
)

const agentGroups = computed(() =>
  groups.value.map((group) => group.name).filter(Boolean)
)

const allResourceRows = computed<PermissionRow[]>(() => {
  const rows: PermissionRow[] = []
  const agentHeader: PermissionRow = {
    key: buildRowKey('resource', 'agent', null),
    label: '全部智能体',
    subLabel: '通配所有智能体',
    scope: 'resource',
    resourceType: 'agent',
    resourceId: null,
  }
  rows.push(agentHeader)
  agents.value.forEach((agent) => {
    rows.push({
      key: buildRowKey('resource', 'agent', agent.id),
      label: agent.name,
      subLabel: agent.owner ? `Owner: ${agent.owner}` : agent.id,
      scope: 'resource',
      resourceType: 'agent',
      resourceId: agent.id,
    })
  })

  const modelHeader: PermissionRow = {
    key: buildRowKey('resource', 'model', null),
    label: '全部模型',
    subLabel: '通配所有模型',
    scope: 'resource',
    resourceType: 'model',
    resourceId: null,
  }
  rows.push(modelHeader)
  models.value.forEach((model) => {
    rows.push({
      key: buildRowKey('resource', 'model', model.id),
      label: model.name,
      subLabel: model.provider || model.id,
      scope: 'resource',
      resourceType: 'model',
      resourceId: model.id,
    })
  })

  const groupHeader: PermissionRow = {
    key: buildRowKey('resource', 'agent_group', null),
    label: '全部分组',
    subLabel: '通配所有分组',
    scope: 'resource',
    resourceType: 'agent_group',
    resourceId: null,
  }
  rows.push(groupHeader)
  agentGroups.value.forEach((group) => {
    rows.push({
      key: buildRowKey('resource', 'agent_group', group),
      label: group,
      subLabel: '智能体分组',
      scope: 'resource',
      resourceType: 'agent_group',
      resourceId: group,
    })
  })

  return rows
})

const allRows = computed(() => [...allMenuRows.value, ...allResourceRows.value])

const rowMetaMap = computed(() => {
  const map = new Map<string, PermissionRow>()
  allRows.value.forEach((row) => {
    map.set(row.key, row)
  })
  return map
})

const tableRows = computed(() => {
  if (scopeTab.value === 'menu') {
    if (selectedScopeId.value === 'all') {
      return allMenuRows.value
    }
    return allMenuRows.value.filter((row) => row.resourceId === selectedScopeId.value)
  }
  return allResourceRows.value.filter((row) => row.resourceType === selectedScopeId.value)
})

const filteredRows = computed(() => {
  const query = tableSearch.value.trim().toLowerCase()
  if (!query) return tableRows.value
  return tableRows.value.filter((row) =>
    [row.label, row.subLabel, row.resourceId]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(query))
  )
})

const loadUsers = async () => {
  usersLoading.value = true
  usersError.value = ''
  try {
    users.value = await fetchUsers()
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

const applyPermissionSummary = (summary: PermissionSubjectSummary | null) => {
  permissionState.value = {}
  inheritedState.value = {}
  subjectReadOnly.value = summary?.read_only ?? false
  if (!summary) return
  summary.items.forEach((item: PermissionSubjectMatrixItem) => {
    const key = buildRowKey(summary.scope, item.resource_type, item.resource_id)
    permissionState.value[key] = { view: false, edit: false, manage: false }
    item.actions.forEach((action) => {
      permissionState.value[key][action] = true
    })
    if (item.inherited_actions && item.inherited_actions.length) {
      inheritedState.value[key] = { view: false, edit: false, manage: false }
      item.inherited_actions.forEach((action) => {
        inheritedState.value[key][action] = true
      })
    }
  })
}

const loadSubjectPermissions = async () => {
  if (!selectedSubjectId.value) {
    applyPermissionSummary(null)
    permissionsLoading.value = false
    return
  }
  permissionsLoading.value = true
  permissionsError.value = ''
  try {
    const summary = await fetchSubjectPermissions({
      subject_type: subjectTab.value,
      subject_id: selectedSubjectId.value,
      scope: scopeTab.value,
    })
    applyPermissionSummary(summary)
  } catch (err) {
    permissionsError.value = err instanceof Error ? err.message : '加载失败'
    applyPermissionSummary(null)
  } finally {
    permissionsLoading.value = false
  }
}

const loadAgentGroups = async () => {
  groupsLoading.value = true
  groupsError.value = ''
  try {
    groups.value = await fetchAgentGroups()
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    groupsLoading.value = false
  }
}

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

const handleCreateGroup = async () => {
  groupLoading.value = true
  groupError.value = ''
  groupSuccess.value = ''
  try {
    await createAgentGroup(groupForm.value)
    groupSuccess.value = '分组已创建。'
    groupForm.value = { name: '', description: '' }
    await loadAgentGroups()
  } catch (err) {
    groupError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    groupLoading.value = false
  }
}

const handleDeleteGroup = async (group: AgentGroup) => {
  const confirmed = window.confirm(`确认删除分组「${group.name}」吗？`)
  if (!confirmed) return
  try {
    await deleteAgentGroup(group.id)
    await loadAgentGroups()
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '删除失败'
  }
}

const handleDeleteRole = async (role: Role) => {
  if (isProtectedRole(role.name)) {
    rolesError.value = '系统角色不可删除'
    return
  }
  const confirmed = window.confirm(`确认删除角色「${role.name}」吗？`)
  if (!confirmed) return
  try {
    await deleteRole(role.id)
    await loadRoles()
  } catch (err) {
    rolesError.value = err instanceof Error ? err.message : '删除失败'
  }
}

const loadResources = async () => {
  try {
    agents.value = await fetchAgents()
  } catch {
    agents.value = []
  }

  try {
    models.value = await fetchModels()
  } catch {
    models.value = []
  }
}

const ensureSubjectSelection = () => {
  if (subjectTab.value === 'user') {
    if (!users.value.length) {
      selectedSubjectId.value = ''
      return
    }
    const exists = users.value.some((user) => String(user.id) === selectedSubjectId.value)
    if (!exists) {
      selectedSubjectId.value = String(users.value[0].id)
    }
    return
  }

  if (!roles.value.length) {
    selectedSubjectId.value = ''
    return
  }
  const exists = roles.value.some((role) => role.name === selectedSubjectId.value)
  if (!exists) {
    selectedSubjectId.value = roles.value[0].name
  }
}

const ensureScopeSelection = () => {
  if (scopeTab.value === 'menu') {
    if (!menuScopeItems.some((item) => item.id === selectedScopeId.value)) {
      selectedScopeId.value = 'agents'
    }
    return
  }
  if (!resourceScopeItems.some((item) => item.id === selectedScopeId.value)) {
    selectedScopeId.value = 'agent'
  }
}

const getRowState = (row: PermissionRow) => {
  if (!permissionState.value[row.key]) {
    permissionState.value[row.key] = { view: false, edit: false, manage: false }
  }
  return permissionState.value[row.key]
}

const isRowChecked = (row: PermissionRow, action: PermissionAction) => {
  return permissionState.value[row.key]?.[action] ?? false
}

const toggleRowAction = (row: PermissionRow, action: PermissionAction, event: Event) => {
  if (isActionDisabled(row, action)) return
  const checked = (event.target as HTMLInputElement).checked
  const state = getRowState(row)
  state[action] = checked
}

const isActionDisabled = (row: PermissionRow, action: PermissionAction) => {
  if (!selectedSubjectId.value) return true
  if (permissionsLoading.value) return true
  if (subjectReadOnly.value) return true
  if (isAdminSubject.value) return true
  if (subjectTab.value === 'user' && inheritedState.value[row.key]?.[action]) return true
  return false
}

const handleSavePermissions = async () => {
  permissionError.value = ''
  permissionSuccess.value = ''

  const subjectId = selectedSubjectId.value
  if (!subjectId) {
    permissionError.value = '请选择用户或角色'
    return
  }
  if (subjectReadOnly.value || isAdminSubject.value) {
    permissionError.value = '当前对象权限不可编辑'
    return
  }

  permissionSaving.value = true
  try {
    const items: Array<{ resource_type: string; resource_id: string | null; actions: PermissionAction[] }> = []
    Object.entries(permissionState.value).forEach(([rowKey, actions]) => {
      const row = rowMetaMap.value.get(rowKey)
      if (!row) return
      const selected = (['view', 'edit', 'manage'] as PermissionAction[]).filter(
        (action) => actions[action]
      )
      if (!selected.length) return
      items.push({
        resource_type: row.resourceType,
        resource_id: row.resourceId,
        actions: selected,
      })
    })

    const summary = await updateSubjectPermissions({
      subject_type: subjectTab.value,
      subject_id: subjectId,
      scope: scopeTab.value,
      items,
    })
    applyPermissionSummary(summary)
    permissionSuccess.value = '权限已保存。'
  } catch (err) {
    permissionError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    permissionSaving.value = false
  }
}

const handleCreateUser = async () => {
  userLoading.value = true
  userError.value = ''
  userSuccess.value = ''

  try {
    await createUser(userForm.value)
    userSuccess.value = '用户已创建。'
    userForm.value = {
      account: '',
      username: '',
      email: '',
      password: '',
      role: 'user',
      status: 'active',
      source: 'local',
      workspace: 'default',
    }
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
    await updateUser(user.id, { role: user.role, status: user.status })
    userSuccess.value = `用户 ${user.username} 已更新。`
    await loadUsers()
    await loadSubjectPermissions()
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
    await loadSubjectPermissions()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

const handleImport = async () => {
  importLoading.value = true
  importError.value = ''
  importSuccess.value = ''

  try {
    const result = await importAgents(importForm.value)
    importSuccess.value = `成功导入 ${result.imported} 条智能体数据。`
    await loadAgentGroups()
  } catch (err) {
    importError.value = err instanceof Error ? err.message : '导入失败'
  } finally {
    importLoading.value = false
  }
}

const handleCreateModel = async () => {
  modelLoading.value = true
  modelError.value = ''
  modelSuccess.value = ''

  try {
    await createModel({
      id: modelForm.value.id,
      name: modelForm.value.name,
      provider: modelForm.value.provider,
      status: modelForm.value.status,
      context_length: modelForm.value.context_length,
      description: modelForm.value.description,
      pricing: modelForm.value.pricing,
      release: modelForm.value.release,
      tags: modelForm.value.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })

    modelSuccess.value = '模型已保存。'
    modelForm.value = {
      id: '',
      name: '',
      provider: '',
      status: 'enabled',
      context_length: 0,
      description: '',
      pricing: '',
      release: '',
      tags: '',
    }
  } catch (err) {
    modelError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    modelLoading.value = false
  }
}

const handleUseSampleImport = () => {
  importForm.value = { ...sampleImport }
}

const handleImportSample = async () => {
  importForm.value = { ...sampleImport }
  await handleImport()
}

const handleSeedModels = async () => {
  modelSeedLoading.value = true
  modelSeedSuccess.value = ''
  modelError.value = ''

  const samples = [
    {
      id: 'model-core',
      name: 'Core LLM',
      provider: 'OpenAI',
      status: 'enabled',
      context_length: 128000,
      description: '主力模型，用于通用任务。',
      pricing: '$0.00 demo',
      release: '2026-02',
      tags: ['multimodal', 'fast'],
    },
    {
      id: 'model-reason',
      name: 'Reasoning Pro',
      provider: 'OpenAI',
      status: 'enabled',
      context_length: 64000,
      description: '推理能力更强的模型。',
      pricing: '$0.00 demo',
      release: '2026-01',
      tags: ['analysis', 'accurate'],
    },
    {
      id: 'model-light',
      name: 'Fast Lite',
      provider: 'OpenAI',
      status: 'disabled',
      context_length: 32000,
      description: '低延迟模型，用于轻量任务。',
      pricing: '$0.00 demo',
      release: '2025-11',
      tags: ['cheap', 'fast'],
    },
  ]

  try {
    for (const sample of samples) {
      try {
        await createModel(sample)
      } catch (err) {
        const message = err instanceof Error ? err.message : ''
        if (!message.includes('already exists')) {
          throw err
        }
      }
    }
    modelSeedSuccess.value = '示例模型已填充。'
  } catch (err) {
    modelError.value = err instanceof Error ? err.message : '填充失败'
  } finally {
    modelSeedLoading.value = false
  }
}

onMounted(loadRoles)
onMounted(loadUsers)
onMounted(loadResources)
onMounted(loadAgentGroups)

watch(
  () => subjectTab.value,
  () => {
    subjectSearch.value = ''
    ensureSubjectSelection()
    loadSubjectPermissions()
  }
)

watch(
  () => scopeTab.value,
  () => {
    ensureScopeSelection()
    loadSubjectPermissions()
  }
)

watch([users, roles], () => {
  ensureSubjectSelection()
  loadSubjectPermissions()
})

watch([selectedSubjectId], () => {
  loadSubjectPermissions()
})

watch([agents, models, groups], () => {
  if (scopeTab.value === 'resource') {
    loadSubjectPermissions()
  }
})
</script>

<style scoped>
.admin {
  display: grid;
  gap: 28px;
}

.section {
  display: grid;
  gap: 16px;
}

.section-header h2 {
  font-family: 'Space Grotesk', sans-serif;
  margin: 0 0 6px;
  font-size: 24px;
}

.section-header p {
  margin: 0;
  color: #4b5b60;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.user-panel {
  display: grid;
  gap: 16px;
}

.user-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 40, 55, 0.1);
  background: #fff;
  min-width: 260px;
  flex: 1;
  max-width: 360px;
}

.filter-select {
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: #395057;
  padding: 2px 4px;
}

.search-box input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 14px;
}


.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.user-form-panel {
  padding: 14px;
  border-radius: 16px;
  background: rgba(15, 179, 185, 0.06);
  border: 1px dashed rgba(15, 179, 185, 0.2);
}

.table {
  display: grid;
  gap: 8px;
  overflow-x: auto;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 40px 120px 140px 120px 200px 120px 120px 180px 260px;
  align-items: center;
  gap: 10px;
  min-width: 1240px;
}

.table-head {
  padding: 10px 8px;
  font-size: 12px;
  color: #6b7b82;
  border-bottom: 1px solid rgba(15, 40, 55, 0.08);
}

.table-body {
  display: grid;
  gap: 6px;
}

.table-row {
  padding: 12px 8px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.table-row:hover {
  box-shadow: 0 10px 24px rgba(15, 40, 55, 0.08);
}

.col {
  font-size: 13px;
  color: #314046;
}

.col-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-control {
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.col-actions select {
  border: 1px solid #d6e0e2;
  border-radius: 10px;
  padding: 6px 8px;
  font-size: 12px;
  background: #fff;
  height: 34px;
}

.col-status select {
  border: 1px solid #d6e0e2;
  border-radius: 10px;
  padding: 6px 8px;
  font-size: 12px;
  background: #fff;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #0f6b4f;
  background: rgba(15, 107, 79, 0.12);
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.field-inline {
  align-items: center;
}

.field label {
  color: #5a6a70;
}

.field input,
.field select {
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 10px 12px;
  font-size: 14px;
}

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost {
  border: 1px solid rgba(15, 179, 185, 0.4);
  color: #0c7e85;
  background: transparent;
  padding: 10px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}

.ghost:hover {
  background: rgba(15, 179, 185, 0.08);
}

.ghost.action-control {
  padding: 0 14px;
  height: 34px;
}

.primary.action-control {
  padding: 0 14px;
  height: 34px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(8, 18, 22, 0.35);
  display: grid;
  place-items: center;
  z-index: 50;
}

.modal-card {
  width: min(420px, 92vw);
  background: #fff;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 18px 50px rgba(15, 40, 55, 0.18);
  display: grid;
  gap: 12px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-close {
  border: none;
  background: transparent;
  font-size: 16px;
  cursor: pointer;
  color: #6a7a80;
}

.modal-body {
  margin: 0;
  color: #4b5b60;
  font-size: 14px;
}

.modal-body code {
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  padding: 2px 6px;
  border-radius: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.state {
  font-size: 13px;
  color: #5a6a70;
  margin-top: 8px;
}

.state.error {
  color: #b13333;
}

.state.success {
  color: #0f6b4f;
}

.policy-list {
  display: grid;
  gap: 12px;
}

.policy-group {
  display: grid;
  gap: 10px;
}

.policy-group > h3 {
  margin: 8px 0 0;
  font-size: 14px;
  color: #4b5b60;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.policy-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 14px;
  border: 1px solid rgba(15, 40, 55, 0.06);
  display: grid;
  gap: 8px;
}

.policy-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.policy-card p {
  margin: 0;
  color: #6a7a80;
  font-size: 12px;
}

.policy-meta {
  font-size: 12px;
  color: #5a6a70;
  display: grid;
  gap: 4px;
}

.policy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ghost.danger {
  border-color: rgba(255, 94, 94, 0.5);
  color: #b13333;
}

.permission-board {
  display: grid;
  gap: 16px;
}

.permission-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.tab-group {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(15, 179, 185, 0.12);
}

.tab {
  border: none;
  background: transparent;
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  color: #4b5b60;
}

.tab.active {
  background: #fff;
  color: #0c7e85;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(15, 40, 55, 0.12);
}

.permission-body {
  display: grid;
  grid-template-columns: minmax(180px, 230px) minmax(180px, 240px) minmax(320px, 1fr);
  gap: 12px;
  min-height: 360px;
}

.permission-column {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 16px;
  border: 1px solid rgba(15, 40, 55, 0.06);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.table-column {
  background: transparent;
  border: none;
  padding: 0;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: #3a4a4f;
}

.search-box.compact {
  min-width: 0;
  max-width: none;
  padding: 8px 12px;
}

.list {
  display: grid;
  gap: 8px;
  overflow-y: auto;
  padding-right: 4px;
}

.list-item {
  text-align: left;
  border: 1px solid transparent;
  background: #fff;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  display: grid;
  gap: 4px;
  box-shadow: 0 6px 14px rgba(15, 40, 55, 0.08);
}

.list-item strong {
  font-size: 13px;
  color: #2e3c41;
}

.list-item small {
  font-size: 11px;
  color: #6a7a80;
}

.list-item.active {
  background: rgba(15, 179, 185, 0.16);
  border-color: rgba(15, 179, 185, 0.45);
}

.role-form {
  display: grid;
  gap: 10px;
}

.role-actions {
  display: flex;
  justify-content: flex-end;
}

.compact-form {
  grid-template-columns: 1fr;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.table-toolbar input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 10px 12px;
  font-size: 14px;
}

.permission-grid .table-head,
.permission-grid .table-row {
  grid-template-columns: 1fr repeat(3, 80px);
  min-width: 520px;
}

.permission-row .col-action {
  display: flex;
  align-items: center;
  justify-content: center;
}

.permission-row input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.row-title {
  font-weight: 600;
  color: #2f3f44;
}

.permission-row small {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #6a7a80;
}

@media (max-width: 1100px) {
  .permission-body {
    grid-template-columns: 1fr;
  }
}
</style>
