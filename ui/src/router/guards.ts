import type { Router } from 'vue-router'

import { clearSession, isSessionExpired } from '../services/session'

export const applyAuthGuard = (router: Router): void => {
  router.beforeEach((to) => {
    if (!to.meta.requiresAuth) return true

    if (isSessionExpired()) {
      clearSession()
      return { name: 'login' }
    }

    return true
  })
}
