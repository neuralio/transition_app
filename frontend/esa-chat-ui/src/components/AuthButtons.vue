<template>
  <div class="flex items-center gap-3 ml-1">
    <!-- LOGOUT (shown when authenticated) -->
    <button
      v-if="authed"
      @click="logout"
      class="inline-flex h-10 w-10 items-center justify-center
             text-gray-700 dark:text-gray-200
             hover:text-[#0892f5] dark:hover:text-[#066cb6]
             focus:outline-none focus:ring-2 focus:ring-indigo-500/50
             transition-colors"
      :title="username ? `Logout (${username})` : 'Logout'"
      aria-label="Logout"
    >
      <!-- FA5 icon; if you use FA6, swap to fa-right-from-bracket -->
      <i class="fas fa-sign-out-alt text-lg"></i>
    </button>

    <!-- LOGIN (shown when NOT authenticated) -->
    <button
      v-else
      @click="login"
      class="inline-flex h-10 w-10 items-center justify-center
             text-gray-700 dark:text-gray-200
             hover:text-green-600 dark:hover:text-green-400
             focus:outline-none focus:ring-2 focus:ring-green-500/50
             transition-colors"
      title="Login"
      aria-label="Login"
    >
      <!-- FA5 icon; if you use FA6, swap to fa-right-to-bracket -->
      <i class="fas fa-sign-in-alt text-lg"></i>
    </button>
  </div>
</template>

<script setup>
  import { ref, onMounted } from 'vue'
  import { keycloak } from '../auth/keycloak';

  const authed = ref(!!keycloak.authenticated)
  const username =
    (keycloak.tokenParsed && keycloak.tokenParsed.preferred_username) || ''

  const login = () =>
    keycloak.login({ redirectUri: window.location.origin + '/' })

  const logout = () =>
    keycloak.logout({ redirectUri: window.location.origin + '/' })

  // keep UI in sync with keycloak events
  const update = () => {
    authed.value = !!keycloak.authenticated
  }

  onMounted(() => {
    keycloak.onAuthSuccess = update
    keycloak.onAuthRefreshSuccess = update
    keycloak.onAuthLogout = update
    keycloak.onAuthError = update
  })
</script>


