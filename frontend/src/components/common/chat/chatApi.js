import axios from 'axios'

const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
export const BASE_URL = isDevelopment
  ? 'http://localhost:8000/api'
  : 'https://main-446811667554.us-central1.run.app/api'

const NO_TOKEN = 'NO_TOKEN'

// Every call here is admin-only: it needs the Firebase ID token
const authHeaders = async (getAuthToken) => {
  const token = await getAuthToken()
  if (!token) {
    throw Object.assign(new Error('no-token'), { code: NO_TOKEN })
  }
  return { Authorization: `Bearer ${token}` }
}

export const sendChat = async (getAuthToken, messages) => {
  const { data } = await axios.post(`${BASE_URL}/ai-chat/`, { messages }, {
    headers: await authHeaders(getAuthToken),
    timeout: 180000 // matches the Function timeout (3 minutes)
  })
  return data
}

export const fetchPending = async (getAuthToken, id) => {
  const { data } = await axios.get(`${BASE_URL}/ai-chat/pending/${id}`, {
    headers: await authHeaders(getAuthToken)
  })
  return data.pending_action
}

export const confirmPending = async (getAuthToken, id, payload) => {
  const { data } = await axios.post(`${BASE_URL}/ai-chat/pending/${id}/confirm`, { payload }, {
    headers: await authHeaders(getAuthToken)
  })
  return data.pending_action
}

export const cancelPending = async (getAuthToken, id) => {
  const { data } = await axios.post(`${BASE_URL}/ai-chat/pending/${id}/cancel`, {}, {
    headers: await authHeaders(getAuthToken)
  })
  return data.pending_action
}

// Recoverable, human-readable errors (Spanish) for any of the calls above
export const describeError = (err) => {
  const status = err.response?.status
  if (err.code === NO_TOKEN || status === 401) {
    return { message: 'Tu sesión expiró. Vuelve a iniciar sesión.', retryable: false }
  }
  if (status === 403) {
    return { message: 'Tu cuenta no tiene permisos para usar el asistente.', retryable: false }
  }
  if (err.response?.data?.error) {
    const details = err.response.data.details
    const extra = Array.isArray(details) && details.length
      ? ` (${details.map((d) => `${(d.loc || []).join('.')}: ${d.msg}`).join('; ')})`
      : ''
    return { message: `${err.response.data.error}${extra}`, retryable: status >= 500 || status === 409 }
  }
  if (err.code === 'ECONNABORTED') {
    return { message: 'La consulta tardó demasiado. Intenta de nuevo.', retryable: true }
  }
  if (!navigator.onLine || err.code === 'ERR_NETWORK') {
    return { message: 'Sin conexión. Revisa tu internet e intenta de nuevo.', retryable: true }
  }
  return { message: 'Error al comunicarse con el asistente.', retryable: true }
}
