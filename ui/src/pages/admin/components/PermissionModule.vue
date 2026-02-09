<template>
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
          <button class="tab" :class="{ active: subjectTab === 'user' }" type="button" @click="subjectTab = 'user'">
            用户
          </button>
          <button class="tab" :class="{ active: subjectTab === 'role' }" type="button" @click="subjectTab = 'role'">
            角色
          </button>
        </div>
        <div class="tab-group">
          <button class="tab" :class="{ active: scopeTab === 'menu' }" type="button" @click="scopeTab = 'menu'">
            菜单权限
          </button>
          <button class="tab" :class="{ active: scopeTab === 'resource' }" type="button" @click="scopeTab = 'resource'">
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
              class="list-item subject-item"
              :class="{ active: selectedSubjectId === String(user.id) }"
              type="button"
              @click="selectedSubjectId = String(user.id)"
            >
              <div class="subject-line">
                <strong>{{ user.username }}</strong>
                <span class="subject-account">{{ user.account }}</span>
              </div>
            </button>
          </div>
          <div v-else class="list">
            <button
              v-for="role in filteredSubjects"
              :key="role.id"
              class="list-item role-item"
              :class="{ active: selectedSubjectId === role.name }"
              type="button"
              @click="selectedSubjectId = role.name"
            >
              <strong>{{ role.name }}</strong>
              <small>{{ role.description || '暂无描述' }}</small>
            </button>
          </div>
        </aside>

        <aside class="permission-column scope-column">
          <div class="column-title">{{ scopeTab === 'menu' ? '菜单权限' : '资源分类' }}</div>
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
                <small v-if="item.subLabel">{{ item.subLabel }}</small>
              </button>
          </div>
        </aside>

        <section class="permission-column table-column">
          <div class="table-toolbar">
            <input v-model="tableSearch" type="text" placeholder="搜索名称" />
          </div>

          <div v-if="permissionsLoading" class="state">加载授权中...</div>
          <div v-else-if="permissionsError" class="state error">{{ permissionsError }}</div>

          <div v-else class="permission-table-wrap">
            <table class="permission-table">
              <colgroup>
                <col class="col-resource" />
                <col class="col-perm" />
                <col class="col-perm" />
                <col class="col-perm" />
              </colgroup>
              <thead>
                <tr class="permission-row">
                  <th class="col-name">资源名称</th>
                  <th class="col-action">
                    <label class="action-all">
                      <input
                        type="checkbox"
                        :checked="isActionAllChecked('view')"
                        :disabled="!canToggleActionAll('view')"
                        @change="toggleActionAll('view', $event)"
                      />
                      <span>查看</span>
                    </label>
                  </th>
                  <th class="col-action">
                    <label class="action-all">
                      <input
                        type="checkbox"
                        :checked="isActionAllChecked('edit')"
                        :disabled="!canToggleActionAll('edit')"
                        @change="toggleActionAll('edit', $event)"
                      />
                      <span>编辑</span>
                    </label>
                  </th>
                  <th class="col-action">
                    <label class="action-all">
                      <input
                        type="checkbox"
                        :checked="isActionAllChecked('manage')"
                        :disabled="!canToggleActionAll('manage')"
                        @change="toggleActionAll('manage', $event)"
                      />
                      <span>管理</span>
                    </label>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in filteredRows" :key="row.key" class="permission-row">
                  <td class="col-name">
                    <span class="row-title">{{ row.label }}</span>
                    <small v-if="row.subLabel">{{ row.subLabel }}</small>
                  </td>
                  <td class="col-action">
                    <label class="action-cell">
                      <input
                        type="checkbox"
                        :disabled="isActionDisabled(row, 'view')"
                        :checked="isRowChecked(row, 'view')"
                        @change="toggleRowAction(row, 'view', $event)"
                      />
                      <span>查看</span>
                    </label>
                  </td>
                  <td class="col-action">
                    <label class="action-cell">
                      <input
                        type="checkbox"
                        :disabled="isActionDisabled(row, 'edit')"
                        :checked="isRowChecked(row, 'edit')"
                        @change="toggleRowAction(row, 'edit', $event)"
                      />
                      <span>编辑</span>
                    </label>
                  </td>
                  <td class="col-action">
                    <label class="action-cell">
                      <input
                        type="checkbox"
                        :disabled="isActionDisabled(row, 'manage')"
                        :checked="isRowChecked(row, 'manage')"
                        @change="toggleRowAction(row, 'manage', $event)"
                      />
                      <span>管理</span>
                    </label>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!filteredRows.length" class="empty-placeholder"></div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { fetchAgents, type AgentSummary } from '../../../services/agents'
