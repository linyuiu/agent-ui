<template>
  <div class="home">
    <header class="topbar">
      <div class="brand">
        <span class="badge">Agent UI</span>
        <div>
          <h1>控制台</h1>
          <p>欢迎回来，{{ username || account || email || '同学' }}</p>
        </div>
      </div>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <div class="sidebar__block">
          <p class="sidebar__title">模块</p>
          <div v-if="loading" class="sidebar__state">加载模块中...</div>
          <div v-if="error" class="sidebar__state error">{{ error }}</div>

        <div class="sidebar__menu">
            <template v-for="item in sidebarModules" :key="item.id">
              <div v-if="item.id === 'admin'" class="nav-group" :class="{ open: adminMenuOpen }">
                <button
                  class="nav-item nav-group-trigger"
                  :class="{ active: adminGroupActive }"
                  type="button"
                  @click="handleAdminModuleClick"
                >
                  <div>
                    <span>{{ getModuleTitle(item) }}</span>
                    <small v-if="getModuleSubtitle(item)">{{ getModuleSubtitle(item) }}</small>
                  </div>
                  <span class="group-caret" :class="{ open: adminMenuOpen }"></span>
                </button>
                <transition name="slide-fade">
                  <div v-if="adminMenuOpen" class="nav-submenu">
                    <button
                      class="nav-sub-item"
                      :class="{ active: activeSystemSubmodule === 'user-role' }"
                      type="button"
                      @click="goToAdminSubmodule('user-role')"
                    >
                      用户角色管理
                    </button>
                    <button
                      class="nav-sub-item"
                      :class="{ active: activeSystemSubmodule === 'permissions' }"
                      type="button"
                      @click="goToAdminSubmodule('permissions')"
                    >
                      权限管理
                    </button>
                    <button
                      class="nav-sub-item"
                      :class="{ active: activeSystemSubmodule === 'models' }"
                      type="button"
                      @click="goToModelsModule"
                    >
                      模型
                    </button>
                    <button
                      class="nav-sub-item"
                      :class="{ active: activeSystemSubmodule === 'agent-sync' }"
                      type="button"
                      @click="goToAdminSubmodule('agent-sync')"
                    >
                      智能体同步
                    </button>
                  </div>
                </transition>
              </div>

              <button
                v-else
                class="nav-item"
                :class="{ active: item.id === activeId }"
                type="button"
                @click="handleModuleClick(item.id)"
              >
                <div>
                  <span>{{ getModuleTitle(item) }}</span>
                  <small v-if="getModuleSubtitle(item)">{{ getModuleSubtitle(item) }}</small>
                </div>
              </button>
            </template>

            <div ref="menuRef" class="user-menu bottom">
              <button class="user-trigger" type="button" @click="toggleMenu">
                <span class="avatar"></span>
                <span class="user-meta">
            <strong>{{ username || account || email || 'Administrator' }}</strong>
                  <small>{{ role || 'admin' }}</small>
                </span>
                <span class="chevron" :class="{ open: showMenu }"></span>
              </button>

              <div v-if="showMenu" class="menu-card">
                <div class="menu-header">
                  <span class="avatar large"></span>
                  <div>
              <strong>{{ username || account || email || 'Administrator' }}</strong>
                    <small>{{ role || 'admin' }}</small>
                  </div>
                </div>
                <div class="menu-items">
                  <button class="menu-item" type="button" @click="goToAdminHome">
                    <span class="icon system"></span>
                    <span>系统管理</span>
                  </button>
                  <button class="menu-item" type="button" @click="goTo('home-password')">
                    <span class="icon lock"></span>
                    <span>修改密码</span>
                  </button>
                  <button class="menu-item" type="button" @click="goTo('home-apikey')">
                    <span class="icon key"></span>
                    <span>API Key</span>
                  </button>
                  <button class="menu-item" type="button" @click="goTo('home-language')">
                    <span class="icon globe"></span>
                    <span>语言</span>
                    <span class="chevron-sm"></span>
                  </button>
                  <button class="menu-item" type="button" @click="goTo('home-about')">
                    <span class="icon info"></span>
                    <span>关于</span>
                  </button>
                  <button class="menu-item" type="button" @click="goTo('home-help')">
                    <span class="icon help"></span>
                    <span>帮助</span>
                  </button>
                </div>
                <div class="menu-footer">
                  <button class="menu-item danger" type="button" @click="handleLogout">
                    <span class="icon logout"></span>
                    <span>退出登录</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <section class="content">
        <RouterView />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchModules, type ModuleSummary } from '../services/dashboard'
