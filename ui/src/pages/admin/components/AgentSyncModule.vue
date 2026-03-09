<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体同步</h2>
        <p>新增智能体、维护分组并配置同步源。</p>
      </div>
    </div>

    <div class="panel">
      <div class="sub-panel">
        <div class="sub-header">
          <h4>智能体管理</h4>
          <p>新增、删除智能体，并支持对同步创建的智能体手动同步对话用户。</p>
        </div>
        <form class="form agent-form" @submit.prevent="handleCreateAgentAdmin">
          <div class="field">
            <label>名称</label>
            <input v-model="agentForm.name" type="text" placeholder="Agent Name" required />
          </div>
          <div class="field">
            <label>URL</label>
            <input v-model="agentForm.url" type="text" placeholder="https://example.com/chat/your-token" required />
          </div>
          <div class="field">
            <label>负责人</label>
            <input v-model="agentForm.owner" type="text" placeholder="system" />
          </div>
          <div class="field">
            <label>状态</label>
            <div class="inline-dropdown" @click.stop>
              <button class="filter-trigger inline-trigger" type="button" @click.stop="toggleAgentStatusDropdown">
                <span>{{ agentForm.status }}</span>
                <span class="caret" :class="{ open: agentStatusOpen }"></span>
              </button>
              <div v-if="agentStatusOpen" class="filter-dropdown inline-dropdown-panel">
                <button class="filter-option" type="button" @click="setAgentStatus('active')">active</button>
                <button class="filter-option" type="button" @click="setAgentStatus('paused')">paused</button>
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
                    <button class="chip-remove" type="button" @click.stop="removeAgentGroup(group)">×</button>
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

        <p v-if="!isAdmin" class="state">仅管理员可新增、删除智能体与同步对话用户。</p>
        <p v-if="agentCreateError" class="state error">{{ agentCreateError }}</p>
        <p v-if="agentCreateSuccess" class="state success">{{ agentCreateSuccess }}</p>
        <p v-if="agentDeleteError" class="state error">{{ agentDeleteError }}</p>
        <p v-if="agentUserSyncError" class="state error">{{ agentUserSyncError }}</p>
        <p v-if="agentUserSyncSuccess" class="state success">{{ agentUserSyncSuccess }}</p>

        <div v-if="agents.length" class="grid">
          <div v-for="agent in agents" :key="agent.id" class="policy-card agent-card">
            <div class="agent-card-head">
              <div>
                <h3>{{ agent.name }}</h3>
                <p>{{ agent.groups?.length ? agent.groups.join('，') : '未分组' }}</p>
              </div>
              <div class="tag-row">
                <span class="tag tag-small" :class="agent.status">{{ agent.status }}</span>
                <span v-if="agent.status_editable_only" class="tag tag-small readonly">同步</span>
              </div>
            </div>
            <p class="agent-card-meta">负责人：{{ agent.owner || 'system' }}</p>
            <p v-if="agent.sync_task_status" class="agent-card-meta">最近任务：{{ agent.sync_task_status }}</p>
            <div class="policy-actions">
              <button
                v-if="agent.can_sync_users"
                class="ghost"
                type="button"
                :disabled="agentUserSyncLoadingId === agent.id || !isAdmin"
                @click="handleSyncAgentUsers(agent)"
              >
                {{ agentUserSyncLoadingId === agent.id ? '同步中...' : '同步用户' }}
              </button>
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
          <div v-for="group in groups" :key="group.id" class="policy-card">
            <div>
              <h3>{{ group.name }}</h3>
              <p>{{ group.description || '暂无描述' }}</p>
            </div>
            <div class="policy-actions">
              <button class="ghost danger" type="button" @click="openDeleteGroup(group)">删除</button>
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
              <input v-model="apiConfigEditForm.base_url" type="text" placeholder="https://mk-ee.fit2cloud.cn" />
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
              <button class="ghost" type="button" :disabled="!isAdmin" @click="openApiSyncModal(config)">同步</button>
              <button class="ghost danger" type="button" @click="openDeleteApiConfig(config)">删除</button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>

  <SyncSelectionModal
    :open="showApiSyncModal"
    :sync-workspaces="syncWorkspaces"
    :selected-workspace-ids="selectedWorkspaceIds"
    :active-workspace-id="activeWorkspaceId"
    :active-workspace="activeWorkspace"
    :active-workspace-apps="activeWorkspaceApps"
    :workspace-app-loading="workspaceAppLoading"
    :workspace-app-errors="workspaceAppErrors"
    :selected-app-ids-by-workspace="selectedAppIdsByWorkspace"
    :all-workspaces-selected="allWorkspacesSelected"
    :is-active-workspace-all-apps-selected="isActiveWorkspaceAllAppsSelected"
    :is-active-workspace-all-apps-disabled="isActiveWorkspaceAllAppsDisabled"
    :can-sync-selected-workspaces="canSyncSelectedWorkspaces"
    :sync-workspace-loading="syncWorkspaceLoading"
    :sync-workspace-error="syncWorkspaceError"
    :api-sync-error="apiSyncError"
    :api-sync-loading="apiSyncLoading"
    @close="closeApiSyncModal"
    @toggle-select-all-workspaces="toggleSelectAllWorkspaces"
    @toggle-workspace-selection="toggleWorkspaceSelection"
    @toggle-active-workspace-all-apps="toggleActiveWorkspaceAllApps"
    @toggle-workspace-app-selection="({ workspaceId, appId }) => toggleWorkspaceAppSelection(workspaceId, appId)"
    @confirm-sync="openSyncChatUserPrompt"
  />

  <ConfirmDialog
    :open="showSyncChatUserPrompt"
    title="同步对话用户"
    message="是否在同步智能体后立即同步对话用户？不立即同步时，后续可在智能体管理中手动执行全量覆盖同步。"
    confirm-text="同步对话用户"
    cancel-text="返回选择"
    secondary-text="仅同步智能体"
    @close="closeSyncChatUserPrompt"
    @secondary="handleSkipSyncChatUsers"
    @confirm="handleConfirmSyncChatUsers"
  />

  <ConfirmDialog
    :open="showGroupDeleteModal"
    title="删除分组"
    :message="`确认删除 ${groupDeleteTarget?.name || ''} 吗？该分组关联的权限数据将一并删除。`"
    :loading="groupDeleting"
    loading-text="处理中..."
    confirm-text="确认删除"
    @close="closeGroupDeleteModal"
    @confirm="confirmDeleteGroup"
  />

  <ConfirmDialog
    :open="showApiDeleteModal"
    title="删除 API 配置"
    :message="`确认删除 ${apiDeleteTarget?.base_url || ''} 吗？`"
    :loading="apiConfigLoading"
    loading-text="处理中..."
    confirm-text="确认删除"
    @close="closeApiDeleteModal"
    @confirm="confirmDeleteApiConfig"
  />

  <ConfirmDialog
    :open="showAgentDeleteModal"
    title="删除智能体"
    :message="`确认删除 ${agentDeleteTarget?.name || ''} 吗？该智能体的权限数据与同步用户数据将一并删除。`"
    :loading="agentDeleteLoading"
    loading-text="处理中..."
    confirm-text="确认删除"
    @close="closeAgentDeleteModal"
    @confirm="confirmDeleteAgent"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import ConfirmDialog from '../../../components/common/ConfirmDialog.vue'
import SyncSelectionModal from './SyncSelectionModal.vue'
import { useAgentSyncModule } from '../composables/useAgentSyncModule'

const {
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
  agentUserSyncLoadingId,
  agentUserSyncError,
  agentUserSyncSuccess,
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
  selectAgentGroup,
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
  toggleWorkspaceSelection,
  toggleSelectAllWorkspaces,
  toggleActiveWorkspaceAllApps,
  toggleWorkspaceAppSelection,
  confirmApiSync,
  handleSyncAgentUsers,
  initialize,
  dispose,
} = useAgentSyncModule()

const showSyncChatUserPrompt = ref(false)

const openSyncChatUserPrompt = () => {
  showSyncChatUserPrompt.value = true
}

const closeSyncChatUserPrompt = () => {
  showSyncChatUserPrompt.value = false
}

const handleConfirmSyncChatUsers = async () => {
  showSyncChatUserPrompt.value = false
  await confirmApiSync(true)
}

const handleSkipSyncChatUsers = async () => {
  showSyncChatUserPrompt.value = false
  await confirmApiSync(false)
}

onMounted(async () => {
  await initialize()
})

onBeforeUnmount(() => {
  dispose()
})
</script>

<style scoped src="./AgentSyncModule.css"></style>
