<template>
    <div :class="['slider-container', { dark: isDark }]">
      <!-- Selected Date Display -->
      <div class="date-display">
        <p>Selected Year: <strong>{{ displayDate }}</strong></p>
      </div>

      <!-- Slider Controls -->
      <div class="slider-controls">
        <!-- Navigation Arrows -->
        <button @click="goToFirst" :disabled="isAtFirst"> « </button>
        <button @click="goToPrevious" :disabled="isAtFirst"> ‹ </button>
        
        <!-- Slider Input -->
        <span class="date-range"><strong>{{ firstDate }}</strong></span>
        <input 
          :id="sliderId" 
          type="range" 
          :min="0" 
          :max="dates.length - 1" 
          v-model="sliderIndex"
          @input="emitSelectedDate"
        />
        <span class="date-range"><strong>{{ lastDate }}</strong></span>

        <!-- Navigation Arrows -->
        <button @click="goToNext" :disabled="isAtLast"> › </button>
        <button @click="goToLast" :disabled="isAtLast"> » </button>
      </div>
    </div>
</template>
  
<script setup>
    import { defineProps, defineEmits, ref, computed } from 'vue'

    const props = defineProps({
      isDark: {
        type: Boolean,
        default: false
      },
      dates: {
        type: Array,
        required: true, // Array of dates
      },
      sliderId: {
        type: String,
        required: true
      }
    })

    const emit = defineEmits([
        'date-changed'
    ])

    const sliderIndex = ref(0)

    const selectedDate = computed(() => props.dates[sliderIndex.value] || "")
    const displayDate = computed(() => selectedDate.value.split("-")[0] || "No date available")
    const firstDate = computed(() => props.dates[0].split("-")[0] || "No dates")
    const lastDate = computed(() => props.dates[props.dates.length - 1].split("-")[0] || "No dates")
    const isAtFirst = computed(() => sliderIndex.value === 0)
    const isAtLast = computed(() => sliderIndex.value === props.dates.length - 1)


    const emitSelectedDate = () => {
        emit("date-changed", selectedDate.value)
    }

    const goToFirst = () => {
        sliderIndex.value = 0
        emitSelectedDate()
    }

    const goToLast = () => {
        sliderIndex.value = props.dates.length - 1
        emitSelectedDate()
    }

    const goToPrevious = () => {
        if (!isAtFirst.value) {
          sliderIndex.value--
          emitSelectedDate()
        }
    }
      
    const goToNext = () => {
        if (!isAtLast.value) {
          sliderIndex.value++
          emitSelectedDate()
        }
    }
</script>
  
<style scoped>
  .slider-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    margin: 0 0 20px 0;
    font-family: Arial, sans-serif;
    width: 100%;
  }

  .date-display,
  .date-range {
    text-align: center;
    font-size: 14px;
    color: #000;
  }

  .slider-container.dark .date-display,
  .slider-container.dark .date-range {
    color: white;
  }

  .slider-controls {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  input[type="range"] {
    width: 500px;
    accent-color: #066cb6;
  }

  .slider-container.dark input[type="range"] {
    accent-color: #066cb6;
  }

  button {
    background-color: #066cb6;
    color: white;
    border: none;
    padding: 5px 10px;
    font-size: 14px;
    cursor: pointer;
    border-radius: 4px;
  }

  button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }

  button:hover {
    background-color: #044c80;
  }
</style>
  