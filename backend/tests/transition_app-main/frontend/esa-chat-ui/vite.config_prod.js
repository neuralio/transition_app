import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    allowedHosts: ['transitionui.neuralio.ai'],
    host: true,  // Allow connections from outside the container
    port: 8080        // Match Docker exposed port
  }
})