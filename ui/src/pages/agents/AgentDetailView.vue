<template>
  <div class="section">
    <div class="section-header">
      <button class="ghost" type="button" @click="goBack">返回列表</button>
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
          <span class="tag tag-large" :class="statusClass">{{ statusLabel }}</span>
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
          <a class="link" :href="openAgentUrl" target="_blank" rel="noopener" @click="handleOpenLink">
            打开链接
          </a>
        </div>
      </div>
    </div>

    <div v-if="agent" class="panel chat-user-panel">
      <div class="section-header compact">
        <div>
          <h3>对话用户</h3>
          <p>展示当前智能体下的用户组与对话用户授权状态，仅用于查看。</p>
        </div>
      </div>
      <p v-if="chatUserLoading" class="state">加载对话用户中...</p>
      <p v-else-if="chatUserError" class="state error">{{ chatUserError }}</p>
      <p v-else-if="chatUserView?.last_synced_at" class="state success">
        最近同步时间：{{ formatIsoDateTime(chatUserView.last_synced_at) }}
      </p>
      <p v-if="chatUserManageSuccess" class="state success">{{ chatUserManageSuccess }}</p>
      <p v-if="chatUserManageError" class="state error">{{ chatUserManageError }}</p>
      <div v-if="chatUserView?.groups?.length" class="chat-user-toolbar">
        <div class="search-box chat-user-search-box">
          <input
            v-model.trim="chatUserSearch"
            type="text"
            placeholder="搜索用户"
          />
        </div>
        <label class="chat-user-filter-toggle" :class="{ active: chatUserAuthorizedOnly }">
          <input v-model="chatUserAuthorizedOnly" type="checkbox" />
          <span>仅看已授权用户</span>
        </label>
        <button
          v-if="chatUserView.manageable && chatUserView.sync_supported"
          class="primary small"
          type="button"
          :disabled="chatUserSavingAll || !hasDirtyChatUserChanges"
          @click="saveAllChatUserAuth"
        >
          {{ chatUserSavingAll ? '保存中...' : '保存授权' }}
        </button>
      </div>
      <div v-if="chatUserView?.groups?.length" class="chat-user-groups">
        <div v-for="group in filteredChatUserGroups" :key="group.id" class="chat-user-group-card">
          <div
            class="chat-user-group-head"
            :class="{ active: group.id === activeGroupId }"
            @click="selectActiveGroup(group.id)"
          >
            <div class="chat-user-group-meta">
              <strong>{{ group.name }}</strong>
              <small>{{ group.id }}</small>
            </div>
            <div class="chat-user-group-actions">
              <span class="tag tag-small readonly chat-user-group-count">
                {{ getAuthorizedCount(group) }}/{{ getGroupTotalUsers(group) }} 已授权
              </span>
              <div
                v-if="chatUserView.manageable && chatUserView.sync_supported && group.id === activeGroupId"
                class="chat-user-group-bulk-actions"
              >
                <button
                  class="ghost small compact"
                  type="button"
                  :disabled="chatUserSavingAll || !activeGroupUsers.length"
                  @click.stop
                  @click="setGroupAuthForVisible(group, true)"
                >
                  全选授权
                </button>
                <button
                  class="ghost small compact"
                  type="button"
                  :disabled="chatUserSavingAll || !activeGroupUsers.length"
                  @click.stop
                  @click="setGroupAuthForVisible(group, false)"
                >
                  全取消授权
                </button>
              </div>
            </div>
          </div>
          <div v-if="group.id === activeGroupId" class="chat-user-group-body">
            <p v-if="activeGroupLoading" class="state">加载对话用户中...</p>
            <p v-else-if="activeGroupError" class="state error">{{ activeGroupError }}</p>
            <div v-else-if="activeGroupUsers.length" class="chat-user-list">
              <div v-for="user in activeGroupUsers" :key="`${group.id}-${user.id}`" class="chat-user-item">
                <div class="chat-user-main">
                  <strong>{{ user.nick_name || user.username }}</strong>
                  <small>{{ user.username }} · {{ user.source || 'unknown' }}</small>
                </div>
                <label
                  v-if="chatUserView.manageable && chatUserView.sync_supported"
                  class="chat-user-auth-control"
                  @click.stop
                >
                  <input
                    type="checkbox"
                    :checked="getUserAuthState(group.id, user.id, user.is_auth)"
                    @change="handleUserAuthChange(group.id, user.id, $event)"
                  />
                  <span>{{ getUserAuthState(group.id, user.id, user.is_auth) ? '已授权' : '未授权' }}</span>
                </label>
                <span v-else class="tag tag-small" :class="user.is_auth ? 'active' : 'paused'">
                  {{ user.is_auth ? '已授权' : '未授权' }}
                </span>
              </div>
            </div>
            <p v-else class="state">没有匹配的对话用户。</p>
          </div>
        </div>
      </div>
      <p
        v-if="chatUserView?.groups?.length && !filteredChatUserGroups.length && !chatUserLoading && !chatUserError"
        class="state"
      >
        没有匹配的对话用户。
      </p>
      <p v-if="!chatUserView?.groups?.length && !chatUserLoading && !chatUserError" class="state">
        暂无对话用户同步数据。
      </p>
    </div>

    <ConfirmDialog
      :open="leaveConfirmOpen"
      title="授权未保存"
      message="当前对话用户授权修改尚未保存，是否先保存再离开？"
      :loading="leaveConfirmLoading"
      confirm-text="保存"
      secondary-text="不保存"
      loading-text="保存中..."
      @close="handleLeaveConfirmClose"
      @secondary="handleLeaveWithoutSaving"
      @confirm="handleLeaveWithSaving"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import {
  fetchAgentDetailPage,
  fetchAgentChatUserGroup,
  updateAgentChatUsers,
  type AgentChatUserGroupView,
  type AgentChatUserView,
  type AgentDetail,
  type AgentSummary,
} from '../../services/agents'
import { buildOpenAgentUrl } from '../../utils/agent-links'
import { formatIsoDateTime } from '../../utils/text-format'

