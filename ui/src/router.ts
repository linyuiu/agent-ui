import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import HomeView from './views/HomeView.vue'
import AgentsListView from './views/AgentsListView.vue'
import AgentDetailView from './views/AgentDetailView.vue'
import ModelsListView from './views/ModelsListView.vue'
import ModelDetailView from './views/ModelDetailView.vue'
import AdminView from './views/AdminView.vue'

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
