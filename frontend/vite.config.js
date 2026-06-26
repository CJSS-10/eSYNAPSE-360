import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy: las llamadas a /api se redirigen al backend Django en desarrollo
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
