import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In other words: during `npm run dev`, any request to /api is forwarded to the FastAPI backend,
// so the browser never hits CORS problems.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true } },
  },
});
