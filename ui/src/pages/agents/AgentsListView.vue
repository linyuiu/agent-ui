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
          <input
            v-model="agentForm.url"
            type="text"
            placeholder="https://example.com/chat/your-token"
            required
          />
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
          <div v-if="agent.groups?.length" class="tag-row">
            <span v-for="group in agent.groups" :key="group" class="chip">分组：{{ group }}</span>
          </div>
        </div>
        <div class="card-meta">
          <span>Owner: {{ agent.owner }}</span>
          <span>Last run: {{ formatIsoDateTime(agent.last_run) }}</span>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentGroupOptions } from '../../composables/use-agent-group-options'
import { useCreatableGroupSelector } from '../../composables/use-creatable-group-selector'
import { useDocumentClick } from '../../composables/use-document-click'
import { createAgent, fetchAgents, type AgentSummary } from '../../services/agents'
import { createAgentGroup } from '../../services/groups'
import { formatIsoDateTime } from '../../utils/text-format'

const router = useRouter()

const agents = ref<AgentSummary[]>([])
const loading = ref(false)
const error = ref('')

const showCreate = ref(false)

const createLoading = ref(false)
const createError = ref('')
const createSuccess = ref('')

const { groupOptions, loadGroupOptions } = useAgentGroupOptions()
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

const selectedGroups = computed({
  get: () => agentForm.value.groups,
  set: (next) => {
    agentForm.value.groups = next
  },
})

const {
  filteredGroups,
  selectGroup,
  removeGroup,
  createOrSelectFromQuery,
} = useCreatableGroupSelector({
  groupOptions,
  selectedGroups,
  query: groupQuery,
  creating: groupCreateLoading,
  error: groupCreateError,
  createGroup: createAgentGroup,
})

const totalCount = computed(() => agents.value.length)
const activeCount = computed(() => agents.value.filter((agent) => agent.status === 'active').length)

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

const toggleStatusDropdown = () => {
  statusOpen.value = !statusOpen.value
}

const setStatus = (value: 'active' | 'paused') => {
  agentForm.value.status = value
  statusOpen.value = false
}

const handleGroupEnter = async () => {
  if (groupCreateLoading.value) return
  const created = await createOrSelectFromQuery()
  if (created) closeGroupDropdown()
}

const loadAgents = async () => {
  loading.value = true
  error.value = ''
  try {
    agents.value = await fetchAgents({ includeDescription: false })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAgents)
onMounted(loadGroupOptions)

const handleOutsideClick = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (!target || !groupDropdownRef.value) return
  if (!groupDropdownRef.value.contains(target)) {
    closeGroupDropdown()
  }
  statusOpen.value = false
}

useDocumentClick(handleOutsideClick)
</script>

<style scoped src="./AgentsListView.css"></style>
