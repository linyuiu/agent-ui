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
      <div v-if="chatUserView?.groups?.length" class="chat-user-groups">
        <div v-for="group in chatUserView.groups" :key="group.id" class="chat-user-group-card">
          <div class="chat-user-group-head">
            <div>
              <strong>{{ group.name }}</strong>
              <small>{{ group.id }}</small>
            </div>
            <span class="tag tag-small readonly">{{ group.users.length }} 人</span>
          </div>
          <div class="chat-user-list">
            <div v-for="user in group.users" :key="`${group.id}-${user.id}`" class="chat-user-item">
              <div class="chat-user-main">
                <strong>{{ user.nick_name || user.username }}</strong>
                <small>{{ user.username }} · {{ user.source || 'unknown' }}</small>
              </div>
              <span class="tag tag-small" :class="user.is_auth ? 'active' : 'paused'">
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
import { fetchAgent, fetchAgentChatUsers, type AgentDetail, type AgentSummary, type AgentChatUserView } from '../../services/agents'
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

const loadAgent = async (id: string) => {
  loading.value = true
  error.value = ''
  chatUserView.value = null
  chatUserError.value = ''
  try {
    const detail = await fetchAgent(id)
    agent.value = detail
    chatUserLoading.value = true
    try {
      chatUserView.value = await fetchAgentChatUsers(id)
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
