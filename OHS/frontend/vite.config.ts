import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-server proxy + port are env-driven so the same vite.config.ts works
// whether the backend runs on 8000 (legacy Dockerfile default) or 8001 (the
// arch-bot dev launcher default). Override via VITE_API_TARGET / FRONTEND_PORT
// in .env.dev or the shell.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8001'
  const port = Number(env.FRONTEND_PORT) || 5173

  return {
    plugins: [react()],
    base: '/ohs/',
    server: {
      port,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
