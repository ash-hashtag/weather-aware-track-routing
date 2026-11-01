import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // maplibre-gl loads its worker from a URL relative to its own module; pre-bundling breaks that.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  build: {
    rolldownOptions: {
      output: {
        // Emit the maplibre worker as .js: some static hosts serve .mjs as text/plain,
        // and browsers refuse to start a worker from a non-JavaScript MIME type.
        assetFileNames: (asset) =>
          asset.names.some((name) => name.endsWith('.mjs')) ? 'assets/[name]-[hash].js' : 'assets/[name]-[hash][extname]',
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
