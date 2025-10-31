<template>
  <div
    :class="[
      'flex items-start gap-3 mb-4',
      isUser ? 'flex-row-reverse' : 'flex-row'
    ]"
  >

  <!-- Avatar Icon -->
  <div
    :class="[
      'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-base',
      isUser
        ? 'bg-[#066cb6] text-white'
        : 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-white'
    ]"
  >
    <i :class="[isUser ? 'fas fa-user' : 'fas fa-robot']"></i>
  </div>

    <!-- Message Content -->
    <div class="flex flex-col max-w-[75%] min-w-[75%]" :class="isUser ? 'items-end' : 'items-start'">
      <div class="text-xs text-gray-400 mb-1">{{ formattedTime }}</div>

      <div
        :class="[
          'relative p-3 rounded-lg text-sm',
          isUser
            ? 'bg-[#066cb6] text-white rounded-br-none'
            : 'bg-gray-200 dark:bg-gray-700 dark:text-white text-gray-900 rounded-bl-none'
        ]"
        v-html="formattedMessage"
        style="line-height: 1.4;"
      ></div>

      <transition name="fade">
        <MapDisplay
          v-if="hasMap"
          :pilotArea="message.mapData?.pilotArea"
          :geoJsonData="message.mapData?.geoJsonData"
          :wmsLayers="message.mapData?.wmsLayers"
          :selectedDate="message.graphData?.selectedDate"
          :triggerWmsClick="message.graphData?.triggerWmsClick || false"
          @updateGraph="data => emit('updateGraph', { idx: index, key: 'graphData', data })"
          @dates-available="dates => emit('dates-available', { idx: index, key: 'graphData', dates })"
          @trigger-wms-click-handled="emit('trigger-wms-click-handled', { idx: index, key: 'graphData', value: false })"
          :mapId="`map-${message.timestamp}`"
          :mapExplanation="message.mapData?.mapExplanation"
        />
      </transition>        
      <DateSlider 
        v-if="hasSlider && message.graphData?.availableDates?.length > 0" 
        :isDark="isDark"
        :dates="message.graphData?.availableDates || []" 
        @date-changed="date => emit('date-changed', { idx: index, key: 'graphData', date })"
        :sliderId="`slider-${message.timestamp}`"
      />       

      <transition name="fade">
        <GraphDisplay 
          v-if="hasGraph" 
          :isDark="isDark"
          :datasets="message.graphData?.data || []"
          :serviceCalled="message.serviceCalled"
          @trigger-wms-click="emit('trigger-wms-click', { idx: index, key: 'graphData', value: true })"
          :graphId="`graph-${message.timestamp}`"
        />
      </transition>


      <!-- Spacer -->
      <div v-if="hasProfitMap || hasProfitSlider || hasProfitGraph" class="mt-6" />

      <transition name="fade">
        <MapDisplay
          v-if="hasProfitMap"
          :pilotArea="message.profitMapData?.pilotArea"
          :geoJsonData="message.profitMapData?.geoJsonData"
          :wmsLayers="message.profitMapData?.wmsLayers"
          :selectedDate="message.profitGraphData?.selectedDate"
          :triggerWmsClick="message.profitGraphData?.triggerWmsClick || false"
          @updateGraph="data => emit('updateProfitGraph', { idx: index, key: 'profitGraphData', data })"
          @dates-available="dates => emit('profit-dates-available', { idx: index, key: 'profitGraphData', dates })"
          @trigger-wms-click-handled="emit('trigger-profit-wms-click-handled', { idx: index, key: 'profitGraphData', value: false })"
          :mapId="`profit-map-${message.timestamp}`"
          :mapExplanation="message.profitMapData?.mapExplanation"
        />
      </transition>        
      <DateSlider 
        v-if="hasProfitSlider && message.profitGraphData?.availableDates?.length > 0" 
        :isDark="isDark"
        :dates="message.profitGraphData?.availableDates || []" 
        @date-changed="date => emit('profit-date-changed', { idx: index, key: 'profitGraphData', date })"
        :sliderId="`profit-slider-${message.timestamp}`"
      />        

      <transition name="fade">
        <GraphDisplay 
          v-if="hasProfitGraph" 
          :isDark="isDark"
          :datasets="message.profitGraphData?.data || []"
          :serviceCalled="message.serviceCalled"
          @trigger-wms-click="emit('trigger-profit-wms-click', { idx: index, key: 'profitGraphData', value: true })"
          :graphId="`profit-graph-${message.timestamp}`"
        />
      </transition>


      <transition-group name="fade" tag="div" v-if="hasBarChart" style="width: 100%;">
        <BarChartDisplay 
          v-for="(chart, idx) in message.barChartData" 
          :key="`chart-${idx}-${message.timestamp}`"
          :isDark="isDark"
          :datasets="[chart]"
          :serviceCalled="message.serviceCalled"
          :chartId="`chart-${idx}-${message.timestamp}`"
        />
      </transition-group>


      <div
        v-if="isUser && !isReadOnly"
        class="flex justify-end gap-2 mt-2 text-xs text-gray-600 dark:text-gray-300"
      >
        <button v-if="isLastUserMessage" @click="$emit('edit', message)">
          <i class="fas fa-edit hover:text-emerald-600 dark:hover:text-emerald-300"></i>
        </button>
        <button @click="$emit('retry', message)">
          <i class="fas fa-redo hover:text-emerald-600 dark:hover:text-emerald-300"></i>
        </button>
      </div>
    </div>
  </div>
</template>


<script setup>
  import { computed } from 'vue'

  import BarChartDisplay from './BarChartDisplay.vue'
  import MapDisplay from './MapDisplay.vue'
  import DateSlider from './DateSlider.vue'
  import GraphDisplay from './GraphDisplay.vue'

  const props = defineProps({
    message: Object,
    index: Number,
    isLastUserMessage: Boolean,
    isDark: Boolean,
    isReadOnly: Boolean
  })

  const emit = defineEmits([
    'trigger-wms-click-handled',
    'trigger-wms-click',
    'updateGraph',
    'dates-available',
    'date-changed',

    'updateProfitGraph',
    'profit-dates-available',
    'profit-date-changed',
    'trigger-profit-wms-click-handled',
    'trigger-profit-wms-click',

    'emit',
    'retry'
  ])

  const isUser = computed(() => props.message.role === 'user')

  const hasMap = computed(() => !isUser.value && props.message.activeComponents?.map && props.message.mapData?.geoJsonData)
  const hasSlider = computed(() => !isUser.value && props.message.activeComponents?.slider)
  const hasGraph = computed(() => !isUser.value && props.message.activeComponents?.graph)

  const hasProfitMap = computed(() => !isUser.value && props.message.activeComponents?.profit_map && props.message.profitMapData?.geoJsonData)
  const hasProfitSlider = computed(() => !isUser.value && props.message.activeComponents?.profit_slider)
  const hasProfitGraph = computed(() => !isUser.value && props.message.activeComponents?.profit_graph)

  const hasBarChart = computed(() => !isUser.value && props.message.activeComponents?.bar_chart && props.message.serviceCalled.toLowerCase().includes("abm"))

  const formattedTime = computed(() => {
    const date = new Date(props.message.timestamp || Date.now())
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })

  const formattedMessage = computed(() => {
    return props.message.content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')       // bold για **text**
      .replace(/(^|\s)(#\w[\w-]*)/g, '$1<span class="font-bold text-emerald-400">$2</span>') // πράσινο hashtag
      .replace(/\n/g, '<br>')                                  // νέα γραμμή
  })

</script>