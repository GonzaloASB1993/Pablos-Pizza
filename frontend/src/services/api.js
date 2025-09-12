import axios from 'axios'
import toast from 'react-hot-toast'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          toast.error('Sesión expirada. Por favor, inicia sesión nuevamente.')
          localStorage.removeItem('authToken')
          window.location.href = '/admin/login'
          break
        case 403:
          toast.error('No tienes permisos para realizar esta acción')
          break
        case 404:
          toast.error('Recurso no encontrado')
          break
        case 422:
          // Validation errors
          if (data.detail && Array.isArray(data.detail)) {
            data.detail.forEach(err => {
              toast.error(`${err.loc[1]}: ${err.msg}`)
            })
          } else if (data.detail) {
            toast.error(data.detail)
          }
          break
        case 500:
          toast.error('Error interno del servidor')
          break
        default:
          toast.error(data.detail || 'Error en la petición')
      }
    } else if (error.request) {
      // Network error
      toast.error('Error de conexión. Verifica tu internet.')
    } else {
      // Other error
      toast.error('Error inesperado')
    }
    
    return Promise.reject(error)
  }
)

// API methods for different entities
export const bookingsAPI = {
  create: (data) => api.post('/bookings/', data),
  getAll: (params = {}) => api.get('/bookings/', { params }),
  getById: (id) => api.get(`/bookings/${id}`),
  update: (id, data) => api.put(`/bookings/${id}`, data),
  cancel: (id) => api.delete(`/bookings/${id}`),
  getCalendarEvents: (year, month) => api.get(`/bookings/calendar/${year}/${month}`),
}

export const eventsAPI = {
  create: (data) => api.post('/events/', data),
  getAll: (params = {}) => api.get('/events/', { params }),
  getById: (id) => api.get(`/events/${id}`),
  updateFinancials: (id, data) => api.put(`/events/${id}/financials`, data),
  requestReview: (id) => api.post(`/events/${id}/request-review`),
  getByBooking: (bookingId) => api.get(`/events/booking/${bookingId}`),
}

export const galleryAPI = {
  upload: (formData) => api.post('/gallery/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getAll: (params = {}) => api.get('/gallery/', { params }),
  getById: (id) => api.get(`/gallery/${id}`),
  update: (id, data) => api.put(`/gallery/${id}`, data),
  delete: (id) => api.delete(`/gallery/${id}`),
  getFeatured: (params = {}) => api.get('/gallery/featured/homepage', { params }),
}

export const reviewsAPI = {
  create: (data) => api.post('/reviews/', data),
  getAll: (params = {}) => api.get('/reviews/', { params }),
  getById: (id) => api.get(`/reviews/${id}`),
  approve: (id) => api.put(`/reviews/${id}/approve`),
  delete: (id) => api.delete(`/reviews/${id}`),
  getStats: () => api.get('/reviews/stats'),
  getByEvent: (eventId) => api.get(`/reviews/event/${eventId}`),
  getFeatured: (params = {}) => api.get('/reviews/featured/top', { params }),
}

export const inventoryAPI = {
  create: (data) => api.post('/inventory/', data),
  getAll: (params = {}) => api.get('/inventory/', { params }),
  updateStock: (id, data) => api.put(`/inventory/${id}/stock`, data),
  getCategories: () => api.get('/inventory/categories'),
  getAlerts: () => api.get('/inventory/alerts'),
}

export const reportsAPI = {
  getMonthly: (year, month) => api.get(`/reports/monthly/${year}/${month}`),
  getAnnual: (year) => api.get(`/reports/annual/${year}`),
  getDashboard: () => api.get('/reports/dashboard'),
  exportMonthly: (year, month, format = 'excel') => 
    api.get(`/reports/export/monthly/${year}/${month}?format=${format}`, {
      responseType: 'blob'
    }),
  getTopClients: (params = {}) => api.get('/reports/clients/top', { params }),
}

export const notificationsAPI = {
  send: (data) => api.post('/notifications/send', data),
  getAll: (params = {}) => api.get('/notifications/', { params }),
  getStats: () => api.get('/notifications/stats'),
  sendTest: (phone, message) => api.post('/notifications/test', { phone, message }),
  sendDailyReminders: () => api.post('/notifications/reminders/send-daily'),
  sendBulk: (data) => api.post('/notifications/bulk-send', data),
}

export const chatAPI = {
  createRoom: (data) => api.post('/chat/rooms', data),
  getRooms: (params = {}) => api.get('/chat/rooms', { params }),
  getMessages: (roomId, params = {}) => api.get(`/chat/rooms/${roomId}/messages`, { params }),
  sendMessage: (roomId, data) => api.post(`/chat/rooms/${roomId}/messages`, data),
  closeRoom: (roomId) => api.put(`/chat/rooms/${roomId}/close`),
  getRoomStatus: (roomId) => api.get(`/chat/rooms/${roomId}/status`),
}

export default api