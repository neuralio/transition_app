<template>
    <div class="flex flex-col h-full overflow-y-auto">
      <!-- Message List -->
      <div ref="scrollContainer" class="flex-1 overflow-y-auto p-4 space-y-4">

        <div v-if="messages.length === 0" class="p-4 text-gray-600 bg-white dark:bg-gray-900 rounded shadow dark:shadow-gray-600 text-center space-y-3">
          <!-- Logo -->
          <img src="https://transition.neuralio.ai/assets/img/transition-logo-horizontal-darkbg.svg" alt="Logo" class="mx-auto h-12 object-contain" />

          <!-- Title -->
          <h2 class="text-lg font-bold">👋 Welcome to the Transition Assistant</h2>

          <!-- Description -->
          <p>
            TRANSITION is your smart assistant powered by advanced Earth Observation and modeling tools.  
            It helps you explore the land's potential under current and future climate conditions.
          </p>

          <!-- Features -->
          <ul class="list-disc text-left pl-5 mt-2 space-y-1 text-sm">
            <li>📊 Simulate <strong> climate projection scenarios to investigate possible features.</strong></li>
            <li>🔋 Run your scenarios <strong> with our agent based modeling framework</strong></li>
            <li>🌍 Results <strong> with graphs and WMS maps</strong> </li>
            <li>✏️ Quickly access services  <strong>using shortcuts such as #crop, #pv and #abm, #pecs, #full for 'Crop Suitability', 'Photovoltaic Simulation', 'Basic Agent-Based Modelling', 'Enhanced Agent-Based Modelling' or 'Full Agent-Based Modelling' scenarios.</strong></li>
          </ul>

          <!-- Suggestion -->
          <p class="mt-2 text-sm italic text-gray-500">
            Try asking:
            <code class="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">What are the available services?</code>
          </p>
        </div>

        <!-- Messages -->
        <ChatBubble
          v-for="(msg, index) in messages"
          :key="index"
          :message="msg"
          :index="index"
          :isLastUserMessage="msg.role === 'user' && isLastUser(index)"

          :isDark="isDark"
          :isReadOnly="isReadOnly"

          @update-user-input="handleUserAOI"

          @updateGraph="payload => emit('updateGraph', payload)"
          @trigger-wms-click="payload => emit('trigger-wms-click', payload)"
          @trigger-wms-click-handled="payload => emit('trigger-wms-click-handled', payload)"
          @dates-available="payload => emit('dates-available', payload)"
          @date-changed="payload => emit('date-changed', payload)"

          @updateProfitGraph="payload => emit('updateProfitGraph', payload)"
          @trigger-profit-wms-click="payload => emit('trigger-profit-wms-click', payload)"
          @trigger-profit-wms-click-handled="payload => emit('trigger-profit-wms-click-handled', payload)"
          @profit-dates-available="payload => emit('profit-dates-available', payload)"
          @profit-date-changed="payload => emit('profit-date-changed', payload)"

          @retry="retryMessage"
          @edit="editMessage"
        />
    
        <!-- Typing Indicator -->
        <div v-if="isTyping" class="p-4 text-sm text-gray-400 dark:text-gray-500">
          <span v-if="showPVindicator">
            Calculations in progress. This may take a little longer than usual. Please hold on...
          </span>
          <span v-else>
            Assistant Typing...
          </span>
        </div>

        <MapDisplayDraw
          v-if="activeComponents.map && !geoJsonData"
          :pilotArea="pilotArea"
          @geojson-input="handleUserAOI"
        />

        <div ref="scrollAnchor" />
      </div>
  
      <!-- Input Bar -->
      <InputBar 
        v-model="userInput" 
        :isReadOnly="isReadOnly"
        @send="sendMessage" 
        @geoJsonCreated="geoJson => emit('geoJsonCreated', geoJson)"
      />

    </div>
  </template>
  
  <script setup>
  import ChatBubble from './ChatBubble.vue'
  import MapDisplayDraw from './MapDisplayDraw.vue'
  import InputBar from './InputBar.vue'

  import { defineProps, defineEmits, ref, watch, nextTick, toRefs } from 'vue'
  import api from '../api'
  
  const props = defineProps({
    isDark: Boolean,
    messages: Array,
    isTyping: Boolean,
    input: String,
    activeComponents: Object,
    pilotArea: String,
    geoJsonData: Object,
    graphData: Array,
    barChartData: Array,
    wmsLayers: Array,
    profitWmsLayers: Array,
    profitGraphData: Array,
    serviceCalled: String,
    showPVindicator: Boolean,
    mapExplanation: String,
    isReadOnly: Boolean,
    sessionId: String
  })
  
  const emit = defineEmits([
    'update:messages', 
    'update:input', 
    'update:isTyping', 
    'response',

    'geoJsonCreated',

    'updateGraph',
    'dates-available',
    'date-changed',
    'trigger-wms-click-handled',
    'trigger-wms-click',

    'updateProfitGraph',
    'profit-dates-available',
    'profit-date-changed',
    'trigger-profit-wms-click-handled',
    'trigger-profit-wms-click',
  ])

  const {
    activeComponents,
    pilotArea,
    graphData,
    barChartData,
    geoJsonData,
    wmsLayers,
    profitWmsLayers,
    profitGraphData,
    mapExplanation
  } = toRefs(props)
  
  const userInput = ref(props.input || '')

  watch(() => props.input, (newVal) => {
    userInput.value = newVal
  })

  watch(() => props.messages, () => {
    nextTick(() => {
      scrollToBottom()
    })
  })

  const scrollAnchor = ref(null)

  const scrollToBottom = () => {
    if (scrollAnchor.value) {
      scrollAnchor.value.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const sendMessage = async (customPayload = null) => {
    let raw = customPayload['raw'].trim()
    let display = customPayload['display'].trim()

    emit('update:isTyping', true)

    const updatedMessages = [...props.messages, {
      role: 'user',
      content: display,       // 👈 pretty text for the bubble
      raw,                    // 👈 keep original text for backend/retry/edit
      isGeoJson: customPayload['isGeoJson'],
      timestamp: new Date()
    }]
    emit('update:messages', updatedMessages)
    emit('update:input', '')

    try {
      const response = await api.post('/api/chat', {
        message: raw,    // 👈 send the original text/JSON to the backend
        session_id: props.sessionId
      }, {
        timeout: 600000  // 10 minutes in ms
      })

      emit('response', response.data)

      // ✅ Wait for Vue to apply reactivity
      await nextTick()

      const newMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
        activeComponents: { ...activeComponents.value },
        mapData: {
          pilotArea: pilotArea.value,
          geoJsonData: geoJsonData.value,
          wmsLayers: [ ...wmsLayers.value ],
          mapExplanation: mapExplanation.value
        },
        graphData: { data: [ ...graphData.value ] },
        barChartData: { data: [ ...barChartData.value ] },
        profitMapData: {
          pilotArea: pilotArea.value,
          geoJsonData: geoJsonData.value,
          wmsLayers: [ ...profitWmsLayers.value ],
          mapExplanation: ""          
        },
        profitGraphData: { data: [ ...profitGraphData.value ] },
        serviceCalled: props.serviceCalled
      }

      emit('update:messages', [...updatedMessages, newMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorReply = {
        role: 'assistant',
        content: 'An error occurred. Please try again.',
        timestamp: new Date()
      }
      emit('update:messages', [...updatedMessages, errorReply])
    } finally {
      emit('update:isTyping', false)
    }
  }

  const retryMessage = (message) => {
    sendMessage(message.raw || message.content)
  }

  const editMessage = (message) => {
    userInput.value = message.raw || message.content
  }

  const isLastUser = (index) => {
    for (let i = props.messages.length - 1; i >= 0; i--) {
      if (props.messages[i].role === 'user') {
        return i === index;
      }
    }
    return false;
  }

  const handleUserAOI = (geojsonText) => {
    userInput.value = geojsonText    
    emit('update:input', geojsonText)
  }
  </script>
  