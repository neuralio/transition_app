import { createApp } from 'vue'
import App from './App.vue'
import './assets/tailwind.css'
import api from './api'
import { keycloak, initKeycloak, startTokenRefresh } from './auth/keycloak'

// ✅ Initialize Keycloak only ONCE here
// pass false to use 'check-sso' (no redirect if user not logged in yet)
await initKeycloak(true)

// optional: keep tokens fresh while the app is open
startTokenRefresh()

// ✅ Attach Authorization header globally (set once)
if (!api.__kc_interceptor_set) {
  api.interceptors.request.use(async (config) => {
    try {
      if (keycloak.token) await keycloak.updateToken(30)
      if (keycloak.token) {
        config.headers.Authorization = `Bearer ${keycloak.token}`
      }
    } catch (_) {
      // not authenticated or refresh failed -> proceed without header
    }
    return config
  })
  api.__kc_interceptor_set = true
}

createApp(App).mount('#app')