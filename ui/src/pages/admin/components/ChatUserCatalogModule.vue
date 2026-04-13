<template>
  <div
    class="section chat-user-section"
    :class="{
      'chat-user-section--with-detail': !!selectedChatUser,
      'chat-user-section--compact': !showPagination && !selectedChatUser,
    }"
  >
    <div class="section-header">
      <div>
        <h2>对话用户</h2>
        <p>查看源系统同步到本地的对话用户，并检查每个用户可访问的智能体。</p>
      </div>
    </div>

    <div class="panel chat-user-panel" :class="{ 'chat-user-panel--compact': !showPagination && !selectedChatUser }">
      <div class="chat-user-toolbar">
        <div class="search-box">
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索用户名、昵称、邮箱或手机号"
            @compositionstart="handleCompositionStart"
            @compositionend="handleCompositionEnd"
            @keydown.enter="handleSearchKeydown"
          />
        </div>

        <div class="chat-user-toolbar__actions">
          <div class="binding-filter">
            <button
              v-for="option in bindingOptions"
              :key="option.value"
              type="button"
              class="binding-filter__item"
              :class="{ active: binding === option.value }"
              @click="setBinding(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <div ref="sourceFilterRef" class="inline-dropdown source-filter" @click.stop>
            <button
              type="button"
              class="filter-trigger inline-trigger source-filter__trigger"
              :class="{ active: sourceDropdownOpen }"
              @click.stop="toggleSourceDropdown"
            >
              <span class="source-filter__label">来源</span>
              <span class="source-filter__value">{{ sourceSummary }}</span>
              <span class="caret" :class="{ open: sourceDropdownOpen }"></span>
            </button>

            <div v-if="sourceDropdownOpen" class="filter-dropdown inline-dropdown-panel source-filter__menu">
              <button
                type="button"
                class="filter-option source-filter__option"
                :class="{ active: !selectedSources.length }"
                @click.stop="clearSources"
              >
                <span class="source-filter__check">{{ !selectedSources.length ? '✓' : '' }}</span>
                <span>全部来源</span>
              </button>
              <button
                v-for="item in sourceOptions"
                :key="item"
                type="button"
                class="filter-option source-filter__option"
                :class="{ active: selectedSources.includes(item) }"
                @click.stop="toggleSource(item)"
              >
                <span class="source-filter__check">{{ selectedSources.includes(item) ? '✓' : '' }}</span>
                <span>{{ item }}</span>
              </button>
            </div>
          </div>
          <button class="ghost chat-user-toolbar__button" type="button" :disabled="loading" @click="handleReset">
            重置
          </button>
          <button class="primary chat-user-toolbar__button" type="button" :disabled="loading" @click="handleSearch">
            {{ loading ? '加载中...' : '查询' }}
          </button>
        </div>
      </div>

      <div class="meta-line">
        <span class="count-pill">共 {{ total }} 个对话用户</span>
        <span class="count-pill">当前第 {{ page }} 页</span>
        <span v-if="sourceOptions.length" class="count-pill">来源 {{ sourceOptions.length }} 种</span>
      </div>

      <p v-if="error" class="state error">{{ error }}</p>

      <div class="chat-user-table-shell" :class="{ 'chat-user-table-shell--compact': !showPagination && !selectedChatUser }">
        <div class="chat-user-table" :class="{ 'chat-user-table--compact': !showPagination && !selectedChatUser }">
          <div class="chat-user-table__head">
            <div>用户名</div>
            <div>昵称</div>
            <div>来源</div>
            <div>状态</div>
            <div>绑定系统用户</div>
            <div>可访问智能体</div>
            <div>用户组</div>
            <div>同步时间</div>
          </div>

          <div
            ref="tableScrollRef"
            class="chat-user-table__scroll"
            :class="{ 'chat-user-table__scroll--compact': !showPagination && !selectedChatUser }"
          >
            <div v-if="loading" class="state chat-user-table__state">加载对话用户中...</div>
            <div
              v-else-if="items.length"
              class="chat-user-table__body"
              :class="{ 'chat-user-table__body--compact': !showPagination && !selectedChatUser }"
            >
              <button
                v-for="item in items"
                :key="item.id"
                type="button"
                class="chat-user-row"
                :class="{ active: selectedChatUserId === item.id }"
                @click="selectChatUser(item)"
              >
                <div class="chat-user-primary">
                  <strong>{{ item.username }}</strong>
                  <small>{{ item.id }}</small>
                </div>
                <div>{{ item.nick_name || '-' }}</div>
                <div>
                  <span class="tag tag-small">{{ item.source || '未知来源' }}</span>
                </div>
                <div>
                  <span class="tag tag-small" :class="item.is_active ? 'editable' : 'readonly'">
                    {{ item.is_active ? 'active' : 'disabled' }}
                  </span>
                </div>
                <div>
                  <span v-if="item.is_bound" class="binding-stack">
                    <strong>{{ item.system_username || item.system_account }}</strong>
                    <small>{{ item.system_account || '-' }}</small>
                  </span>
                  <span v-else class="binding-empty">未绑定</span>
                </div>
                <div>
                  <span class="count-pill compact">{{ item.accessible_agent_count }} 个</span>
                </div>
                <div>
                  <div v-if="item.user_group_names.length" class="chip-row">
                    <span
                      v-for="groupName in item.user_group_names"
                      :key="`${item.id}-${groupName}`"
                      class="pill-chip"
                    >
                      {{ groupName }}
                    </span>
                  </div>
                  <span v-else class="binding-empty">未分组</span>
                </div>
                <div>{{ formatIsoDateTime(item.synced_at || '') || '-' }}</div>
              </button>
            </div>
            <p v-else class="state chat-user-table__state">暂无对话用户数据。</p>
          </div>
        </div>
      </div>

      <div v-if="showPagination" class="chat-user-pagination">
        <div class="chat-user-pagination__nav">
          <label class="page-size-inline">
            <span>每页</span>
            <select v-model.number="pageSize" @change="handlePageSizeChange">
              <option v-for="size in pageSizeOptions" :key="size" :value="size">
                {{ size }} 条
              </option>
            </select>
          </label>
          <button
            class="ghost chat-user-pagination__button"
            type="button"
            :disabled="page <= 1 || loading"
            @click="goToPage(page - 1)"
          >
            上一页
          </button>
          <span class="chat-user-pagination__page-text">第 {{ page }} / {{ pageCount }} 页</span>
          <label class="page-jump-inline">
            <span>跳至</span>
            <input
              v-model="jumpPageInput"
              type="number"
              min="1"
              :max="pageCount"
              @keydown.enter.prevent="handleJumpPage"
            />
            <span>页</span>
          </label>
          <button class="ghost chat-user-pagination__button" type="button" :disabled="loading" @click="handleJumpPage">
            跳转
          </button>
          <button
            class="ghost chat-user-pagination__button"
            type="button"
            :disabled="page >= pageCount || loading"
            @click="goToPage(page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <div v-if="selectedChatUser" class="panel">
      <div class="panel-header detail-header">
        <div>
          <h2>{{ selectedChatUser.nick_name || selectedChatUser.username }}</h2>
          <p>
            {{ selectedChatUser.username }}
            <span v-if="selectedChatUser.source">· {{ selectedChatUser.source }}</span>
          </p>
        </div>
        <div class="meta-line">
          <span class="count-pill" :class="selectedChatUser.is_bound ? 'bound-pill' : 'unbound-pill'">
            {{ selectedChatUser.is_bound ? '已绑定系统用户' : '未绑定系统用户' }}
          </span>
          <span class="count-pill">可访问智能体 {{ selectedChatUser.accessible_agent_count }} 个</span>
        </div>
      </div>

      <div class="chat-user-detail-meta">
        <div class="detail-meta-card">
          <span class="label">系统用户</span>
          <strong>{{ selectedChatUser.system_username || '未绑定' }}</strong>
          <small>{{ selectedChatUser.system_account || '暂无系统账号' }}</small>
        </div>
        <div class="detail-meta-card">
          <span class="label">邮箱</span>
          <strong>{{ selectedChatUser.email || '-' }}</strong>
          <small>{{ selectedChatUser.phone || '暂无手机号' }}</small>
        </div>
        <div class="detail-meta-card">
          <span class="label">来源用户组</span>
          <strong>{{ selectedChatUser.user_group_names[0] || '未分组' }}</strong>
          <small v-if="selectedChatUser.user_group_names.length > 1">
            共 {{ selectedChatUser.user_group_names.length }} 个用户组
          </small>
          <small v-else>同步时间：{{ formatIsoDateTime(selectedChatUser.synced_at || '') || '-' }}</small>
        </div>
      </div>

      <p v-if="detailError" class="state error">{{ detailError }}</p>
      <p v-else-if="detailLoading" class="state">加载可访问智能体中...</p>
      <div v-else-if="selectedChatUserDetail?.items.length" class="chat-user-agent-grid">
        <article
          v-for="item in selectedChatUserDetail.items"
          :key="item.agent_id"
          class="chat-user-agent-card"
        >
          <div class="chat-user-agent-card__head">
            <div>
              <h3>{{ item.agent_name }}</h3>
              <p>{{ item.agent_owner || 'system' }}</p>
            </div>
            <span class="tag tag-small" :class="item.agent_status === 'active' ? 'editable' : 'readonly'">
              {{ item.agent_status || 'unknown' }}
            </span>
          </div>

          <div class="chat-user-agent-card__meta">
            <span v-if="item.workspace_name">工作空间：{{ item.workspace_name }}</span>
            <span v-if="item.source_type">来源：{{ item.source_type }}</span>
            <span v-if="item.last_run">最近运行：{{ formatIsoDateTime(item.last_run) }}</span>
          </div>

          <div class="chip-row">
            <span
              v-for="groupName in item.group_names"
              :key="`${item.agent_id}-${groupName}`"
              class="pill-chip"
            >
              {{ groupName }}
            </span>
          </div>

          <div class="button-row">
            <button class="ghost" type="button" @click="goToAgentDetail(item.agent_id)">
              查看智能体
            </button>
          </div>
        </article>
      </div>
      <p v-else class="state">当前对话用户暂无已授权的智能体。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useImeFriendlyEnter } from '../../../composables/use-ime-friendly-enter'
