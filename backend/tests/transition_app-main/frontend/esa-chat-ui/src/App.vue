<template>
  <div :class="{ 'dark': isDark }" class="h-screen overflow-hidden">
    <div class="flex h-full">
      <!-- Sidebar -->
      <SideBar
        :isSidebarOpen="isSidebarOpen"
        :chatSessions="orderedSessions"
        :activeSessionId="activeSessionId"
        @toggle-sidebar="toggleSidebar"
        @new-chat="startNewChat"
        @select-session="loadSession"
        @delete-session="handleDeleteSession"
        @rename-session="handleRenameSession"
      />

      <!-- Main Content -->
      <div class="flex-1 relative bg-white dark:bg-gray-900 text-gray-900 dark:text-white flex flex-col">
        <!-- Top bar -->
        <TopBar
          :isSidebarOpen="isSidebarOpen"
          :isDark="isDark"
          @toggle-sidebar="toggleSidebar"
          @new-chat="startNewChat"
          @toggle-dark="toggleDark"
        />

        <!-- Chat Area -->
        <ChatArea
          :isDark="isDark"
          :messages="messages"
          :isTyping="isTyping"
          :activeComponents="activeComponents"
          :pilotArea="pilotArea"
          :geoJsonData="geoJsonData"
          :graphData="graphData"
          :barChartData="barChartData"
          :wmsLayers="wmsLayers"
          :profitGraphData="profitGraphData"
          :profitWmsLayers="profitWmsLayers"
          :serviceCalled="serviceCalled"
          :showPVindicator="showPVindicator"
          :mapExplanation="mapExplanation"
          :isReadOnly="isReadOnly"
          :sessionId="activeSessionId"

          v-model:triggerWmsClick="triggerWmsClick"
          v-model:triggerProfitWmsClick="triggerProfitWmsClick"

          @update:messages="messages = $event"
          @update:isTyping="isTyping = $event"
          @response="handleChatbotResponse"

          @geoJsonCreated="handleGeoJsonCreated"

          @update-graph="handleGraphUpdate"
          @dates-available="updateAvailableDates"
          @date-changed="handleDateChange"
          @trigger-wms-click-handled="setWmsTrigger"
          @trigger-wms-click="setWmsTrigger"

          @update-profit-graph="handleProfitGraphUpdate"
          @profit-dates-available="updateProfitAvailableDates"
          @profit-date-changed="handleProfitDateChange"
          @trigger-profit-wms-click-handled="setProfitWmsTrigger"
          @trigger-profit-wms-click="setProfitWmsTrigger"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, computed } from 'vue'

import SideBar from './components/SideBar.vue'
import TopBar from './components/TopBar.vue'
import ChatArea from './components/ChatArea.vue'

import { chatBot } from './composables/chatBot.js'
import api from './api'
import { keycloak } from './auth/keycloak.js'
import useSessions from './composables/useSessions.js'

const isDark = ref(false)
const isSidebarOpen = ref(true)
const messages = ref([])
const isTyping = ref(false)

const chatSessions = ref([])
const activeSessionId = ref(crypto.randomUUID())
const currentSessionId = ref(activeSessionId.value)
const isLoadingSession = ref(false)

const globalArea = ref(null)
const pilotArea = ref(null)
const serviceCalled = ref(null)
const showPVindicator = ref(false)
const activeComponents = ref({ 
  map: false, 
  graph: false, 
  simple_map: false, 
  bar_chart: false, 
  slider: false, 
  profit_map: false, 
  profit_graph: false, 
  profit_slider: false
})
const graphData = ref([])
const barChartData = ref([])
const wmsLayers = ref([])
const profitGraphData = ref([])
const profitWmsLayers = ref([])
const geoJsonData = ref(null)
const selectedDate = ref(null)
const availableDates = ref([])
const selectedProfitDate = ref(null)
const availableProfitDates = ref([])
const triggerWmsClick = ref(false)
const triggerProfitWmsClick = ref(false)
const mapExplanation = ref(null)

const isReadOnly = computed(() => currentSessionId.value !== activeSessionId.value)
const orderedSessions = computed(
  () => [...chatSessions.value].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))
)
const handledDeepLink = ref(false)

const { handleChatbotResponse } = chatBot(
  activeComponents,
  graphData,
  profitGraphData,
  barChartData,
  wmsLayers,
  profitWmsLayers,
  geoJsonData, 
  globalArea,
  pilotArea, 
  serviceCalled,
  showPVindicator,
  mapExplanation
)

const {
  fetchSessions,
  fetchSession,
  saveSession,
  debouncedSave,
  renameSession,
  seedHistory,
  deleteSession: deleteSessionApi
} = useSessions(api)


