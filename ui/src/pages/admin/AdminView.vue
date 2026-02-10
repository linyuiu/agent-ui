<template>
  <div class="admin-view">
    <UserRoleModule v-if="currentSystemAdminTab === 'user-role'" />
    <PermissionModule v-else-if="currentSystemAdminTab === 'permissions'" />
    <AuthSettingsModule v-else-if="currentSystemAdminTab === 'auth-settings'" />
    <AgentSyncModule v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AgentSyncModule from './components/AgentSyncModule.vue'
import AuthSettingsModule from './components/AuthSettingsModule.vue'
import PermissionModule from './components/PermissionModule.vue'
import UserRoleModule from './components/UserRoleModule.vue'

type SystemAdminTab = 'user-role' | 'permissions' | 'auth-settings' | 'agent-sync'

const route = useRoute()

const normalizeSystemAdminTab = (value: unknown): SystemAdminTab => {
  const text = String(value || '')
  if (text === 'permissions') return 'permissions'
  if (text === 'auth-settings') return 'auth-settings'
  if (text === 'agent-sync') return 'agent-sync'
  return 'user-role'
}

const currentSystemAdminTab = computed<SystemAdminTab>(() =>
  normalizeSystemAdminTab(route.query.tab)
)
</script>

<style scoped src="./AdminView.css"></style>