import { fetchModels, type ModelSummary } from '../../../services/models'
import {
  fetchAgentGroups,
  fetchRoles,
  fetchSubjectPermissions,
  fetchUsers,
  updateSubjectPermissions,
  type AdminUser,
  type AgentGroup,
  type PermissionSubjectMatrixItem,
  type Role,
} from '../../../services/admin'

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

const permissionSaving = ref(false)
const permissionError = ref('')
const permissionSuccess = ref('')

const subjectTab = ref<'user' | 'role'>('user')
const scopeTab = ref<'menu' | 'resource'>('menu')
const subjectSearch = ref('')
const tableSearch = ref('')
const selectedSubjectId = ref('')
const selectedScopeId = ref('agents')
const permissionState = ref<Record<string, PermissionActionState>>({})

const buildRowKey = (scope: string, resourceType: string, resourceId: string | null) =>
  `${scope}::${resourceType}::${resourceId ?? '*'}`

const menuScopeItems: ScopeItem[] = [
  { id: 'all', label: '全部菜单', subLabel: '' },
  { id: 'agents', label: '智能体', subLabel: '' },
  { id: 'models', label: '模型', subLabel: '' },
  { id: 'admin', label: '系统管理', subLabel: '' },
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

const agentGroups = computed(() => groups.value.map((group) => group.name).filter(Boolean))

const allResourceRows = computed<PermissionRow[]>(() => {
  const rows: PermissionRow[] = []
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
  allRows.value.forEach((row) => map.set(row.key, row))
  return map
})

const tableRows = computed(() => {
  if (scopeTab.value === 'menu') {
    if (selectedScopeId.value === 'all') return allMenuRows.value
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

const isAdminSubject = computed(() => subjectTab.value === 'role' && selectedSubjectId.value === 'admin')

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

const loadResources = async () => {
  const [agentsResult, modelsResult] = await Promise.allSettled([
    fetchAgents({ includeDescription: false }),
    fetchModels(),
  ])
  agents.value = agentsResult.status === 'fulfilled' ? agentsResult.value : []
  models.value = modelsResult.status === 'fulfilled' ? modelsResult.value : []
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

let permissionLoadQueued = false
const scheduleLoadSubjectPermissions = () => {
  if (permissionLoadQueued) return
  permissionLoadQueued = true
  Promise.resolve().then(() => {
    permissionLoadQueued = false
    void loadSubjectPermissions()
  })
}

const ensureSubjectSelection = () => {
  if (subjectTab.value === 'user') {
    if (!users.value.length) {
      selectedSubjectId.value = ''
      return
    }
    const exists = users.value.some((user) => String(user.id) === selectedSubjectId.value)
    if (!exists) selectedSubjectId.value = String(users.value[0].id)
    return
  }

  if (!roles.value.length) {
    selectedSubjectId.value = ''
    return
  }
  const exists = roles.value.some((role) => role.name === selectedSubjectId.value)
  if (!exists) selectedSubjectId.value = roles.value[0].name
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

const isRowChecked = (row: PermissionRow, action: PermissionAction) =>
  permissionState.value[row.key]?.[action] ?? false

const setActionValue = (row: PermissionRow, action: PermissionAction, value: boolean) => {
  if (isActionDisabled(row, action)) return
  const state = getRowState(row)
  state[action] = value
}

const setRowActionWithHierarchy = (row: PermissionRow, action: PermissionAction, checked: boolean) => {
  if (checked) {
    if (action === 'view') {
      setActionValue(row, 'view', true)
      return
    }
    if (action === 'edit') {
      setActionValue(row, 'edit', true)
      setActionValue(row, 'view', true)
      return
    }
    setActionValue(row, 'manage', true)
    setActionValue(row, 'edit', true)
    setActionValue(row, 'view', true)
    return
  }

  if (action === 'view') {
    setActionValue(row, 'view', false)
    setActionValue(row, 'edit', false)
    setActionValue(row, 'manage', false)
    return
  }
  if (action === 'edit') {
    setActionValue(row, 'edit', false)
    setActionValue(row, 'manage', false)
    return
  }
  setActionValue(row, 'manage', false)
}

const toggleRowAction = (row: PermissionRow, action: PermissionAction, event: Event) => {
  if (isActionDisabled(row, action)) return
  const checked = (event.target as HTMLInputElement).checked
  setRowActionWithHierarchy(row, action, checked)
}

const isActionDisabled = (row: PermissionRow, action: PermissionAction) => {
  if (!selectedSubjectId.value) return true
  if (permissionsLoading.value) return true
  if (subjectReadOnly.value) return true
  if (isAdminSubject.value) return true
  if (subjectTab.value === 'user' && inheritedState.value[row.key]?.[action]) return true
  return false
}

const canToggleActionAll = (action: PermissionAction) =>
  filteredRows.value.some((row) => !isActionDisabled(row, action))

const isActionAllChecked = (action: PermissionAction) => {
  if (!filteredRows.value.length) return false
  const editableRows = filteredRows.value.filter((row) => !isActionDisabled(row, action))
  if (!editableRows.length) return false
  return editableRows.every((row) => isRowChecked(row, action))
}

const toggleActionAll = (action: PermissionAction, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  filteredRows.value.forEach((row) => {
    setRowActionWithHierarchy(row, action, checked)
  })
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
      const selected = (['view', 'edit', 'manage'] as PermissionAction[]).filter((action) => actions[action])
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

onMounted(async () => {
  await Promise.all([loadUsers(), loadRoles(), loadResources(), loadAgentGroups()])
  ensureSubjectSelection()
  ensureScopeSelection()
  scheduleLoadSubjectPermissions()
})

watch(
  () => subjectTab.value,
  () => {
    subjectSearch.value = ''
    ensureSubjectSelection()
    scheduleLoadSubjectPermissions()
  }
)

watch(
  () => scopeTab.value,
  () => {
    ensureScopeSelection()
    scheduleLoadSubjectPermissions()
  }
)

watch([users, roles], () => {
  ensureSubjectSelection()
  scheduleLoadSubjectPermissions()
})

watch([selectedSubjectId], () => {
  scheduleLoadSubjectPermissions()
})

watch([agents, models, groups], () => {
  if (scopeTab.value === 'resource') {
    scheduleLoadSubjectPermissions()
  }
})
</script>

<style scoped>
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
  border: 1px solid rgba(15, 40, 55, 0.18);
}

.permission-board {
  display: grid;
  gap: 16px;
  grid-template-rows: auto;
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

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.primary:disabled {
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

.permission-body {
  display: grid;
  grid-template-columns: 180px 180px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.permission-column {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 16px;
  border: 1px solid rgba(15, 40, 55, 0.16);
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
  overflow: visible;
  min-width: 0;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: #3a4a4f;
}

.search-box.compact {
  min-width: 0;
  max-width: none;
  padding: 0 10px;
  height: 34px;
  align-items: center;
  flex: 0 0 auto;
  box-sizing: border-box;
  border: 1px solid rgba(15, 40, 55, 0.16);
  box-shadow: none;
  background: #fff;
  margin-bottom: 6px;
  border-radius: 12px;
}

.search-box.compact input {
  height: 100%;
  background: transparent;
  border: none;
  outline: none;
  width: 100%;
}

.list {
  display: grid;
  gap: 8px;
  overflow-y: auto;
  padding-right: 4px;
  flex: 1;
  min-height: 0;
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
  height: 60px;
}

.list-item.subject-item,
.list-item.role-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subject-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.subject-account {
  font-size: 11px;
  color: #6a7a80;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.table-toolbar input {
  width: min(100%, 380px);
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 0 12px;
  font-size: 14px;
  height: 34px;
}

.action-all {
  display: grid;
  grid-template-columns: 12px auto;
  align-items: center;
  justify-content: flex-start;
  column-gap: 6px;
  font-size: 12px;
  color: #6b7b82;
  user-select: none;
  width: 100%;
}

.action-all input {
  width: 12px;
  height: 12px;
  accent-color: #0fb3b9;
}

.action-cell {
  display: grid;
  grid-template-columns: 12px auto;
  align-items: center;
  justify-content: flex-start;
  column-gap: 6px;
  font-size: 12px;
  color: #6b7b82;
  user-select: none;
  width: 100%;
}

.permission-table-wrap {
  width: 100%;
}

.permission-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0 6px;
}

.permission-table col.col-resource {
  width: auto;
}

.permission-table col.col-perm {
  width: 110px;
}

.permission-table thead th {
  font-size: 12px;
  color: #6b7b82;
  font-weight: 600;
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid rgba(15, 40, 55, 0.08);
}

.permission-table tbody td {
  padding: 12px 8px;
  background: #fff;
  border-top: 1px solid rgba(15, 40, 55, 0.06);
  border-bottom: 1px solid rgba(15, 40, 55, 0.06);
}

.permission-table tbody td:first-child {
  border-left: 1px solid rgba(15, 40, 55, 0.06);
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}

.permission-table tbody td:last-child {
  border-right: 1px solid rgba(15, 40, 55, 0.06);
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
}

.permission-table .col-action {
  text-align: left;
}

.permission-row input[type='checkbox'] {
  width: 12px;
  height: 12px;
  accent-color: #0fb3b9;
  margin: 0;
  vertical-align: middle;
}

.empty-placeholder {
  min-height: 24px;
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

@media (max-width: 1400px) {
  .permission-body {
    grid-template-columns: 160px 160px minmax(0, 1fr);
  }
}

@media (max-width: 1100px) {
  .permission-body {
    grid-template-columns: 1fr;
  }
}
</style>
