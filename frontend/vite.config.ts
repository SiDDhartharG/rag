import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // A fixed port the backend's CORS list knows about. strictPort fails loudly instead of silently moving to another port.
  server: { port: 5180, strictPort: true },
})