onMounted(async() => {
  if (localStorage.getItem('dark') === 'true') {
    isDark.value = true
  }

  // Load session list (metadata) when authenticated
  const loadList = async () => {
    const list = await fetchSessions()
    chatSessions.value = list.map(s => ({
      id: s.id,
      title: s.title,
      updated_at: typeof s.updated_at === 'string'
        ? (Date.parse(s.updated_at) / 1000) || 0
        : Number(s.updated_at) || 0, // keep for sorting
      messages: [] // fetch full only when opened
    }))
  }

  // Load saved session metadata from the server
  // If already authenticated (hard reload after login, etc.)
  if (keycloak?.authenticated) {
    try {
      await loadList()
      await handleDeepLink() 
    } catch (e) {
      console.warn('Could not fetch sessions list:', e?.response?.data || e.message)
    }
  } else if (keycloak) {
    // Wait for login success exactly once
    const orig = keycloak.onAuthSuccess
    keycloak.onAuthSuccess = async () => {
      try {
        await loadList()
        await handleDeepLink() 
      } catch (e) {
        console.warn('Could not fetch sessions list:', e?.response?.data || e.message)
      } finally {
        // restore any previous handler
        keycloak.onAuthSuccess = orig
      }
    }
  }
})

const toggleDark = () => {
  isDark.value = !isDark.value
  localStorage.setItem('dark', isDark.value)
}

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

async function handleDeepLink() {
  if (handledDeepLink.value) return

  const params = new URLSearchParams(window.location.search)
  const deepLinkId = params.get('sessionId')
  if (!deepLinkId) { handledDeepLink.value = true; return }

  // Make sure it exists in the list (refresh if needed)
  const exists = chatSessions.value.some(s => s.id === deepLinkId)
  if (!exists) {
    try {
      const list = await fetchSessions()
      chatSessions.value = list.map(s => ({
        id: s.id,
        title: s.title,
        updated_at: typeof s.updated_at === 'string'
        ? (Date.parse(s.updated_at) / 1000) || 0
        : Number(s.updated_at) || 0,
        messages: []
      }))
    } catch (e) {
      console.warn('Could not refresh sessions for deep link:', e?.response?.data || e.message)
    }
  }

  // Open it
  try { await loadSession(deepLinkId) } catch (e) {
    console.warn('Failed to open deep-linked session:', e?.response?.data || e.message)
  }

  // Clean the URL (optional)
  const url = new URL(window.location.href)
  url.searchParams.delete('sessionId')
  window.history.replaceState({}, '', url)

  handledDeepLink.value = true
}

async function resetSession(sessionId) {
  try {
    const response = await api.post('/api/clear-session', 
      { session_id: sessionId },
    );
    return response.data;
  } catch (error) {
    console.error("Error clearing session:", error.response?.data || error.message);
  }
}

async function upsertLocalSessionList(id, title, messageArr = [], tsSec = null) {
  // Ensure the saved session appears in the list (fallback when offline)
  const entry = { 
    id, 
    title: title || 'Untitled Chat', 
    updated_at: tsSec ?? (Date.now() / 1000),
    messages: [...messageArr] 
  }
  const idx = chatSessions.value.findIndex(s => s.id === id)
  if (idx !== -1) {
    chatSessions.value[idx] = entry
  } else {
    chatSessions.value.unshift(entry)
  }
}

