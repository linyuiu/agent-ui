<template>
  <div class="admin">
    <div class="section">
      <div class="section-header">
        <div>
          <h2>权限策略</h2>
          <p>使用 ABAC 规则控制菜单与资源访问。</p>
        </div>
      </div>

      <div class="panel">
        <form class="form" @submit.prevent="handleCreatePolicy">
          <div class="field">
            <label>策略名称</label>
            <input v-model="policyForm.name" type="text" placeholder="例如: 允许运营查看智能体" required />
          </div>
          <div class="field">
            <label>效力</label>
            <select v-model="policyForm.effect">
              <option value="allow">allow</option>
              <option value="deny">deny</option>
            </select>
          </div>
          <div class="field">
            <label>动作</label>
            <input v-model="policyForm.actions" type="text" placeholder="view,manage" />
          </div>
          <div class="field">
            <label>资源类型</label>
            <select v-model="policyForm.resource_type">
              <option value="menu">menu</option>
              <option value="agent">agent</option>
              <option value="model">model</option>
            </select>
          </div>
          <div class="field">
            <label>资源 ID (可选)</label>
            <input v-model="policyForm.resource_id" type="text" placeholder="例如: agents / model-001" />
          </div>
          <div class="field">
            <label>用户角色 (可选)</label>
            <input v-model="policyForm.role" type="text" placeholder="admin / ops" />
          </div>
          <div class="field">
            <label>用户邮箱 (可选)</label>
            <input v-model="policyForm.email" type="text" placeholder="user@example.com" />
          </div>
          <div class="field">
            <label>资源标签 (可选)</label>
            <input v-model="policyForm.tags" type="text" placeholder="tag1,tag2" />
          </div>
          <div class="field">
            <label>资源状态 (可选)</label>
            <input v-model="policyForm.status" type="text" placeholder="active / enabled" />
          </div>
          <div class="field">
            <label>资源负责人 (可选)</label>
            <input v-model="policyForm.owner" type="text" placeholder="Operations" />
          </div>
          <div class="field field-inline">
            <label>
              <input v-model="policyForm.enabled" type="checkbox" />
              启用策略
            </label>
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="policyLoading">
              {{ policyLoading ? '保存中...' : editingPolicyId ? '更新策略' : '保存策略' }}
            </button>
            <button
              v-if="editingPolicyId"
              class="ghost"
              type="button"
              @click="resetPolicyForm"
            >
              取消编辑
            </button>
          </div>
        </form>

        <p v-if="policyError" class="state error">{{ policyError }}</p>
      </div>

      <div class="policy-list">
        <div v-if="policiesLoading" class="state">加载策略中...</div>
        <div v-if="policiesError" class="state error">{{ policiesError }}</div>

        <div v-if="policies.length" class="grid">
          <div v-for="policy in policies" :key="policy.id" class="policy-card">
            <div>
              <h3>{{ policy.name }}</h3>
              <p>{{ policy.effect }} | {{ policy.actions.join(', ') }}</p>
            </div>
            <div class="policy-meta">
              <span>资源: {{ policy.resource_type }} {{ policy.resource_id || '*' }}</span>
              <span>条件: {{ formatAttrs(policy.subject_attrs) }}</span>
            </div>
            <div class="policy-actions">
              <button class="ghost" type="button" @click="handleEditPolicy(policy)">编辑</button>
              <button class="ghost" type="button" @click="handleCopyPolicy(policy)">复制</button>
              <button class="ghost danger" type="button" @click="handleDeletePolicy(policy)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>智能体接入</h2>
          <p>填写 API 地址与 AK/SK，拉取并保存智能体数据。</p>
        </div>
      </div>

      <div class="panel">
        <form class="form" @submit.prevent="handleImport">
          <div class="field">
            <label>API 地址</label>
            <input v-model="importForm.api_url" type="text" placeholder="https://api.example.com/agents" required />
          </div>
          <div class="field">
            <label>AK</label>
            <input v-model="importForm.ak" type="text" placeholder="access key" required />
          </div>
          <div class="field">
            <label>SK</label>
            <input v-model="importForm.sk" type="password" placeholder="secret key" required />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="importLoading">
              {{ importLoading ? '拉取中...' : '拉取并保存' }}
            </button>
            <button class="ghost" type="button" @click="handleUseSampleImport">填充示例</button>
            <button class="ghost" type="button" @click="handleImportSample">一键导入示例</button>
          </div>
        </form>

        <p v-if="importError" class="state error">{{ importError }}</p>
        <p v-if="importSuccess" class="state success">{{ importSuccess }}</p>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>模型配置</h2>
          <p>新增模型并用于授权。</p>
        </div>
      </div>

      <div class="panel">
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
            <button class="primary" type="submit" :disabled="modelLoading">
              {{ modelLoading ? '保存中...' : '保存模型' }}
            </button>
            <button class="ghost" type="button" :disabled="modelSeedLoading" @click="handleSeedModels">
              {{ modelSeedLoading ? '填充中...' : '填充示例模型' }}
            </button>
          </div>
        </form>

        <p v-if="modelError" class="state error">{{ modelError }}</p>
        <p v-if="modelSuccess" class="state success">{{ modelSuccess }}</p>
        <p v-if="modelSeedSuccess" class="state success">{{ modelSeedSuccess }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createModel,
  createPolicy,
  deletePolicy,
  fetchPolicies,
  importAgents,
  updatePolicy,
  type Policy,
} from '../api'

