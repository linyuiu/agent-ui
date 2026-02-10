import { computed, ref } from 'vue'

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
import { getCurrentRole } from '../../../services/session'

export const useAgentSyncModule = () => {
  const roleLocal = ref(getCurrentRole())
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
  const agentGroupDropdownOpen = ref(false)
  const agentGroupDropdownRef = ref<HTMLElement | null>(null)
  const agentGroupInputRef = ref<HTMLInputElement | null>(null)

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
  const syncWorkspaceLoading = ref(false)
  const syncWorkspaceError = ref('')
  const selectedWorkspaceIds = ref<string[]>([])
  const activeWorkspaceId = ref('')
  const workspaceApps = ref<Record<string, Fit2CloudApplication[]>>({})
  const workspaceAppLoading = ref<Record<string, boolean>>({})
  const workspaceAppErrors = ref<Record<string, string>>({})
  const selectedAppIdsByWorkspace = ref<Record<string, string[]>>({})

  const filteredAgentGroups = computed(() => {
    const query = agentGroupQuery.value.trim().toLowerCase()
    const options = groups.value.map((group) => group.name)
    return options.filter((group) => {
      if (!query) return true
      return group.toLowerCase().includes(query)
    })
  })

  const allWorkspacesSelected = computed(
    () =>
      syncWorkspaces.value.length > 0 &&
      selectedWorkspaceIds.value.length === syncWorkspaces.value.length
  )

  const selectedWorkspaceItems = computed(() =>
    syncWorkspaces.value.filter((workspace) => selectedWorkspaceIds.value.includes(workspace.id))
  )

  const activeWorkspace = computed(
    () => syncWorkspaces.value.find((workspace) => workspace.id === activeWorkspaceId.value) || null
  )

  const activeWorkspaceApps = computed(() => {
    if (!activeWorkspaceId.value) return []
    return workspaceApps.value[activeWorkspaceId.value] || []
  })

  const isActiveWorkspaceAllAppsSelected = computed(() => {
    if (!activeWorkspace.value) return false
    return isWorkspaceAllAppsSelected(activeWorkspace.value.id)
  })

  const isActiveWorkspaceAllAppsDisabled = computed(() => {
    if (!activeWorkspace.value) return true
    const workspaceId = activeWorkspace.value.id
    return Boolean(workspaceAppLoading.value[workspaceId]) || activeWorkspaceApps.value.length === 0
  })

  const canSyncSelectedWorkspaces = computed(() => {
    if (!selectedWorkspaceIds.value.length) return false
    return selectedWorkspaceIds.value.every((workspaceId) => {
      const selected = selectedAppIdsByWorkspace.value[workspaceId] || []
      return selected.length > 0
    })
  })

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
    } catch (err) {
      groupsError.value = err instanceof Error ? err.message : '加载失败'
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

  const selectAgentGroup = (group: string) => {
    if (!agentForm.value.groups.includes(group)) {
      agentForm.value.groups.push(group)
    }
    agentGroupQuery.value = ''
  }

  const removeAgentGroup = (group: string) => {
    const index = agentForm.value.groups.indexOf(group)
    if (index >= 0) {
      agentForm.value.groups.splice(index, 1)
    }
  }

  const handleAgentGroupEnter = async () => {
    const name = agentGroupQuery.value.trim()
    if (!name) return
    if (agentForm.value.groups.includes(name)) {
      agentGroupQuery.value = ''
      return
    }
    const exists = groups.value.some((group) => group.name === name)
    if (exists) {
      selectAgentGroup(name)
      return
    }
    try {
      await createAgentGroup({ name })
      await loadAgentGroups()
      selectAgentGroup(name)
    } catch (err) {
      agentCreateError.value = err instanceof Error ? err.message : '新增分组失败'
    }
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
    syncWorkspaceLoading.value = false
    syncWorkspaces.value = []
    selectedWorkspaceIds.value = []
    activeWorkspaceId.value = ''
    workspaceApps.value = {}
    workspaceAppLoading.value = {}
    workspaceAppErrors.value = {}
    selectedAppIdsByWorkspace.value = {}
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
      if (syncWorkspaces.value.length > 0) {
        activeWorkspaceId.value = syncWorkspaces.value[0].id
        await loadWorkspaceApplications(syncWorkspaces.value[0].id)
      }
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

  const setActiveWorkspace = async (workspace: Fit2CloudWorkspace) => {
    activeWorkspaceId.value = workspace.id
    await loadWorkspaceApplications(workspace.id)
  }

  const loadWorkspaceApplications = async (workspaceId: string) => {
    if (!apiSyncTarget.value) return
    const hasLoaded = Object.prototype.hasOwnProperty.call(workspaceApps.value, workspaceId)
    if (hasLoaded || workspaceAppLoading.value[workspaceId]) return
    workspaceAppLoading.value = { ...workspaceAppLoading.value, [workspaceId]: true }
    workspaceAppErrors.value = { ...workspaceAppErrors.value, [workspaceId]: '' }
    try {
      const apps = await fetchFit2CloudApplications(apiSyncTarget.value.id, workspaceId)
      workspaceApps.value = { ...workspaceApps.value, [workspaceId]: apps }
      selectedAppIdsByWorkspace.value = { ...selectedAppIdsByWorkspace.value, [workspaceId]: [] }
    } catch (err) {
      workspaceAppErrors.value = {
        ...workspaceAppErrors.value,
        [workspaceId]: err instanceof Error ? err.message : '加载应用失败',
      }
    } finally {
      workspaceAppLoading.value = { ...workspaceAppLoading.value, [workspaceId]: false }
    }
  }

  const toggleWorkspaceSelection = async (workspace: Fit2CloudWorkspace) => {
    const workspaceId = workspace.id
    activeWorkspaceId.value = workspaceId
    if (selectedWorkspaceIds.value.includes(workspaceId)) {
      selectedWorkspaceIds.value = selectedWorkspaceIds.value.filter((id) => id !== workspaceId)
      const nextSelectedApps = { ...selectedAppIdsByWorkspace.value }
      delete nextSelectedApps[workspaceId]
      selectedAppIdsByWorkspace.value = nextSelectedApps
      if (activeWorkspaceId.value === workspaceId) {
        const nextActive = selectedWorkspaceIds.value[0] || syncWorkspaces.value[0]?.id || ''
        activeWorkspaceId.value = nextActive
        if (nextActive) {
          await loadWorkspaceApplications(nextActive)
        }
      }
      return
    }
    selectedWorkspaceIds.value = [...selectedWorkspaceIds.value, workspaceId]
    await loadWorkspaceApplications(workspaceId)
  }

  const toggleSelectAllWorkspaces = async () => {
    if (allWorkspacesSelected.value) {
      selectedWorkspaceIds.value = []
      selectedAppIdsByWorkspace.value = {}
      if (syncWorkspaces.value.length > 0) {
        activeWorkspaceId.value = syncWorkspaces.value[0].id
        await loadWorkspaceApplications(syncWorkspaces.value[0].id)
      }
      return
    }
    const workspaceIds = syncWorkspaces.value.map((workspace) => workspace.id)
    selectedWorkspaceIds.value = workspaceIds
    if (workspaceIds.length > 0) {
      activeWorkspaceId.value = workspaceIds[0]
    }
    await Promise.all(workspaceIds.map((workspaceId) => loadWorkspaceApplications(workspaceId)))
  }

  const isWorkspaceAllAppsSelected = (workspaceId: string) => {
    const apps = workspaceApps.value[workspaceId] || []
    if (!apps.length) return false
    const selectedIds = selectedAppIdsByWorkspace.value[workspaceId] || []
    return selectedIds.length === apps.length
  }

  const toggleWorkspaceAppSelection = (workspaceId: string, appId: string) => {
    const selectedIds = selectedAppIdsByWorkspace.value[workspaceId] || []
    if (selectedIds.includes(appId)) {
      selectedAppIdsByWorkspace.value = {
        ...selectedAppIdsByWorkspace.value,
        [workspaceId]: selectedIds.filter((id) => id !== appId),
      }
      return
    }
    selectedAppIdsByWorkspace.value = {
      ...selectedAppIdsByWorkspace.value,
      [workspaceId]: [...selectedIds, appId],
    }
  }

  const toggleWorkspaceAllApps = (workspaceId: string) => {
    const apps = workspaceApps.value[workspaceId] || []
    if (!apps.length) return
    if (isWorkspaceAllAppsSelected(workspaceId)) {
      selectedAppIdsByWorkspace.value = { ...selectedAppIdsByWorkspace.value, [workspaceId]: [] }
      return
    }
    selectedAppIdsByWorkspace.value = {
      ...selectedAppIdsByWorkspace.value,
      [workspaceId]: apps.map((app) => app.id),
    }
  }

  const toggleActiveWorkspaceAllApps = () => {
    if (!activeWorkspace.value) return
    toggleWorkspaceAllApps(activeWorkspace.value.id)
  }

  const confirmApiSync = async () => {
    if (!apiSyncTarget.value) return
    apiSyncError.value = ''
    apiSyncSuccess.value = ''
    if (!selectedWorkspaceIds.value.length) {
      apiSyncError.value = '请选择至少一个工作空间。'
      return
    }
    if (!canSyncSelectedWorkspaces.value) {
      apiSyncError.value = '每个已选工作空间至少选择一个智能体。'
      return
    }

    const workspacePayloads = selectedWorkspaceItems.value
      .map((workspace) => {
        const apps = workspaceApps.value[workspace.id] || []
        const selectedIds = selectedAppIdsByWorkspace.value[workspace.id] || []
        const syncAll = apps.length > 0 && selectedIds.length === apps.length
        return {
          workspace_id: workspace.id,
          workspace_name: workspace.name,
          application_ids: syncAll ? undefined : selectedIds,
          sync_all: syncAll,
        }
      })
      .filter((item) => item.sync_all || (item.application_ids && item.application_ids.length > 0))

    if (!workspacePayloads.length) {
      apiSyncError.value = '未找到可同步的智能体选择。'
      return
    }

    apiSyncLoading.value = true
    try {
      const result = await syncFit2CloudByConfig(apiSyncTarget.value.id, {
        workspaces: workspacePayloads,
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

  const initialize = async () => {
    await Promise.all([loadAgents(), loadAgentGroups(), loadApiConfigs()])
    document.addEventListener('click', handleDocumentClick)
  }

  const dispose = () => {
    document.removeEventListener('click', handleDocumentClick)
  }

  return {
    isAdmin,
    agents,
    groups,
    apiConfigs,
    groupsLoading,
    groupsError,
    groupLoading,
    groupError,
    groupSuccess,
    groupForm,
    showGroupDeleteModal,
    groupDeleteTarget,
    groupDeleting,
    agentCreateLoading,
    agentCreateError,
    agentCreateSuccess,
    agentDeleteError,
    agentDeleteLoading,
    showAgentDeleteModal,
    agentDeleteTarget,
    agentStatusOpen,
    agentGroupQuery,
    agentGroupDropdownOpen,
    agentGroupDropdownRef,
    agentGroupInputRef,
    agentForm,
    apiConfigLoading,
    apiConfigEditLoading,
    apiConfigError,
    apiConfigSuccess,
    apiSyncLoading,
    apiSyncError,
    apiSyncSuccess,
    showApiDeleteModal,
    apiDeleteTarget,
    editingApiConfigId,
    apiConfigEditForm,
    fitSyncForm,
    showApiSyncModal,
    syncWorkspaces,
    syncWorkspaceLoading,
    syncWorkspaceError,
    selectedWorkspaceIds,
    activeWorkspaceId,
    workspaceAppLoading,
    workspaceAppErrors,
    selectedAppIdsByWorkspace,
    filteredAgentGroups,
    allWorkspacesSelected,
    activeWorkspace,
    activeWorkspaceApps,
    isActiveWorkspaceAllAppsSelected,
    isActiveWorkspaceAllAppsDisabled,
    canSyncSelectedWorkspaces,
    toggleAgentStatusDropdown,
    setAgentStatus,
    openAgentGroupDropdown,
    focusAgentGroupInput,
    removeAgentGroup,
    handleAgentGroupEnter,
    handleCreateAgentAdmin,
    openDeleteAgent,
    closeAgentDeleteModal,
    confirmDeleteAgent,
    handleCreateGroup,
    openDeleteGroup,
    closeGroupDeleteModal,
    confirmDeleteGroup,
    startInlineApiConfigEdit,
    cancelInlineApiConfigEdit,
    saveInlineApiConfigEdit,
    handleSaveApiConfig,
    openDeleteApiConfig,
    closeApiDeleteModal,
    confirmDeleteApiConfig,
    openApiSyncModal,
    closeApiSyncModal,
    setActiveWorkspace,
    toggleWorkspaceSelection,
    toggleSelectAllWorkspaces,
    toggleActiveWorkspaceAllApps,
    toggleWorkspaceAppSelection,
    confirmApiSync,
    initialize,
    dispose,
  }
}
