import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Shown in the sidebar so people can confirm which build they are running.
  define: { __BUILD_TIME__: JSON.stringify(new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC') },
  server: { host: true, port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  preview: { host: true, port: 4173, proxy: { '/api': 'http://localhost:8000' } },
})
