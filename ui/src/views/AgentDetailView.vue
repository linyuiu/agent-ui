<template>
  <div class="section">
    <div class="section-header">
      <button class="ghost" type="button" @click="goBack">返回列表</button>
      <button
        v-if="agent?.editable"
        class="primary"
        type="button"
        @click="toggleEdit"
      >
        {{ editing ? '取消编辑' : '编辑智能体' }}
      </button>
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
          <span class="tag" :class="agent.status">{{ agent.status }}</span>
          <span class="tag" :class="agent.editable ? 'editable' : 'readonly'">
            {{ agent.editable ? '可编辑' : '只读' }}
          </span>
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
          <span>{{ formatTime(agent.last_run) }}</span>
        </div>
        <div v-if="agent.url">
          <span class="label">URL</span>
          <a class="link" :href="agent.url" target="_blank" rel="noopener">打开链接</a>
        </div>
      </div>
    </div>

    <p v-if="agent && !agent.editable" class="state">
      该智能体来源于 API，同步数据不可手动编辑。
    </p>

    <div v-if="agent && agent.editable && editing" class="panel edit-panel">
      <form class="form" @submit.prevent="handleUpdate">
        <div class="field">
          <label>名称</label>
          <input v-model="editForm.name" type="text" required />
        </div>
        <div class="field">
          <label>URL</label>
          <input v-model="editForm.url" type="text" required />
        </div>
        <div class="field">
          <label>负责人</label>
          <input v-model="editForm.owner" type="text" />
        </div>
        <div class="field">
          <label>状态</label>
          <select v-model="editForm.status">
            <option value="active">active</option>
            <option value="paused">paused</option>
          </select>
        </div>
        <div class="field">
          <label>最近运行时间</label>
          <input v-model="editForm.last_run" type="text" />
        </div>
        <div class="field">
          <label>描述</label>
          <input v-model="editForm.description" type="text" />
        </div>
        <div class="field">
          <label>分组</label>
          <input v-model="editForm.groups" type="text" placeholder="例如: operations, core" />
        </div>
        <div class="button-row">
          <button class="primary" type="submit" :disabled="saving">
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
        </div>
      </form>
      <p v-if="saveError" class="state error">{{ saveError }}</p>
      <p v-if="saveSuccess" class="state success">{{ saveSuccess }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAgent, updateAgent, type AgentDetail } from '../api/agents'

const route = useRoute()
const router = useRouter()

const agent = ref<AgentDetail | null>(null)
const loading = ref(false)
const error = ref('')
const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref('')

const editForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  last_run: '',
  description: '',
  groups: '',
})

const formatTime = (value: string) => {
  return value.replace('T', ' ').replace('Z', '')
}

const loadAgent = async (id: string) => {
  loading.value = true
  error.value = ''
  try {
    agent.value = await fetchAgent(id)
    if (agent.value) {
      editForm.value = {
        name: agent.value.name,
        url: agent.value.url,
        owner: agent.value.owner,
        status: agent.value.status,
        last_run: agent.value.last_run,
        description: agent.value.description,
        groups: agent.value.groups?.join(',') || '',
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

const toggleEdit = () => {
  editing.value = !editing.value
  saveError.value = ''
  saveSuccess.value = ''
}

const handleUpdate = async () => {
  if (!agent.value) return
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await updateAgent(agent.value.id, {
      name: editForm.value.name,
      url: editForm.value.url,
      owner: editForm.value.owner,
      status: editForm.value.status,
      last_run: editForm.value.last_run,
      description: editForm.value.description,
      groups: editForm.value.groups
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    saveSuccess.value = '智能体已更新。'
    await loadAgent(agent.value.id)
    editing.value = false
  } catch (err) {
    saveError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    saving.value = false
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

<style scoped>
.section {
  display: grid;
  gap: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.state {
  font-size: 14px;
  color: #5a6a70;
}

.state.error {
  color: #b13333;
}

.detail {
  display: grid;
  gap: 20px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 20px;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.tag-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.detail-header h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 26px;
  margin: 0 0 6px;
}

.detail-header p {
  margin: 0;
  color: #4b5b60;
}

.meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  font-size: 14px;
}

.label {
  display: block;
  font-size: 12px;
  color: #6a7a80;
  margin-bottom: 4px;
}

.link {
  color: #0c7e85;
  text-decoration: none;
  font-weight: 600;
}

.link:hover {
  text-decoration: underline;
}

.chips {
  display: grid;
  gap: 16px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  font-size: 12px;
}

.chip-muted {
  background: rgba(255, 127, 80, 0.16);
  color: #b24724;
}

.tag {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
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

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.panel {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
  gap: 10px;
}
</style>
