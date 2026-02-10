<template>
  <div class="page">
    <div class="orb orb-1" aria-hidden="true"></div>
    <div class="orb orb-2" aria-hidden="true"></div>
    <div class="orb orb-3" aria-hidden="true"></div>

    <main class="card">
      <header class="card__header">
        <p class="eyebrow">Agent UI</p>
        <h1>欢迎回来</h1>
        <p class="subtitle">使用账号和密码登录，继续你的工作流。</p>
      </header>

      <form class="form" @submit.prevent="handleSubmit">
        <label class="field">
          <span>登录方式</span>
          <select v-model="passwordProviderKey">
            <option value="">本地账号</option>
            <option v-for="provider in passwordProviders" :key="provider.key" :value="provider.key">
              {{ provider.name }} ({{ provider.protocol }})
            </option>
          </select>
        </label>

        <label class="field">
          <span>账号</span>
          <input
            v-model="account"
            type="text"
            placeholder="demo"
            autocomplete="username"
            required
          />
        </label>

        <label class="field">
          <span>密码</span>
          <div class="input-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="至少 6 位"
              autocomplete="current-password"
              required
            />
            <button
              class="toggle"
              type="button"
              :aria-pressed="showPassword"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <svg
                v-if="showPassword"
                class="eye-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <circle
                  cx="12"
                  cy="12"
                  r="3"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                />
              </svg>
              <svg
                v-else
                class="eye-icon"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  d="M3 4.5 21 19.5"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                />
                <path
                  d="M6.6 7.3C4.2 9 2.7 12 2.7 12s3.5 7 10 7c2.2 0 4.1-.7 5.6-1.7"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  d="M9 5.5a9.7 9.7 0 0 1 3-.5c6.5 0 10 7 10 7s-1.4 2.7-4.4 4.7"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </button>
          </div>
        </label>

        <button class="submit" type="submit" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else>登录中...</span>
        </button>
      </form>

      <p v-if="error" class="notice notice--error">{{ error }}</p>

      <div v-if="redirectProviders.length" class="sso-block">
        <p class="sso-title">单点登录</p>
        <div class="sso-actions">
          <button
            v-for="provider in redirectProviders"
            :key="provider.key"
            class="ghost sso-btn"
            type="button"
            @click="handleRedirectSso(provider.key)"
          >
            {{ provider.name }}
          </button>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { createChatSession } from '../../services/chat-session'
import {
  buildSsoStartUrl,
  fetchEnabledSsoProviders,
  ssoPasswordLogin,
  type SsoProviderPublic,
} from '../../services/sso'
import { persistAuthSession } from '../../utils/auth-storage'

const route = useRoute()
const router = useRouter()

const account = ref('')
const password = ref('')
const passwordProviderKey = ref('')
const ssoProviders = ref<SsoProviderPublic[]>([])
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const redirectProviders = computed(() => ssoProviders.value.filter((item) => item.login_mode === 'redirect'))
const passwordProviders = computed(() => ssoProviders.value.filter((item) => item.login_mode === 'password'))

const getRedirectTarget = () =>
  typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : ''

const persistPermissions = async (token: string) => {
  try {
    const permResponse = await fetch(`${apiBase}/auth/permissions`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (permResponse.ok) {
      const permPayload = await permResponse.json()
      persistAuthSession({ permissions: permPayload })
    }
  } catch {
    // ignore permission fetch failures on login
  }
}

const finalizeLogin = async (payload: { access_token?: string; user?: unknown }) => {
  const token = payload?.access_token || ''
  if (!token) throw new Error('登录响应缺少 token')
  persistAuthSession({
    token,
    user: payload?.user as Record<string, unknown>,
  })
  await persistPermissions(token)

  const redirectTarget = getRedirectTarget()
  const isChatRedirect = redirectTarget.startsWith('/chat/')
  if (isChatRedirect) {
    await createChatSession()
    window.location.assign(redirectTarget)
    return
  }
  createChatSession().catch(() => undefined)
  if (redirectTarget) {
    await router.push(redirectTarget)
    return
  }
  await router.push({ name: 'home-agents' })
}

const handleSubmit = async () => {
  error.value = ''
  loading.value = true

  try {
    if (passwordProviderKey.value) {
      const payload = await ssoPasswordLogin({
        provider_key: passwordProviderKey.value,
        account: account.value,
        password: password.value,
      })
      await finalizeLogin(payload)
      return
    }

    const response = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        account: account.value,
        password: password.value,
      }),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = payload?.detail
      throw new Error(typeof detail === 'string' ? detail : '登录失败，请检查账号密码。')
    }
    await finalizeLogin(payload)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

const handleRedirectSso = (providerKey: string) => {
  const redirectTarget = getRedirectTarget() || '/home/agents'
  window.location.assign(buildSsoStartUrl(providerKey, redirectTarget))
}

const consumeSsoHashToken = async () => {
  const hash = window.location.hash.replace(/^#/, '')
  if (!hash) return
  const hashParams = new URLSearchParams(hash)
  const token = hashParams.get('token') || ''
  if (!token) return

  loading.value = true
  error.value = ''
  try {
    const meResp = await fetch(`${apiBase}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (!meResp.ok) {
      throw new Error('单点登录状态失效，请重新登录')
    }
    const user = await meResp.json()
    history.replaceState(null, '', window.location.pathname + window.location.search)
    await finalizeLogin({ access_token: token, user })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '单点登录失败'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  ssoProviders.value = await fetchEnabledSsoProviders()
  await consumeSsoHashToken()
})
</script>

<style scoped src="./LoginView.css"></style>
