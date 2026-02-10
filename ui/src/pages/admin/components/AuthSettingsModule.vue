<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>登录系统</h2>
        <p>配置 LDAP、CAS、OIDC、OAuth2、SAML2 单点登录。</p>
      </div>
    </div>

    <div class="panel auth-settings-panel">
      <div class="sso-tab-row">
        <button
          v-for="tab in protocolTabs"
          :key="tab.protocol"
          class="sso-tab"
          :class="{ active: activeProtocol === tab.protocol }"
          type="button"
          @click="activeProtocol = tab.protocol"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="sso-form-wrap">
        <form class="sso-form-grid" @submit.prevent="handleSave">
          <template v-if="activeProtocol === 'ldap'">
            <div class="field">
              <label>LDAP 地址 <span class="required">*</span></label>
              <input v-model="forms.ldap.server_url" type="text" placeholder="ldap://10.1.11.41" required />
            </div>
            <div class="field">
              <label>绑定 DN <span class="required">*</span></label>
              <input v-model="forms.ldap.bind_dn" type="text" placeholder="cn=admin,dc=example,dc=com" />
            </div>
            <div class="field">
              <label>密码</label>
              <div class="password-field">
                <input
                  v-model="forms.ldap.bind_password"
                  :type="showLdapPassword ? 'text' : 'password'"
                  placeholder="绑定账号密码"
                />
                <button class="password-toggle" type="button" @click="showLdapPassword = !showLdapPassword">
                  {{ showLdapPassword ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field">
              <label>用户 OU(Base DN) <span class="required">*</span></label>
              <input v-model="forms.ldap.base_dn" type="text" placeholder="ou=users,dc=example,dc=com" required />
            </div>
            <div class="field">
              <label>用户过滤器</label>
              <input v-model="forms.ldap.user_filter" type="text" placeholder="(uid={account})" />
            </div>
            <div class="field">
              <label>账号属性</label>
              <input v-model="forms.ldap.account_attr" type="text" placeholder="uid" />
            </div>
          </template>

          <template v-else-if="activeProtocol === 'cas'">
            <div class="field">
              <label>CAS 地址 <span class="required">*</span></label>
              <input
                v-model="forms.cas.cas_base_url"
                type="text"
                placeholder="https://cas.example.com/cas"
                required
              />
            </div>
            <div class="field">
              <label>登录地址</label>
              <input v-model="forms.cas.login_url" type="text" placeholder="https://cas.example.com/cas/login" />
            </div>
            <div class="field">
              <label>票据校验地址</label>
              <input
                v-model="forms.cas.validate_url"
                type="text"
                placeholder="https://cas.example.com/cas/serviceValidate"
              />
            </div>
          </template>

          <template v-else-if="activeProtocol === 'oidc'">
            <div class="field">
              <label>Issuer / Discovery URL <span class="required">*</span></label>
              <input
                v-model="forms.oidc.discovery_url"
                type="text"
                placeholder="https://idp.example.com/.well-known/openid-configuration"
                required
              />
            </div>
            <div class="field">
              <label>Client ID <span class="required">*</span></label>
              <input v-model="forms.oidc.client_id" type="text" placeholder="client-id" required />
            </div>
            <div class="field">
              <label>Client Secret</label>
              <div class="password-field">
                <input
                  v-model="forms.oidc.client_secret"
                  :type="showOidcSecret ? 'text' : 'password'"
                  placeholder="client-secret"
                />
                <button class="password-toggle" type="button" @click="showOidcSecret = !showOidcSecret">
                  {{ showOidcSecret ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field">
              <label>Scope</label>
              <input v-model="forms.oidc.scope" type="text" placeholder="openid profile email" />
            </div>
            <div class="field">
              <label>UserInfo URL</label>
              <input v-model="forms.oidc.userinfo_url" type="text" placeholder="https://idp.example.com/userinfo" />
            </div>
            <div class="field">
              <label>Audience</label>
              <input v-model="forms.oidc.audience" type="text" placeholder="api://resource" />
            </div>
          </template>

          <template v-else-if="activeProtocol === 'oauth2'">
            <div class="field">
              <label>授权地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.authorize_url"
                type="text"
                placeholder="https://idp.example.com/oauth2/authorize"
                required
              />
            </div>
            <div class="field">
              <label>令牌地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.token_url"
                type="text"
                placeholder="https://idp.example.com/oauth2/token"
                required
              />
            </div>
            <div class="field">
              <label>Client ID <span class="required">*</span></label>
              <input v-model="forms.oauth2.client_id" type="text" placeholder="client-id" required />
            </div>
            <div class="field">
              <label>Client Secret</label>
              <div class="password-field">
                <input
                  v-model="forms.oauth2.client_secret"
                  :type="showOauth2Secret ? 'text' : 'password'"
                  placeholder="client-secret"
                />
                <button class="password-toggle" type="button" @click="showOauth2Secret = !showOauth2Secret">
                  {{ showOauth2Secret ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field">
              <label>Scope</label>
              <input v-model="forms.oauth2.scope" type="text" placeholder="openid profile email" />
            </div>
            <div class="field">
              <label>UserInfo URL</label>
              <input v-model="forms.oauth2.userinfo_url" type="text" placeholder="https://idp.example.com/userinfo" />
            </div>
            <div class="field">
              <label>Audience</label>
              <input v-model="forms.oauth2.audience" type="text" placeholder="api://resource" />
            </div>
          </template>

          <template v-else>
            <div class="field">
              <label>SAML2 SSO URL <span class="required">*</span></label>
              <input v-model="forms.saml2.sso_url" type="text" placeholder="https://idp.example.com/saml/sso" required />
            </div>
            <div class="field">
              <label>RelayState 参数名</label>
              <input v-model="forms.saml2.relay_state_key" type="text" placeholder="RelayState" />
            </div>
            <div class="field">
              <label>ACS 参数名</label>
              <input v-model="forms.saml2.acs_key" type="text" placeholder="acs" />
            </div>
          </template>

          <div class="sub-title">通用设置</div>

          <div class="field">
            <label>配置标识 Key <span class="required">*</span></label>
            <input v-model="currentForm.key" type="text" placeholder="ldap-default" required />
          </div>
          <div class="field">
            <label>显示名称 <span class="required">*</span></label>
            <input v-model="currentForm.name" type="text" placeholder="LDAP 登录" required />
          </div>
          <div class="field">
            <label>默认角色</label>
            <input v-model="currentForm.default_role" type="text" placeholder="user" />
          </div>
          <div class="field">
            <label>默认工作空间</label>
            <input v-model="currentForm.default_workspace" type="text" placeholder="default" />
          </div>

          <div class="sub-title">属性映射</div>

          <div class="field">
            <label>账号映射字段</label>
            <input v-model="currentForm.mapping_account" type="text" placeholder="preferred_username" />
          </div>
          <div class="field">
            <label>用户名映射字段</label>
            <input v-model="currentForm.mapping_username" type="text" placeholder="name" />
          </div>
          <div class="field">
            <label>邮箱映射字段</label>
            <input v-model="currentForm.mapping_email" type="text" placeholder="email" />
          </div>
          <div class="field">
            <label>工作空间映射字段</label>
            <input v-model="currentForm.mapping_workspace" type="text" placeholder="workspace" />
          </div>

          <div class="field full-row checkbox-row">
            <label class="checkbox-item">
              <input v-model="currentForm.enabled" type="checkbox" />
              启用 {{ activeTabLabel }} 认证
            </label>
            <label class="checkbox-item">
              <input v-model="currentForm.auto_create_user" type="checkbox" />
              自动创建用户
            </label>
          </div>

          <div class="button-row full-row">
            <button class="primary" type="submit" :disabled="saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="ghost" type="button" :disabled="testing" @click="handleTest">
              {{ testing ? '测试中...' : '测试连接' }}
            </button>
            <button class="ghost danger" type="button" :disabled="!currentProvider" @click="openDeleteModal">
              删除配置
            </button>
          </div>
        </form>

        <p v-if="error" class="state error">{{ error }}</p>
        <p v-if="success" class="state success">{{ success }}</p>
        <p class="state current-config">
          当前配置：{{ currentProvider ? `${currentProvider.name} (${currentProvider.key})` : '未保存' }}
        </p>
      </div>
    </div>
  </div>

  <div v-if="showDeleteModal" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>删除登录配置</h3>
        <button class="modal-close" type="button" @click="closeDeleteModal">✕</button>
      </div>
      <p class="modal-body">
        确认删除 <strong>{{ currentProvider?.name || activeTabLabel }}</strong> 配置吗？删除后该协议将不可用。
      </p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="closeDeleteModal">取消</button>
        <button class="primary" type="button" :disabled="deleting" @click="confirmDelete">
          {{ deleting ? '删除中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createSsoProvider,
  deleteSsoProvider,
  fetchSsoProviders,
  testSsoProvider,
  updateSsoProvider,
} from '../../../services/system/sso'
import type { SsoProvider, SsoProviderCreate, SsoProviderProtocol } from '../../../services/system/types'

type ProtocolTab = { protocol: SsoProviderProtocol; label: string }
type BaseForm = {
  key: string
  name: string
  enabled: boolean
  auto_create_user: boolean
  default_role: string
  default_workspace: string
  mapping_account: string
  mapping_username: string
  mapping_email: string
  mapping_workspace: string
}
type LdapForm = BaseForm & {
  server_url: string
  bind_dn: string
  bind_password: string
  base_dn: string
  user_filter: string
  account_attr: string
}
type CasForm = BaseForm & {
  cas_base_url: string
  login_url: string
  validate_url: string
}
type OidcForm = BaseForm & {
  discovery_url: string
  client_id: string
  client_secret: string
  scope: string
  userinfo_url: string
  audience: string
}
type Oauth2Form = BaseForm & {
  authorize_url: string
  token_url: string
  client_id: string
  client_secret: string
  scope: string
  userinfo_url: string
  audience: string
}
type Saml2Form = BaseForm & {
  sso_url: string
  relay_state_key: string
  acs_key: string
}

const protocolTabs: ProtocolTab[] = [
  { protocol: 'ldap', label: 'LDAP' },
  { protocol: 'cas', label: 'CAS' },
  { protocol: 'oidc', label: 'OIDC' },
  { protocol: 'oauth2', label: 'OAuth2' },
  { protocol: 'saml2', label: 'SAML2' },
]

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const deleting = ref(false)
const showDeleteModal = ref(false)
const error = ref('')
const success = ref('')
const activeProtocol = ref<SsoProviderProtocol>('ldap')

const showLdapPassword = ref(false)
const showOidcSecret = ref(false)
const showOauth2Secret = ref(false)

const providers = ref<SsoProvider[]>([])

const defaultBaseForm = (protocol: SsoProviderProtocol, label: string): BaseForm => ({
  key: `${protocol}-default`,
  name: `${label} 登录`,
  enabled: false,
  auto_create_user: true,
  default_role: 'user',
  default_workspace: 'default',
  mapping_account: '',
  mapping_username: '',
  mapping_email: '',
  mapping_workspace: '',
})

const createDefaultLdapForm = (): LdapForm => ({
  ...defaultBaseForm('ldap', 'LDAP'),
  enabled: false,
  server_url: '',
  bind_dn: '',
  bind_password: '',
  base_dn: '',
  user_filter: '(uid={account})',
  account_attr: 'uid',
})

const createDefaultCasForm = (): CasForm => ({
  ...defaultBaseForm('cas', 'CAS'),
  cas_base_url: '',
  login_url: '',
  validate_url: '',
})

const createDefaultOidcForm = (): OidcForm => ({
  ...defaultBaseForm('oidc', 'OIDC'),
  discovery_url: '',
  client_id: '',
  client_secret: '',
  scope: 'openid profile email',
  userinfo_url: '',
  audience: '',
})

const createDefaultOauth2Form = (): Oauth2Form => ({
  ...defaultBaseForm('oauth2', 'OAuth2'),
  authorize_url: '',
  token_url: '',
  client_id: '',
  client_secret: '',
  scope: 'openid profile email',
  userinfo_url: '',
  audience: '',
})

const createDefaultSaml2Form = (): Saml2Form => ({
  ...defaultBaseForm('saml2', 'SAML2'),
  sso_url: '',
  relay_state_key: 'RelayState',
  acs_key: 'acs',
})

const forms = reactive({
  ldap: createDefaultLdapForm(),
  cas: createDefaultCasForm(),
  oidc: createDefaultOidcForm(),
  oauth2: createDefaultOauth2Form(),
  saml2: createDefaultSaml2Form(),
})

const activeTabLabel = computed(
  () => protocolTabs.find((tab) => tab.protocol === activeProtocol.value)?.label || activeProtocol.value
)

const currentProvider = computed(() => {
  return providers.value.find((item) => item.protocol === activeProtocol.value) || null
})

const currentForm = computed(() => forms[activeProtocol.value])

const readText = (payload: Record<string, unknown>, key: string) => {
  const value = payload[key]
  if (value === null || value === undefined) return ''
  return String(value)
}

const fillCommonForm = (target: BaseForm, provider: SsoProvider) => {
  const mapping = (provider.attribute_mapping || {}) as Record<string, unknown>
  target.key = provider.key || target.key
  target.name = provider.name || target.name
  target.enabled = !!provider.enabled
  target.auto_create_user = !!provider.auto_create_user
  target.default_role = provider.default_role || 'user'
  target.default_workspace = provider.default_workspace || 'default'
  target.mapping_account = readText(mapping, 'account')
  target.mapping_username = readText(mapping, 'username')
  target.mapping_email = readText(mapping, 'email')
  target.mapping_workspace = readText(mapping, 'workspace')
}

const hydrateFormsFromProviders = () => {
  forms.ldap = createDefaultLdapForm()
  forms.cas = createDefaultCasForm()
  forms.oidc = createDefaultOidcForm()
  forms.oauth2 = createDefaultOauth2Form()
  forms.saml2 = createDefaultSaml2Form()

  for (const provider of providers.value) {
    const config = (provider.config || {}) as Record<string, unknown>
    if (provider.protocol === 'ldap') {
      fillCommonForm(forms.ldap, provider)
      forms.ldap.server_url = readText(config, 'server_url')
      forms.ldap.bind_dn = readText(config, 'bind_dn')
      forms.ldap.bind_password = readText(config, 'bind_password')
      forms.ldap.base_dn = readText(config, 'base_dn')
      forms.ldap.user_filter = readText(config, 'user_filter') || '(uid={account})'
      forms.ldap.account_attr = readText(config, 'account_attr') || 'uid'
      continue
    }
    if (provider.protocol === 'cas') {
      fillCommonForm(forms.cas, provider)
      forms.cas.cas_base_url = readText(config, 'cas_base_url')
      forms.cas.login_url = readText(config, 'login_url')
      forms.cas.validate_url = readText(config, 'validate_url')
      continue
    }
    if (provider.protocol === 'oidc') {
      fillCommonForm(forms.oidc, provider)
      forms.oidc.discovery_url = readText(config, 'discovery_url') || readText(config, 'issuer')
      forms.oidc.client_id = readText(config, 'client_id')
      forms.oidc.client_secret = readText(config, 'client_secret')
      forms.oidc.scope = readText(config, 'scope') || readText(config, 'scopes') || 'openid profile email'
      forms.oidc.userinfo_url = readText(config, 'userinfo_url')
      forms.oidc.audience = readText(config, 'audience')
      continue
    }
    if (provider.protocol === 'oauth2') {
      fillCommonForm(forms.oauth2, provider)
      forms.oauth2.authorize_url = readText(config, 'authorize_url')
      forms.oauth2.token_url = readText(config, 'token_url')
      forms.oauth2.client_id = readText(config, 'client_id')
      forms.oauth2.client_secret = readText(config, 'client_secret')
      forms.oauth2.scope = readText(config, 'scope') || readText(config, 'scopes') || 'openid profile email'
      forms.oauth2.userinfo_url = readText(config, 'userinfo_url')
      forms.oauth2.audience = readText(config, 'audience')
      continue
    }
    if (provider.protocol === 'saml2') {
      fillCommonForm(forms.saml2, provider)
      forms.saml2.sso_url = readText(config, 'sso_url')
      forms.saml2.relay_state_key = readText(config, 'relay_state_key') || 'RelayState'
      forms.saml2.acs_key = readText(config, 'acs_key') || 'acs'
    }
  }
}

const buildAttributeMapping = (form: BaseForm): Record<string, string> => {
  const mapping: Record<string, string> = {}
  if (form.mapping_account.trim()) mapping.account = form.mapping_account.trim()
  if (form.mapping_username.trim()) mapping.username = form.mapping_username.trim()
  if (form.mapping_email.trim()) mapping.email = form.mapping_email.trim()
  if (form.mapping_workspace.trim()) mapping.workspace = form.mapping_workspace.trim()
  return mapping
}

const buildConfigByProtocol = (protocol: SsoProviderProtocol): Record<string, unknown> => {
  if (protocol === 'ldap') {
    return {
      server_url: forms.ldap.server_url.trim(),
      bind_dn: forms.ldap.bind_dn.trim(),
      bind_password: forms.ldap.bind_password,
      base_dn: forms.ldap.base_dn.trim(),
      user_filter: forms.ldap.user_filter.trim() || '(uid={account})',
      account_attr: forms.ldap.account_attr.trim() || 'uid',
    }
  }
  if (protocol === 'cas') {
    return {
      cas_base_url: forms.cas.cas_base_url.trim(),
      login_url: forms.cas.login_url.trim(),
      validate_url: forms.cas.validate_url.trim(),
    }
  }
  if (protocol === 'oidc') {
    return {
      discovery_url: forms.oidc.discovery_url.trim(),
      client_id: forms.oidc.client_id.trim(),
      client_secret: forms.oidc.client_secret,
      scope: forms.oidc.scope.trim() || 'openid profile email',
      userinfo_url: forms.oidc.userinfo_url.trim(),
      audience: forms.oidc.audience.trim(),
    }
  }
  if (protocol === 'oauth2') {
    return {
      authorize_url: forms.oauth2.authorize_url.trim(),
      token_url: forms.oauth2.token_url.trim(),
      client_id: forms.oauth2.client_id.trim(),
      client_secret: forms.oauth2.client_secret,
      scope: forms.oauth2.scope.trim() || 'openid profile email',
      userinfo_url: forms.oauth2.userinfo_url.trim(),
      audience: forms.oauth2.audience.trim(),
    }
  }
  return {
    sso_url: forms.saml2.sso_url.trim(),
    relay_state_key: forms.saml2.relay_state_key.trim() || 'RelayState',
    acs_key: forms.saml2.acs_key.trim() || 'acs',
  }
}

const clearMessages = () => {
  error.value = ''
  success.value = ''
}

const loadProviders = async () => {
  loading.value = true
  clearMessages()
  try {
    providers.value = await fetchSsoProviders()
    hydrateFormsFromProviders()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载登录配置失败'
  } finally {
    loading.value = false
  }
}

const buildSavePayload = (protocol: SsoProviderProtocol): SsoProviderCreate => {
  const form = forms[protocol]
  return {
    key: form.key.trim() || `${protocol}-default`,
    name: form.name.trim() || `${activeTabLabel.value} 登录`,
    protocol,
    enabled: !!form.enabled,
    auto_create_user: !!form.auto_create_user,
    default_role: form.default_role.trim() || 'user',
    default_workspace: form.default_workspace.trim() || 'default',
    config: buildConfigByProtocol(protocol),
    attribute_mapping: buildAttributeMapping(form),
  }
}

const handleSave = async () => {
  clearMessages()
  saving.value = true
  const protocol = activeProtocol.value
  try {
    const payload = buildSavePayload(protocol)
    if (currentProvider.value) {
      await updateSsoProvider(currentProvider.value.id, payload)
      success.value = `${activeTabLabel.value} 配置已更新`
    } else {
      await createSsoProvider(payload)
      success.value = `${activeTabLabel.value} 配置已保存`
    }
    await loadProviders()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存配置失败'
  } finally {
    saving.value = false
  }
}

const handleTest = async () => {
  clearMessages()
  testing.value = true
  const protocol = activeProtocol.value
  try {
    const res = await testSsoProvider({
      protocol,
      config: buildConfigByProtocol(protocol),
      attribute_mapping: buildAttributeMapping(forms[protocol]),
    })
    success.value = res.message || '测试成功'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '测试连接失败'
  } finally {
    testing.value = false
  }
}

const openDeleteModal = () => {
  clearMessages()
  if (!currentProvider.value) {
    error.value = '当前协议还没有已保存配置'
    return
  }
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
}

const confirmDelete = async () => {
  if (!currentProvider.value) return
  deleting.value = true
  clearMessages()
  try {
    await deleteSsoProvider(currentProvider.value.id)
    success.value = `${activeTabLabel.value} 配置已删除`
    showDeleteModal.value = false
    await loadProviders()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

onMounted(loadProviders)
</script>

<style scoped src="./AuthSettingsModule.css"></style>
