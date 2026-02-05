<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体</h2>
        <p>管理不同任务的智能体实例与能力配置。</p>
      </div>
      <div class="actions">
        <button class="ghost" type="button" @click="showCreate = !showCreate">
          {{ showCreate ? '关闭创建' : '新建智能体' }}
        </button>
        <button class="ghost" type="button" @click="showSync = !showSync">
          {{ showSync ? '关闭同步' : 'API 同步' }}
        </button>
      </div>
    </div>

    <div v-if="showCreate" class="panel">
      <form class="form" @submit.prevent="handleCreateAgent">
        <div class="field">
          <label>名称</label>
          <input v-model="agentForm.name" type="text" placeholder="Agent Name" required />
        </div>
        <div class="field">
          <label>URL</label>
          <input v-model="agentForm.url" type="text" placeholder="https://example.com/agent" required />
        </div>
        <div class="field">
          <label>负责人</label>
          <input v-model="agentForm.owner" type="text" placeholder="Operations" />
        </div>
        <div class="field">
          <label>状态</label>
          <select v-model="agentForm.status">
            <option value="active">active</option>
            <option value="paused">paused</option>
          </select>
        </div>
        <div class="field">
          <label>最近运行时间</label>
          <input v-model="agentForm.last_run" type="text" placeholder="2026-02-05T10:00:00Z" />
        </div>
        <div class="field">
          <label>描述</label>
          <input v-model="agentForm.description" type="text" placeholder="简短说明" />
        </div>
        <div class="field">
          <label>分组</label>
          <input v-model="agentForm.groups" type="text" placeholder="例如: operations, core" />
        </div>
        <div class="button-row">
          <button class="primary" type="submit" :disabled="createLoading">
            {{ createLoading ? '创建中...' : '创建智能体' }}
          </button>
        </div>
      </form>

      <p v-if="createError" class="state error">{{ createError }}</p>
      <p v-if="createSuccess" class="state success">{{ createSuccess }}</p>
    </div>

    <div v-if="showSync" class="panel">
      <form class="form" @submit.prevent="handleSyncPreview">
        <div class="field">
          <label>API 地址</label>
          <input v-model="syncForm.api_url" type="text" placeholder="https://api.example.com/agents" />
        </div>
        <div class="field">
          <label>AK</label>
          <input v-model="syncForm.ak" type="text" placeholder="access key" />
        </div>
        <div class="field">
          <label>SK</label>
          <input v-model="syncForm.sk" type="password" placeholder="secret key" />
        </div>
        <div class="button-row">
          <button class="ghost" type="submit">保存配置</button>
          <button class="primary" type="button" disabled>同步数据</button>
        </div>
      </form>
      <p class="state">当前仅展示样式，后端同步逻辑待接入。</p>
      <p v-if="syncMessage" class="state success">{{ syncMessage }}</p>
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
            <span class="tag" :class="agent.status">{{ agent.status }}</span>
            <span class="tag" :class="agent.editable ? 'editable' : 'readonly'">
              {{ agent.editable ? '可编辑' : '只读' }}
            </span>
          </div>
          <p>{{ agent.description }}</p>
          <div v-if="agent.groups?.length" class="tag-row">
            <span v-for="group in agent.groups" :key="group" class="chip">分组：{{ group }}</span>
          </div>
        </div>
        <div class="card-meta">
          <span>Owner: {{ agent.owner }}</span>
          <span>Last run: {{ formatTime(agent.last_run) }}</span>
          <a
            v-if="agent.url"
            class="link"
            :href="agent.url"
            target="_blank"
            rel="noopener"
            @click.stop
          >
            打开链接
          </a>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createAgent, fetchAgents, type AgentSummary } from '../api/agents'

const router = useRouter()

const agents = ref<AgentSummary[]>([])
const loading = ref(false)
const error = ref('')

const showCreate = ref(false)
const showSync = ref(false)

const createLoading = ref(false)
const createError = ref('')
const createSuccess = ref('')

const syncMessage = ref('')

const agentForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  last_run: '',
  description: '',
  groups: '',
})

const syncForm = ref({
  api_url: '',
  ak: '',
  sk: '',
})

const formatTime = (value: string) => {
  return value.replace('T', ' ').replace('Z', '')
}

const goDetail = async (id: string) => {
  await router.push({ name: 'home-agent-detail', params: { id } })
}

const handleCreateAgent = async () => {
  createLoading.value = true
  createError.value = ''
  createSuccess.value = ''

  try {
    await createAgent({
      name: agentForm.value.name,
      url: agentForm.value.url,
      owner: agentForm.value.owner || 'system',
      status: agentForm.value.status,
      last_run: agentForm.value.last_run,
      description: agentForm.value.description,
      groups: agentForm.value.groups
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    createSuccess.value = '智能体已创建。'
    agentForm.value = {
      name: '',
      url: '',
      owner: '',
      status: 'active',
      last_run: '',
      description: '',
      groups: '',
    }
    await loadAgents()
  } catch (err) {
    createError.value = err instanceof Error ? err.message : '创建失败'
  } finally {
    createLoading.value = false
  }
}

const handleSyncPreview = () => {
  syncMessage.value = '已保存同步配置（样式预览）。'
}

const loadAgents = async () => {
  loading.value = true
  error.value = ''
  try {
    agents.value = await fetchAgents()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAgents)
</script>

<style scoped>
.section {
  display: grid;
  gap: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.section-header h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 26px;
  margin: 0 0 6px;
}

.section-header p {
  margin: 0;
  color: #4b5b60;
}

.state {
  font-size: 14px;
  color: #5a6a70;
}

.state.error {
  color: #b13333;
}

.state.success {
  color: #0f6b4f;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(15, 40, 55, 0.06);
  display: grid;
  gap: 12px;
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.field label {
  color: #5a6a70;
}

.field input,
.field select {
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 10px 12px;
  font-size: 14px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.card {
  text-align: left;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 18px;
  display: grid;
  gap: 12px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(15, 40, 55, 0.06);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(15, 40, 55, 0.12);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card h3 {
  margin: 0;
  font-size: 16px;
}

.card p {
  margin: 0;
  color: #5a6a70;
  font-size: 14px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.chip {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(255, 127, 80, 0.16);
  color: #b24724;
}

.card-meta {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #6a7a80;
}

.link {
  color: #0c7e85;
  text-decoration: none;
  font-weight: 600;
}

.link:hover {
  text-decoration: underline;
}

.tag {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
}

.tag.paused {
  background: rgba(255, 127, 80, 0.16);
  color: #b24724;
}

.tag.editable {
  background: rgba(15, 107, 79, 0.12);
  color: #0f6b4f;
}

.tag.readonly {
  background: rgba(90, 106, 112, 0.16);
  color: #4b5b60;
}

.ghost {
  border: 1px solid rgba(15, 179, 185, 0.4);
  color: #0c7e85;
  background: transparent;
  padding: 10px 18px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}

.ghost:hover {
  background: rgba(15, 179, 185, 0.08);
}
</style>
