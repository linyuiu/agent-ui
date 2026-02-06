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
            </button>

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
                  <button class="menu-item" type="button" @click="goTo('home-admin')">
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchModules, type ModuleSummary } from '../services/dashboard'

const router = useRouter()
const route = useRoute()
const email = ref(localStorage.getItem('user_email') || '')
const username = ref(localStorage.getItem('user_name') || '')
const account = ref(localStorage.getItem('user_account') || '')
const role = ref(localStorage.getItem('user_role') || '')
const showMenu = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const modules = ref<ModuleSummary[]>([])
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
  localStorage.removeItem('user_role')
  localStorage.removeItem('user_name')
  localStorage.removeItem('user_account')
  localStorage.removeItem('user_permissions')
  showMenu.value = false
  await router.push({ name: 'login' })
}

const toggleMenu = () => {
  showMenu.value = !showMenu.value
}

const goTo = async (name: string) => {
  showMenu.value = false
  await router.push({ name })
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
</script>

<style scoped>
.home {
  --page-gap: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: var(--page-gap);
  padding: 16px clamp(20px, 4vw, 48px);
  box-sizing: border-box;
  overflow: hidden;
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
  height: 84px;
  min-height: 84px;
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
  gap: var(--page-gap);
  flex: 1;
  min-height: 0;
}

.sidebar {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 22px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 12px 30px rgba(15, 40, 55, 0.1);
  overflow: hidden;
}

.sidebar__block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.sidebar__title {
  margin: 0;
  font-weight: 600;
  color: #3a4a4f;
}

.sidebar__menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
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
  border: 1px solid rgba(15, 40, 55, 0.1);
  background: transparent;
  padding: 10px 12px;
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


.content {
  background: rgba(255, 255, 255, 0.78);
  border-radius: 26px;
  padding: 28px clamp(20px, 4vw, 40px) 32px;
  box-shadow: 0 16px 40px rgba(15, 40, 55, 0.12);
  min-height: 0;
  overflow-y: auto;
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

.user-menu.bottom {
  margin-top: auto;
}

.user-menu {
  position: relative;
  width: 100%;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 12px;
  border: none;
  background: #fff;
  padding: 10px 14px;
  border-radius: 16px;
  box-shadow: 0 8px 20px rgba(15, 40, 55, 0.12);
  cursor: pointer;
  width: 100%;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 30%, #4be0a5, #1aa27a);
}

.avatar.large {
  width: 48px;
  height: 48px;
  border-radius: 16px;
}

.user-meta {
  display: grid;
  text-align: left;
  min-width: 0;
}

.user-meta strong {
  font-size: 14px;
  color: #2f3f44;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-meta small {
  font-size: 12px;
  color: #6a7a80;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  width: 10px;
  height: 10px;
  border-right: 2px solid #5c6b71;
  border-bottom: 2px solid #5c6b71;
  transform: rotate(45deg);
  transition: transform 0.2s ease;
  margin-left: auto;
}

.chevron.open {
  transform: rotate(-135deg);
}

.menu-card {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 12px);
  width: auto;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 16px 40px rgba(15, 40, 55, 0.2);
  border: 1px solid rgba(15, 40, 55, 0.08);
  padding: 12px;
  z-index: 20;
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px 12px;
  border-bottom: 1px solid rgba(15, 40, 55, 0.08);
}

.menu-header strong {
  font-size: 14px;
  color: #2d3c41;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-header small {
  display: block;
  font-size: 12px;
  color: #6a7a80;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-items {
  display: grid;
  gap: 6px;
  padding: 10px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: #2f3f44;
}

.menu-item:hover {
  background: rgba(15, 179, 185, 0.12);
}

.menu-item.danger {
  color: #b13333;
}

.menu-footer {
  border-top: 1px solid rgba(15, 40, 55, 0.08);
  padding-top: 8px;
}

.icon {
  width: 20px;
  height: 20px;
  border-radius: 8px;
  background: rgba(15, 179, 185, 0.12);
  position: relative;
}

.icon::after {
  content: '';
  position: absolute;
  inset: 6px;
  border-radius: 4px;
  background: #0fb3b9;
}

.icon.lock::after {
  background: #3a87c6;
}

.icon.key::after {
  background: #f5a524;
}

.icon.globe::after {
  background: #7a6ff0;
}

.icon.info::after {
  background: #5b6b71;
}

.icon.help::after {
  background: #ff7f50;
}

.icon.logout::after {
  background: #d35454;
}

.chevron-sm {
  margin-left: auto;
  width: 8px;
  height: 8px;
  border-right: 2px solid #98a2a8;
  border-bottom: 2px solid #98a2a8;
  transform: rotate(-45deg);
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
