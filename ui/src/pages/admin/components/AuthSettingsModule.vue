<template>
  <div class="section">
    <div class="section-header">
      <div>
        <h2>登录系统</h2>
        <p>分别配置 LDAP、CAS、OIDC、OAuth2、SAML2 登录方式。</p>
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
        <div class="sso-protocol-header">
          <div>
            <h3>{{ activeTabLabel }} 配置</h3>
            <p>{{ protocolDescriptions[activeProtocol] }}</p>
          </div>
          <span class="config-state" :class="{ configured: !!currentProvider }">
            {{ currentProvider ? '已保存' : '未保存' }}
          </span>
        </div>

        <form class="sso-form-grid" @submit.prevent="handleSave">
          <template v-if="activeProtocol === 'ldap'">
            <div class="field">
              <label>LDAP 地址 <span class="required">*</span></label>
              <input v-model="forms.ldap.server_url" type="text" placeholder="ldap://10.1.11.41" required />
            </div>
            <div class="field">
              <label>绑定 DN</label>
              <input v-model="forms.ldap.bind_dn" type="text" placeholder="cn=admin,dc=example,dc=com" />
            </div>
            <div class="field">
              <label>绑定密码</label>
              <div class="password-field">
                <input
                  v-model="forms.ldap.bind_password"
                  :type="showSecret.ldap ? 'text' : 'password'"
                  placeholder="绑定账号密码"
                />
                <button class="password-toggle" type="button" @click="showSecret.ldap = !showSecret.ldap">
                  {{ showSecret.ldap ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field">
              <label>用户 OU <span class="required">*</span></label>
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
            <div class="field full-row">
              <label>字段映射</label>
              <textarea
                v-model="forms.ldap.field_mapping_text"
                rows="4"
                placeholder='{"username":"uid","nick_name":"cn","email":"mail"}'
              ></textarea>
              <p class="field-hint">LDAP 可按需配置字段映射，未填写时将使用默认字段名。</p>
            </div>
          </template>

          <template v-else-if="activeProtocol === 'cas'">
            <div class="field">
              <label>IdpUri <span class="required">*</span></label>
              <input v-model="forms.cas.cas_base_url" type="text" placeholder="http://47.120.55.164:8083/cas" required />
            </div>
            <div class="field">
              <label>验证地址 <span class="required">*</span></label>
              <input
                v-model="forms.cas.validate_url"
                type="text"
                placeholder="http://47.120.55.164:8083/cas/serviceValidate"
                required
              />
            </div>
            <div class="field full-row">
              <label>回调地址 <span class="required">*</span></label>
              <input v-model="forms.cas.callback_url" type="text" :placeholder="defaultCallback('cas')" required />
              <p class="field-hint">CAS 使用默认返回字段，不需要单独配置字段映射。</p>
            </div>
          </template>

          <template v-else-if="activeProtocol === 'oidc'">
            <div class="field">
              <label>Discovery 地址 <span class="required">*</span></label>
              <input
                v-model="forms.oidc.discovery_url"
                type="text"
                placeholder="https://idp.example.com/.well-known/openid-configuration"
                required
              />
            </div>
            <div class="field">
              <label>连接范围</label>
              <input v-model="forms.oidc.scope" type="text" placeholder="openid profile email" />
            </div>
            <div class="field">
              <label>客户端 ID <span class="required">*</span></label>
              <input v-model="forms.oidc.client_id" type="text" placeholder="client-id" required />
            </div>
            <div class="field">
              <label>客户端密钥</label>
              <div class="password-field">
                <input
                  v-model="forms.oidc.client_secret"
                  :type="showSecret.oidc ? 'text' : 'password'"
                  placeholder="client-secret"
                />
                <button class="password-toggle" type="button" @click="showSecret.oidc = !showSecret.oidc">
                  {{ showSecret.oidc ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field full-row">
              <label>字段映射 <span class="required">*</span></label>
              <textarea
                v-model="forms.oidc.field_mapping_text"
                rows="4"
                placeholder='{"username":"preferred_username","nick_name":"name","email":"email"}'
                required
              ></textarea>
            </div>
            <div class="field full-row">
              <label>回调地址 <span class="required">*</span></label>
              <input v-model="forms.oidc.callback_url" type="text" :placeholder="defaultCallback('oidc')" required />
            </div>
          </template>

          <template v-else-if="activeProtocol === 'oauth2'">
            <div class="field">
              <label>授权端地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.authorize_url"
                type="text"
                placeholder="https://github.com/login/oauth/authorize"
                required
              />
            </div>
            <div class="field">
              <label>Token 端地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.token_url"
                type="text"
                placeholder="https://github.com/login/oauth/access_token"
                required
              />
            </div>
            <div class="field full-row">
              <label>用户信息端地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.userinfo_url"
                type="text"
                placeholder="https://api.github.com/user"
                required
              />
            </div>
            <div class="field">
              <label>连接范围</label>
              <input v-model="forms.oauth2.scope" type="text" placeholder="user:email" />
            </div>
            <div class="field">
              <label>客户端 ID <span class="required">*</span></label>
              <input v-model="forms.oauth2.client_id" type="text" placeholder="client-id" required />
            </div>
            <div class="field">
              <label>客户端密钥</label>
              <div class="password-field">
                <input
                  v-model="forms.oauth2.client_secret"
                  :type="showSecret.oauth2 ? 'text' : 'password'"
                  placeholder="client-secret"
                />
                <button class="password-toggle" type="button" @click="showSecret.oauth2 = !showSecret.oauth2">
                  {{ showSecret.oauth2 ? '隐藏' : '显示' }}
                </button>
              </div>
            </div>
            <div class="field full-row">
              <label>字段映射 <span class="required">*</span></label>
              <textarea
                v-model="forms.oauth2.field_mapping_text"
                rows="4"
                placeholder='{"username":"login","nick_name":"name","email":"email"}'
                required
              ></textarea>
            </div>
            <div class="field full-row">
              <label>回调地址 <span class="required">*</span></label>
              <input
                v-model="forms.oauth2.callback_url"
                type="text"
                :placeholder="defaultCallback('oauth2')"
                required
              />
            </div>
          </template>

          <template v-else>
            <div class="field">
              <label>SSO 地址 <span class="required">*</span></label>
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
            <div class="field full-row">
              <label>字段映射 <span class="required">*</span></label>
              <textarea
                v-model="forms.saml2.field_mapping_text"
                rows="4"
                placeholder='{"username":"NameID","nick_name":"displayName","email":"email"}'
                required
              ></textarea>
            </div>
            <div class="field full-row">
              <label>回调地址 <span class="required">*</span></label>
              <input
                v-model="forms.saml2.callback_url"
                type="text"
                :placeholder="defaultCallback('saml2')"
                required
              />
            </div>
          </template>

          <div class="common-settings full-row">
            <label class="checkbox-item">
              <input v-model="currentForm.enabled" type="checkbox" />
              启用 {{ activeTabLabel }} 认证
            </label>
            <label class="checkbox-item">
              <input v-model="currentForm.auto_create_user" type="checkbox" />
              自动创建用户
            </label>
            <div class="field compact-field">
              <label>默认角色</label>
              <input v-model="currentForm.default_role" type="text" placeholder="user" />
            </div>
            <div class="field compact-field">
              <label>默认工作空间</label>
              <input v-model="currentForm.default_workspace" type="text" placeholder="default" />
            </div>
          </div>

          <div class="button-row full-row">
            <button class="primary" type="submit" :disabled="saving || loading">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="ghost" type="button" :disabled="testing || loading" @click="handleTest">
              {{ testing ? '测试中...' : '测试连接' }}
            </button>
            <button class="ghost danger" type="button" :disabled="!currentProvider || deleting" @click="openDeleteModal">
              删除配置
            </button>
          </div>
        </form>

        <p v-if="error" class="state error">{{ error }}</p>
        <p v-if="success" class="state success">{{ success }}</p>
        <p class="state current-config">
          当前配置：{{ currentProvider ? `${currentProvider.name}（${currentProvider.enabled ? '已启用' : '未启用'}）` : '未保存' }}
        </p>
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

type CommonForm = {
  enabled: boolean
  auto_create_user: boolean
  default_role: string
  default_workspace: string
}

type MappingForm = CommonForm & { field_mapping_text: string }

type LdapForm = MappingForm & {
  server_url: string
  bind_dn: string
  bind_password: string
  base_dn: string
  user_filter: string
  account_attr: string
}

type CasForm = CommonForm & {
  cas_base_url: string
  validate_url: string
  callback_url: string
}

type OidcForm = MappingForm & {
  discovery_url: string
  client_id: string
  client_secret: string
  scope: string
  callback_url: string
}

type Oauth2Form = MappingForm & {
  authorize_url: string
  token_url: string
  userinfo_url: string
  scope: string
  client_id: string
  client_secret: string
  callback_url: string
}

type Saml2Form = MappingForm & {
  sso_url: string
  relay_state_key: string
  acs_key: string
  callback_url: string
}

const protocolTabs: ProtocolTab[] = [
  { protocol: 'ldap', label: 'LDAP' },
  { protocol: 'cas', label: 'CAS' },
  { protocol: 'oidc', label: 'OIDC' },
  { protocol: 'oauth2', label: 'OAuth2' },
  { protocol: 'saml2', label: 'SAML2' },
]

const protocolDescriptions: Record<SsoProviderProtocol, string> = {
  ldap: '通过目录服务完成账号密码校验，并按映射同步用户信息。',
  cas: '通过 CAS Ticket 校验登录，默认读取返回用户名，不需要配置字段映射。',
  oidc: '通过 OIDC Discovery 获取授权配置，并按字段映射提取用户名信息。',
  oauth2: '通过 OAuth2 授权端、Token 端和用户信息端完成登录与用户同步。',
  saml2: '通过 SAML2 IdP 返回断言，并按字段映射提取用户名、昵称和邮箱。',
}

const protocolLabels: Record<SsoProviderProtocol, string> = {
  ldap: 'LDAP',
  cas: 'CAS',
  oidc: 'OIDC',
  oauth2: 'OAuth2',
  saml2: 'SAML2',
}

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const deleting = ref(false)
const showDeleteModal = ref(false)
const error = ref('')
const success = ref('')
const activeProtocol = ref<SsoProviderProtocol>('ldap')
const providers = ref<SsoProvider[]>([])
const showSecret = reactive<Record<'ldap' | 'oidc' | 'oauth2', boolean>>({
  ldap: false,
  oidc: false,
  oauth2: false,
})

const defaultCommon = (): CommonForm => ({
  enabled: false,
  auto_create_user: true,
  default_role: 'user',
  default_workspace: 'default',
})

const defaultCallback = (protocol: SsoProviderProtocol) => `${apiBase}/auth/sso/callback/${protocol}`

const createDefaultLdapForm = (): LdapForm => ({
  ...defaultCommon(),
  server_url: '',
  bind_dn: '',
  bind_password: '',
  base_dn: '',
  user_filter: '(uid={account})',
  account_attr: 'uid',
  field_mapping_text: '{"username":"uid","nick_name":"cn","email":"mail"}',
})

const createDefaultCasForm = (): CasForm => ({
  ...defaultCommon(),
  cas_base_url: '',
  validate_url: '',
  callback_url: defaultCallback('cas'),
})

const createDefaultOidcForm = (): OidcForm => ({
  ...defaultCommon(),
  discovery_url: '',
  client_id: '',
  client_secret: '',
  scope: 'openid profile email',
  callback_url: defaultCallback('oidc'),
  field_mapping_text: '{"username":"preferred_username","nick_name":"name","email":"email"}',
})

const createDefaultOauth2Form = (): Oauth2Form => ({
  ...defaultCommon(),
  authorize_url: '',
  token_url: '',
  userinfo_url: '',
  scope: 'user:email',
  client_id: '',
  client_secret: '',
  callback_url: defaultCallback('oauth2'),
  field_mapping_text: '{"username":"login","nick_name":"name","email":"email"}',
})

const createDefaultSaml2Form = (): Saml2Form => ({
  ...defaultCommon(),
  sso_url: '',
  relay_state_key: 'RelayState',
  acs_key: 'acs',
  callback_url: defaultCallback('saml2'),
  field_mapping_text: '{"username":"NameID","nick_name":"displayName","email":"email"}',
})

const forms = reactive({
  ldap: createDefaultLdapForm(),
  cas: createDefaultCasForm(),
  oidc: createDefaultOidcForm(),
  oauth2: createDefaultOauth2Form(),
  saml2: createDefaultSaml2Form(),
})

const activeTabLabel = computed(
  () => protocolTabs.find((tab) => tab.protocol === activeProtocol.value)?.label || activeProtocol.value,
)
const currentProvider = computed(() => providers.value.find((item) => item.protocol === activeProtocol.value) || null)
const currentForm = computed(() => forms[activeProtocol.value])

const readText = (payload: Record<string, unknown>, key: string, fallback = '') => {
  const value = payload[key]
  if (value === null || value === undefined) return fallback
  return String(value)
}

const formatMapping = (mapping: Record<string, unknown> | undefined, fallback: string) => {
  if (!mapping || Object.keys(mapping).length === 0) {
    return fallback
  }
  return JSON.stringify(mapping, null, 2)
}

const resetForms = () => {
  Object.assign(forms.ldap, createDefaultLdapForm())
  Object.assign(forms.cas, createDefaultCasForm())
  Object.assign(forms.oidc, createDefaultOidcForm())
  Object.assign(forms.oauth2, createDefaultOauth2Form())
  Object.assign(forms.saml2, createDefaultSaml2Form())
}

const hydrateFormsFromProviders = () => {
  resetForms()

  for (const provider of providers.value) {
    const config = (provider.config || {}) as Record<string, unknown>
    const mapping = (provider.field_mapping || {}) as Record<string, unknown>
    const common = {
      enabled: !!provider.enabled,
      auto_create_user: !!provider.auto_create_user,
      default_role: provider.default_role || 'user',
      default_workspace: provider.default_workspace || 'default',
    }

    if (provider.protocol === 'ldap') {
      Object.assign(forms.ldap, common, {
        server_url: readText(config, 'server_url'),
        bind_dn: readText(config, 'bind_dn'),
        bind_password: readText(config, 'bind_password'),
        base_dn: readText(config, 'base_dn'),
        user_filter: readText(config, 'user_filter', '(uid={account})'),
        account_attr: readText(config, 'account_attr', 'uid'),
        field_mapping_text: formatMapping(mapping, createDefaultLdapForm().field_mapping_text),
      })
      continue
    }

    if (provider.protocol === 'cas') {
      Object.assign(forms.cas, common, {
        cas_base_url: readText(config, 'cas_base_url') || readText(config, 'idp_uri'),
        validate_url: readText(config, 'validate_url'),
        callback_url: readText(config, 'callback_url', defaultCallback('cas')),
      })
      continue
    }

    if (provider.protocol === 'oidc') {
      Object.assign(forms.oidc, common, {
        discovery_url: readText(config, 'discovery_url') || readText(config, 'issuer'),
        client_id: readText(config, 'client_id'),
        client_secret: readText(config, 'client_secret'),
        scope: readText(config, 'scope', 'openid profile email'),
        callback_url: readText(config, 'callback_url', defaultCallback('oidc')),
        field_mapping_text: formatMapping(mapping, createDefaultOidcForm().field_mapping_text),
      })
      continue
    }

    if (provider.protocol === 'oauth2') {
      Object.assign(forms.oauth2, common, {
        authorize_url: readText(config, 'authorize_url'),
        token_url: readText(config, 'token_url'),
        userinfo_url: readText(config, 'userinfo_url'),
        scope: readText(config, 'scope', 'user:email'),
        client_id: readText(config, 'client_id'),
        client_secret: readText(config, 'client_secret'),
        callback_url: readText(config, 'callback_url', defaultCallback('oauth2')),
        field_mapping_text: formatMapping(mapping, createDefaultOauth2Form().field_mapping_text),
      })
      continue
    }

    Object.assign(forms.saml2, common, {
      sso_url: readText(config, 'sso_url'),
      relay_state_key: readText(config, 'relay_state_key', 'RelayState'),
      acs_key: readText(config, 'acs_key', 'acs'),
      callback_url: readText(config, 'callback_url', defaultCallback('saml2')),
      field_mapping_text: formatMapping(mapping, createDefaultSaml2Form().field_mapping_text),
    })
  }
}

const parseFieldMapping = (text: string, required: boolean) => {
  const raw = text.trim()
  if (!raw) {
    if (required) throw new Error('字段映射不能为空')
    return {}
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    throw new Error('字段映射必须是合法 JSON')
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('字段映射必须是 JSON 对象')
  }

  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
    const field = String(key || '').trim()
    const claim = String(value || '').trim()
    if (!field || !claim) continue
    result[field] = claim
  }

  if (required && !result.username) {
    throw new Error('字段映射至少需要包含 username')
  }
  return result
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
      idp_uri: forms.cas.cas_base_url.trim(),
      validate_url: forms.cas.validate_url.trim(),
      callback_url: forms.cas.callback_url.trim() || defaultCallback('cas'),
    }
  }

  if (protocol === 'oidc') {
    return {
      discovery_url: forms.oidc.discovery_url.trim(),
      client_id: forms.oidc.client_id.trim(),
      client_secret: forms.oidc.client_secret,
      scope: forms.oidc.scope.trim() || 'openid profile email',
      callback_url: forms.oidc.callback_url.trim() || defaultCallback('oidc'),
    }
  }

  if (protocol === 'oauth2') {
    return {
      authorize_url: forms.oauth2.authorize_url.trim(),
      token_url: forms.oauth2.token_url.trim(),
      userinfo_url: forms.oauth2.userinfo_url.trim(),
      scope: forms.oauth2.scope.trim() || 'user:email',
      client_id: forms.oauth2.client_id.trim(),
      client_secret: forms.oauth2.client_secret,
      callback_url: forms.oauth2.callback_url.trim() || defaultCallback('oauth2'),
    }
  }

  return {
    sso_url: forms.saml2.sso_url.trim(),
    relay_state_key: forms.saml2.relay_state_key.trim() || 'RelayState',
    acs_key: forms.saml2.acs_key.trim() || 'acs',
    callback_url: forms.saml2.callback_url.trim() || defaultCallback('saml2'),
  }
}

const buildFieldMapping = (protocol: SsoProviderProtocol) => {
  if (protocol === 'cas') return {}
  if (protocol === 'ldap') return parseFieldMapping(forms.ldap.field_mapping_text, false)
  if (protocol === 'oidc') return parseFieldMapping(forms.oidc.field_mapping_text, true)
  if (protocol === 'oauth2') return parseFieldMapping(forms.oauth2.field_mapping_text, true)
  return parseFieldMapping(forms.saml2.field_mapping_text, true)
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

const buildSavePayload = (protocol: SsoProviderProtocol): SsoProviderCreate => ({
  key: protocol,
  name: protocolLabels[protocol],
  protocol,
  enabled: currentForm.value.enabled,
  auto_create_user: currentForm.value.auto_create_user,
  default_role: currentForm.value.default_role.trim() || 'user',
  default_workspace: currentForm.value.default_workspace.trim() || 'default',
  config: buildConfigByProtocol(protocol),
  field_mapping: buildFieldMapping(protocol),
})

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
      field_mapping: buildFieldMapping(protocol),
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