import { clearAuthStorage } from '../utils/auth-storage'

const router = useRouter()
const route = useRoute()
const email = ref(localStorage.getItem('user_email') || '')
const username = ref(localStorage.getItem('user_name') || '')
const account = ref(localStorage.getItem('user_account') || '')
const role = ref(localStorage.getItem('user_role') || '')
const showMenu = ref(false)
const menuRef = ref<HTMLElement | null>(null)
const adminMenuOpen = ref(false)

const modules = ref<ModuleSummary[]>([])
const loading = ref(false)
const error = ref('')

const activeId = computed(() => {
  return (route.meta.module as string) || modules.value[0]?.id || 'agents'
})

const isModelsRoute = computed(() => (route.meta.module as string) === 'models')
const adminGroupActive = computed(() => activeId.value === 'admin' || isModelsRoute.value)
const sidebarModules = computed(() => modules.value.filter((item) => item.id !== 'models'))

const adminSubmoduleList = ['user-role', 'permissions', 'agent-sync'] as const
type AdminSubmodule = (typeof adminSubmoduleList)[number]

const normalizeAdminSubmodule = (value: unknown): AdminSubmodule => {
  const text = String(value || '')
  if (adminSubmoduleList.includes(text as AdminSubmodule)) {
    return text as AdminSubmodule
  }
  return 'user-role'
}

const activeAdminSubmodule = computed<AdminSubmodule>(() => normalizeAdminSubmodule(route.query.tab))
const activeSystemSubmodule = computed(() => {
  if (isModelsRoute.value) return 'models'
  return activeAdminSubmodule.value
})

const getModuleTitle = (item: ModuleSummary) => {
  if (item.id === 'agents') return '智能体'
  if (item.id === 'models') return '模型'
  if (item.id === 'admin') return '系统管理'
  return item.title
}

const getModuleSubtitle = (_item: ModuleSummary) => ''

const handleAdminModuleClick = async () => {
  if ((route.meta.module as string) !== 'admin') {
    adminMenuOpen.value = true
    await router.push({ name: 'home-admin', query: { tab: 'user-role' } })
    return
  }

  adminMenuOpen.value = !adminMenuOpen.value
  if (adminMenuOpen.value && !route.query.tab) {
    await router.replace({ name: 'home-admin', query: { tab: 'user-role' } })
  }
}

const goToAdminSubmodule = async (tab: AdminSubmodule) => {
  adminMenuOpen.value = true
  await router.push({ name: 'home-admin', query: { tab } })
}

const goToModelsModule = async () => {
  adminMenuOpen.value = true
  await router.push({ name: 'home-models' })
}

const handleModuleClick = async (id: string) => {
  if (id === 'admin') {
    await handleAdminModuleClick()
    return
  }
  adminMenuOpen.value = false
  if (id === 'models') {
    await router.push({ name: 'home-models' })
    return
  }
  await router.push({ name: 'home-agents' })
}

const handleLogout = async () => {
  clearAuthStorage()
  showMenu.value = false
  await router.push({ name: 'login' })
}

const toggleMenu = () => {
  showMenu.value = !showMenu.value
}

const goTo = async (name: string) => {
  showMenu.value = false
  if (name !== 'home-admin') {
    adminMenuOpen.value = false
  }
  await router.push({ name })
}

const goToAdminHome = async () => {
  showMenu.value = false
  adminMenuOpen.value = true
  await router.push({ name: 'home-admin', query: { tab: activeAdminSubmodule.value } })
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
    modules.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadModules)
onMounted(() => {
  const moduleId = route.meta.module as string
  if (moduleId === 'admin' || moduleId === 'models') {
    adminMenuOpen.value = true
  }
})

const handleClickOutside = (event: MouseEvent) => {
  if (!showMenu.value) return
  const target = event.target as Node
  if (menuRef.value && !menuRef.value.contains(target)) {
    showMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(
  () => route.fullPath,
  () => {
    const moduleId = route.meta.module as string
    if (moduleId === 'admin' || moduleId === 'models') {
      adminMenuOpen.value = true
    }
  }
)
</script>

<style scoped src="./AppShell.css"></style>
