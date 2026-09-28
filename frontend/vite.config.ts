import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Frontend dev server on :5173 proxies /api to the FastAPI backend on :8000,
// so the browser only ever talks to localhost and never sees provider secrets.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } },
  },
  build: { chunkSizeWarningLimit: 2000 },
})
