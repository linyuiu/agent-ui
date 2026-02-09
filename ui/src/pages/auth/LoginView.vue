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

    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { persistAuthSession } from '../../utils/auth-storage'

const router = useRouter()

const account = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const handleSubmit = async () => {
  error.value = ''
  loading.value = true

  try {
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
      const message = typeof detail === 'string' ? detail : '登录失败，请检查账号密码。'
      throw new Error(message)
    }

    const token = payload?.access_token
    persistAuthSession({
      token,
      user: payload?.user,
    })

    if (token) {
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

    await router.push({ name: 'home-agents' })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="./LoginView.css"></style>
