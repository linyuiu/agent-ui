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
import { changePassword } from '../../services/auth'
import { clearAuthStorage } from '../../utils/auth-storage'

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
    clearAuthStorage()
    await router.push({ name: 'login' })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    loading.value = false
  }
}
</script>
