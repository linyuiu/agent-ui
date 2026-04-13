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
  const apiBase = normalizeProxyTarget(env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/chat': {
          target: apiBase,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
