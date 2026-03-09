<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体</h2>
        <p>查看当前智能体实例与运行状态。</p>
        <div class="meta-line">
          <span class="count-pill">总数 {{ totalCount }}</span>
          <span class="count-pill">活跃 {{ activeCount }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="state">加载智能体列表中...</div>
    <div v-if="error" class="state error">{{ error }}</div>

    <div v-if="!loading" class="grid">
      <button
        v-for="agent in agents"
        :key="agent.id"
        class="card"
        type="button"
        @click="goDetail(agent.id)"
      >
        <div>
          <div class="card-title">
            <h3>{{ agent.name }}</h3>
            <span class="tag" :class="statusClass(agent)">{{ statusLabel(agent) }}</span>
          </div>
          <div v-if="agent.groups?.length" class="tag-row">
            <span v-for="group in agent.groups" :key="group" class="chip">分组：{{ group }}</span>
          </div>
        </div>
        <div class="card-meta">
          <span>Owner: {{ agent.owner }}</span>
          <span>Last run: {{ formatIsoDateTime(agent.last_run) }}</span>
          <a
            v-if="agent.url"
            class="link"
            :href="openAgentUrl(agent)"
            target="_blank"
            rel="noopener"
            @click.stop="handleOpenLink(agent, $event)"
          >
            打开链接
          </a>
        </div>
      </button>
    </div>

    <ConfirmDialog
      :open="showBlockedDialog"
      title="访问受限"
      :message="blockedDialogMessage"
      cancel-text="关闭"
      confirm-text="我知道了"
      @close="closeBlockedDialog"
      @confirm="closeBlockedDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import { fetchAgents, type AgentSummary } from '../../services/agents'
import { buildOpenAgentUrl } from '../../utils/agent-links'
import { formatIsoDateTime } from '../../utils/text-format'

const ACCESS_BLOCKED_MESSAGE = '该智能体暂时不可访问'

const router = useRouter()

const agents = ref<AgentSummary[]>([])
const loading = ref(false)
const error = ref('')
const showBlockedDialog = ref(false)
const blockedDialogMessage = ref(ACCESS_BLOCKED_MESSAGE)

const totalCount = computed(() => agents.value.length)
const isAgentActive = (agent: Pick<AgentSummary, 'status'>) =>
  (agent.status || '').toLowerCase() === 'active'
const activeCount = computed(() => agents.value.filter((agent) => isAgentActive(agent)).length)

const statusClass = (agent: Pick<AgentSummary, 'status'>) => (isAgentActive(agent) ? 'active' : 'paused')
const statusLabel = (agent: Pick<AgentSummary, 'status'>) => (isAgentActive(agent) ? 'active' : 'inactive')

const openAgentUrl = (agent: AgentSummary) => buildOpenAgentUrl(agent)

const openBlockedDialog = (agentName?: string) => {
  blockedDialogMessage.value = agentName ? `智能体「${agentName}」暂时不可访问。` : ACCESS_BLOCKED_MESSAGE
  showBlockedDialog.value = true
}

const closeBlockedDialog = () => {
  showBlockedDialog.value = false
}

const handleOpenLink = (agent: AgentSummary, event: MouseEvent) => {
  if (!isAgentActive(agent)) {
    event.preventDefault()
    openBlockedDialog(agent.name)
  }
}

const goDetail = async (id: string) => {
  await router.push({ name: 'home-agent-detail', params: { id } })
}

const loadAgents = async () => {
  loading.value = true
  error.value = ''
  try {
    agents.value = await fetchAgents({ includeDescription: false })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAgents)
</script>

<style scoped src="./AgentsListView.css"></style>