const ACCESS_BLOCKED_MESSAGE = '该智能体暂时不可访问'

const route = useRoute()
const router = useRouter()

const agent = ref<AgentDetail | null>(null)
const loading = ref(false)
const error = ref('')
const chatUserView = ref<AgentChatUserView | null>(null)
const chatUserLoading = ref(false)
const activeGroupId = ref('')
const chatUserGroupViews = ref<Record<string, AgentChatUserGroupView>>({})
const activeGroupLoading = ref(false)
const activeGroupError = ref('')
const chatUserError = ref('')
const chatUserManageError = ref('')
const chatUserManageSuccess = ref('')
const chatUserSavingAll = ref(false)
const chatUserDrafts = ref<Record<string, Record<string, boolean>>>({})
const chatUserSearch = ref('')
const chatUserAuthorizedOnly = ref(false)
const leaveConfirmOpen = ref(false)
const leaveConfirmLoading = ref(false)
const pendingLeaveTarget = ref<RouteLocationRaw | null>(null)
const allowRouteLeave = ref(false)

const isAgentActive = (target: Pick<AgentSummary, 'status'>) =>
  (target.status || '').toLowerCase() === 'active'

const statusClass = computed(() => {
  if (!agent.value) return 'paused'
  return isAgentActive(agent.value) ? 'active' : 'paused'
})

const statusLabel = computed(() => {
  if (!agent.value) return 'inactive'
  return isAgentActive(agent.value) ? 'active' : 'inactive'
})

const openAgentUrl = computed(() => (agent.value ? buildOpenAgentUrl(agent.value) : ''))

const handleOpenLink = (event: MouseEvent) => {
  if (!agent.value) return
  if (!isAgentActive(agent.value)) {
    event.preventDefault()
    window.alert(ACCESS_BLOCKED_MESSAGE)
  }
}

const normalizeSearch = (value: string) => value.trim().toLowerCase()

const matchChatUser = (user: AgentChatUserView['groups'][number]['users'][number], query: string) => {
  if (!query) return true
  const haystacks = [
    user.username,
    user.nick_name,
    user.source,
    user.email,
    user.phone,
  ]
  return haystacks.some((item) => String(item || '').toLowerCase().includes(query))
}

