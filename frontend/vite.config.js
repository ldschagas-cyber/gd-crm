import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon-32x32.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'GD Conecta CRM',
        short_name: 'GD CRM',
        description: 'CRM GD Conecta',
        lang: 'pt-BR',
        start_url: '/',
        display: 'standalone',
        background_color: '#F5F1EB',
        theme_color: '#2D3561',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // API/uploads/docs são proxy do backend — a PWA só deve cachear os
        // assets estáticos do próprio build, nunca respostas dinâmicas.
        navigateFallbackDenylist: [/^\/api\//, /^\/uploads\//, /^\/docs/],
      },
    }),
  ],
  server: {
    port: 5173,
    watch: {
      // bind mounts do Windows via Docker Desktop não propagam eventos inotify
      // para o container, então o chokidar do Vite precisa de polling.
      usePolling: true,
      interval: 300,
    },
  },
  preview: {
    // permite acessar o preview via hostname do túnel (trycloudflare/loca.lt),
    // que muda a cada execução — só usado neste teste local, nunca em produção
    allowedHosts: true,
  },
})
