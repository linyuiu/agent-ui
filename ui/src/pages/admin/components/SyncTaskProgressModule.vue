<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>同步任务进度</h2>
        <p>{{ pollingHint }}</p>
      </div>
      <div class="task-toolbar">
        <span class="task-toolbar-status" :class="{ running: hasActiveTasks }">
          {{ hasActiveTasks ? '自动刷新中' : '自动刷新已停止' }}
        </span>
        <button class="ghost" type="button" :disabled="loading" @click="refreshTasks">
          {{ loading ? '刷新中...' : '立即刷新' }}
        </button>
      </div>
    </div>

    <div class="panel">
      <p v-if="loading" class="state">加载任务中...</p>
      <p v-if="error" class="state error">{{ error }}</p>
      <div v-if="tasks.length" class="grid task-grid">
        <div v-for="task in tasks" :key="task.id" class="policy-card task-card">
          <div class="task-card-head">
            <div>
              <h3>{{ task.agent_name || '智能体同步任务' }}</h3>
              <p>{{ task.workspace_name || task.workspace_id || '未指定工作空间' }}</p>
            </div>
            <span class="tag tag-small" :class="taskStatusClass(task.status)">
              {{ queueStatusLabel(task.status) }}
            </span>
          </div>

          <div class="task-progress">
            <div class="task-progress-track">
              <span class="task-progress-fill" :style="{ width: `${taskProgress(task)}%` }"></span>
            </div>
            <small>步骤进度：{{ task.completed_steps }} / {{ task.total_steps || 0 }}</small>
          </div>

          <div class="task-meta">
            <span>队列状态：{{ queueStatusLabel(task.status) }}</span>
            <span v-if="task.total_records">记录进度：{{ task.processed_records }} / {{ task.total_records }}</span>
            <span v-if="task.celery_task_id">任务 ID：{{ task.celery_task_id }}</span>
          </div>

          <p class="task-message">{{ task.error || task.message || '等待执行' }}</p>

          <div class="task-times">
            <small>创建时间：{{ formatIsoDateTime(task.created_at) }}</small>
            <small v-if="task.started_at">开始时间：{{ formatIsoDateTime(task.started_at) }}</small>
            <small v-if="task.finished_at">结束时间：{{ formatIsoDateTime(task.finished_at) }}</small>
          </div>
        </div>
      </div>
      <p v-else-if="!loading" class="state">暂无同步任务。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { fetchAgentSyncTasks, type SyncTask } from '../../../services/admin'
import { formatIsoDateTime } from '../../../utils/text-format'

const tasks = ref<SyncTask[]>([])
const loading = ref(false)
const error = ref('')

const activeStatuses = new Set(['pending', 'running'])
let pollTimer: number | null = null

const hasActiveTasks = computed(() => tasks.value.some((task) => activeStatuses.has(task.status)))

const pollingHint = computed(() =>
  hasActiveTasks.value
    ? '展示同步队列执行情况，存在运行中任务时每 5 秒自动刷新。'
    : '展示同步队列执行情况。当前没有运行中任务，自动刷新已停止。'
)

const stopPolling = () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

const ensurePolling = () => {
  if (!hasActiveTasks.value) {
    stopPolling()
    return
  }
  if (pollTimer !== null) {
    return
  }
  pollTimer = window.setInterval(() => {
    void loadTasks(true)
  }, 5000)
}

const loadTasks = async (silent = false) => {
  if (!silent) {
    loading.value = true
  }
  error.value = ''
  try {
    tasks.value = await fetchAgentSyncTasks()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载任务失败'
  } finally {
    if (!silent) {
      loading.value = false
    }
    ensurePolling()
  }
}

const refreshTasks = async () => {
  await loadTasks()
}

const taskProgress = (task: SyncTask) => {
  if (!task.total_steps) return task.status === 'completed' ? 100 : 0
  return Math.min(100, Math.round((task.completed_steps / task.total_steps) * 100))
}

const queueStatusLabel = (status: string) => {
  if (status === 'pending') return '等待执行'
  if (status === 'running') return '执行中'
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '执行失败'
  return status || '未知状态'
}

const taskStatusClass = (status: string) => {
  if (status === 'completed') return 'active'
  if (status === 'failed') return 'paused'
  if (status === 'running') return 'editable'
  return 'readonly'
}

onMounted(async () => {
  await loadTasks()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped src="./SyncTaskProgressModule.css"></style>
