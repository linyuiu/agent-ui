<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>智能体</h2>
        <p>管理不同任务的智能体实例与能力配置。</p>
        <div class="meta-line">
          <span class="count-pill">总数 {{ totalCount }}</span>
          <span class="count-pill">活跃 {{ activeCount }}</span>
        </div>
      </div>
      <div class="actions">
        <button class="ghost" type="button" @click="showCreate = !showCreate">
          {{ showCreate ? '关闭创建' : '新建智能体' }}
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
          <div class="inline-dropdown" @click.stop>
            <button class="filter-trigger inline-trigger" type="button" @click.stop="toggleStatusDropdown">
              <span>{{ agentForm.status }}</span>
              <span class="caret" :class="{ open: statusOpen }"></span>
            </button>
            <div v-if="statusOpen" class="filter-dropdown inline-dropdown-panel">
              <button class="filter-option" type="button" @click="setStatus('active')">
                active
              </button>
              <button class="filter-option" type="button" @click="setStatus('paused')">
                paused
              </button>
            </div>
          </div>
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
          <div class="combo-wrap" ref="groupDropdownRef">
            <div class="combo-input" @click="focusGroupInput">
              <template v-for="group in agentForm.groups" :key="group">
                <span class="chip">
                  {{ group }}
                  <button class="chip-remove" type="button" @click.stop="removeGroup(group)">
                    ×
                  </button>
                </span>
              </template>
              <input
                ref="groupInputRef"
                v-model="groupQuery"
                type="text"
                :placeholder="agentForm.groups.length ? '' : '输入或选择分组'"
                @focus="openGroupDropdown"
                @keydown.enter.prevent="handleGroupEnter"
              />
              <span v-if="agentForm.groups.length" class="combo-more">...</span>
              <span class="combo-caret" :class="{ open: groupDropdownOpen }"></span>
            </div>
            <div v-if="groupDropdownOpen" class="dropdown" @click.stop>
              <button
                v-for="group in filteredGroups"
                :key="group"
                type="button"
                class="dropdown-item"
                @click="selectGroup(group)"
              >
                <span>{{ group }}</span>
                <span class="dropdown-check">
                  <input type="checkbox" :checked="agentForm.groups.includes(group)" disabled />
                </span>
              </button>
              <p v-if="!filteredGroups.length" class="dropdown-empty">
                {{ groupQuery.trim() ? '按回车创建新分组' : '暂无可用分组' }}
              </p>
            </div>
          </div>
          <small v-if="groupCreateError" class="state error">{{ groupCreateError }}</small>
        </div>
        <div class="button-row action-row">
          <button class="primary" type="submit" :disabled="createLoading">
            {{ createLoading ? '创建中...' : '创建智能体' }}
          </button>
        </div>
      </form>

      <p v-if="createError" class="state error">{{ createError }}</p>
      <p v-if="createSuccess" class="state success">{{ createSuccess }}</p>
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
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createAgent, fetchAgents, type AgentSummary } from '../../services/agents'
import { createAgentGroup, fetchAgentGroups } from '../../services/groups'

const router = useRouter()

const agents = ref<AgentSummary[]>([])
const loading = ref(false)
const error = ref('')

const showCreate = ref(false)
 

const createLoading = ref(false)
const createError = ref('')
const createSuccess = ref('')

const groupOptions = ref<string[]>([])
const groupQuery = ref('')
const groupCreateLoading = ref(false)
const groupCreateError = ref('')
const groupDropdownOpen = ref(false)
const groupDropdownRef = ref<HTMLElement | null>(null)
const groupInputRef = ref<HTMLInputElement | null>(null)
const statusOpen = ref(false)

const agentForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  last_run: '',
  description: '',
  groups: [] as string[],
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
  groupCreateError.value = ''

  try {
    await createAgent({
      name: agentForm.value.name,
      url: agentForm.value.url,
      owner: agentForm.value.owner || 'system',
      status: agentForm.value.status,
      last_run: agentForm.value.last_run,
      description: agentForm.value.description,
      groups: agentForm.value.groups,
    })
    createSuccess.value = '智能体已创建。'
    agentForm.value = {
      name: '',
      url: '',
      owner: '',
      status: 'active',
      last_run: '',
      description: '',
      groups: [],
    }
    groupQuery.value = ''
    await loadAgents()
  } catch (err) {
    createError.value = err instanceof Error ? err.message : '创建失败'
  } finally {
    createLoading.value = false
  }
}

const openGroupDropdown = () => {
  groupDropdownOpen.value = true
}

const closeGroupDropdown = () => {
  groupDropdownOpen.value = false
}

const focusGroupInput = () => {
  groupInputRef.value?.focus()
  openGroupDropdown()
}

const filteredGroups = computed(() => {
  const query = groupQuery.value.trim().toLowerCase()
  return groupOptions.value.filter((group) => {
    if (!query) return true
    return group.toLowerCase().includes(query)
  })
})

const selectGroup = (group: string) => {
  if (!agentForm.value.groups.includes(group)) {
    agentForm.value.groups.push(group)
  }
  groupQuery.value = ''
}

const removeGroup = (group: string) => {
  const index = agentForm.value.groups.indexOf(group)
  if (index >= 0) {
    agentForm.value.groups.splice(index, 1)
  }
}

const toggleStatusDropdown = () => {
  statusOpen.value = !statusOpen.value
}

const setStatus = (value: 'active' | 'paused') => {
  agentForm.value.status = value
  statusOpen.value = false
}

