import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API requests (adjust the path prefix if necessary)
      // Using a generic '/api' prefix for now.
      // Requests to e.g. /api/agents/Weather%20Agent/execute will be proxied to http://localhost:8000/agents/Weather%20Agent/execute
      '/api': {
        target: 'http://localhost:8000', // Your backend FastAPI server
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') // Remove the /api prefix before forwarding
      },
      // If you were still serving old static files from FastAPI and needed direct access:
      // '/static': {
      //   target: 'http://localhost:8000',
      //   changeOrigin: true,
      // }
    }
  }
})
