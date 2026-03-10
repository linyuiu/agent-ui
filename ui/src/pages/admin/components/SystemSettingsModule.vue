<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>系统设置</h2>
        <p>统一管理登录方式、默认登录入口和第三方用户自动创建规则。</p>
      </div>
    </div>

    <div class="panel">
      <div v-if="loading" class="state">加载中...</div>
      <div v-else class="settings-layout">
        <div v-if="error" class="state error">{{ error }}</div>

        <div class="settings-card">
          <div class="settings-card__header">
            <div>
              <h3>登录方式</h3>
              <p>统一管理启用的登录入口和默认登录方式。</p>
            </div>
            <span class="tag" :class="{ disabled: !saveMessage }">{{ saveMessage || '未保存' }}</span>
          </div>

          <div class="settings-list">
            <section class="settings-item">
              <div class="settings-item__head">
                <label class="settings-label">登录方式 <span>*</span></label>
              </div>
              <div class="method-grid">
                <label v-for="method in loginMethods" :key="method.value" class="method-option">
                  <input
                    v-model="draft.enabled_methods"
                    type="checkbox"
                    :value="method.value"
                  />
                  <span>{{ method.label }}</span>
                </label>
              </div>
            </section>

            <section class="settings-item">
              <div class="settings-item__head">
                <label class="settings-label">默认登录方式 <span>*</span></label>
              </div>
              <div class="method-grid radios">
                <label
                  v-for="method in enabledMethodOptions"
                  :key="`default-${method.value}`"
                  class="method-option"
                >
                  <input
                    v-model="draft.default_login_method"
                    type="radio"
                    name="default-login-method"
                    :value="method.value"
                  />
                  <span>{{ method.label }}</span>
                </label>
              </div>
            </section>

            <section class="settings-item">
              <div class="settings-item__head">
                <label class="settings-label">第三方用户默认配置 <span>*</span></label>
              </div>
              <div class="third-party-grid">
                <label class="checkbox-item settings-check">
                  <input v-model="draft.auto_create_user" type="checkbox" />
                  自动创建用户
                </label>

                <div ref="roleDropdownRef" class="field select-field">
                  <label>默认角色</label>
                  <div class="inline-dropdown" @click.stop>
                    <button
                      class="filter-trigger inline-trigger"
                      type="button"
                      @click.stop="roleDropdownOpen = !roleDropdownOpen"
                    >
                      <span>{{ draft.default_role }}</span>
                      <span class="caret" :class="{ open: roleDropdownOpen }"></span>
                    </button>
                    <div v-if="roleDropdownOpen" class="filter-dropdown inline-dropdown-panel">
                      <button
                        v-for="role in roleOptions"
                        :key="role"
                        class="filter-option"
                        type="button"
                        @click="selectDefaultRole(role)"
                      >
                        <span>{{ draft.default_role === role ? '✓ ' : '' }}{{ role }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="button-row">
            <button class="primary" type="button" :disabled="saving" @click="handleSave">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { fetchRoles } from '../../../services/system/roles'
import { fetchSystemAuthSettings, updateSystemAuthSettings } from '../../../services/system/sso'
import type { LoginMethod, Role, SystemAuthSetting } from '../../../services/system/types'

type MethodOption = {
  value: LoginMethod
  label: string
}

const loginMethods: MethodOption[] = [
  { value: 'local', label: '账号登录' },
  { value: 'cas', label: 'CAS' },
  { value: 'ldap', label: 'LDAP' },
  { value: 'oidc', label: 'OIDC' },
  { value: 'oauth2', label: 'OAuth2' },
  { value: 'saml2', label: 'SAML2' },
]

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const saveMessage = ref('')
const roles = ref<Role[]>([])
const settings = ref<SystemAuthSetting | null>(null)
const roleDropdownOpen = ref(false)
const roleDropdownRef = ref<HTMLElement | null>(null)
const draft = reactive<{
  enabled_methods: LoginMethod[]
  default_login_method: LoginMethod
  auto_create_user: boolean
  default_role: string
}>({
  enabled_methods: ['local'],
  default_login_method: 'local',
  auto_create_user: true,
  default_role: 'user',
})

const roleOptions = computed(() => {
  const names = roles.value.map((item) => item.name)
  return names.length ? names : ['user']
})

const enabledMethodOptions = computed(() =>
  loginMethods.filter((item) => draft.enabled_methods.includes(item.value))
)

const selectDefaultRole = (role: string) => {
  draft.default_role = role
  roleDropdownOpen.value = false
}

const applySettings = (payload: SystemAuthSetting) => {
  settings.value = payload
  draft.enabled_methods = [...payload.enabled_methods]
  draft.default_login_method = payload.default_login_method
  draft.auto_create_user = payload.auto_create_user
  draft.default_role = payload.default_role || 'user'
}

watch(
  () => [...draft.enabled_methods],
  (methods) => {
    if (!methods.length) {
      draft.enabled_methods = ['local']
      return
    }
    if (!methods.includes(draft.default_login_method)) {
      draft.default_login_method = methods.includes('local') ? 'local' : methods[0]
    }
  },
  { deep: false }
)

const loadData = async () => {
  loading.value = true
  error.value = ''
  try {
    const [settingsPayload, rolesPayload] = await Promise.all([
      fetchSystemAuthSettings(),
      fetchRoles(),
    ])
    roles.value = rolesPayload
    applySettings(settingsPayload)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载系统设置失败'
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!draft.enabled_methods.length) {
    error.value = '至少启用一种登录方式'
    return
  }
  if (!draft.enabled_methods.includes(draft.default_login_method)) {
    error.value = '默认登录方式必须在已启用的登录方式中'
    return
  }

  saving.value = true
  error.value = ''
  saveMessage.value = ''
  try {
    const saved = await updateSystemAuthSettings({
      enabled_methods: draft.enabled_methods,
      default_login_method: draft.default_login_method,
      auto_create_user: draft.auto_create_user,
      default_role: draft.default_role,
    })
    applySettings(saved)
    saveMessage.value = '已保存'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存系统设置失败'
  } finally {
    saving.value = false
  }
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (roleDropdownRef.value && target && !roleDropdownRef.value.contains(target)) {
    roleDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  void loadData()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped src="./SystemSettingsModule.css"></style>