const policies = ref<Policy[]>([])
const policiesLoading = ref(false)
const policiesError = ref('')

const policyLoading = ref(false)
const policyError = ref('')
const editingPolicyId = ref<number | null>(null)

const importLoading = ref(false)
const importError = ref('')
const importSuccess = ref('')

const modelLoading = ref(false)
const modelError = ref('')
const modelSuccess = ref('')
const modelSeedLoading = ref(false)
const modelSeedSuccess = ref('')

const policyForm = ref({
  name: '',
  effect: 'allow',
  actions: 'view',
  resource_type: 'menu',
  resource_id: '',
  role: '',
  email: '',
  tags: '',
  status: '',
  owner: '',
  enabled: true,
})

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

const sampleImport = {
  api_url: 'http://localhost:8000/demo/agents',
  ak: 'demo-ak',
  sk: 'demo-sk',
}

const importForm = ref({
  api_url: sampleImport.api_url,
  ak: sampleImport.ak,
  sk: sampleImport.sk,
})

const resetPolicyForm = () => {
  policyForm.value = {
    name: '',
    effect: 'allow',
    actions: 'view',
    resource_type: 'menu',
    resource_id: '',
    role: '',
    email: '',
    tags: '',
    status: '',
    owner: '',
    enabled: true,
  }
  editingPolicyId.value = null
}

const formatAttrs = (attrs: Record<string, unknown>) => {
  const entries = Object.entries(attrs)
  if (!entries.length) return '无'
  return entries
    .map(([key, value]) => `${key}:${Array.isArray(value) ? value.join('|') : String(value)}`)
    .join(', ')
}

const loadPolicies = async () => {
  policiesLoading.value = true
  policiesError.value = ''
  try {
    policies.value = await fetchPolicies()
  } catch (err) {
    policiesError.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    policiesLoading.value = false
  }
}

const handleCreatePolicy = async () => {
  policyLoading.value = true
  policyError.value = ''

  const actions = policyForm.value.actions
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  const subject_attrs: Record<string, unknown> = {}
  if (policyForm.value.role) subject_attrs.role = policyForm.value.role
  if (policyForm.value.email) subject_attrs.email = policyForm.value.email

  const resource_attrs: Record<string, unknown> = {}
  if (policyForm.value.tags) {
    resource_attrs.tags = policyForm.value.tags
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }
  if (policyForm.value.status) resource_attrs.status = policyForm.value.status
  if (policyForm.value.owner) resource_attrs.owner = policyForm.value.owner

  try {
    const payload = {
      name: policyForm.value.name,
      effect: policyForm.value.effect,
      actions,
      resource_type: policyForm.value.resource_type,
      resource_id: policyForm.value.resource_id || null,
      subject_attrs,
      resource_attrs,
      enabled: policyForm.value.enabled,
    }

    if (editingPolicyId.value) {
      await updatePolicy(editingPolicyId.value, payload)
    } else {
      await createPolicy(payload)
    }

    resetPolicyForm()

    await loadPolicies()
  } catch (err) {
    policyError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    policyLoading.value = false
  }
}

