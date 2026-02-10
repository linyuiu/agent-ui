<template>
  <div v-if="open" class="modal-backdrop">
    <div class="modal-card modal-large">
      <div class="modal-header">
        <h3>同步智能体</h3>
        <button class="modal-close" type="button" @click="$emit('close')">✕</button>
      </div>
      <div class="modal-body">
        <div class="sync-grid">
          <div class="sync-panel">
            <div class="sync-panel-header">
              <span class="column-title">工作空间</span>
              <label class="checkbox-line">
                <input
                  type="checkbox"
                  :checked="allWorkspacesSelected"
                  :disabled="!syncWorkspaces.length"
                  @change="$emit('toggle-select-all-workspaces')"
                />
                <span>全选</span>
              </label>
            </div>
            <div v-if="syncWorkspaceLoading" class="state">加载工作空间中...</div>
            <div v-else-if="syncWorkspaceError" class="state error">{{ syncWorkspaceError }}</div>
            <div v-else class="list">
              <div
                v-for="workspace in syncWorkspaces"
                :key="workspace.id"
                class="list-item checkbox-item"
                :class="{
                  active: selectedWorkspaceIds.includes(workspace.id),
                  focused: activeWorkspaceId === workspace.id,
                }"
                @click="$emit('set-active-workspace', workspace)"
              >
                <input
                  type="checkbox"
                  :checked="selectedWorkspaceIds.includes(workspace.id)"
                  @click.stop
                  @change.stop="$emit('toggle-workspace-selection', workspace)"
                />
                <div class="checkbox-text">
                  <strong>{{ workspace.name }}</strong>
                  <small>{{ workspace.id }}</small>
                </div>
              </div>
              <div v-if="!syncWorkspaces.length" class="state">暂无工作空间</div>
            </div>
          </div>
          <div class="sync-panel">
            <div class="sync-panel-header">
              <span class="column-title">智能体</span>
              <label class="checkbox-line">
                <input
                  type="checkbox"
                  :checked="isActiveWorkspaceAllAppsSelected"
                  :disabled="isActiveWorkspaceAllAppsDisabled"
                  @change="$emit('toggle-active-workspace-all-apps')"
                />
                <span>全选</span>
              </label>
            </div>
            <div class="list">
              <template v-if="activeWorkspace">
                <div class="workspace-app-group">
                  <div class="workspace-app-header">
                    <div class="workspace-app-title">
                      <strong>{{ activeWorkspace.name }}</strong>
                      <small>{{ activeWorkspace.id }}</small>
                    </div>
                  </div>
                  <div v-if="workspaceAppLoading[activeWorkspace.id]" class="state">加载智能体中...</div>
                  <div v-else-if="workspaceAppErrors[activeWorkspace.id]" class="state error">
                    {{ workspaceAppErrors[activeWorkspace.id] }}
                  </div>
                  <div v-else-if="!activeWorkspaceApps.length" class="state">暂无智能体</div>
                  <div v-else class="workspace-app-items">
                    <label
                      v-for="app in activeWorkspaceApps"
                      :key="`${activeWorkspace.id}-${app.id}`"
                      class="list-item checkbox-item"
                    >
                      <input
                        type="checkbox"
                        :checked="(selectedAppIdsByWorkspace[activeWorkspace.id] || []).includes(app.id)"
                        @change="
                          $emit('toggle-workspace-app-selection', {
                            workspaceId: activeWorkspace.id,
                            appId: app.id,
                          })
                        "
                      />
                      <div class="checkbox-text">
                        <strong>{{ app.name }}</strong>
                        <small>{{ app.id }}</small>
                      </div>
                    </label>
                  </div>
                </div>
              </template>
              <div v-else class="state">请先点击工作空间</div>
            </div>
          </div>
        </div>
        <p v-if="apiSyncError" class="state error">{{ apiSyncError }}</p>
      </div>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="$emit('close')">取消</button>
        <button
          class="primary"
          type="button"
          :disabled="apiSyncLoading || !canSyncSelectedWorkspaces"
          @click="$emit('confirm-sync')"
        >
          {{ apiSyncLoading ? '同步中...' : '确认同步' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Fit2CloudApplication, Fit2CloudWorkspace } from '../../../services/admin'

defineProps<{
  open: boolean
  syncWorkspaces: Fit2CloudWorkspace[]
  selectedWorkspaceIds: string[]
  activeWorkspaceId: string
  activeWorkspace: Fit2CloudWorkspace | null
  activeWorkspaceApps: Fit2CloudApplication[]
  workspaceAppLoading: Record<string, boolean>
  workspaceAppErrors: Record<string, string>
  selectedAppIdsByWorkspace: Record<string, string[]>
  allWorkspacesSelected: boolean
  isActiveWorkspaceAllAppsSelected: boolean
  isActiveWorkspaceAllAppsDisabled: boolean
  canSyncSelectedWorkspaces: boolean
  syncWorkspaceLoading: boolean
  syncWorkspaceError: string
  apiSyncError: string
  apiSyncLoading: boolean
}>()

defineEmits<{
  (event: 'close'): void
  (event: 'toggle-select-all-workspaces'): void
  (event: 'set-active-workspace', workspace: Fit2CloudWorkspace): void
  (event: 'toggle-workspace-selection', workspace: Fit2CloudWorkspace): void
  (event: 'toggle-active-workspace-all-apps'): void
  (event: 'toggle-workspace-app-selection', payload: { workspaceId: string; appId: string }): void
  (event: 'confirm-sync'): void
}>()
</script>

<style scoped src="./SyncSelectionModal.css"></style>
