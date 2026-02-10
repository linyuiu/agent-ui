import type { Router } from 'vue-router'

import { getSessionToken } from '../services/session'

export const applyAuthGuard = (router: Router): void => {
  router.beforeEach((to) => {
    if (!to.meta.requiresAuth) return true

    const token = getSessionToken()
    if (!token) {
      return { name: 'login' }
    }

    return true
  })
}