const handleEditPolicy = (policy: Policy) => {
  policyForm.value = {
    name: policy.name,
    effect: policy.effect,
    actions: policy.actions.join(', '),
    resource_type: policy.resource_type,
    resource_id: policy.resource_id || '',
    role: String(policy.subject_attrs?.role || ''),
    email: String(policy.subject_attrs?.email || ''),
    tags: Array.isArray(policy.resource_attrs?.tags)
      ? policy.resource_attrs.tags.join(', ')
      : '',
    status: String(policy.resource_attrs?.status || ''),
    owner: String(policy.resource_attrs?.owner || ''),
    enabled: policy.enabled,
  }
  editingPolicyId.value = policy.id
}

const handleCopyPolicy = async (policy: Policy) => {
  try {
    await createPolicy({
      name: `${policy.name} 副本`,
      effect: policy.effect,
      actions: policy.actions,
      resource_type: policy.resource_type,
      resource_id: policy.resource_id,
      subject_attrs: policy.subject_attrs,
      resource_attrs: policy.resource_attrs,
      enabled: policy.enabled,
    })
    await loadPolicies()
  } catch (err) {
    policyError.value = err instanceof Error ? err.message : '复制失败'
  }
}

const handleDeletePolicy = async (policy: Policy) => {
  const confirmed = window.confirm(`确认删除策略「${policy.name}」吗？`)
  if (!confirmed) return

  try {
    await deletePolicy(policy.id)
    if (editingPolicyId.value === policy.id) {
      resetPolicyForm()
    }
    await loadPolicies()
  } catch (err) {
    policyError.value = err instanceof Error ? err.message : '删除失败'
  }
}

const handleImport = async () => {
  importLoading.value = true
  importError.value = ''
  importSuccess.value = ''

  try {
    const result = await importAgents(importForm.value)
    importSuccess.value = `成功导入 ${result.imported} 条智能体数据。`
  } catch (err) {
    importError.value = err instanceof Error ? err.message : '导入失败'
  } finally {
    importLoading.value = false
  }
}

const handleCreateModel = async () => {
  modelLoading.value = true
  modelError.value = ''
  modelSuccess.value = ''

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

    modelSuccess.value = '模型已保存。'
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
  } catch (err) {
    modelError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    modelLoading.value = false
  }
}

const handleUseSampleImport = () => {
  importForm.value = { ...sampleImport }
}

const handleImportSample = async () => {
  importForm.value = { ...sampleImport }
  await handleImport()
}

const handleSeedModels = async () => {
  modelSeedLoading.value = true
  modelSeedSuccess.value = ''
  modelError.value = ''

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
    modelSeedSuccess.value = '示例模型已填充。'
  } catch (err) {
    modelError.value = err instanceof Error ? err.message : '填充失败'
  } finally {
    modelSeedLoading.value = false
  }
}

onMounted(loadPolicies)
</script>

<style scoped>
.admin {
  display: grid;
  gap: 28px;
}

.section {
  display: grid;
  gap: 16px;
}

.section-header h2 {
  font-family: 'Space Grotesk', sans-serif;
  margin: 0 0 6px;
  font-size: 24px;
}

.section-header p {
  margin: 0;
  color: #4b5b60;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
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

.field-inline {
  align-items: center;
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

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost {
  border: 1px solid rgba(15, 179, 185, 0.4);
  color: #0c7e85;
  background: transparent;
  padding: 10px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}

.ghost:hover {
  background: rgba(15, 179, 185, 0.08);
}

.state {
  font-size: 13px;
  color: #5a6a70;
  margin-top: 8px;
}

.state.error {
  color: #b13333;
}

.state.success {
  color: #0f6b4f;
}

.policy-list {
  display: grid;
  gap: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.policy-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 14px;
  border: 1px solid rgba(15, 40, 55, 0.06);
  display: grid;
  gap: 8px;
}

.policy-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.policy-card p {
  margin: 0;
  color: #6a7a80;
  font-size: 12px;
}

.policy-meta {
  font-size: 12px;
  color: #5a6a70;
  display: grid;
  gap: 4px;
}

.policy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ghost.danger {
  border-color: rgba(255, 94, 94, 0.5);
  color: #b13333;
}
</style>
