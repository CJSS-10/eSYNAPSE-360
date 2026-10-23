import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy: las llamadas a /api se redirigen al backend Django en desarrollo.
// El modo pruebas usa otro backend (ESYNAPSE_API) y otro puerto (--port).
const BACKEND = process.env.ESYNAPSE_API || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/media': { target: BACKEND, changeOrigin: true },
    },
  },
})
