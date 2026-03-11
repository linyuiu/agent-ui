<template>
  <div class="section">
    <div class="section-header">
      <button class="ghost" type="button" @click="goBack">返回列表</button>
    </div>

    <div v-if="loading" class="state">加载详情中...</div>
    <div v-if="error" class="state error">{{ error }}</div>

    <div v-if="agent" class="detail">
      <div class="detail-header">
        <div>
          <h2>{{ agent.name }}</h2>
          <p>{{ agent.description }}</p>
        </div>
        <div class="tag-group">
          <span class="tag tag-large" :class="statusClass">{{ statusLabel }}</span>
        </div>
      </div>

      <div class="meta">
        <div>
          <span class="label">Owner</span>
          <span>{{ agent.owner }}</span>
        </div>
        <div>
          <span class="label">Group</span>
          <span>{{ agent.groups?.length ? agent.groups.join(', ') : '未分组' }}</span>
        </div>
        <div>
          <span class="label">Last run</span>
          <span>{{ formatIsoDateTime(agent.last_run) }}</span>
        </div>
        <div v-if="agent.url">
          <span class="label">URL</span>
          <a class="link" :href="openAgentUrl" target="_blank" rel="noopener" @click="handleOpenLink">
            打开链接
          </a>
        </div>
      </div>
    </div>

    <div v-if="agent" class="panel chat-user-panel">
      <div class="section-header compact">
        <div>
          <h3>对话用户</h3>
          <p>展示当前智能体下的用户组与对话用户授权状态，仅用于查看。</p>
        </div>
      </div>
      <p v-if="chatUserLoading" class="state">加载对话用户中...</p>
      <p v-else-if="chatUserError" class="state error">{{ chatUserError }}</p>
      <p v-else-if="chatUserView?.last_synced_at" class="state success">
        最近同步时间：{{ formatIsoDateTime(chatUserView.last_synced_at) }}
      </p>
      <p v-if="chatUserManageSuccess" class="state success">{{ chatUserManageSuccess }}</p>
      <p v-if="chatUserManageError" class="state error">{{ chatUserManageError }}</p>
      <div v-if="chatUserView?.groups?.length" class="chat-user-groups">
        <div v-for="group in chatUserView.groups" :key="group.id" class="chat-user-group-card">
          <div class="chat-user-group-head">
            <div>
              <strong>{{ group.name }}</strong>
              <small>{{ group.id }}</small>
            </div>
            <div class="chat-user-group-actions">
              <span class="tag tag-small readonly">{{ group.authorized_count }}/{{ group.users.length }} 已授权</span>
              <button
                v-if="chatUserView.manageable && chatUserView.sync_supported"
                class="ghost small"
                type="button"
                :disabled="chatUserSavingGroupId === group.id || !isGroupDirty(group)"
                @click="saveGroupAuth(group)"
              >
                {{ chatUserSavingGroupId === group.id ? '保存中...' : '保存授权' }}
              </button>
            </div>
          </div>
          <div class="chat-user-list">
            <div v-for="user in group.users" :key="`${group.id}-${user.id}`" class="chat-user-item">
              <div class="chat-user-main">
                <strong>{{ user.nick_name || user.username }}</strong>
                <small>{{ user.username }} · {{ user.source || 'unknown' }}</small>
              </div>
              <label
                v-if="chatUserView.manageable && chatUserView.sync_supported"
                class="chat-user-auth-control"
              >
                <input
                  type="checkbox"
                  :checked="getUserAuthState(group.id, user.id, user.is_auth)"
                  @change="handleUserAuthChange(group.id, user.id, $event)"
                />
                <span>{{ getUserAuthState(group.id, user.id, user.is_auth) ? '已授权' : '未授权' }}</span>
              </label>
              <span v-else class="tag tag-small" :class="user.is_auth ? 'active' : 'paused'">
                {{ user.is_auth ? '已授权' : '未授权' }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <p v-else-if="!chatUserLoading && !chatUserError" class="state">暂无对话用户同步数据。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchAgent,
  fetchAgentChatUsers,
  updateAgentChatUsers,
  type AgentChatUserGroupView,
  type AgentChatUserView,
  type AgentDetail,
  type AgentSummary,
} from '../../services/agents'
import { buildOpenAgentUrl } from '../../utils/agent-links'
import { formatIsoDateTime } from '../../utils/text-format'

