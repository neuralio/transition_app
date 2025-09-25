<template>
    <form @submit.prevent="handleSend" class="p-4 border-t dark:border-gray-700">
      <div>
        <div class="flex items-center gap-3 rounded-xl">
          <input
            :value="props.modelValue"
            :disabled="isReadOnly"
            @input="emit('update:modelValue', $event.target.value)"
            @keyup.enter="handleSend"
            type="text"
            class="flex-1 px-4 py-2 rounded-lg focus-within:border-gray-800 border border-gray-300 dark:focus-within:border-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 outline-none disabled:cursor-not-allowed"
            :placeholder="placeholder"
          />
          <button
            type="submit"
            class="text-emerald-500 hover:text-emerald-600 dark:text-emerald-400 dark:hover:text-emerald-300 disabled:text-gray-400 disabled:dark:text-gray-600 disabled:cursor-not-allowed"
            :disabled="!text.trim() || isReadOnly"
          >
            <i class="fas fa-paper-plane text-lg"></i>
          </button>
        </div>
        
        <!-- Helper Text -->
        <div class="flex items-center justify-between mt-2 px-1">
          <p class="text-xs text-gray-400 dark:text-gray-500">
            Press Enter to send
          </p>
          <p class="text-xs text-gray-400 dark:text-gray-500">
            Use hashtags for quick access (#crop, #pv, #abm, #pecs, #full)
          </p>
          <p class="text-xs text-gray-400 dark:text-gray-500">
            <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-300 rounded text-gray-600">Shift</kbd> + 
            <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-300 rounded text-gray-600">Enter</kbd> for new line
          </p>
        </div>

      </div>  
    </form>
  </template>
  
  <script setup>
  import { ref, watch, computed } from 'vue'
  import { tryParseGeoJSON, summarizeGeoJSON } from '../utils/geojson'

  const props = defineProps({
    modelValue: String,
    isReadOnly: Boolean
  })
  
  const emit = defineEmits(['update:modelValue', 'send', 'geoJsonCreated'])
  
  const text = ref(props.modelValue || '')
  const placeholder = computed(() => props.isReadOnly ? "This conversation is closed! You can start a new one if you wish!" : "Type a message...")

  watch(() => props.modelValue, (newVal) => {
    text.value = newVal
  })

  const handleSend = () => {
    const rawStr = (text.value ?? '').trim()
    if (!rawStr) return

    let payload = { display: rawStr, raw: rawStr, isGeoJson: false }

    const parsed = tryParseGeoJSON(rawStr)
    if (parsed) {
      emit('geoJsonCreated', parsed)
      payload = { display: summarizeGeoJSON(parsed), raw: rawStr, isGeoJson: true }
    }

    emit('send', payload)            // 👈 emit a structured payload instead of a plain string
    emit('update:modelValue', '')
    text.value = ''
  }
  </script>
  