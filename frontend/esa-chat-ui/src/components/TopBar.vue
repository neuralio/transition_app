<template>
    <div class="flex justify-between items-center p-2 border-b dark:border-gray-700">
      <div class="flex items-center gap-4">
        <!-- Show toggle and new chat only when sidebar is hidden -->
        <button
          v-if="!isSidebarOpen"
          @click="$emit('toggle-sidebar')"
          title="Show Sidebar"
          class="text-gray-800 dark:text-white hover:text-[#0892f5] dark:hover:text-[#066cb6]"
        >
          <i class="fas fa-book"></i>
        </button>
        <button
          v-if="!isSidebarOpen"
          @click="$emit('new-chat')"
          title="New Chat"
          class="text-gray-800 dark:text-white hover:text-[#0892f5] dark:hover:text-[#066cb6]"
        >
          <i class="fas fa-plus"></i>
        </button>
      </div>

      <!-- 🔰 Logo -->
      <div class="flex flex-col items-center text-center" v-if="!isSidebarOpen">
        <img src="https://neuralio.ai/assets/img/neuralio-logo-hor-lightbg.svg" alt="Logo" class="object-contain" style="height: 35px;"/>
        <span class="text-xs text-gray-600 dark:text-gray-400 italic">Your vision, enhanced</span>
      </div>

      <div class="flex items-center gap-1">
        <button
          @click="$emit('toggle-dark')"
          class="text-gray-700 dark:text-gray-200 hover:text-[#f6f654] dark:hover:text-[#fafaa2] text-xl"
          title="Toggle Light/Dark Mode"
        >
          <i :class="isDark ? 'fas fa-sun' : 'fas fa-moon'"></i>
        </button>
        <auth-buttons></auth-buttons>
      </div>
    </div>
</template>
  
<script setup>
  import AuthButtons from './AuthButtons.vue';
  defineProps({
    isSidebarOpen: Boolean,
    isDark: Boolean
  })
  defineEmits(['toggle-sidebar', 'new-chat', 'toggle-dark'])
</script>
  