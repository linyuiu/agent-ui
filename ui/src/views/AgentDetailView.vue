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
        <span class="tag" :class="agent.status">{{ agent.status }}</span>
      </div>

      <div class="meta">
        <div>
          <span class="label">Owner</span>
          <span>{{ agent.owner }}</span>
        </div>
        <div>
          <span class="label">Last run</span>
          <span>{{ formatTime(agent.last_run) }}</span>
        </div>
      </div>

      <div class="chips">
        <div>
          <span class="label">Tools</span>
          <div class="chip-row">
            <span v-for="tool in agent.tools" :key="tool" class="chip">{{ tool }}</span>
          </div>
        </div>
        <div>
          <span class="label">Tags</span>
          <div class="chip-row">
            <span v-for="tag in agent.tags" :key="tag" class="chip chip-muted">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAgent, type AgentDetail } from '../api'

const route = useRoute()
const router = useRouter()

const agent = ref<AgentDetail | null>(null)
const loading = ref(false)
const error = ref('')

const formatTime = (value: string) => {
  return value.replace('T', ' ').replace('Z', '')
}

const loadAgent = async (id: string) => {
  loading.value = true
  error.value = ''
  try {
    agent.value = await fetchAgent(id)
  } catch (err) {
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

<style scoped>
.section {
  display: grid;
  gap: 20px;
}

.section-header {
  display: flex;
  justify-content: flex-start;
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