import {
  fetchChatUserAccessibleAgents,
  fetchChatUsers,
  type ChatUserAccessibleAgentsResponse,
  type ChatUserCatalogItem,
} from '../../../services/admin'
import { formatIsoDateTime } from '../../../utils/text-format'

const router = useRouter()

const items = ref<ChatUserCatalogItem[]>([])
const sourceOptions = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [20, 50, 100, 200]
const keyword = ref('')
const selectedSources = ref<string[]>([])
const binding = ref<'' | 'bound' | 'unbound'>('')
const loading = ref(false)
const error = ref('')
const selectedChatUserId = ref('')
const selectedChatUser = ref<ChatUserCatalogItem | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const detailCache = ref<Record<string, ChatUserAccessibleAgentsResponse>>({})
const sourceDropdownOpen = ref(false)
const sourceFilterRef = ref<HTMLElement | null>(null)
const jumpPageInput = ref('1')
const tableScrollRef = ref<HTMLElement | null>(null)

const bindingOptions = [
  { value: '' as const, label: '全部用户' },
  { value: 'bound' as const, label: '只看已绑定系统用户' },
  { value: 'unbound' as const, label: '只看未绑定系统用户' },
]

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const showPagination = computed(() => total.value > pageSize.value && pageCount.value > 1)
const sourceSummary = computed(() => {
  if (!selectedSources.value.length) return '全部来源'
  if (selectedSources.value.length === 1) return selectedSources.value[0]
  return `已选 ${selectedSources.value.length} 项`
})
const selectedChatUserDetail = computed(() =>
  selectedChatUserId.value ? detailCache.value[selectedChatUserId.value] || null : null
)

