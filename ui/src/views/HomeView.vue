<template>
  <div class="home">
    <header class="topbar">
      <div class="brand">
        <span class="badge">Agent UI</span>
        <div>
          <h1>控制台</h1>
          <p>欢迎回来，{{ email || '同学' }}</p>
        </div>
      </div>
      <button class="ghost" type="button" @click="handleLogout">退出登录</button>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <p class="sidebar__title">模块</p>
        <div v-if="loading" class="sidebar__state">加载模块中...</div>
        <div v-if="error" class="sidebar__state error">{{ error }}</div>

        <button
          v-for="item in modules"
          :key="item.id"
          class="nav-item"
          :class="{ active: item.id === activeId }"
          type="button"
          @click="handleModuleClick(item.id)"
        >
          <div>
            <span>{{ item.title }}</span>
            <small>{{ item.subtitle }}</small>
          </div>
          <div class="nav-meta">
            <strong>{{ item.active }}</strong>
            <span>/{{ item.total }}</span>
          </div>
        </button>
      </aside>

      <section class="content">
        <RouterView />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchModules, type ModuleSummary } from '../api'

const router = useRouter()
const route = useRoute()
const email = ref(localStorage.getItem('user_email') || '')

const fallbackModules: ModuleSummary[] = [
  {
    id: 'agents',
    title: '智能体',
    subtitle: '管理与调度',
    total: 0,
    active: 0,
    description: '管理智能体实例与运行状态。',
  },
  {
    id: 'models',
    title: '模型',
    subtitle: '能力与成本',
    total: 0,
    active: 0,
    description: '查看模型版本与推理指标。',
  },
]

const modules = ref<ModuleSummary[]>(fallbackModules)
const loading = ref(false)
const error = ref('')

const activeId = computed(() => {
  return (route.meta.module as string) || modules.value[0]?.id || 'agents'
})

const handleModuleClick = async (id: string) => {
  if (id === 'models') {
    await router.push({ name: 'home-models' })
    return
  }
  if (id === 'admin') {
    await router.push({ name: 'home-admin' })
    return
  }
  await router.push({ name: 'home-agents' })
}

const handleLogout = async () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_email')
  await router.push({ name: 'login' })
}

const loadModules = async () => {
  loading.value = true
  error.value = ''

  try {
    modules.value = await fetchModules()
    const activeModuleId = route.meta.module as string | undefined
    if (activeModuleId && !modules.value.some((item) => item.id === activeModuleId)) {
      const first = modules.value[0]?.id
      if (first) {
        await handleModuleClick(first)
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模块加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadModules)
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: grid;
  gap: 24px;
  padding: 32px clamp(20px, 4vw, 48px) 48px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 20px;
  padding: 18px 24px;
  box-shadow: 0 12px 36px rgba(15, 40, 55, 0.1);
}

.brand {
  display: flex;
  align-items: center;
  gap: 18px;
}

.badge {
  display: inline-flex;
  font-size: 12px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #516168;
  background: rgba(15, 179, 185, 0.08);
  padding: 6px 10px;
  border-radius: 999px;
  align-self: flex-start;
}

h1 {
  font-family: 'Space Grotesk', sans-serif;
  margin: 0;
  font-size: 28px;
}

.topbar p {
  margin: 4px 0 0;
  color: #4b5b60;
}

.layout {
  display: grid;
  grid-template-columns: minmax(200px, 240px) 1fr;
  gap: 24px;
}

.sidebar {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 22px;
  padding: 22px;
  display: grid;
  gap: 14px;
  box-shadow: 0 12px 30px rgba(15, 40, 55, 0.1);
}

.sidebar__title {
  margin: 0;
  font-weight: 600;
  color: #3a4a4f;
}

.sidebar__state {
  font-size: 12px;
  color: #6a7a80;
}

.sidebar__state.error {
  color: #b13333;
}

.nav-item {
  text-align: left;
  border: none;
  background: transparent;
  padding: 12px 14px;
  border-radius: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #304045;
  transition: background 0.2s ease, transform 0.2s ease;
}

.nav-item small {
  color: #6a7a80;
  font-size: 12px;
}

.nav-item:hover {
  background: rgba(15, 179, 185, 0.08);
  transform: translateY(-1px);
}

.nav-item.active {
  background: rgba(15, 179, 185, 0.16);
  font-weight: 600;
}

.nav-meta {
  display: grid;
  justify-items: end;
  font-size: 12px;
  color: #5a6a70;
}

.nav-meta strong {
  font-size: 14px;
  color: #0c7e85;
}

.content {
  background: rgba(255, 255, 255, 0.78);
  border-radius: 26px;
  padding: 28px clamp(20px, 4vw, 40px) 32px;
  box-shadow: 0 16px 40px rgba(15, 40, 55, 0.12);
  min-height: 480px;
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

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