const ACCESS_BLOCKED_MESSAGE = '该智能体暂时不可访问'

const route = useRoute()
const router = useRouter()

const agent = ref<AgentDetail | null>(null)
const loading = ref(false)
const error = ref('')
const chatUserView = ref<AgentChatUserView | null>(null)
const chatUserLoading = ref(false)
const chatUserError = ref('')
const chatUserManageError = ref('')
const chatUserManageSuccess = ref('')
const chatUserSavingGroupId = ref('')
const chatUserDrafts = ref<Record<string, Record<string, boolean>>>({})

const isAgentActive = (target: Pick<AgentSummary, 'status'>) =>
  (target.status || '').toLowerCase() === 'active'

const statusClass = computed(() => {
  if (!agent.value) return 'paused'
  return isAgentActive(agent.value) ? 'active' : 'paused'
})

const statusLabel = computed(() => {
  if (!agent.value) return 'inactive'
  return isAgentActive(agent.value) ? 'active' : 'inactive'
})

const openAgentUrl = computed(() => (agent.value ? buildOpenAgentUrl(agent.value) : ''))

const handleOpenLink = (event: MouseEvent) => {
  if (!agent.value) return
  if (!isAgentActive(agent.value)) {
    event.preventDefault()
    window.alert(ACCESS_BLOCKED_MESSAGE)
  }
}

const resetChatUserDrafts = (view: AgentChatUserView | null) => {
  const next: Record<string, Record<string, boolean>> = {}
  for (const group of view?.groups || []) {
    next[group.id] = {}
    for (const user of group.users) {
      next[group.id][user.id] = Boolean(user.is_auth)
    }
  }
  chatUserDrafts.value = next
}

const getUserAuthState = (groupId: string, userId: string, fallback: boolean) =>
  chatUserDrafts.value[groupId]?.[userId] ?? fallback

const setUserAuthState = (groupId: string, userId: string, value: boolean) => {
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  chatUserDrafts.value = {
    ...chatUserDrafts.value,
    [groupId]: {
      ...(chatUserDrafts.value[groupId] || {}),
      [userId]: value,
    },
  }
}

const handleUserAuthChange = (groupId: string, userId: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  setUserAuthState(groupId, userId, Boolean(target?.checked))
}

const isGroupDirty = (group: AgentChatUserGroupView) =>
  group.users.some((user) => getUserAuthState(group.id, user.id, user.is_auth) !== Boolean(user.is_auth))

const saveGroupAuth = async (group: AgentChatUserGroupView) => {
  if (!agent.value || !chatUserView.value?.manageable || !chatUserView.value?.sync_supported) return
  chatUserSavingGroupId.value = group.id
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  try {
    const updated = await updateAgentChatUsers(agent.value.id, {
      group_id: group.id,
      users: group.users.map((user) => ({
        chat_user_id: user.id,
        is_auth: getUserAuthState(group.id, user.id, Boolean(user.is_auth)),
      })),
    })
    chatUserView.value = updated
    resetChatUserDrafts(updated)
    chatUserManageSuccess.value = `${group.name} 授权已更新。`
  } catch (err) {
    chatUserManageError.value = err instanceof Error ? err.message : '更新授权失败'
  } finally {
    chatUserSavingGroupId.value = ''
  }
}

const loadAgent = async (id: string) => {
  loading.value = true
  error.value = ''
  chatUserView.value = null
  chatUserError.value = ''
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  chatUserDrafts.value = {}
  try {
    const detail = await fetchAgent(id)
    agent.value = detail
    chatUserLoading.value = true
    try {
      const view = await fetchAgentChatUsers(id)
      chatUserView.value = view
      resetChatUserDrafts(view)
    } catch (chatErr) {
      chatUserView.value = null
      chatUserError.value = chatErr instanceof Error ? chatErr.message : '加载对话用户失败'
    } finally {
      chatUserLoading.value = false
    }
  } catch (err) {
    agent.value = null
    chatUserLoading.value = false
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

const goBack = async () => {
  await router.push({ name: 'home-agents' })
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') {
      loadAgent(id)
    }
  },
  { immediate: true },
)
</script>

<style scoped src="./AgentDetailView.css"></style>