const upsertGroupView = (group: AgentChatUserGroupView) => {
  chatUserGroupViews.value = {
    ...chatUserGroupViews.value,
    [group.id]: group,
  }
  chatUserDrafts.value = {
    ...chatUserDrafts.value,
    [group.id]: Object.fromEntries(group.users.map((user) => [user.id, Boolean(user.is_auth)])),
  }
  if (chatUserView.value) {
    chatUserView.value = {
      ...chatUserView.value,
      groups: chatUserView.value.groups.map((item) =>
        item.id === group.id
          ? {
              ...item,
              name: group.name,
              authorized_count: group.authorized_count,
              total_users: group.total_users,
            }
          : item
      ),
      total_users: chatUserView.value.groups.reduce(
        (sum, item) => sum + (item.id === group.id ? group.total_users : item.total_users),
        0
      ),
    }
  }
}

const getUserAuthState = (groupId: string, userId: string, fallback: boolean) =>
  chatUserDrafts.value[groupId]?.[userId] ?? fallback

const getAuthorizedCount = (group: AgentChatUserGroupView) => {
  const detail = chatUserGroupViews.value[group.id]
  if (!detail) return group.authorized_count
  return detail.users.filter((user) => getUserAuthState(group.id, user.id, Boolean(user.is_auth))).length
}

const getGroupTotalUsers = (group: AgentChatUserGroupView) =>
  chatUserGroupViews.value[group.id]?.total_users ?? group.total_users

const setUserAuthState = (groupId: string, userId: string, value: boolean) => {
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  chatUserDrafts.value = {
    ...chatUserDrafts.value,
    [groupId]: {
      ...(chatUserDrafts.value[groupId] || {}),
      [userId]: value,
    },
  }
}

const setGroupAuthForVisible = (group: AgentChatUserGroupView, value: boolean) => {
  if (group.id !== activeGroupId.value) return
  for (const user of activeGroupUsers.value) {
    setUserAuthState(group.id, user.id, value)
  }
}

const handleUserAuthChange = (groupId: string, userId: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  setUserAuthState(groupId, userId, Boolean(target?.checked))
}

const isGroupDirty = (group: AgentChatUserGroupView) =>
  (chatUserGroupViews.value[group.id]?.users || []).some(
    (user) => getUserAuthState(group.id, user.id, user.is_auth) !== Boolean(user.is_auth)
  )

const hasDirtyChatUserChanges = computed(() =>
  (chatUserView.value?.groups || []).some((group) => isGroupDirty(group)),
)

const filteredChatUserGroups = computed(() => {
  const groups = chatUserView.value?.groups || []
  if (!chatUserAuthorizedOnly.value) return groups
  return groups.filter((group) => getAuthorizedCount(group) > 0)
})

const activeGroup = computed(
  () => filteredChatUserGroups.value.find((group) => group.id === activeGroupId.value) || null
)

const activeGroupUsers = computed(() => {
  const group = activeGroup.value
  if (!group) return []
  const detail = chatUserGroupViews.value[group.id]
  if (!detail) return []
  const query = normalizeSearch(chatUserSearch.value)
  return detail.users.filter((user) => {
    const matchesQuery = !query || matchChatUser(user, query)
    const matchesAuth = !chatUserAuthorizedOnly.value || getUserAuthState(group.id, user.id, Boolean(user.is_auth))
    return matchesQuery && matchesAuth
  })
})

const saveAllChatUserAuth = async () => {
  if (!agent.value || !chatUserView.value?.manageable || !chatUserView.value?.sync_supported) return
  const draftSnapshot = JSON.parse(JSON.stringify(chatUserDrafts.value)) as Record<string, Record<string, boolean>>
  const dirtyGroups = (chatUserView.value.groups || []).filter((group) =>
    (chatUserGroupViews.value[group.id]?.users || []).some(
      (user) => (draftSnapshot[group.id]?.[user.id] ?? Boolean(user.is_auth)) !== Boolean(user.is_auth),
    ),
  )
  if (!dirtyGroups.length) return

  chatUserSavingAll.value = true
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  try {
    for (const group of dirtyGroups) {
      const detail = chatUserGroupViews.value[group.id]
      if (!detail) continue
      const updatedGroup = await updateAgentChatUsers(agent.value.id, {
        group_id: group.id,
        users: detail.users.map((user) => ({
          chat_user_id: user.id,
          is_auth: draftSnapshot[group.id]?.[user.id] ?? Boolean(user.is_auth),
        })),
      })
      upsertGroupView(updatedGroup)
    }
    chatUserManageSuccess.value =
      dirtyGroups.length === 1 ? `${dirtyGroups[0].name} 授权已更新。` : `已更新 ${dirtyGroups.length} 个用户组的授权。`
    return true
  } catch (err) {
    chatUserManageError.value = err instanceof Error ? err.message : '更新授权失败'
    return false
  } finally {
    chatUserSavingAll.value = false
  }
}

