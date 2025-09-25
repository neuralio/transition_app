import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || ''
});

// Helper to lazily get keycloak via Vue inject (inside composition API context)
export function useApiWithAuth() {
  const keycloak = inject('keycloak')

  // Attach/refresh token per request
  api.interceptors.request.use(async (config) => {
    try { await keycloak.updateToken(30); } catch (_) {}
    if (keycloak.token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${keycloak.token}`;
    }
    return config;
  });

  // Optional: retry once on 401 after a forced refresh
  api.interceptors.response.use(
    res => res,
    async (error) => {
      const original = error.config;
      if (error.response?.status === 401 && !original.__retried) {
        original.__retried = true;
        try {
          await keycloak.updateToken(30);
          original.headers = original.headers || {};
          original.headers.Authorization = `Bearer ${keycloak.token}`;
          return api(original);
        } catch {
          keycloak.login();
        }
      }
      throw error;
    }
  );

  return api
}

export default api;