function autoTitleFromMessages(msgs) {
  const firstUser = (msgs || []).find(m => m.role === 'user')
  if (!firstUser?.content) return 'Untitled'
  let s = firstUser.content
    .replace(/\s+/g, ' ')
    .replace(/^[#>\-\*\s]+/, '')
    .trim()
  if (s.length > 60) s = s.slice(0, 57).trim() + '…'
  // Capitalize first letter
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function normalizeMessage(msg) {
  if (Array.isArray(msg.graphData)) {
    msg.graphData = { data: msg.graphData }
  }
  if (Array.isArray(msg.profitGraphData)) {
    msg.profitGraphData = { data: msg.profitGraphData }
  }
  return msg
}

const clearLocalValues  = () => {
  // 🚫 Clear frontend memory values that pollute backend state
  geoJsonData.value = null
  globalArea.value = null
  pilotArea.value = null
  serviceCalled.value = null
  mapExplanation.value = null
  selectedDate.value = null
  availableDates.value = []
  selectedProfitDate.value = null
  availableProfitDates.value = []

  // Reset all session-related state
  messages.value = []
  isTyping.value = false
  showPVindicator.value = false
  activeComponents.value = { 
    map: false, 
    graph: false, 
    simple_map: false, 
    bar_chart: false, 
    slider: false, 
    profit_map: false, 
    profit_graph: false, 
    profit_slider: false
  }
  graphData.value = []
  barChartData.value = []
  wmsLayers.value = []
  profitGraphData.value = []
  profitWmsLayers.value = []
}


const startNewChat = async (opts = {}) => {
  const skipSave = opts?.skipSave === true

  // 1) Save the current live session only if not skipping, not read-only, and there are messages
  if (!skipSave && !isReadOnly.value && messages.value.length) {
    const justSavedId = activeSessionId.value
    // const justSavedTitle = messages.value[0]?.content || 'Untitled Chat'
    const justSavedTitle = messages.value[0]?.content.trim()
      ? messages.value[0].content.trim()
      : autoTitleFromMessages(messages.value)
    const justSavedMessages = [...messages.value]

    try {
      await saveSession(justSavedId, justSavedTitle, justSavedMessages)

      // 2) Refresh the list from server so it shows the newly saved session
      try {
        const list = await fetchSessions()
        chatSessions.value = list.map(s => ({
          id: s.id, 
          title: s.title, 
          updated_at: typeof s.updated_at === 'string'
            ? (Date.parse(s.updated_at) / 1000) || 0
            : Number(s.updated_at) || 0, 
          messages: []   // keep metadata; fetch full when opened
        }))
      } catch {
        // fallback: reflect it locally immediately
        await upsertLocalSessionList(justSavedId, justSavedTitle, justSavedMessages)
      }
    } catch (e) {
      console.warn('Failed to save current session before new chat:', e?.response?.data || e.message)
      // still try to reflect it locally to avoid “losing” it from the UI
      await upsertLocalSessionList(justSavedId, justSavedTitle, justSavedMessages)
    }
  }

  // 3) Create a fresh session id and reset backend state for the new, empty chat
  activeSessionId.value = crypto.randomUUID()
  await resetSession(String(activeSessionId.value))

  clearLocalValues()

  // Mark this new id as the live (editable) session
  currentSessionId.value = activeSessionId.value
}


const loadSession = async (sessionId) => {
  // Save the session we’re leaving only if it was live/editable
  if (!isReadOnly.value && messages.value.length) {
    const justSavedId = activeSessionId.value
    const justSavedTitle = messages.value[0]?.content.trim()
      ? messages.value[0].content.trim()
      : autoTitleFromMessages(messages.value)
    const justSavedMessages = [...messages.value]

    try {
      await saveSession(justSavedId, justSavedTitle, justSavedMessages)

      try {
        const list = await fetchSessions()
        chatSessions.value = list.map(s => ({ 
          id: s.id, 
          title: s.title, 
          updated_at: typeof s.updated_at === 'string'
            ? (Date.parse(s.updated_at) / 1000) || 0
            : Number(s.updated_at) || 0, 
          messages: [] 
        }))
      } catch {
        await upsertLocalSessionList(justSavedId, justSavedTitle, justSavedMessages)
      }
    } catch (e) {
      console.warn('Failed to save previous session:', e?.response?.data || e.message)
      // still try to reflect it locally to avoid “losing” it from the UI
      await upsertLocalSessionList(justSavedId, justSavedTitle, justSavedMessages)
    }
  }

  clearLocalValues()

  // Switch IDs and reset server-side chat state to match the target session
  activeSessionId.value = sessionId
  currentSessionId.value = null
  await resetSession(String(activeSessionId.value))

  // Fetch full session from the server
  isLoadingSession.value = true
  try {
    const data = await fetchSession(sessionId)
    // Force reactivity for ChatArea
    messages.value = []
    await nextTick()
    messages.value = data.messages.map(m => normalizeMessage({ ...m })) // deep-ish clone
  } catch (e) {
    console.error('Failed to fetch session:', e?.response?.data || e.message)
    isLoadingSession.value = false
    return
  }
  isLoadingSession.value = false

  // Seed Redis LLM history so /api/chat continues this thread seamlessly
  try {
    await seedHistory(sessionId)
  } catch (e) {
    console.warn('Failed to seed LLM history:', e?.response?.data || e.message)
  }
}

const handleDeleteSession = async (sessionId) => {
  // Basic confirm to avoid accidental deletes; remove if you don’t want it
  if (!window.confirm('Are you sure you wish to delete this session? This action is permanent and cannot be undone!')) return

  try {
    await deleteSessionApi(sessionId)

    // Drop from local list
    chatSessions.value = chatSessions.value.filter(s => s.id !== sessionId)

    // If you deleted the currently open session
    if (activeSessionId.value === sessionId) {
      // Clear UI state and start a brand-new chat (do NOT try to save the deleted one)
      await startNewChat({ skipSave: true })
    }
  } catch (e) {
    console.warn('Failed to delete session:', e?.response?.data || e.message)
  }
}

const handleRenameSession = async ({ id, title }) => {
// Rename without changing order (touch=false)
  try {
    await renameSession(id, title, false) // keep the same updated_at (no bump)

    // Update local list title (no order change)
    const idx = chatSessions.value.findIndex(s => s.id === id)
    if (idx !== -1) {
      chatSessions.value[idx] = { ...chatSessions.value[idx], title }
    }

    // If the active session is live (editable) and matches, we can optionally
    // also update the first message preview logic later—but title is independent.
  } catch (e) {
    console.warn('Failed to rename session:', e?.response?.data || e.message)
  }
}


const handleGeoJsonCreated = (geoJson) => {
  // Only parse if it's a string
  if (typeof geoJson === 'string') {
    try {
      geoJsonData.value = JSON.parse(geoJson)
      globalArea.value = JSON.parse(geoJson)
    } catch (e) {
      console.error("Failed to parse geojson string:", e)
    }
  } else if (typeof geoJson === 'object') {
    geoJsonData.value = geoJson
    globalArea.value = geoJson
  } else {
    console.warn("Unknown geojson format:", geoJson)
  }
}


function upsertDataset(datasets, newData) {
  if (!newData || !Array.isArray(newData.years) || !Array.isArray(newData.scores) || !newData.layerTitle ) {
    console.warn("Invalid graph data received:", newData);
    return datasets
  }
  const i = datasets.findIndex(d => d.layerName === newData.layerTitle)
  if (i !== -1) {
    datasets[i] = { layerName: newData.layerTitle, years: newData.years, scores: newData.scores }
  } else {
    datasets.push({
      layerName: newData.layerTitle,
      years: newData.years,
      scores: newData.scores
    })
  }
  return datasets
}

const handleGraphUpdate = ({idx, key, data}) => {
  // Find message
  const msg = messages.value[idx]
  if (!msg) return

  // ensure the panel object exists and has a .data array
  if (!msg[key] || !Array.isArray(msg[key].data)) {
    msg[key] = { ...(msg[key] || {}), data: [] }
  }

  const ds = msg[key].data.slice()
  msg[key].data = upsertDataset(ds, data)
}

const handleDateChange = ({ idx, key, date }) => {
  const msg = messages.value[idx]
  if (!msg) return

  if (!msg[key] || typeof msg[key] !== 'object') {
    msg[key] = { data: [] }
  }
  msg[key].selectedDate = date ?? null
}

const updateAvailableDates = ({ idx, key, dates }) => {
  const msg = messages.value[idx]
  if (!msg) return

  if (!msg[key] || typeof msg[key] !== 'object') {
    msg[key] = { data: [] }
  }
  msg[key].availableDates = dates || []
  msg[key].selectedDate = (dates && dates[0]) || null
}

const setWmsTrigger = ({ idx, key, value }) => {
  const msg = messages.value[idx]
  if (!msg) return

  if (!msg[key] || typeof msg[key] !== 'object') {
    msg[key] = { data: [] }
  }
  msg[key].triggerWmsClick = !!value
}


const handleProfitGraphUpdate = handleGraphUpdate
const updateProfitAvailableDates = updateAvailableDates
const handleProfitDateChange = handleDateChange
const setProfitWmsTrigger = setWmsTrigger


watch(
  messages, (newMessages) => {
    if (isLoadingSession.value) return
    if (isReadOnly.value) return
    if (!newMessages.length) return

    // Save to server (debounced)
    debouncedSave(
      activeSessionId.value,
      newMessages[0]?.content || 'Untitled Chat',
      newMessages
    )

    // Keep local sidebar state in sync (optional)
    const idx = chatSessions.value.find(s => s.id === activeSessionId.value)
    const ts = Date.now() / 1000
    const ttl = newMessages[0]?.content || (chatSessions.value[idx]?.title ?? 'Untitled Chat')

    if (idx !== -1) {
      chatSessions.value[idx] = {
        ...chatSessions.value[idx],
        title: ttl,
        updated_at: ts   // seconds epoch, good enough for sorting
      }
    } else {
      // if this session isn't in the list yet, add it
      chatSessions.value.unshift({
        id: activeSessionId.value,
        title: ttl,
        updated_at: ts,
        messages: []
      })
    }
  },
  { deep: true }
)
</script>

<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css');

body {
  background-color: white;
}
.dark body {
  background-color: #111827;
  color: white;
}
a {
  color: inherit;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
.slide-enter-active, .slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from, .slide-leave-to {
  transform: translateX(-100%);
}
button {
  border: none;
  background: transparent;
  cursor: pointer;
}
</style>