const loadChatUserGroup = async (groupId: string, options?: { force?: boolean }) => {
  if (!agent.value || !groupId) return
  if (!options?.force && chatUserGroupViews.value[groupId]) return
  activeGroupLoading.value = true
  activeGroupError.value = ''
  try {
    const group = await fetchAgentChatUserGroup(agent.value.id, groupId)
    upsertGroupView(group)
  } catch (err) {
    activeGroupError.value = err instanceof Error ? err.message : '加载对话用户失败'
  } finally {
    activeGroupLoading.value = false
  }
}

const selectActiveGroup = (groupId: string) => {
  if (!groupId || groupId === activeGroupId.value) return
  activeGroupId.value = groupId
}

const proceedPendingLeave = async () => {
  const target = pendingLeaveTarget.value
  pendingLeaveTarget.value = null
  leaveConfirmOpen.value = false
  if (!target) return
  allowRouteLeave.value = true
  await router.push(target)
}

const handleLeaveConfirmClose = () => {
  if (leaveConfirmLoading.value) return
  leaveConfirmOpen.value = false
  pendingLeaveTarget.value = null
}

const handleLeaveWithoutSaving = async () => {
  if (leaveConfirmLoading.value) return
  await proceedPendingLeave()
}

const handleLeaveWithSaving = async () => {
  if (leaveConfirmLoading.value) return
  leaveConfirmLoading.value = true
  try {
    const saved = await saveAllChatUserAuth()
    if (!saved) return
    await proceedPendingLeave()
  } finally {
    leaveConfirmLoading.value = false
  }
}

const loadAgent = async (id: string) => {
  loading.value = true
  error.value = ''
  chatUserView.value = null
  activeGroupId.value = ''
  chatUserGroupViews.value = {}
  activeGroupError.value = ''
  chatUserError.value = ''
  chatUserManageError.value = ''
  chatUserManageSuccess.value = ''
  chatUserDrafts.value = {}
  chatUserSavingAll.value = false
  chatUserSearch.value = ''
  chatUserAuthorizedOnly.value = false
  try {
    chatUserLoading.value = true
    const detailPage = await fetchAgentDetailPage(id)
    agent.value = detailPage.agent
    chatUserView.value = detailPage.chat_users
    if (detailPage.initial_group) {
      upsertGroupView(detailPage.initial_group)
      activeGroupId.value = detailPage.initial_group.id
    } else {
      const [firstGroup] = detailPage.chat_users.groups || []
      if (firstGroup) {
        activeGroupId.value = firstGroup.id
      }
    }
  } catch (err) {
    agent.value = null
    chatUserView.value = null
    chatUserLoading.value = false
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    chatUserLoading.value = false
    loading.value = false
  }
}

const goBack = async () => {
  await router.push({ name: 'home-agents' })
}

onBeforeRouteLeave((to) => {
  if (allowRouteLeave.value) {
    allowRouteLeave.value = false
    return true
  }
  if (!hasDirtyChatUserChanges.value) return true
  pendingLeaveTarget.value = {
    name: to.name || undefined,
    params: to.params,
    query: to.query,
    hash: to.hash,
  }
  leaveConfirmOpen.value = true
  return false
})

watch(
  () => activeGroupId.value,
  (groupId) => {
    if (groupId) {
      void loadChatUserGroup(groupId)
    }
  }
)

watch(
  () => filteredChatUserGroups.value.map((group) => group.id).join(','),
  (groupIds) => {
    const ids = groupIds ? groupIds.split(',').filter(Boolean) : []
    if (!ids.length) {
      activeGroupId.value = ''
      return
    }
    if (!ids.includes(activeGroupId.value)) {
      activeGroupId.value = ids[0]
    }
  },
  { immediate: true }
)

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') {
      loadAgent(id)
    }
  },
  { immediate: true },
)
</script>

<style scoped src="./AgentDetailView.css"></style>