const loadChatUsers = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchChatUsers({
      page: page.value,
      page_size: pageSize.value,
      q: keyword.value,
      source: selectedSources.value,
      binding: binding.value,
    })
    items.value = response.items
    total.value = response.total
    sourceOptions.value = response.sources
    if (selectedChatUserId.value && !response.items.some((item) => item.id === selectedChatUserId.value)) {
      selectedChatUserId.value = ''
      selectedChatUser.value = null
      detailError.value = ''
    }
    await nextTick()
    if (tableScrollRef.value) {
      tableScrollRef.value.scrollTop = 0
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载对话用户失败'
  } finally {
    loading.value = false
  }
}

const loadChatUserDetail = async (chatUser: ChatUserCatalogItem) => {
  selectedChatUserId.value = chatUser.id
  selectedChatUser.value = chatUser
  detailError.value = ''
  if (detailCache.value[chatUser.id]) return
  detailLoading.value = true
  try {
    const response = await fetchChatUserAccessibleAgents(chatUser.id)
    detailCache.value = {
      ...detailCache.value,
      [chatUser.id]: response,
    }
    selectedChatUser.value = response.chat_user
    items.value = items.value.map((item) => (item.id === response.chat_user.id ? response.chat_user : item))
  } catch (err) {
    detailError.value = err instanceof Error ? err.message : '加载可访问智能体失败'
  } finally {
    detailLoading.value = false
  }
}

