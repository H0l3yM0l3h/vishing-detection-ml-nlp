import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Bind on all interfaces so the dev server can be opened from a phone on
    // the same Wi-Fi, for real-device testing. This affects `npm run dev`
    // only — production is served by Vercel and is unaffected.
    //
    // Note this exposes the dev server to your local network while it runs.
    // The API is NOT exposed: requests still go through the proxy below,
    // which reaches the backend over loopback on this machine.
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
