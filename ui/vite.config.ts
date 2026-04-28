import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

const normalizeProxyTarget = (rawTarget: string) => {
  try {
    const target = new URL(rawTarget)
    if (target.hostname === 'localhost') {
      target.hostname = '127.0.0.1'
    }
    return target.toString()
  } catch {
    return rawTarget
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBase = normalizeProxyTarget(env.VITE_API_BASE_URL)

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/auth': {
          target: apiBase,
          changeOrigin: true,
        },
        '/admin': {
          target: apiBase,
          changeOrigin: true,
        },
        '/dashboard': {
          target: apiBase,
          changeOrigin: true,
        },
        '/agents': {
          target: apiBase,
          changeOrigin: true,
        },
        '/agent-groups': {
          target: apiBase,
          changeOrigin: true,
        },
        '/models': {
          target: apiBase,
          changeOrigin: true,
        },
        '/demo': {
          target: apiBase,
          changeOrigin: true,
        },
        '/chat': {
          target: apiBase,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['vue', 'vue-router'],
          },
        },
      },
    },
  }
})
