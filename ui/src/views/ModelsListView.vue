<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>模型</h2>
        <p>查看模型能力、成本与推理指标。</p>
      </div>
      <button class="ghost" type="button">新建模型配置</button>
    </div>

    <div v-if="loading" class="state">加载模型列表中...</div>
    <div v-if="error" class="state error">{{ error }}</div>

    <div v-if="!loading" class="grid">
      <button
        v-for="model in models"
        :key="model.id"
        class="card"
        type="button"
        @click="goDetail(model.id)"
      >
        <div>
          <div class="card-title">
            <h3>{{ model.name }}</h3>
            <span class="tag" :class="model.status">{{ model.status }}</span>
          </div>
          <p>{{ model.description }}</p>
        </div>
        <div class="card-meta">
          <span>Provider: {{ model.provider }}</span>
          <span>Context: {{ model.context_length.toLocaleString() }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchModels, type ModelSummary } from '../api'

const router = useRouter()

const models = ref<ModelSummary[]>([])
const loading = ref(false)
const error = ref('')

const goDetail = async (id: string) => {
  await router.push({ name: 'home-model-detail', params: { id } })
}

const loadModels = async () => {
  loading.value = true
  error.value = ''
  try {
    models.value = await fetchModels()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadModels)
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

.card-meta {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #6a7a80;
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

.tag.disabled {
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
