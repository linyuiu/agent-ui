<template>
  <div class="admin-view">
    <UserRoleModule v-if="currentSystemAdminTab === 'user-role'" />
    <PermissionModule v-else-if="currentSystemAdminTab === 'permissions'" />
    <SystemSettingsModule v-else-if="currentSystemAdminTab === 'system-settings'" />
    <AuthSettingsModule v-else-if="currentSystemAdminTab === 'auth-settings'" />
    <SyncTaskProgressModule v-else-if="currentSystemAdminTab === 'sync-progress'" />
    <AgentSyncModule v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AgentSyncModule from './components/AgentSyncModule.vue'
import AuthSettingsModule from './components/AuthSettingsModule.vue'
import PermissionModule from './components/PermissionModule.vue'
import SyncTaskProgressModule from './components/SyncTaskProgressModule.vue'
import SystemSettingsModule from './components/SystemSettingsModule.vue'
import UserRoleModule from './components/UserRoleModule.vue'

type SystemAdminTab =
  | 'user-role'
  | 'permissions'
  | 'system-settings'
  | 'auth-settings'
  | 'agent-sync'
  | 'sync-progress'

const route = useRoute()

const normalizeSystemAdminTab = (value: unknown): SystemAdminTab => {
  const text = String(value || '')
  if (text === 'permissions') return 'permissions'
  if (text === 'system-settings') return 'system-settings'
  if (text === 'auth-settings') return 'auth-settings'
  if (text === 'sync-progress') return 'sync-progress'
  if (text === 'agent-sync') return 'agent-sync'
  return 'user-role'
}

const currentSystemAdminTab = computed<SystemAdminTab>(() =>
  normalizeSystemAdminTab(route.query.tab)
)
</script>

<style scoped src="./AdminView.css"></style>
