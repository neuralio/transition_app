<template>
  <transition name="slide">
    <div
      v-if="isSidebarOpen"
      class="w-64 bg-gray-100 dark:bg-gray-800 transition-all flex flex-col"
    >
      <!-- 🔰 Logo -->
      <div class="px-4 py-3 flex flex-col items-center text-center">
        <img src="https://neuralio.ai/assets/img/neuralio-logo-hor-lightbg.svg" alt="Logo" class="h-12 object-contain mb-1" />
        <span class="text-xs text-gray-600 dark:text-gray-400 italic">Your vision, enhanced</span>
      </div>

      <!-- Sidebar Top Bar -->
      <div class="flex items-center justify-between px-4 py-2 border-t border-gray-300 dark:border-gray-700">
        <div class="flex items-center gap-2">
          <button
            @click="$emit('toggle-sidebar')"
            title="Toggle Sidebar"
            class="text-gray-800 dark:text-white hover:text-[#0892f5] dark:hover:text-[#066cb6]"
          >
            <i class="fas fa-book"></i>
          </button>
          <!-- <button title="Search" class="text-gray-800 dark:text-white">
            <i class="fas fa-search"></i>
          </button> -->
        </div>
        <button
          @click="$emit('new-chat')"
          title="New Chat"
          class="text-gray-800 dark:text-white hover:text-[#0892f5] dark:hover:text-[#066cb6]"
        >
          <i class="fas fa-plus"></i>
        </button>
      </div>

      <!-- Sidebar Content -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="chatSessions.length === 0" class="text-center py-8 text-gray-400">
          <i class="fas fa-comments text-3xl mb-3"></i>
          <p class="text-sm">No conversations yet</p>
        </div>

        <ul class="space-y-0.5 px-2 py-3">
          <li
            v-for="session in chatSessions"
            :key="session.id"
            class="group relative flex items-center justify-between gap-1 cursor-pointer px-2 py-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
            :class="session.id === activeSessionId ? 'bg-gray-300 dark:bg-gray-700 font-semibold' : ''"
            @click="$emit('select-session', session.id)"
          >
            <!-- Title / Inline editor -->
            <div class="min-w-0 flex-1">
              <template v-if="editingId === session.id">
                <form
                  class="w-full"
                  @submit.prevent="confirmRename(session.id)"
                  @click.stop
                >
                  <input
                    :id="`rename-${session.id}`"
                    v-model="editingTitle"
                    class="w-full text-[13px] leading-5 px-2 py-0.5 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"
                    @click.stop
                    @keydown.esc.stop.prevent="cancelRename"
                    @blur="confirmRename(session.id)"
                    :placeholder="session.title || 'Untitled'"
                    autocomplete="off"
                    spellcheck="false"
                  />
                </form>
              </template>
              <template v-else>
                <!-- Native tooltip via title= shows full text on hover -->
                <div
                  class="truncate text-[13px] leading-5 text-gray-800 dark:text-gray-100"
                  :title="session.title || 'Untitled'"
                >
                  {{ session.title || 'Untitled' }}
                </div>
              </template>
            </div>

            <!-- Actions (appear on hover) -->
            <div class="flex-shrink-0 flex items-center gap-1">
              <button
                class="opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-gray-500 hover:text-emerald-600 dark:hover:text-emerald-300 p-0.5 rounded"
                title="Rename session"
                @click.stop="startRename(session.id, session.title)"
              >
                <i class="fas fa-pen pb-1.5" style="font-size: 0.75rem;"></i>
              </button>
              <button
                class="opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-gray-500 hover:text-[#9e0230] dark:hover:text-[#fd0952] p-0.5 rounded"
                title="Delete session"
                @click.stop="$emit('delete-session', session.id)"
              >
                <i class="fas fa-trash pb-1.5" style="font-size: 0.75rem;"></i>
              </button>
            </div>
          </li>
        </ul>
      </div> 
    </div>
  </transition>
</template>


  <script setup>
    import { ref, nextTick } from 'vue'

    const props = defineProps({
        isSidebarOpen: Boolean,
        chatSessions: Array,
        activeSessionId: String
    })
    
    const emit = defineEmits([
      'toggle-sidebar', 
      'new-chat', 
      'select-session', 
      'delete-session', 
      'rename-session'
    ])

    /* Inline rename state */
    const editingId = ref(null)
    const editingTitle = ref('')
    const originalTitle = ref('')
    const renameInFlight = ref(false)

    async function startRename(id, currentTitle) {
      editingId.value = id
      originalTitle.value = (currentTitle || '').trim()
      editingTitle.value = originalTitle.value
      await nextTick()
      const el = document.getElementById(`rename-${id}`)
      if (el) { el.focus(); el.select() }
    }

    function confirmRename(id) {
      // prevent duplicate calls (Enter + blur)
      if (renameInFlight.value) return
      if (editingId.value !== id) return

      const newTitle = (editingTitle.value || '').trim()

      // If empty or unchanged → just exit edit mode silently
      if (!newTitle || newTitle === originalTitle.value) {
        editingId.value = null
        editingTitle.value = ''
        originalTitle.value = ''
        return
      }

      renameInFlight.value = true
      // emit to parent; parent updates title without reordering
      emit('rename-session', { id, title: newTitle })
      // immediately exit edit mode; UI updates instantly
      editingId.value = null
      editingTitle.value = ''
      originalTitle.value = ''
      // allow future renames
      renameInFlight.value = false
    }

    function cancelRename() {
      editingId.value = null
      editingTitle.value = ''
      originalTitle.value = ''
    }
  </script>
  