const handleCreateGroup = async () => {
  const name = groupQuery.value.trim()
  if (!name) return
  groupCreateLoading.value = true
  groupCreateError.value = ''
  try {
    const created = await createAgentGroup({ name })
    if (!groupOptions.value.includes(created.name)) {
      groupOptions.value.push(created.name)
      groupOptions.value.sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
    }
    if (!agentForm.value.groups.includes(created.name)) {
      agentForm.value.groups.push(created.name)
    }
    groupQuery.value = ''
    closeGroupDropdown()
  } catch (err) {
    const message = err instanceof Error ? err.message : '新增分组失败'
    if (message.includes('exists') || message.includes('已存在')) {
      if (groupOptions.value.includes(name) && !agentForm.value.groups.includes(name)) {
        agentForm.value.groups.push(name)
        groupQuery.value = ''
        groupCreateError.value = ''
        closeGroupDropdown()
        return
      }
    }
    groupCreateError.value = message
  } finally {
    groupCreateLoading.value = false
  }
}

const handleGroupEnter = async () => {
  if (groupCreateLoading.value) return
  const name = groupQuery.value.trim()
  if (!name) return
  const existing = groupOptions.value.find((group) => group === name)
  if (existing) {
    selectGroup(existing)
    return
  }
  await handleCreateGroup()
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

const loadGroups = async () => {
  try {
    const groups = await fetchAgentGroups()
    groupOptions.value = groups.map((group) => group.name)
  } catch {
    groupOptions.value = []
  }
}

onMounted(loadAgents)
onMounted(loadGroups)

const handleOutsideClick = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (!target || !groupDropdownRef.value) return
  if (!groupDropdownRef.value.contains(target)) {
    closeGroupDropdown()
  }
  statusOpen.value = false
}

onMounted(() => document.addEventListener('click', handleOutsideClick))
onUnmounted(() => document.removeEventListener('click', handleOutsideClick))
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
  grid-template-columns: repeat(7, minmax(160px, 1fr)) 160px;
  gap: 12px;
  align-items: end;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 13px;
  min-width: 0;
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

.combo-wrap {
  position: relative;
  width: 100%;
  min-width: 0;
}

.combo-input {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 0 10px;
  background: #fff;
  cursor: text;
  overflow: hidden;
  white-space: nowrap;
  max-width: 100%;
  box-sizing: border-box;
}

.combo-input input {
  border: none;
  outline: none;
  flex: 1 1 120px;
  min-width: 90px;
  font-size: 14px;
  height: 100%;
  min-width: 0;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  font-size: 12px;
  height: 24px;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 0 auto;
}

.combo-caret {
  margin-left: auto;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #0c7e85;
  transition: transform 0.2s ease;
}

.combo-more {
  color: #8a9aa0;
  font-size: 12px;
  margin-left: 4px;
}

.combo-caret.open {
  transform: rotate(180deg);
}

.inline-dropdown {
  position: relative;
}

.filter-trigger {
  border: none;
  background: rgba(15, 179, 185, 0.1);
  color: #0c7e85;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex: 0 0 auto;
  min-width: 64px;
  transition: background 0.2s ease, transform 0.2s ease;
}

.filter-trigger:hover {
  background: rgba(15, 179, 185, 0.18);
  transform: translateY(-1px);
}

.caret {
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #0c7e85;
  transition: transform 0.2s ease;
}

.caret.open {
  transform: rotate(180deg);
}

.inline-trigger {
  width: 100%;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #d6e0e2;
  color: #2f3f44;
  padding: 6px 10px;
  border-radius: 12px;
  font-weight: 500;
  min-width: 80px;
  height: 40px;
}

.filter-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 110px;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.18);
  border-radius: 12px;
  padding: 6px;
  display: grid;
  gap: 4px;
  box-shadow: 0 12px 24px rgba(15, 40, 55, 0.12);
  z-index: 20;
}

.inline-dropdown-panel {
  width: 100%;
  min-width: 0;
}

.filter-option {
  border: none;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #2f3f44;
  cursor: pointer;
  transition: background 0.2s ease;
}

.filter-option:hover {
  background: rgba(15, 179, 185, 0.12);
}
.dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 80%;
  min-width: 0;
  max-width: 100%;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.18);
  border-radius: 12px;
  padding: 6px;
  display: grid;
  gap: 4px;
  max-height: 200px;
  overflow: auto;
  z-index: 20;
  box-shadow: 0 12px 24px rgba(15, 40, 55, 0.12);
}

.dropdown-item {
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  font-size: 13px;
  color: #2f3f44;
  transition: background 0.2s ease;
}

.dropdown-check {
  display: inline-flex;
  align-items: center;
}

.dropdown-check input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.dropdown-item:hover {
  background: rgba(15, 179, 185, 0.12);
}

.dropdown-empty {
  padding: 8px 10px;
  font-size: 12px;
  color: #8a9aa0;
}

.selected-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.chip-remove {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 14px;
  margin-left: 4px;
  cursor: pointer;
}

.button-row {
  align-self: end;
  justify-self: start;
  min-width: 0;
}

.action-row {
  align-self: end;
  display: flex;
  align-items: center;
  height: 40px;
}

@media (max-width: 1400px) {
  .form {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
}

.hint {
  font-size: 11px;
  color: #7a8a90;
  margin-top: 6px;
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
const totalCount = computed(() => agents.value.length)
const activeCount = computed(() => agents.value.filter((agent) => agent.status === 'active').length)
