<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>模型管理</h2>
        <p>在系统管理中维护模型基础信息与高级参数。</p>
      </div>
      <button class="primary" type="button" :disabled="!isAdmin" @click="openCreateModel">
        新增模型
      </button>
    </div>

    <p v-if="!isAdmin" class="state">仅管理员可新增、编辑和删除模型。</p>
    <p v-if="error" class="state error">{{ error }}</p>
    <p v-if="saveSuccess" class="state success">{{ saveSuccess }}</p>
    <p v-if="deleteError" class="state error">{{ deleteError }}</p>

    <div v-if="loading" class="state">加载模型中...</div>
    <div v-else class="model-grid">
      <article v-for="item in models" :key="item.id" class="model-card">
        <header class="model-card-header">
          <h3>{{ item.name }}</h3>
          <span class="status-chip" :class="item.status">{{ item.status }}</span>
        </header>
        <p class="model-card-desc">{{ item.description || '暂无描述' }}</p>
        <div class="model-card-meta">
          <span>类型：{{ item.model_type || 'llm' }}</span>
          <span>基础模型：{{ item.base_model || '-' }}</span>
          <span>Provider：{{ item.provider || '-' }}</span>
        </div>
        <div class="model-card-actions">
          <button class="ghost" type="button" :disabled="!isAdmin" @click="openEditModel(item.id)">编辑</button>
          <button class="ghost danger" type="button" :disabled="!isAdmin" @click="openDeleteModel(item)">
            删除
          </button>
        </div>
      </article>
      <p v-if="!models.length" class="state">暂无模型数据</p>
    </div>
  </div>

  <div v-if="showEditor" class="modal-backdrop">
    <div class="editor-modal">
      <header class="editor-header">
        <h3>{{ editingModelId ? '编辑模型' : '新增模型' }}</h3>
        <button class="modal-close" type="button" @click="closeEditor">✕</button>
      </header>

      <div class="editor-tabs">
        <button class="tab" :class="{ active: activeTab === 'basic' }" type="button" @click="activeTab = 'basic'">
          基础信息
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'advanced' }"
          type="button"
          @click="activeTab = 'advanced'"
        >
          高级设置
        </button>
      </div>

      <div v-if="activeTab === 'basic'" class="form basic-form">
        <div class="field">
          <label>模型名称</label>
          <input v-model="modelForm.name" type="text" placeholder="请输入模型名称" />
        </div>
        <div class="field">
          <label>模型类型</label>
          <select v-model="modelForm.model_type">
            <option value="llm">大语言模型</option>
            <option value="embedding">向量模型</option>
            <option value="rerank">重排模型</option>
            <option value="vision">视觉模型</option>
          </select>
        </div>
        <div class="field">
          <label>基础模型</label>
          <input v-model="modelForm.base_model" type="text" placeholder="例如 gpt-4o" />
        </div>
        <div class="field">
          <label>Provider</label>
          <input v-model="modelForm.provider" type="text" placeholder="例如 OpenAI" />
        </div>
        <div class="field">
          <label>API URL</label>
          <input v-model="modelForm.api_url" type="text" placeholder="https://api.example.com/v1" />
        </div>
        <div class="field">
          <label>API Key</label>
          <input
            v-model="modelForm.api_key"
            type="password"
            :placeholder="editingModelId ? '留空则不修改' : '请输入 API Key'"
          />
          <small v-if="editingModelId && apiKeyMasked">当前：{{ apiKeyMasked }}</small>
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
          <input v-model="modelForm.tags" type="text" placeholder="tag1,tag2" />
        </div>
      </div>

      <div v-else class="advanced-panel">
        <div class="advanced-header">
          <h4>模型参数</h4>
          <button class="ghost" type="button" @click="openAddParameter">添加参数</button>
        </div>
        <table class="parameter-table">
          <thead>
            <tr>
              <th>显示名称</th>
              <th>参数</th>
              <th>组件类型</th>
              <th>默认值</th>
              <th>必填</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in modelForm.parameters" :key="`${item.key}-${index}`">
              <td>{{ item.label }}</td>
              <td>{{ item.key }}</td>
              <td>{{ item.component_type }}</td>
              <td>{{ item.default_value || '-' }}</td>
              <td>{{ item.required ? '是' : '否' }}</td>
              <td class="table-actions">
                <button class="link-btn" type="button" @click="openEditParameter(index)">编辑</button>
                <button class="link-btn danger" type="button" @click="removeParameter(index)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!modelForm.parameters.length" class="state">暂无参数，点击“添加参数”创建。</p>
      </div>

      <p v-if="saveError" class="state error">{{ saveError }}</p>
      <div class="editor-actions">
        <button class="ghost" type="button" @click="closeEditor">取消</button>
        <button class="primary" type="button" :disabled="saveLoading || !isAdmin" @click="saveModel">
          {{ saveLoading ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div v-if="showParameterDrawer" class="drawer-backdrop" @click.self="closeParameterDrawer">
      <div class="drawer-card">
        <header class="drawer-header">
          <h4>{{ editingParameterIndex === null ? '添加参数' : '编辑参数' }}</h4>
          <button class="modal-close" type="button" @click="closeParameterDrawer">✕</button>
        </header>
        <div class="form drawer-form">
          <div class="field">
            <label>参数</label>
            <input v-model="parameterForm.key" type="text" placeholder="请输入参数名" />
          </div>
          <div class="field">
            <label>显示名称</label>
            <input v-model="parameterForm.label" type="text" placeholder="请输入显示名称" />
          </div>
          <div class="field">
            <label>参数提示说明</label>
            <input v-model="parameterForm.hint" type="text" placeholder="请输入参数提示说明" />
          </div>
          <div class="field">
            <label>组件类型</label>
            <select v-model="parameterForm.component_type">
              <option value="input">输入框</option>
              <option value="slider">滑块</option>
              <option value="select">下拉框</option>
              <option value="switch">开关</option>
            </select>
          </div>
          <div class="field">
            <label>默认值</label>
            <input v-model="parameterForm.default_value" type="text" placeholder="请输入默认值" />
          </div>
          <label class="required-line">
            <input v-model="parameterForm.required" type="checkbox" />
            <span>是否必填</span>
          </label>
        </div>
        <div class="editor-actions">
          <button class="ghost" type="button" @click="closeParameterDrawer">取消</button>
          <button class="primary" type="button" @click="saveParameter">保存参数</button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="showDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除模型</h3>
        <button class="modal-close" type="button" @click="closeDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ deleteTarget?.name }}</strong> 吗？该模型的资源权限数据将一并删除。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="deleteLoading" @click="confirmDeleteModel">
          {{ deleteLoading ? '处理中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createModel,
  deleteModel,
  fetchModel,
  fetchModels,
  updateModel,
  type ModelDetail,
  type ModelParameterItem,
  type ModelSummary,
} from '../../../services/models'
import { getCurrentRole } from '../../../services/session'

const roleLocal = ref(getCurrentRole())
const isAdmin = computed(() => roleLocal.value === 'admin')

const models = ref<ModelSummary[]>([])
const loading = ref(false)
const error = ref('')
const saveLoading = ref(false)
const saveError = ref('')
const saveSuccess = ref('')
const deleteError = ref('')

const showEditor = ref(false)
const editingModelId = ref('')
const activeTab = ref<'basic' | 'advanced'>('basic')
const apiKeyMasked = ref('')

const showDeleteModal = ref(false)
const deleteTarget = ref<ModelSummary | null>(null)
const deleteLoading = ref(false)

const showParameterDrawer = ref(false)
const editingParameterIndex = ref<number | null>(null)

const modelForm = reactive({
  id: '',
  name: '',
  provider: '',
  model_type: 'llm',
  base_model: '',
  api_url: '',
  api_key: '',
  status: 'enabled',
  context_length: 0,
  description: '',
  pricing: '',
  release: '',
  tags: '',
  parameters: [] as ModelParameterItem[],
})

const parameterForm = reactive<ModelParameterItem>({
  key: '',
  label: '',
  hint: '',
  required: false,
  component_type: 'input',
  default_value: '',
})

const resetModelForm = () => {
  modelForm.id = ''
  modelForm.name = ''
  modelForm.provider = ''
  modelForm.model_type = 'llm'
  modelForm.base_model = ''
  modelForm.api_url = ''
  modelForm.api_key = ''
  modelForm.status = 'enabled'
  modelForm.context_length = 0
  modelForm.description = ''
  modelForm.pricing = ''
  modelForm.release = ''
  modelForm.tags = ''
  modelForm.parameters = []
}

const resetParameterForm = () => {
  parameterForm.key = ''
  parameterForm.label = ''
  parameterForm.hint = ''
  parameterForm.required = false
  parameterForm.component_type = 'input'
  parameterForm.default_value = ''
}

const loadModels = async () => {
  loading.value = true
  error.value = ''
  try {
    models.value = await fetchModels()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载模型失败'
    models.value = []
  } finally {
    loading.value = false
  }
}

const openCreateModel = () => {
  if (!isAdmin.value) {
    return
  }
  saveError.value = ''
  saveSuccess.value = ''
  editingModelId.value = ''
  apiKeyMasked.value = ''
  activeTab.value = 'basic'
  resetModelForm()
  showEditor.value = true
}

const fillModelFormFromDetail = (detail: ModelDetail) => {
  modelForm.id = detail.id
  modelForm.name = detail.name
  modelForm.provider = detail.provider
  modelForm.model_type = detail.model_type || 'llm'
  modelForm.base_model = detail.base_model || ''
  modelForm.api_url = detail.api_url || ''
  modelForm.api_key = ''
  modelForm.status = detail.status || 'enabled'
  modelForm.context_length = Number(detail.context_length || 0)
  modelForm.description = detail.description || ''
  modelForm.pricing = detail.pricing || ''
  modelForm.release = detail.release || ''
  modelForm.tags = (detail.tags || []).join(',')
  modelForm.parameters = (detail.parameters || []).map((item) => ({
    key: item.key,
    label: item.label,
    hint: item.hint || '',
    required: Boolean(item.required),
    component_type: item.component_type || 'input',
    default_value: item.default_value || '',
  }))
}

const openEditModel = async (id: string) => {
  if (!isAdmin.value) {
    return
  }
  saveError.value = ''
  saveSuccess.value = ''
  try {
    const detail = await fetchModel(id)
    fillModelFormFromDetail(detail)
    editingModelId.value = id
    apiKeyMasked.value = detail.api_key_masked || ''
    activeTab.value = 'basic'
    showEditor.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载模型详情失败'
  }
}

const closeEditor = () => {
  showEditor.value = false
  activeTab.value = 'basic'
  editingModelId.value = ''
  apiKeyMasked.value = ''
  saveError.value = ''
  resetModelForm()
  resetParameterForm()
  showParameterDrawer.value = false
  editingParameterIndex.value = null
}

const openAddParameter = () => {
  editingParameterIndex.value = null
  resetParameterForm()
  showParameterDrawer.value = true
}

const openEditParameter = (index: number) => {
  const item = modelForm.parameters[index]
  if (!item) return
  editingParameterIndex.value = index
  parameterForm.key = item.key
  parameterForm.label = item.label
  parameterForm.hint = item.hint
  parameterForm.required = item.required
  parameterForm.component_type = item.component_type
  parameterForm.default_value = item.default_value
  showParameterDrawer.value = true
}

const removeParameter = (index: number) => {
  modelForm.parameters = modelForm.parameters.filter((_item, itemIndex) => itemIndex !== index)
}

const closeParameterDrawer = () => {
  showParameterDrawer.value = false
  editingParameterIndex.value = null
  resetParameterForm()
}

const saveParameter = () => {
  const key = parameterForm.key.trim()
  const label = parameterForm.label.trim()
  if (!key || !label) {
    saveError.value = '参数与显示名称不能为空。'
    return
  }
  const next: ModelParameterItem = {
    key,
    label,
    hint: parameterForm.hint.trim(),
    required: parameterForm.required,
    component_type: parameterForm.component_type || 'input',
    default_value: parameterForm.default_value.trim(),
  }
  if (editingParameterIndex.value === null) {
    modelForm.parameters = [...modelForm.parameters, next]
  } else {
    modelForm.parameters = modelForm.parameters.map((item, index) =>
      index === editingParameterIndex.value ? next : item
    )
  }
  closeParameterDrawer()
}

const buildTagList = (raw: string) =>
  raw
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

const saveModel = async () => {
  if (!isAdmin.value) {
    return
  }
  saveError.value = ''
  saveSuccess.value = ''

  const name = modelForm.name.trim()
  const apiUrl = modelForm.api_url.trim()
  const apiKey = modelForm.api_key.trim()
  if (!name) {
    saveError.value = '模型名称不能为空。'
    activeTab.value = 'basic'
    return
  }
  if (!apiUrl) {
    saveError.value = 'API URL 不能为空。'
    activeTab.value = 'basic'
    return
  }
  if (!editingModelId.value && !apiKey) {
    saveError.value = 'API Key 不能为空。'
    activeTab.value = 'basic'
    return
  }

  saveLoading.value = true
  try {
    const payload = {
      id: modelForm.id.trim() || undefined,
      name,
      provider: modelForm.provider.trim(),
      model_type: modelForm.model_type,
      base_model: modelForm.base_model.trim(),
      api_url: apiUrl,
      status: modelForm.status,
      context_length: Number(modelForm.context_length || 0),
      description: modelForm.description.trim(),
      pricing: modelForm.pricing.trim(),
      release: modelForm.release.trim(),
      tags: buildTagList(modelForm.tags),
      parameters: modelForm.parameters.map((item) => ({ ...item })),
    }
    if (editingModelId.value) {
      await updateModel(editingModelId.value, {
        ...payload,
        api_key: apiKey || undefined,
      })
      saveSuccess.value = '模型已更新。'
    } else {
      await createModel({
        ...payload,
        api_key: apiKey,
      })
      saveSuccess.value = '模型已创建。'
    }
    await loadModels()
    closeEditor()
  } catch (err) {
    saveError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    saveLoading.value = false
  }
}

const openDeleteModel = (item: ModelSummary) => {
  if (!isAdmin.value) {
    return
  }
  deleteError.value = ''
  deleteTarget.value = item
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  deleteTarget.value = null
}

const confirmDeleteModel = async () => {
  if (!deleteTarget.value) return
  deleteLoading.value = true
  deleteError.value = ''
  try {
    await deleteModel(deleteTarget.value.id)
    closeDeleteModal()
    await loadModels()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : '删除模型失败'
  } finally {
    deleteLoading.value = false
  }
}

onMounted(loadModels)
</script>

<style scoped src="./ModelManagementModule.css"></style>