const selectChatUser = async (chatUser: ChatUserCatalogItem) => {
  if (selectedChatUserId.value === chatUser.id && detailCache.value[chatUser.id]) return
  await loadChatUserDetail(chatUser)
}

const handleSearch = async () => {
  page.value = 1
  await loadChatUsers()
}

const {
  handleCompositionStart,
  handleCompositionEnd,
  handleEnterKeydown: handleSearchKeydown,
} = useImeFriendlyEnter(handleSearch, { preventDefault: true })

const handleReset = async () => {
  keyword.value = ''
  selectedSources.value = []
  binding.value = ''
  sourceDropdownOpen.value = false
  page.value = 1
  await loadChatUsers()
}

const setBinding = async (value: '' | 'bound' | 'unbound') => {
  if (binding.value === value) return
  binding.value = value
  page.value = 1
  await loadChatUsers()
}

const goToPage = async (target: number) => {
  if (target < 1 || target > pageCount.value || target === page.value) {
    jumpPageInput.value = String(page.value)
    return
  }
  page.value = target
  jumpPageInput.value = String(target)
  await loadChatUsers()
}

const handlePageSizeChange = async () => {
  page.value = 1
  jumpPageInput.value = '1'
  await loadChatUsers()
}

const handleJumpPage = async () => {
  const target = Number.parseInt(jumpPageInput.value, 10)
  if (Number.isNaN(target)) {
    jumpPageInput.value = String(page.value)
    return
  }
  await goToPage(target)
}

const goToAgentDetail = async (agentId: string) => {
  await router.push({ name: 'home-agent-detail', params: { id: agentId } })
}

const toggleSourceDropdown = () => {
  sourceDropdownOpen.value = !sourceDropdownOpen.value
}

const toggleSource = (value: string) => {
  const next = new Set(selectedSources.value)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  selectedSources.value = Array.from(next)
}

const clearSources = () => {
  selectedSources.value = []
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (!target) return
  if (sourceFilterRef.value && !sourceFilterRef.value.contains(target)) {
    sourceDropdownOpen.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  await loadChatUsers()
  jumpPageInput.value = String(page.value)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped src="./ChatUserCatalogModule.css"></style>
