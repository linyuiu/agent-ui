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

      <form v-if="showPasswordForm" class="form" @submit.prevent="handleSubmit">
        <div class="form-title-row">
          <h2 class="form-title">账号登录</h2>
          <button
            v-if="selectedPasswordProvider && localLoginEnabled"
            class="ghost switch-btn"
            type="button"
            @click="resetToLocalLogin"
          >
            使用本地登录
          </button>
        </div>

        <p v-if="selectedPasswordProvider" class="provider-hint">
          当前使用 {{ selectedPasswordProvider.name }} 登录
        </p>

        <div v-if="bindMessage" class="notice notice--warning">
          <strong>{{ bindProviderName || '单点登录' }}</strong>
          <span>{{ bindMessage }}</span>
        </div>

        <div v-if="bindSuccessMessage" class="notice notice--success">
          <strong>绑定成功</strong>
          <span>{{ bindSuccessMessage }}</span>
        </div>

        <label class="field">
          <span>账号</span>
          <input v-model="account" type="text" placeholder="账号/邮箱" autocomplete="username" required />
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
              <svg v-if="showPassword" class="eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.6" />
              </svg>
              <svg v-else class="eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 4.5 21 19.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
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

      <div v-if="otherProviders.length" class="sso-block">
        <div class="sso-divider">
          <span>其他登录方式</span>
        </div>
        <div class="sso-actions">
          <button
            v-for="provider in otherProviders"
            :key="provider.key"
            class="ghost sso-btn"
            :class="{ active: selectedPasswordProvider?.key === provider.key }"
            type="button"
            :title="provider.name"
            @click="handleProviderShortcut(provider)"
          >
            <span class="sso-btn__icon">{{ providerIcon(provider) }}</span>
            <span class="sso-btn__label">{{ providerShortcutLabel(provider) }}</span>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createChatSession } from '../../services/chat-session'
import {
  bindSsoIdentity,
  buildSsoStartUrl,
  fetchSsoLoginOptions,
  ssoPasswordLogin,
  type SsoBindPending,
  type SsoProviderPublic,
} from '../../services/sso'
import { clearAuthSession, persistAuthSession, type AuthUserSnapshot } from '../../utils/auth-storage'
import { clearCachedLoginKey, encryptLoginCredentials } from '../../utils/login-crypto'

const route = useRoute()
const router = useRouter()

const account = ref('')
const password = ref('')
const passwordProviderKey = ref('')
const ssoProviders = ref<SsoProviderPublic[]>([])
const localLoginEnabled = ref(true)
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const bindMessage = ref('')
const bindProviderName = ref('')
const pendingBindToken = ref('')
const bindSuccessMessage = ref('')

const apiBase = import.meta.env.VITE_API_BASE_URL || ''

const passwordProviders = computed(() => ssoProviders.value.filter((item) => item.login_mode === 'password'))
const otherProviders = computed(() =>
  ssoProviders.value.filter((item) => item.key !== selectedPasswordProvider.value?.key)
)
const selectedPasswordProvider = computed(() =>
  passwordProviders.value.find((item) => item.key === passwordProviderKey.value) || null
)
const showPasswordForm = computed(
  () => localLoginEnabled.value || passwordProviders.value.length > 0 || !!pendingBindToken.value
)

const getRedirectTarget = () =>
  typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : ''

const providerShortcutLabel = (provider: SsoProviderPublic) => {
  const protocol = provider.protocol.toUpperCase()
  return protocol === 'OAUTH2' ? 'OAuth2' : protocol
}

const providerIcon = (provider: SsoProviderPublic) => {
  const protocol = provider.protocol.toUpperCase()
  if (protocol === 'OAUTH2') return 'OA'
  return protocol.slice(0, 2)
}

const resetToLocalLogin = () => {
  passwordProviderKey.value = ''
}

const applyLoginOptions = (payload: {
  enabled_methods: Array<'local' | 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'>
  default_login_method: 'local' | 'ldap' | 'cas' | 'oidc' | 'oauth2' | 'saml2'
  providers: SsoProviderPublic[]
}) => {
  ssoProviders.value = payload.providers
  localLoginEnabled.value = payload.enabled_methods.includes('local')
  passwordProviderKey.value = ''

  if (payload.default_login_method === 'local') return
  const defaultPasswordProvider = payload.providers.find(
    (item) => item.protocol === payload.default_login_method && item.login_mode === 'password'
  )
  if (defaultPasswordProvider) {
    passwordProviderKey.value = defaultPasswordProvider.key
  }
}

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

