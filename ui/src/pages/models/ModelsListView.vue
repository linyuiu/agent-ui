<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>模型</h2>
        <p>查看模型能力、成本与推理指标。</p>
        <div class="meta-line">
          <span class="count-pill">总数 {{ totalCount }}</span>
          <span class="count-pill">启用 {{ enabledCount }}</span>
        </div>
      </div>
      <button class="ghost" type="button" @click="showCreate = !showCreate">
        {{ showCreate ? '关闭创建' : '新建模型配置' }}
      </button>
    </div>

    <div v-if="showCreate" class="panel">
      <form class="form" @submit.prevent="handleCreateModel">
        <div class="field">
          <label>模型 ID</label>
          <input v-model="modelForm.id" type="text" placeholder="model-001" required />
        </div>
        <div class="field">
          <label>模型名称</label>
          <input v-model="modelForm.name" type="text" placeholder="Reasoning Pro" required />
        </div>
        <div class="field">
          <label>Provider</label>
          <input v-model="modelForm.provider" type="text" placeholder="OpenAI" />
        </div>
        <div class="field">
          <label>状态</label>
          <select v-model="modelForm.status">
            <option value="enabled">enabled</option>
            <option value="disabled">disabled</option>
          </select>
        </div>
        <div class="field">
          <label>上下文长度</label>
          <input v-model.number="modelForm.context_length" type="number" min="0" />
        </div>
        <div class="field">
          <label>描述</label>
          <input v-model="modelForm.description" type="text" placeholder="简短描述" />
        </div>
        <div class="field">
          <label>价格</label>
          <input v-model="modelForm.pricing" type="text" placeholder="$0.00" />
        </div>
        <div class="field">
          <label>版本</label>
          <input v-model="modelForm.release" type="text" placeholder="2026-02" />
        </div>
        <div class="field">
          <label>标签</label>
          <input v-model="modelForm.tags" type="text" placeholder="fast,accurate" />
        </div>
        <div class="button-row">
          <button class="primary" type="submit" :disabled="createLoading">
            {{ createLoading ? '保存中...' : '保存模型' }}
          </button>
          <button class="ghost" type="button" :disabled="seedLoading" @click="handleSeedModels">
            {{ seedLoading ? '填充中...' : '填充示例模型' }}
          </button>
        </div>
      </form>

      <p v-if="createError" class="state error">{{ createError }}</p>
      <p v-if="createSuccess" class="state success">{{ createSuccess }}</p>
      <p v-if="seedSuccess" class="state success">{{ seedSuccess }}</p>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createModel, fetchModels, type ModelSummary } from '../../services/models'

const router = useRouter()

const models = ref<ModelSummary[]>([])
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const createLoading = ref(false)
const createError = ref('')
const createSuccess = ref('')
const seedLoading = ref(false)
const seedSuccess = ref('')

const modelForm = ref({
  id: '',
  name: '',
  provider: '',
  status: 'enabled',
  context_length: 0,
  description: '',
  pricing: '',
  release: '',
  tags: '',
})

const totalCount = computed(() => models.value.length)
const enabledCount = computed(() => models.value.filter((model) => model.status === 'enabled').length)

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

const handleCreateModel = async () => {
  createLoading.value = true
  createError.value = ''
  createSuccess.value = ''

  try {
    await createModel({
      id: modelForm.value.id,
      name: modelForm.value.name,
      provider: modelForm.value.provider,
      status: modelForm.value.status,
      context_length: modelForm.value.context_length,
      description: modelForm.value.description,
      pricing: modelForm.value.pricing,
      release: modelForm.value.release,
      tags: modelForm.value.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    createSuccess.value = '模型已保存。'
    modelForm.value = {
      id: '',
      name: '',
      provider: '',
      status: 'enabled',
      context_length: 0,
      description: '',
      pricing: '',
      release: '',
      tags: '',
    }
    await loadModels()
  } catch (err) {
    createError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    createLoading.value = false
  }
}

const handleSeedModels = async () => {
  seedLoading.value = true
  seedSuccess.value = ''
  createError.value = ''

  const samples = [
    {
      id: 'model-core',
      name: 'Core LLM',
      provider: 'OpenAI',
      status: 'enabled',
      context_length: 128000,
      description: '主力模型，用于通用任务。',
      pricing: '$0.00 demo',
      release: '2026-02',
      tags: ['multimodal', 'fast'],
    },
    {
      id: 'model-reason',
      name: 'Reasoning Pro',
      provider: 'OpenAI',
      status: 'enabled',
      context_length: 64000,
      description: '推理能力更强的模型。',
      pricing: '$0.00 demo',
      release: '2026-01',
      tags: ['analysis', 'accurate'],
    },
    {
      id: 'model-light',
      name: 'Fast Lite',
      provider: 'OpenAI',
      status: 'disabled',
      context_length: 32000,
      description: '低延迟模型，用于轻量任务。',
      pricing: '$0.00 demo',
      release: '2025-11',
      tags: ['cheap', 'fast'],
    },
  ]

  try {
    for (const sample of samples) {
      try {
        await createModel(sample)
      } catch (err) {
        const message = err instanceof Error ? err.message : ''
        if (!message.includes('already exists')) {
          throw err
        }
      }
    }
    seedSuccess.value = '示例模型已填充。'
    await loadModels()
  } catch (err) {
    createError.value = err instanceof Error ? err.message : '填充失败'
  } finally {
    seedLoading.value = false
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

.meta-line {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.count-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  font-size: 12px;
  font-weight: 600;
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
  height: 40px;
  box-sizing: border-box;
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
