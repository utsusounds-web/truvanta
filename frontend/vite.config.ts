import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false, // registered manually in PwaUpdatePrompt.tsx for custom update UI
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Truvanta',
        short_name: 'Truvanta',
        description: 'Know what you sold. Know what you have. Know where your money went.',
        theme_color: '#10263B',
        background_color: '#FBF9F5',
        display: 'standalone',
        start_url: '/dashboard',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Only the app shell (JS/CSS/HTML/icons) is precached here — API
        // requests are deliberately left alone so they hit the network
        // normally and fail fast when offline; the app's own IndexedDB
        // outbox (src/offline/) is what actually handles working offline,
        // not the service worker.
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    css: false,
  },
})
