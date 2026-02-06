<template>
  <div class="section">
    <div class="section-header">
      <button class="ghost" type="button" @click="goBack">返回列表</button>
      <button class="primary" type="button" @click="toggleEdit">
        {{ editing ? '取消编辑' : '编辑模型' }}
      </button>
    </div>

    <div v-if="loading" class="state">加载详情中...</div>
    <div v-if="error" class="state error">{{ error }}</div>

    <div v-if="model" class="detail">
      <div class="detail-header">
        <div>
          <h2>{{ model.name }}</h2>
          <p>{{ model.description }}</p>
        </div>
        <span class="tag" :class="model.status">{{ model.status }}</span>
      </div>

      <div class="meta">
        <div>
          <span class="label">Provider</span>
          <span>{{ model.provider }}</span>
        </div>
        <div>
          <span class="label">Context length</span>
          <span>{{ model.context_length.toLocaleString() }}</span>
        </div>
        <div>
          <span class="label">Release</span>
          <span>{{ model.release }}</span>
        </div>
        <div>
          <span class="label">Pricing</span>
          <span>{{ model.pricing }}</span>
        </div>
      </div>

      <div>
        <span class="label">Tags</span>
        <div class="chip-row">
          <span v-for="tag in model.tags" :key="tag" class="chip">{{ tag }}</span>
        </div>
      </div>
    </div>

    <div v-if="model && editing" class="panel edit-panel">
      <form class="form" @submit.prevent="handleUpdate">
        <div class="field">
          <label>模型名称</label>
          <input v-model="editForm.name" type="text" required />
        </div>
        <div class="field">
          <label>Provider</label>
          <input v-model="editForm.provider" type="text" />
        </div>
        <div class="field">
          <label>状态</label>
          <select v-model="editForm.status">
            <option value="enabled">enabled</option>
            <option value="disabled">disabled</option>
          </select>
        </div>
        <div class="field">
          <label>上下文长度</label>
          <input v-model.number="editForm.context_length" type="number" min="0" />
        </div>
        <div class="field">
          <label>描述</label>
          <input v-model="editForm.description" type="text" />
        </div>
        <div class="field">
          <label>价格</label>
          <input v-model="editForm.pricing" type="text" />
        </div>
        <div class="field">
          <label>版本</label>
          <input v-model="editForm.release" type="text" />
        </div>
        <div class="field">
          <label>标签</label>
          <input v-model="editForm.tags" type="text" placeholder="tag1,tag2" />
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
import { fetchModel, updateModel, type ModelDetail } from '../../services/models'

const route = useRoute()
const router = useRouter()

const model = ref<ModelDetail | null>(null)
const loading = ref(false)
const error = ref('')
const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref('')

const editForm = ref({
  name: '',
  provider: '',
  status: 'enabled',
  context_length: 0,
  description: '',
  pricing: '',
  release: '',
  tags: '',
})

const loadModel = async (id: string) => {
  loading.value = true
  error.value = ''
  try {
    model.value = await fetchModel(id)
    if (model.value) {
      editForm.value = {
        name: model.value.name,
        provider: model.value.provider,
        status: model.value.status,
        context_length: model.value.context_length,
        description: model.value.description,
        pricing: model.value.pricing,
        release: model.value.release,
        tags: model.value.tags.join(','),
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
  if (!model.value) return
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await updateModel(model.value.id, {
      name: editForm.value.name,
      provider: editForm.value.provider,
      status: editForm.value.status,
      context_length: editForm.value.context_length,
      description: editForm.value.description,
      pricing: editForm.value.pricing,
      release: editForm.value.release,
      tags: editForm.value.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    saveSuccess.value = '模型已更新。'
    await loadModel(model.value.id)
    editing.value = false
  } catch (err) {
    saveError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    saving.value = false
  }
}

const goBack = async () => {
  await router.push({ name: 'home-models' })
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') {
      loadModel(id)
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

.tag {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
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
