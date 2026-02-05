<template>
  <div class="info-view">
    <div class="panel">
      <div class="panel-header">
        <h2>修改密码</h2>
        <p>为当前登录账户设置新的密码。</p>
      </div>
      <div class="panel-body">
        <form class="form" @submit.prevent="handleSubmit">
          <div class="field">
            <label>当前密码</label>
            <input v-model="currentPassword" type="password" required />
          </div>
          <div class="field">
            <label>新密码</label>
            <input v-model="newPassword" type="password" required />
          </div>
          <div class="field">
            <label>确认新密码</label>
            <input v-model="confirmPassword" type="password" required />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="loading">
              {{ loading ? '保存中...' : '保存密码' }}
            </button>
          </div>
        </form>

        <p v-if="error" class="state error">{{ error }}</p>
        <p v-if="success" class="state success">{{ success }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { changePassword } from '../api/auth'

const router = useRouter()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

const handleSubmit = async () => {
  error.value = ''
  success.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    success.value = '密码已更新，请重新登录。'
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_email')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_name')
    localStorage.removeItem('user_account')
    localStorage.removeItem('user_permissions')
    await router.push({ name: 'login' })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.info-view {
  display: grid;
  gap: 16px;
}

.panel {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 24px;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.panel-header h2 {
  margin: 0 0 6px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 24px;
}

.panel-header p {
  margin: 0;
  color: #5b6b71;
}

.panel-body {
  margin-top: 18px;
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.field label {
  color: #5a6a70;
}

.field input {
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 10px 12px;
  font-size: 14px;
}

.button-row {
  display: flex;
  gap: 10px;
}

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.state {
  font-size: 13px;
  color: #5a6a70;
  margin-top: 12px;
}

.state.error {
  color: #b13333;
}

.state.success {
  color: #0f6b4f;
}
</style>
