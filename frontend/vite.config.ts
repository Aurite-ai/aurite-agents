/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from 'tailwindcss'; // Import tailwindcss for v3
import autoprefixer from 'autoprefixer'; // Import autoprefixer

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts', // or './setupTests.ts' if at root of frontend/
    css: true, // if you want to process CSS during tests
  },
  server: {
    host: '0.0.0.0', // Exposes server to the network, crucial for Docker
    port: 5173,
    proxy: {
      // Proxy API requests
      // Requests to e.g. /api/agents/Weather%20Agent/execute will be proxied to http://backend:8000/agents/Weather%20Agent/execute
      '/api': {
        target: 'http://backend:8000', // 'backend' will be the service name in docker-compose.yml
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') // Remove the /api prefix before forwarding
      },
    },
  },
  css: {
    postcss: {
      plugins: [
        tailwindcss,    // Use tailwindcss directly for v3
        autoprefixer,       // Use the imported autoprefixer plugin
      ],
    },
  },
})
