import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: {
      // bind mounts do Windows via Docker Desktop não propagam eventos inotify
      // para o container, então o chokidar do Vite precisa de polling.
      usePolling: true,
      interval: 300,
    },
  },
})
