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
          <span class="tag tag-large" :class="agent.status">{{ agent.status }}</span>
          <span class="tag tag-large" :class="agent.editable ? 'editable' : 'readonly'">
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
          <span>{{ formatIsoDateTime(agent.last_run) }}</span>
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
          <div class="inline-dropdown" @click.stop>
            <button class="filter-trigger inline-trigger" type="button" @click.stop="toggleStatusDropdown">
              <span>{{ editForm.status }}</span>
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
          <input v-model="editForm.last_run" type="text" />
        </div>
        <div class="field">
          <label>描述</label>
          <input v-model="editForm.description" type="text" />
        </div>
        <div class="field">
          <label>分组</label>
          <div class="combo-wrap" ref="groupDropdownRef">
            <div class="combo-input" @click="focusGroupInput">
              <template v-for="group in editForm.groups" :key="group">
                <span class="pill-chip">
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
                :placeholder="editForm.groups.length ? '' : '输入或选择分组'"
                @focus="openGroupDropdown"
                @keydown.enter.prevent="handleGroupEnter"
              />
              <span v-if="editForm.groups.length" class="combo-more">...</span>
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
                  <input type="checkbox" :checked="editForm.groups.includes(group)" disabled />
                </span>
              </button>
              <p v-if="!filteredGroups.length" class="dropdown-empty">
                {{ groupQuery.trim() ? '按回车创建新分组' : '暂无可用分组' }}
              </p>
            </div>
          </div>
          <small v-if="groupCreateError" class="state error">{{ groupCreateError }}</small>
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentGroupOptions } from '../../composables/use-agent-group-options'
import { useCreatableGroupSelector } from '../../composables/use-creatable-group-selector'
import { useDocumentClick } from '../../composables/use-document-click'
import { fetchAgent, updateAgent, type AgentDetail } from '../../services/agents'
import { createAgentGroup } from '../../services/groups'
import { formatIsoDateTime } from '../../utils/text-format'

const route = useRoute()
const router = useRouter()

const agent = ref<AgentDetail | null>(null)
const loading = ref(false)
const error = ref('')
const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref('')
const { groupOptions, loadGroupOptions } = useAgentGroupOptions()
const groupQuery = ref('')
const groupCreateLoading = ref(false)
const groupCreateError = ref('')
const groupDropdownOpen = ref(false)
const groupDropdownRef = ref<HTMLElement | null>(null)
const groupInputRef = ref<HTMLInputElement | null>(null)
const statusOpen = ref(false)

const editForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  last_run: '',
  description: '',
  groups: [] as string[],
})

const selectedGroups = computed({
  get: () => editForm.value.groups,
  set: (next) => {
    editForm.value.groups = next
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
        groups: agent.value.groups ? [...agent.value.groups] : [],
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
  groupCreateError.value = ''
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
      groups: editForm.value.groups,
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
  editForm.value.status = value
  statusOpen.value = false
}

const handleGroupEnter = async () => {
  if (groupCreateLoading.value) return
  const created = await createOrSelectFromQuery()
  if (created) closeGroupDropdown()
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

<style scoped src="./AgentDetailView.css"></style>
