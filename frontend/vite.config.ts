import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // maplibre-gl loads its worker from a URL relative to its own module; pre-bundling breaks that.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
