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

      <div class="hint">
        <span>本地开发提示：</span>
        <span>使用 `backend/scripts/seed_user.py` 创建演示用户。</span>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

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
    if (token) {
      localStorage.setItem('access_token', token)
    }
    if (payload?.user?.email) {
      localStorage.setItem('user_email', payload.user.email)
    }
    if (payload?.user?.username) {
      localStorage.setItem('user_name', payload.user.username)
    }
    if (payload?.user?.account) {
      localStorage.setItem('user_account', payload.user.account)
    }
    if (payload?.user?.role) {
      localStorage.setItem('user_role', payload.user.role)
    }

    if (token) {
      try {
        const permResponse = await fetch(`${apiBase}/auth/permissions`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
        if (permResponse.ok) {
          const permPayload = await permResponse.json()
          localStorage.setItem('user_permissions', JSON.stringify(permPayload))
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

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 48px 20px;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(2px);
  opacity: 0.6;
  animation: float 12s ease-in-out infinite;
}

.orb-1 {
  width: 260px;
  height: 260px;
  background: radial-gradient(circle at 30% 30%, #ffb86b, #ff7f50);
  top: -60px;
  left: -40px;
}

.orb-2 {
  width: 220px;
  height: 220px;
  background: radial-gradient(circle at 30% 30%, #5ce1e6, #0fb3b9);
  bottom: -40px;
  right: -30px;
  animation-delay: -3s;
}

.orb-3 {
  width: 140px;
  height: 140px;
  background: radial-gradient(circle at 30% 30%, #ffd29f, #ff9b6a);
  top: 40%;
  right: 10%;
  animation-delay: -6s;
}

.card {
  position: relative;
  z-index: 1;
  width: min(420px, 92vw);
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 28px;
  box-shadow: 0 20px 60px rgba(15, 40, 55, 0.18);
  padding: 36px 34px 30px;
  backdrop-filter: blur(12px);
  animation: rise 0.8s ease both;
}

.card__header h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 30px;
  margin: 8px 0 6px;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin: 0;
  color: #5a6b70;
}

.subtitle {
  margin: 0 0 24px;
  color: #506067;
  font-size: 14px;
}

.form {
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
  font-size: 14px;
  color: #2b3b40;
}

.field input {
  border-radius: 14px;
  border: 1px solid #d6e0e2;
  padding: 12px 14px;
  font-size: 15px;
  background: #fff;
  transition: border 0.2s ease, box-shadow 0.2s ease;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrap input {
  width: 100%;
  padding-right: 68px;
}

.toggle {
  position: absolute;
  right: 10px;
  border: none;
  background: rgba(15, 179, 185, 0.08);
  color: #0a7e84;
  padding: 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.toggle:hover {
  background: rgba(15, 179, 185, 0.16);
  transform: translateY(-1px);
}

.toggle:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(15, 179, 185, 0.2);
}

.eye-icon {
  width: 18px;
  height: 18px;
}

.field input:focus {
  outline: none;
  border-color: #0fb3b9;
  box-shadow: 0 0 0 3px rgba(15, 179, 185, 0.15);
}

.submit {
  margin-top: 8px;
  border: none;
  border-radius: 14px;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(120deg, #ff7f50, #ff9b6a);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  box-shadow: 0 12px 30px rgba(255, 127, 80, 0.35);
}

.submit:hover {
  transform: translateY(-1px);
}

.submit:disabled {
  cursor: not-allowed;
  opacity: 0.7;
  transform: none;
  box-shadow: none;
}

.notice {
  margin-top: 16px;
  font-size: 14px;
  padding: 10px 12px;
  border-radius: 12px;
}

.notice--error {
  background: rgba(255, 94, 94, 0.12);
  color: #b13333;
}

.hint {
  margin-top: 18px;
  font-size: 12px;
  color: #6c7b80;
  display: grid;
  gap: 4px;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(18px);
  }
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
