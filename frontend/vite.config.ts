import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/auth': 'https://rag-backend-6ozj.onrender.com',
      '/documents': 'https://rag-backend-6ozj.onrender.com',
      '/chat': 'https://rag-backend-6ozj.onrender.com',
      '/dashboard': 'https://rag-backend-6ozj.onrender.com',
      '/health': 'https://rag-backend-6ozj.onrender.com',
      '/api': 'https://rag-backend-6ozj.onrender.com',
    }
  },
  build: {
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'vendor-react';
            }
            if (id.includes('framer-motion') || id.includes('lucide-react')) {
              return 'vendor-ui';
            }
            if (id.includes('jspdf')) {
              return 'vendor-pdf';
            }
            return 'vendor';
          }
        }
      }
    }
  }
})

