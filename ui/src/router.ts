import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import HomeView from './views/HomeView.vue'
import AgentsListView from './views/AgentsListView.vue'
import AgentDetailView from './views/AgentDetailView.vue'
import ModelsListView from './views/ModelsListView.vue'
import ModelDetailView from './views/ModelDetailView.vue'
import AdminView from './views/AdminView.vue'
import InfoView from './views/InfoView.vue'
import PasswordView from './views/PasswordView.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: LoginView },
  {
    path: '/home',
    component: HomeView,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/home/agents' },
      {
        path: 'agents',
        name: 'home-agents',
        component: AgentsListView,
        meta: { requiresAuth: true, module: 'agents' },
      },
      {
        path: 'agents/:id',
        name: 'home-agent-detail',
        component: AgentDetailView,
        meta: { requiresAuth: true, module: 'agents' },
      },
      {
        path: 'models',
        name: 'home-models',
        component: ModelsListView,
        meta: { requiresAuth: true, module: 'models' },
      },
      {
        path: 'models/:id',
        name: 'home-model-detail',
        component: ModelDetailView,
        meta: { requiresAuth: true, module: 'models' },
      },
      {
        path: 'admin',
        name: 'home-admin',
        component: AdminView,
        meta: { requiresAuth: true, module: 'admin' },
      },
      {
        path: 'account/password',
        name: 'home-password',
        component: PasswordView,
        meta: {
          requiresAuth: true,
          module: 'admin',
          title: '修改密码',
          description: '为当前登录账户设置新的密码。',
        },
      },
      {
        path: 'account/apikey',
        name: 'home-apikey',
        component: InfoView,
        meta: {
          requiresAuth: true,
          module: 'admin',
          title: 'API Key',
          description: '管理调用接口所需的密钥与权限。',
        },
      },
      {
        path: 'account/language',
        name: 'home-language',
        component: InfoView,
        meta: {
          requiresAuth: true,
          module: 'admin',
          title: '语言',
          description: '设置界面显示语言与时区偏好。',
        },
      },
      {
        path: 'account/about',
        name: 'home-about',
        component: InfoView,
        meta: {
          requiresAuth: true,
          module: 'admin',
          title: '关于',
          description: '查看当前系统版本与服务状态。',
        },
      },
      {
        path: 'account/help',
        name: 'home-help',
        component: InfoView,
        meta: {
          requiresAuth: true,
          module: 'admin',
          title: '帮助',
          description: '查看使用指引与常见问题。',
        },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) return true

  const token = localStorage.getItem('access_token')
  if (!token) {
    return { name: 'login' }
  }

  return true
})

export default router
