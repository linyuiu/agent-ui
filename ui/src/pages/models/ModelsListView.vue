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
import { parseCommaSeparated } from '../../utils/text-format'

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
      tags: parseCommaSeparated(modelForm.value.tags),
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

<style scoped src="./ModelsListView.css"></style>