const setBindPending = (payload: SsoBindPending) => {
  pendingBindToken.value = payload.bind_token
  bindMessage.value = payload.message
  bindProviderName.value = payload.provider_name
  bindSuccessMessage.value = ''
  resetToLocalLogin()
}

const syncSessionExpiresAt = (response: Response) => {
  const expiresAt = response.headers.get('x-session-expires-at')
  if (expiresAt) {
    persistAuthSession({ sessionExpiresAt: expiresAt })
  }
}

const persistPermissions = async () => {
  try {
    const permResponse = await fetch(`${apiBase}/auth/permissions`, {
      credentials: 'include',
    })
    syncSessionExpiresAt(permResponse)
    if (permResponse.ok) {
      const permPayload = await permResponse.json()
      persistAuthSession({ permissions: permPayload })
    }
  } catch {
    // ignore permission fetch failures on login
  }
}

const finalizeLogin = async (payload: {
  access_token?: string
  user?: unknown
  permissions?: unknown
  session_expires_at?: string
}) => {
  persistAuthSession({
    user: payload?.user as AuthUserSnapshot,
    permissions: payload?.permissions,
    sessionExpiresAt: payload?.session_expires_at,
  })
  if (typeof payload?.permissions === 'undefined') {
    await persistPermissions()
  }

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

const parseLoginError = (payload: unknown, fallback: string) => {
  const detail = (payload as { detail?: unknown })?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown; msg?: unknown })?.message || (detail as { msg?: unknown })?.msg
    if (typeof message === 'string' && message.trim()) return message
  }
  return fallback
}

const shouldRetryWithFreshLoginKey = (err: unknown) => {
  const message = err instanceof Error ? err.message : String(err || '')
  return (
    message.includes('登录密钥已过期') ||
    message.includes('登录数据解密失败') ||
    message.includes('登录凭据处理失败') ||
    message.includes('登录凭据解密失败')
  )
}

const submitLoginOnce = async () => {
  const encrypted = await encryptLoginCredentials(account.value, password.value)
  if (passwordProviderKey.value) {
    const result = await ssoPasswordLogin({
      provider_key: passwordProviderKey.value,
      encrypted_payload: encrypted.encrypted_payload,
      key_id: encrypted.key_id,
    })
    if (result.type === 'bind_required') {
      setBindPending(result.payload)
      return
    }
    await finalizeLogin(result.payload)
    return
  }

  const response = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      encrypted_payload: encrypted.encrypted_payload,
      key_id: encrypted.key_id,
    }),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(parseLoginError(payload, '登录失败，请检查账号密码。'))
  }

  if (pendingBindToken.value) {
    try {
      await bindSsoIdentity(pendingBindToken.value)
      bindSuccessMessage.value = `${bindProviderName.value || '单点账号'} 已绑定到当前本地账号，正在进入系统。`
      pendingBindToken.value = ''
      bindMessage.value = ''
      await wait(1000)
      bindProviderName.value = ''
    } catch (err) {
      clearAuthSession()
      throw err
    }
  }

  await finalizeLogin(payload)
}

const handleSubmit = async () => {
  error.value = ''
  bindSuccessMessage.value = ''
  loading.value = true

  try {
    try {
      await submitLoginOnce()
    } catch (err) {
      if (!shouldRetryWithFreshLoginKey(err)) {
        throw err
      }
      clearCachedLoginKey()
      await submitLoginOnce()
    }
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

const handleProviderShortcut = (provider: SsoProviderPublic) => {
  if (provider.login_mode === 'password') {
    passwordProviderKey.value = provider.key
    return
  }
  handleRedirectSso(provider.key)
}

const consumeCookieLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const meResp = await fetch(`${apiBase}/auth/me`, {
      credentials: 'include',
    })
    if (!meResp.ok) {
      return
    }
    syncSessionExpiresAt(meResp)
    const user = await meResp.json()
    await finalizeLogin({ user })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '单点登录失败'
  } finally {
    loading.value = false
  }
}

const consumeBindQuery = () => {
  const bindToken = typeof route.query.bind_token === 'string' ? route.query.bind_token : ''
  const bindText = typeof route.query.bind_message === 'string' ? route.query.bind_message : ''
  const providerName = typeof route.query.bind_provider === 'string' ? route.query.bind_provider : ''
  if (!bindToken) return
  pendingBindToken.value = bindToken
  bindMessage.value = bindText || '请先使用本地账号登录后完成绑定'
  bindProviderName.value = providerName
}

onMounted(async () => {
  applyLoginOptions(await fetchSsoLoginOptions())
  consumeBindQuery()
  if (route.query.sso === '1') {
    await consumeCookieLogin()
  }
})
</script>

<style scoped src="./LoginView.css"></style>
