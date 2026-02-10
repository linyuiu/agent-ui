<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体同步</h2>
        <p>新增智能体、维护分组并执行同步接入。</p>
      </div>
    </div>

    <div class="panel">
      <div class="section-header">
        <div>
          <h3>智能体管理</h3>
          <p>新增、删除智能体，并维护分组。</p>
        </div>
      </div>

      <div class="sub-panel">
        <div class="sub-header">
          <h4>新增智能体</h4>
          <p>仅管理员可管理智能体，其他角色需授权。</p>
        </div>
        <form class="form agent-form" @submit.prevent="handleCreateAgentAdmin">
          <div class="field">
            <label>名称</label>
            <input v-model="agentForm.name" type="text" placeholder="Agent Name" required />
          </div>
          <div class="field">
            <label>URL</label>
            <input
              v-model="agentForm.url"
              type="text"
              placeholder="https://example.com/chat/your-token"
              required
            />
          </div>
          <div class="field">
            <label>负责人</label>
            <input v-model="agentForm.owner" type="text" placeholder="system" />
          </div>
          <div class="field">
            <label>状态</label>
            <div class="inline-dropdown" @click.stop>
              <button
                class="filter-trigger inline-trigger"
                type="button"
                @click.stop="toggleAgentStatusDropdown"
              >
                <span>{{ agentForm.status }}</span>
                <span class="caret" :class="{ open: agentStatusOpen }"></span>
              </button>
              <div v-if="agentStatusOpen" class="filter-dropdown inline-dropdown-panel">
                <button class="filter-option" type="button" @click="setAgentStatus('active')">
                  active
                </button>
                <button class="filter-option" type="button" @click="setAgentStatus('paused')">
                  paused
                </button>
              </div>
            </div>
          </div>
          <div class="field">
            <label>描述</label>
            <input v-model="agentForm.description" type="text" placeholder="简短说明" />
          </div>
          <div class="field">
            <label>分组</label>
            <div ref="agentGroupDropdownRef" class="combo-wrap">
              <div class="combo-input" @click="focusAgentGroupInput">
                <template v-for="group in agentForm.groups" :key="group">
                  <span class="chip">
                    {{ group }}
                    <button class="chip-remove" type="button" @click.stop="removeAgentGroup(group)">
                      ×
                    </button>
                  </span>
                </template>
                <input
                  ref="agentGroupInputRef"
                  v-model="agentGroupQuery"
                  type="text"
                  :placeholder="agentForm.groups.length ? '' : '输入或选择分组'"
                  @focus="openAgentGroupDropdown"
                  @keydown.enter.prevent="handleAgentGroupEnter"
                />
                <span v-if="agentForm.groups.length" class="combo-more">...</span>
                <span class="combo-caret" :class="{ open: agentGroupDropdownOpen }"></span>
              </div>
              <div v-if="agentGroupDropdownOpen" class="dropdown" @click.stop>
                <button
                  v-for="group in filteredAgentGroups"
                  :key="group"
                  class="dropdown-item"
                  type="button"
                  @click="selectAgentGroup(group)"
                >
                  <span>{{ group }}</span>
                  <span class="dropdown-check">
                    <input type="checkbox" :checked="agentForm.groups.includes(group)" disabled />
                  </span>
                </button>
                <p v-if="!filteredAgentGroups.length" class="dropdown-empty">
                  {{ agentGroupQuery.trim() ? '按回车创建新分组' : '暂无可用分组' }}
                </p>
              </div>
            </div>
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="agentCreateLoading || !isAdmin">
              {{ agentCreateLoading ? '保存中...' : '新增智能体' }}
            </button>
          </div>
        </form>

        <p v-if="!isAdmin" class="state">仅管理员可新增或删除智能体。</p>
        <p v-if="agentCreateError" class="state error">{{ agentCreateError }}</p>
        <p v-if="agentCreateSuccess" class="state success">{{ agentCreateSuccess }}</p>
        <p v-if="agentDeleteError" class="state error">{{ agentDeleteError }}</p>

        <div v-if="agents.length" class="grid">
          <div
            v-for="agent in agents"
            :key="agent.id"
            v-memo="[agent.id, agent.name, agent.url, agent.editable]"
            class="policy-card"
          >
            <div>
              <h3>{{ agent.name }}</h3>
            </div>
            <div class="policy-actions">
              <button
                class="ghost danger"
                type="button"
                :disabled="agentDeleteLoading || !isAdmin"
                @click="openDeleteAgent(agent)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="sub-panel">
        <div class="sub-header">
          <h4>分组管理</h4>
          <p>创建与维护可用于授权的分组。</p>
        </div>
        <form class="form group-create-form" @submit.prevent="handleCreateGroup">
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
          <div
            v-for="group in groups"
            :key="group.id"
            v-memo="[group.id, group.name, group.description]"
            class="policy-card"
          >
            <div>
              <h3>{{ group.name }}</h3>
              <p>{{ group.description || '暂无描述' }}</p>
            </div>
            <div class="policy-actions">
              <button class="ghost danger" type="button" @click="openDeleteGroup(group)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体接入</h2>
        <p>填写 API 域名与 Token，添加后可选择工作空间并同步智能体。</p>
      </div>
    </div>

    <div class="panel">
      <form class="form api-config-form" @submit.prevent="handleSaveApiConfig">
        <div class="field">
          <label>API 域名</label>
          <input v-model="fitSyncForm.base_url" type="text" placeholder="https://mk-ee.fit2cloud.cn" />
        </div>
        <div class="field">
          <label>Token</label>
          <input v-model="fitSyncForm.token" type="password" placeholder="Bearer token" />
        </div>
        <div class="button-row">
          <button class="primary" type="submit" :disabled="apiConfigLoading || !isAdmin">
            {{ apiConfigLoading ? '添加中...' : '添加' }}
          </button>
        </div>
      </form>

      <p v-if="!isAdmin" class="state">仅管理员可执行同步。</p>
      <p v-if="apiConfigError" class="state error">{{ apiConfigError }}</p>
      <p v-if="apiConfigSuccess" class="state success">{{ apiConfigSuccess }}</p>
      <p v-if="apiSyncError" class="state error">{{ apiSyncError }}</p>
      <p v-if="apiSyncSuccess" class="state success">{{ apiSyncSuccess }}</p>

      <div v-if="apiConfigs.length" class="grid">
        <div v-for="config in apiConfigs" :key="config.id" class="policy-card api-config-card">
          <div v-if="editingApiConfigId === config.id" class="form api-config-card-form">
            <div class="field">
              <label>API 域名</label>
              <input
                v-model="apiConfigEditForm.base_url"
                type="text"
                placeholder="https://mk-ee.fit2cloud.cn"
              />
            </div>
            <div class="field">
              <label>Token（留空则不修改）</label>
              <input v-model="apiConfigEditForm.token" type="password" placeholder="Bearer token" />
            </div>
          </div>
          <div v-else>
            <h3>{{ config.base_url }}</h3>
            <p>Token：{{ config.token_hint }}</p>
          </div>
          <div class="policy-actions">
            <template v-if="editingApiConfigId === config.id">
              <button
                class="ghost"
                type="button"
                :disabled="apiConfigEditLoading || !isAdmin"
                @click="saveInlineApiConfigEdit(config.id)"
              >
                {{ apiConfigEditLoading ? '保存中...' : '保存修改' }}
              </button>
              <button class="ghost" type="button" :disabled="apiConfigEditLoading" @click="cancelInlineApiConfigEdit">
                取消
              </button>
            </template>
            <template v-else>
              <button class="ghost" type="button" @click="startInlineApiConfigEdit(config)">编辑</button>
              <button class="ghost" type="button" :disabled="!isAdmin" @click="openApiSyncModal(config)">
                同步
              </button>
              <button class="ghost danger" type="button" @click="openDeleteApiConfig(config)">
                删除
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="showGroupDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除分组</h3>
        <button class="modal-close" type="button" @click="closeGroupDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ groupDeleteTarget?.name }}</strong> 吗？该分组关联的权限数据将一并删除。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeGroupDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="groupDeleting" @click="confirmDeleteGroup">
          {{ groupDeleting ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="showApiDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除 API 配置</h3>
        <button class="modal-close" type="button" @click="closeApiDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ apiDeleteTarget?.base_url }}</strong> 吗？
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeApiDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="apiConfigLoading" @click="confirmDeleteApiConfig">
          {{ apiConfigLoading ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="showApiSyncModal" class="modal-backdrop">
    <div class="modal-card modal-large">
      <div class="modal-header">
        <h3>同步智能体</h3>
        <button class="modal-close" type="button" @click="closeApiSyncModal">✕</button>
      </div>
      <div class="modal-body">
        <div class="sync-grid">
          <div class="sync-panel">
            <div class="sync-panel-header">
              <span class="column-title">工作空间</span>
            </div>
            <div v-if="syncWorkspaceLoading" class="state">加载工作空间中...</div>
            <div v-else-if="syncWorkspaceError" class="state error">{{ syncWorkspaceError }}</div>
            <div v-else class="list">
              <button
                v-for="workspace in syncWorkspaces"
                :key="workspace.id"
                class="list-item"
                :class="{ active: selectedWorkspaceId === workspace.id }"
                type="button"
                @click="selectWorkspace(workspace)"
              >
                <strong>{{ workspace.name }}</strong>
                <small>{{ workspace.id }}</small>
              </button>
              <div v-if="!syncWorkspaces.length" class="state">暂无工作空间</div>
            </div>
          </div>
          <div class="sync-panel">
            <div class="sync-panel-header">
              <span class="column-title">智能体</span>
              <label class="checkbox-line">
                <input
                  type="checkbox"
                  :checked="allAppsSelected"
                  :disabled="!syncApps.length"
                  @change="toggleSelectAllApps"
                />
                <span>全选</span>
              </label>
            </div>
            <div v-if="syncAppsLoading" class="state">加载智能体中...</div>
            <div v-else-if="syncAppsError" class="state error">{{ syncAppsError }}</div>
            <div v-else class="list">
              <label v-for="app in syncApps" :key="app.id" class="list-item checkbox-item">
                <input
                  type="checkbox"
                  :checked="selectedAppIds.includes(app.id)"
                  @change="toggleAppSelection(app.id)"
                />
                <div class="checkbox-text">
                  <strong>{{ app.name }}</strong>
                  <small>{{ app.id }}</small>
                </div>
              </label>
              <div v-if="selectedWorkspaceId && !syncApps.length" class="state">暂无智能体</div>
              <div v-else-if="!selectedWorkspaceId" class="state">请先选择工作空间</div>
            </div>
          </div>
        </div>
        <p v-if="apiSyncError" class="state error">{{ apiSyncError }}</p>
      </div>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeApiSyncModal">取消</button>
        <button
          class="primary"
          type="button"
          :disabled="apiSyncLoading || !selectedWorkspaceId || !selectedAppIds.length"
          @click="confirmApiSync"
        >
          {{ apiSyncLoading ? '同步中...' : '确认同步' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="showAgentDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除智能体</h3>
        <button class="modal-close" type="button" @click="closeAgentDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ agentDeleteTarget?.name }}</strong> 吗？该智能体的权限数据将一并删除。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeAgentDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="agentDeleteLoading" @click="confirmDeleteAgent">
          {{ agentDeleteLoading ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useCreatableGroupSelector } from '../../../composables/use-creatable-group-selector'
import { useDocumentClick } from '../../../composables/use-document-click'
import { createAgent, deleteAgent, fetchAgents, type AgentSummary } from '../../../services/agents'
import {
  createAgentApiConfig,
  createAgentGroup,
  deleteAgentApiConfig,
  deleteAgentGroup,
  fetchAgentApiConfigs,
  fetchAgentGroups,
  fetchFit2CloudApplications,
  fetchFit2CloudWorkspaces,
  syncFit2CloudByConfig,
  updateAgentApiConfig,
  type AgentApiConfig,
  type AgentApiConfigUpdate,
  type AgentGroup,
  type Fit2CloudApplication,
  type Fit2CloudWorkspace,
} from '../../../services/admin'

const roleLocal = ref(localStorage.getItem('user_role') || '')
const isAdmin = computed(() => roleLocal.value === 'admin')

const agents = ref<AgentSummary[]>([])
const groups = ref<AgentGroup[]>([])
const apiConfigs = ref<AgentApiConfig[]>([])

const groupsLoading = ref(false)
const groupsError = ref('')

const groupLoading = ref(false)
const groupError = ref('')
const groupSuccess = ref('')
const groupForm = ref({
  name: '',
  description: '',
})

const showGroupDeleteModal = ref(false)
const groupDeleteTarget = ref<AgentGroup | null>(null)
const groupDeleting = ref(false)

const agentCreateLoading = ref(false)
const agentCreateError = ref('')
const agentCreateSuccess = ref('')
const agentDeleteError = ref('')
const agentDeleteLoading = ref(false)

const showAgentDeleteModal = ref(false)
const agentDeleteTarget = ref<AgentSummary | null>(null)

const agentStatusOpen = ref(false)
const agentGroupQuery = ref('')
const agentGroupCreateLoading = ref(false)
const agentGroupDropdownOpen = ref(false)
const agentGroupDropdownRef = ref<HTMLElement | null>(null)
const agentGroupInputRef = ref<HTMLInputElement | null>(null)
const agentGroupOptions = ref<string[]>([])

const agentForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  description: '',
  groups: [] as string[],
})

const apiConfigLoading = ref(false)
const apiConfigEditLoading = ref(false)
const apiConfigError = ref('')
const apiConfigSuccess = ref('')
const apiSyncLoading = ref(false)
const apiSyncError = ref('')
const apiSyncSuccess = ref('')

const showApiDeleteModal = ref(false)
const apiDeleteTarget = ref<AgentApiConfig | null>(null)

const editingApiConfigId = ref<number | null>(null)
const apiConfigEditForm = ref({
  base_url: '',
  token: '',
})

const fitSyncForm = ref({
  base_url: '',
  token: '',
})

const showApiSyncModal = ref(false)
const apiSyncTarget = ref<AgentApiConfig | null>(null)
const syncWorkspaces = ref<Fit2CloudWorkspace[]>([])
const syncApps = ref<Fit2CloudApplication[]>([])
const syncWorkspaceLoading = ref(false)
const syncAppsLoading = ref(false)
const syncWorkspaceError = ref('')
const syncAppsError = ref('')
const selectedWorkspaceId = ref('')
const selectedWorkspaceName = ref('')
const selectedAppIds = ref<string[]>([])

const selectedAgentGroups = computed({
  get: () => agentForm.value.groups,
  set: (next: string[]) => {
    agentForm.value.groups = next
  },
})

const {
  filteredGroups: filteredAgentGroups,
  selectGroup: selectAgentGroup,
  removeGroup: removeAgentGroup,
  createOrSelectFromQuery: createOrSelectAgentGroupFromQuery,
} = useCreatableGroupSelector({
  groupOptions: agentGroupOptions,
  selectedGroups: selectedAgentGroups,
  query: agentGroupQuery,
  creating: agentGroupCreateLoading,
  error: agentCreateError,
  createGroup: ({ name }) => createAgentGroup({ name }),
})

const allAppsSelected = computed(
  () => syncApps.value.length > 0 && selectedAppIds.value.length === syncApps.value.length
)

const loadAgents = async () => {
  try {
    agents.value = await fetchAgents({ includeDescription: false })
  } catch {
    agents.value = []
  }
}

const loadAgentGroups = async () => {
  groupsLoading.value = true
  groupsError.value = ''
  try {
    groups.value = await fetchAgentGroups()
    agentGroupOptions.value = groups.value.map((group) => group.name)
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '加载失败'
    agentGroupOptions.value = []
  } finally {
    groupsLoading.value = false
  }
}

const loadApiConfigs = async () => {
  apiConfigError.value = ''
  try {
    apiConfigs.value = await fetchAgentApiConfigs()
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '加载失败'
    apiConfigs.value = []
  }
}

const upsertApiConfig = (config: AgentApiConfig) => {
  const next = [...apiConfigs.value]
  const index = next.findIndex((item) => item.id === config.id)
  if (index >= 0) {
    next[index] = config
  } else {
    next.unshift(config)
  }
  next.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  apiConfigs.value = next
}

const toggleAgentStatusDropdown = () => {
  agentStatusOpen.value = !agentStatusOpen.value
}

const setAgentStatus = (value: 'active' | 'paused') => {
  agentForm.value.status = value
  agentStatusOpen.value = false
}

const openAgentGroupDropdown = () => {
  agentGroupDropdownOpen.value = true
}

const closeAgentGroupDropdown = () => {
  agentGroupDropdownOpen.value = false
}

const focusAgentGroupInput = () => {
  agentGroupInputRef.value?.focus()
  openAgentGroupDropdown()
}

const handleAgentGroupEnter = async () => {
  if (agentGroupCreateLoading.value) return
  const name = agentGroupQuery.value.trim()
  if (!name) return
  const exists = agentGroupOptions.value.includes(name)
  const selected = await createOrSelectAgentGroupFromQuery()
  if (!selected) return
  if (!exists) {
    await loadAgentGroups()
  }
  closeAgentGroupDropdown()
}

const handleCreateAgentAdmin = async () => {
  if (!isAdmin.value) {
    agentCreateError.value = '仅管理员可新增智能体。'
    return
  }
  agentCreateLoading.value = true
  agentCreateError.value = ''
  agentCreateSuccess.value = ''
  try {
    await createAgent({
      name: agentForm.value.name,
      url: agentForm.value.url,
      owner: agentForm.value.owner || 'system',
      status: agentForm.value.status,
      last_run: '',
      description: agentForm.value.description,
      groups: agentForm.value.groups,
    })
    agentCreateSuccess.value = '智能体已新增。'
    agentForm.value = {
      name: '',
      url: '',
      owner: '',
      status: 'active',
      description: '',
      groups: [],
    }
    agentGroupQuery.value = ''
    await Promise.all([loadAgents(), loadAgentGroups()])
  } catch (err) {
    agentCreateError.value = err instanceof Error ? err.message : '新增失败'
  } finally {
    agentCreateLoading.value = false
  }
}

const openDeleteAgent = (agent: AgentSummary) => {
  agentDeleteTarget.value = agent
  showAgentDeleteModal.value = true
}

const closeAgentDeleteModal = () => {
  showAgentDeleteModal.value = false
  agentDeleteTarget.value = null
}

const handleDeleteAgentAdmin = async (agent: AgentSummary) => {
  if (!isAdmin.value) {
    agentDeleteError.value = '仅管理员可删除智能体。'
    return
  }
  agentDeleteLoading.value = true
  agentDeleteError.value = ''
  try {
    await deleteAgent(agent.id)
    await loadAgents()
  } catch (err) {
    agentDeleteError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    agentDeleteLoading.value = false
  }
}

const confirmDeleteAgent = async () => {
  if (!agentDeleteTarget.value) return
  await handleDeleteAgentAdmin(agentDeleteTarget.value)
  closeAgentDeleteModal()
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

const openDeleteGroup = (group: AgentGroup) => {
  groupDeleteTarget.value = group
  showGroupDeleteModal.value = true
}

const closeGroupDeleteModal = () => {
  showGroupDeleteModal.value = false
  groupDeleteTarget.value = null
}

const confirmDeleteGroup = async () => {
  if (!groupDeleteTarget.value) return
  groupDeleting.value = true
  groupsError.value = ''
  try {
    await deleteAgentGroup(groupDeleteTarget.value.id)
    closeGroupDeleteModal()
    await loadAgentGroups()
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    groupDeleting.value = false
  }
}

const startInlineApiConfigEdit = (config: AgentApiConfig) => {
  editingApiConfigId.value = config.id
  apiConfigEditForm.value = {
    base_url: config.base_url,
    token: '',
  }
  apiConfigError.value = ''
  apiConfigSuccess.value = ''
}

const cancelInlineApiConfigEdit = () => {
  editingApiConfigId.value = null
  apiConfigEditForm.value = {
    base_url: '',
    token: '',
  }
}

const saveInlineApiConfigEdit = async (configId: number) => {
  apiConfigError.value = ''
  apiConfigSuccess.value = ''
  if (!isAdmin.value) {
    apiConfigError.value = '仅管理员可编辑配置。'
    return
  }
  if (!apiConfigEditForm.value.base_url.trim()) {
    apiConfigError.value = '请填写 API 域名。'
    return
  }
  apiConfigEditLoading.value = true
  try {
    const payload: AgentApiConfigUpdate = {
      base_url: apiConfigEditForm.value.base_url,
    }
    if (apiConfigEditForm.value.token.trim()) {
      payload.token = apiConfigEditForm.value.token
    }
    const saved = await updateAgentApiConfig(configId, payload)
    upsertApiConfig(saved)
    cancelInlineApiConfigEdit()
    apiConfigSuccess.value = '配置已更新。'
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '更新失败'
  } finally {
    apiConfigEditLoading.value = false
  }
}

const handleSaveApiConfig = async () => {
  apiConfigError.value = ''
  apiConfigSuccess.value = ''
  if (!isAdmin.value) {
    apiConfigError.value = '仅管理员可添加配置。'
    return
  }
  if (!fitSyncForm.value.base_url || !fitSyncForm.value.token) {
    apiConfigError.value = '请填写 API 域名与 Token。'
    return
  }
  apiConfigLoading.value = true
  try {
    const saved = await createAgentApiConfig({
      base_url: fitSyncForm.value.base_url,
      token: fitSyncForm.value.token,
    })
    upsertApiConfig(saved)
    apiConfigSuccess.value = '配置已添加。'
    fitSyncForm.value = {
      base_url: '',
      token: '',
    }
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    apiConfigLoading.value = false
  }
}

const openDeleteApiConfig = (config: AgentApiConfig) => {
  apiDeleteTarget.value = config
  showApiDeleteModal.value = true
}

const closeApiDeleteModal = () => {
  showApiDeleteModal.value = false
  apiDeleteTarget.value = null
}

const confirmDeleteApiConfig = async () => {
  if (!apiDeleteTarget.value) return
  const targetId = apiDeleteTarget.value.id
  apiConfigLoading.value = true
  apiConfigError.value = ''
  try {
    await deleteAgentApiConfig(targetId)
    apiConfigs.value = apiConfigs.value.filter((config) => config.id !== targetId)
    if (editingApiConfigId.value === targetId) {
      cancelInlineApiConfigEdit()
    }
    closeApiDeleteModal()
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    apiConfigLoading.value = false
  }
}

const resetApiSyncState = () => {
  syncWorkspaceError.value = ''
  syncAppsError.value = ''
  syncWorkspaceLoading.value = false
  syncAppsLoading.value = false
  syncWorkspaces.value = []
  syncApps.value = []
  selectedWorkspaceId.value = ''
  selectedWorkspaceName.value = ''
  selectedAppIds.value = []
}

const openApiSyncModal = async (config: AgentApiConfig) => {
  if (!isAdmin.value) {
    apiSyncError.value = '仅管理员可执行同步。'
    return
  }
  apiSyncError.value = ''
  apiSyncSuccess.value = ''
  apiSyncTarget.value = config
  showApiSyncModal.value = true
  resetApiSyncState()
  syncWorkspaceLoading.value = true
  try {
    syncWorkspaces.value = await fetchFit2CloudWorkspaces(config.id)
  } catch (err) {
    syncWorkspaceError.value = err instanceof Error ? err.message : '加载工作空间失败'
  } finally {
    syncWorkspaceLoading.value = false
  }
}

const closeApiSyncModal = () => {
  showApiSyncModal.value = false
  apiSyncTarget.value = null
  resetApiSyncState()
}

const selectWorkspace = async (workspace: Fit2CloudWorkspace) => {
  if (!apiSyncTarget.value) return
  selectedWorkspaceId.value = workspace.id
  selectedWorkspaceName.value = workspace.name
  selectedAppIds.value = []
  syncApps.value = []
  syncAppsError.value = ''
  syncAppsLoading.value = true
  try {
    syncApps.value = await fetchFit2CloudApplications(apiSyncTarget.value.id, workspace.id)
  } catch (err) {
    syncAppsError.value = err instanceof Error ? err.message : '加载应用失败'
  } finally {
    syncAppsLoading.value = false
  }
}

const toggleAppSelection = (appId: string) => {
  if (selectedAppIds.value.includes(appId)) {
    selectedAppIds.value = selectedAppIds.value.filter((id) => id !== appId)
    return
  }
  selectedAppIds.value = [...selectedAppIds.value, appId]
}

const toggleSelectAllApps = () => {
  if (allAppsSelected.value) {
    selectedAppIds.value = []
    return
  }
  selectedAppIds.value = syncApps.value.map((app) => app.id)
}

const confirmApiSync = async () => {
  if (!apiSyncTarget.value) return
  apiSyncError.value = ''
  apiSyncSuccess.value = ''
  if (!selectedWorkspaceId.value) {
    apiSyncError.value = '请选择工作空间。'
    return
  }
  if (!selectedAppIds.value.length) {
    apiSyncError.value = '请选择需要同步的智能体。'
    return
  }
  apiSyncLoading.value = true
  try {
    const result = await syncFit2CloudByConfig(apiSyncTarget.value.id, {
      workspace_id: selectedWorkspaceId.value,
      workspace_name: selectedWorkspaceName.value || undefined,
      application_ids: selectedAppIds.value,
      sync_all: allAppsSelected.value,
    })
    apiSyncSuccess.value = `同步完成：新增 ${result.imported}，更新 ${result.updated}。`
    if (result.errors?.length) {
      apiSyncError.value = result.errors.slice(0, 3).join('；')
    }
    closeApiSyncModal()
    await loadAgents()
  } catch (err) {
    apiSyncError.value = err instanceof Error ? err.message : '同步失败'
  } finally {
    apiSyncLoading.value = false
  }
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node
  if (agentGroupDropdownOpen.value && agentGroupDropdownRef.value) {
    if (!agentGroupDropdownRef.value.contains(target)) {
      closeAgentGroupDropdown()
    }
  }
  agentStatusOpen.value = false
}

onMounted(async () => {
  await Promise.all([loadAgents(), loadAgentGroups(), loadApiConfigs()])
})

useDocumentClick(handleDocumentClick)
</script>

<style scoped src="./AgentSyncModule.css"></style>
