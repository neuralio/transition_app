import { ref } from 'vue'

export default function useSessions(api) {
  const saving = ref(false)

  function debounce(fn, wait = 800) {
    let t
    return (...args) => {
      clearTimeout(t)
      t = setTimeout(() => fn(...args), wait)
    }
  }

  async function fetchSessions() {
    const { data } = await api.get('/api/sessions')
    // [{ id, title, updated_at, message_count }]
    return data
  }

  async function fetchSession(sessionId) {
    const { data } = await api.get(`/api/sessions/${sessionId}`)
    return data // { id,title,messages,created_at,updated_at }
  }

  async function saveSession(sessionId, title, messages) {
    if (!sessionId || !Array.isArray(messages)) return
    saving.value = true
    try {
      await api.post('/api/sessions', {
        session_id: sessionId,
        title: title || 'Untitled Chat',
        messages
      })
    } finally {
      saving.value = false
    }
  }

  const debouncedSave = debounce(saveSession, 800)

  async function renameSession(sessionId, title, touch = false) {
    await api.patch(`/api/sessions/${sessionId}/title`, { title, touch })
  }

  async function seedHistory(sessionId) {
    await api.post(`/api/sessions/${sessionId}/seed`)
  }

  async function deleteSession(sessionId) {
    await api.delete(`/api/sessions/${sessionId}`)
  }

  return {
    saving,
    fetchSessions,
    fetchSession,
    saveSession,
    debouncedSave,
    renameSession,
    seedHistory,
    deleteSession
  }
}
