import Keycloak from 'keycloak-js';

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
});

export async function initKeycloak(loginRequired = true) {
  const onLoad = loginRequired ? 'login-required' : 'check-sso';
  const authenticated = await keycloak.init({
    onLoad,
    pkceMethod: 'S256',
    checkLoginIframe: false,
    // silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
  });
  return authenticated;
}

export function startTokenRefresh() {
  const interval = setInterval(async () => {
    try {
      await keycloak.updateToken(30); // refresh if expiring in 30s
    } catch (e) {
      // refresh failed (e.g. session expired) -> go to login
      try { keycloak.login(); } catch (_) {}
    }
  }, 20000);
  return () => clearInterval(interval);
}

// Optional: react exactly at expiry as well
keycloak.onTokenExpired = () => {
  keycloak.updateToken(30).catch(() => keycloak.login());
};