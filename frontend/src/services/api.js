import axios from 'axios'
import toast from 'react-hot-toast'


// API Configuration - simplified for production
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const BASE_URL = isDevelopment
  ? 'http://localhost:8000/api'  // Development - Flask runs on port 8000
  : 'https://main-446811667554.us-central1.run.app/api'  // Production Cloud Run


// Create axios instance
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})


// Clear old mock inventory data on load
if (localStorage.getItem('inventory')) {
  localStorage.removeItem('inventory')
}

// Mock data storage in localStorage for demo
const getMockData = (key) => {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '[]')

    // Initialize default data if empty
    if (data.length === 0) {
      switch (key) {
        case 'inventory':
          // No more mock data initialization for inventory - using real API
          return []
        case 'events':
          // Limpiar eventos existentes - empezar desde cero
          setMockData('events', [])
          return []
        case 'gallery':
          // Limpiar galería existente - empezar desde cero
          setMockData('gallery', [])
          return []
      }
    }

    return data
  } catch {
    return []
  }
}

const setMockData = (key, data) => {
  localStorage.setItem(key, JSON.stringify(data))
}

// Mock API responses
const mockAPI = {
  bookings: {
    create: async (data) => {
      const bookings = getMockData('bookings')
      const newBooking = {
        ...data,
        id: Date.now(),
        created_at: new Date().toISOString(),
        status: 'pending'
      }
      bookings.push(newBooking)
      setMockData('bookings', bookings)
      return { data: newBooking }
    },
    getAll: async () => {
      const bookings = getMockData('bookings')
      return { data: bookings }
    },
    update: async (id, data) => {
      const bookings = getMockData('bookings')
      const index = bookings.findIndex(b => b.id === parseInt(id))
      if (index !== -1) {
        const oldStatus = bookings[index].status
        bookings[index] = { ...bookings[index], ...data }
        setMockData('bookings', bookings)

        // Si el evento se confirma, simular envío de notificaciones
        if (oldStatus !== 'confirmed' && data.status === 'confirmed') {
          // Enviar notificaciones en producción
        }
      }
      return { data: bookings[index] }
    },
    checkAvailability: async (selectedDate, selectedTime) => {
      const bookings = getMockData('bookings')
      const conflicts = []
      const availableSlots = []

      if (!selectedDate) {
        return { data: { conflicts: [], availableSlots: [] } }
      }

      // Generar slots de tiempo disponibles (9:00 AM a 8:00 PM)
      const timeSlots = []
      for (let hour = 9; hour <= 20; hour++) {
        timeSlots.push(`${hour.toString().padStart(2, '0')}:00`)
      }

      // Verificar conflictos con eventos existentes del mismo día
      const dayBookings = bookings.filter(booking => {
        return booking.event_date === selectedDate &&
               ['pending', 'confirmed', 'completed'].includes(booking.status)
      })

      dayBookings.forEach(booking => {
        if (booking.event_time) {
          const eventHour = parseInt(booking.event_time.split(':')[0])
          // Bloquear 6 horas: 4 del evento + 2 de traslado
          for (let i = eventHour - 6; i <= eventHour + 6; i++) {
            const blockedTime = `${i.toString().padStart(2, '0')}:00`
            if (timeSlots.includes(blockedTime)) {
              const index = timeSlots.indexOf(blockedTime)
              if (index > -1) {
                timeSlots.splice(index, 1)
              }
            }
          }
        }
      })

      // Si se proporcionó una hora específica, verificar si está disponible
      if (selectedTime) {
        const selectedHour = parseInt(selectedTime.split(':')[0])
        const isConflict = dayBookings.some(booking => {
          if (!booking.event_time) return false
          const bookingHour = parseInt(booking.event_time.split(':')[0])
          // Verificar si está dentro del rango de 6 horas
          return Math.abs(selectedHour - bookingHour) < 6
        })

        if (isConflict) {
          conflicts.push({
            time: selectedTime,
            reason: 'Conflicto con evento existente (requiere 6 horas de separación)'
          })
        }
      }

      return {
        data: {
          conflicts,
          availableSlots: timeSlots,
          canSchedule: conflicts.length === 0
        }
      }
    },
    cancel: async (id) => {
      const bookings = getMockData('bookings')
      const index = bookings.findIndex(b => b.id === parseInt(id))
      if (index !== -1) {
        bookings.splice(index, 1)
        setMockData('bookings', bookings)
        return { data: { message: 'Agendamiento eliminado' } }
      } else {
        throw new Error('Agendamiento no encontrado')
      }
    }
  },
  // inventory: Removed - now using real API
  events: {
    create: async (data) => {
      const events = getMockData('events')
      const newEvent = {
        ...data,
        id: Date.now(),
        created_at: new Date().toISOString()
      }
      events.push(newEvent)
      setMockData('events', events)
      return { data: newEvent }
    },
    getAll: async () => {
      const events = getMockData('events')
      return { data: events }
    },
    updateFinancials: async (id, data) => {
      const events = getMockData('events')
      const index = events.findIndex(e => e.id === parseInt(id))
      if (index !== -1) {
        events[index] = { ...events[index], ...data }
        setMockData('events', events)
      }
      return { data: events[index] }
    }
  },
  reviews: {
    create: async (data) => {
      const reviews = getMockData('reviews')
      const newReview = {
        ...data,
        id: Date.now(),
        created_at: new Date().toISOString(),
        approved: false
      }
      reviews.push(newReview)
      setMockData('reviews', reviews)
      return { data: newReview }
    },
    getAll: async (params = {}) => {
      let reviews = getMockData('reviews')
      if (params.approved_only) {
        reviews = reviews.filter(r => r.approved)
      }
      if (params.limit) {
        reviews = reviews.slice(0, parseInt(params.limit))
      }
      return { data: reviews }
    }
  },
  gallery: {
    upload: async (formData) => {
      // Mock file upload - just store metadata with random pizza images
      const gallery = getMockData('gallery')

      const pizzaImages = [
        'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1520201163981-8cc95007dd2a?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1506354666786-959d6d497f1a?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1571997478779-2adcbbe9ab2f?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1548610762-7c6afe24c261?w=400&h=300&fit=crop&auto=format',
        'https://images.unsplash.com/photo-1579952363873-27d3bfad9c0d?w=400&h=300&fit=crop&auto=format'
      ]

      const randomImage = pizzaImages[Math.floor(Math.random() * pizzaImages.length)]

      const newImage = {
        id: Date.now() + Math.random(),
        title: formData.get('title'),
        description: formData.get('description'),
        event_id: formData.get('event_id'),
        category: formData.get('category'),
        url: randomImage,
        created_at: new Date().toISOString()
      }
      gallery.push(newImage)
      setMockData('gallery', gallery)
      return { data: newImage }
    },
    getByEvent: async (eventId) => {
      const gallery = getMockData('gallery')
      const eventImages = gallery.filter(img => img.event_id == eventId)
      return { data: eventImages }
    }
  }
}

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

// API methods for different entities (using mock data for now)
export const bookingsAPI = {
  create: async (data) => {
    const response = await api.post('/bookings/', data)
    return response
  },
  getAll: (params = {}) => api.get('/bookings/', { params }),
  getById: (id) => api.get(`/bookings/${id}`),
  update: (id, data) => api.put(`/bookings/${id}`, data),
  delete: (id) => api.delete(`/bookings/${id}`),
  cancel: (id) => api.delete(`/bookings/${id}`),
  getCalendarEvents: (year, month) => api.get(`/bookings/calendar/${year}/${month}`),
  // Aún no existe endpoint real para disponibilidad; mantener mock temporalmente
  checkAvailability: (selectedDate, selectedTime) => mockAPI.bookings.checkAvailability(selectedDate, selectedTime),

  // Payments
  addPayment: (bookingId, data) => api.post(`/bookings/${bookingId}/payments`, data),
  updatePayment: (bookingId, paymentId, data) => api.put(`/bookings/${bookingId}/payments/${paymentId}`, data),
  deletePayment: (bookingId, paymentId) => api.delete(`/bookings/${bookingId}/payments/${paymentId}`),
}

export const eventsAPI = {
  create: (data) => api.post('/events/', data),
  getAll: (params = {}) => api.get('/events/', { params }),
  getById: (id) => api.get(`/events/${id}`),
  update: (id, data) => api.put(`/events/${id}`, data),
  publish: (id, isPublished, isFeatured = false) => api.put(`/events/${id}/publish`, { is_published: isPublished, is_featured: isFeatured }),
  requestReview: (id) => api.post(`/events/${id}/request-review`),
  getByBooking: (bookingId) => api.get(`/events/booking/${bookingId}`),
  generateDescription: (eventData) => api.post('/events/generate-description', eventData),
}

export const galleryAPI = {
  upload: (formData) => api.post('/gallery/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getAll: (params = {}) => api.get('/gallery/', { params }),
  getPublic: () => api.get('/gallery/public'),
  getById: (id) => api.get(`/gallery/${id}`),
  update: (id, data) => api.put(`/gallery/${id}`, data),
  delete: (id) => api.delete(`/gallery/${id}`),
  publish: (id, isPublished) => api.put(`/gallery/${id}/publish`, { is_published: isPublished }),
  getFeatured: (params = {}) => api.get('/gallery/featured/homepage', { params }),
  getByEvent: (eventId) => api.get(`/gallery/event/${eventId}`),
}

export const reviewsAPI = {
  create: (data) => mockAPI.reviews.create(data),
  getAll: (params = {}) => mockAPI.reviews.getAll(params),
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
  getById: (id) => api.get(`/inventory/${id}`),
  update: (id, data) => api.put(`/inventory/${id}`, data),
  delete: (id) => api.delete(`/inventory/${id}`),
  updateStock: (id, data) => api.put(`/inventory/${id}/stock`, data),
  getCategories: () => api.get('/inventory/categories'),
  getAlerts: () => api.get('/inventory/alerts'),
  // Weighted average cost movements
  createMovement: (data) => api.post('/inventory/movements/', data),
  getMovements: (params = {}) => api.get('/inventory-movements/', { params }),
  getMovement: (id) => api.get(`/inventory/movements/${id}`),
  revertWaste: (movementId) => api.post(`/inventory/movements/${movementId}/revert`),
  // Nutrition auto-fill
  nutritionLookup: (name) => api.get('/inventory/nutrition-lookup', { params: { name } }),
  autoFillNutrition: (id) => api.post(`/inventory/${id}/auto-nutrition`),
}

export const recipesAPI = {
  create: (data) => api.post('/recipes/', data),
  getAll: (params = {}) => api.get('/recipes/', { params }),
  getById: (id) => api.get(`/recipes/${id}`),
  update: (id, data) => api.put(`/recipes/${id}`, data),
  delete: (id) => api.delete(`/recipes/${id}`),
  calculateCost: (id) => api.post(`/recipes/${id}/calculate-cost`),
  getNutrition: (id) => api.get(`/recipes/${id}/nutrition`),
}

export const productionBatchesAPI = {
  create: (data) => api.post('/production-batches/', data),
  getAll: (params = {}) => api.get('/production-batches/', { params }),
  updateStatus: (id, status) => api.put(`/production-batches/${id}/status`, { status }),
  complete: (id) => api.post(`/production-batches/${id}/complete`),
  cancel: (id) => api.delete(`/production-batches/${id}`),
  getLabel: (id) => api.get(`/production-batches/${id}/label`),
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
  getWasteSummary: (params = {}) => api.get('/reports/waste-summary', { params }),
}

export const notificationsAPI = {
  send: (data) => api.post('/notifications/send', data),
  getAll: (params = {}) => api.get('/notifications/', { params }),
  getStats: () => api.get('/notifications/stats'),
  sendTest: (phone, message) => api.post('/notifications/test', { phone, message }),
  sendDailyReminders: () => api.post('/notifications/reminders/send-daily'),
  sendBulk: (data) => api.post('/notifications/bulk-send', data),
}

// Event Supplies API
export const eventSuppliesAPI = {
  create: (data) => api.post('/event-supplies/', data),
  getByBooking: (bookingId) => api.get(`/event-supplies/booking/${bookingId}`),
  update: (suppliesId, data) => api.put(`/event-supplies/${suppliesId}`, data),
  getStatus: (bookingId) => api.get(`/event-supplies/status/${bookingId}`),
}

// Event Consumption API
export const eventConsumptionAPI = {
  create: (data) => api.post('/event-consumption/', data),
  getByEvent: (eventId) => api.get(`/event-consumption/event/${eventId}`),
}

// Contact API
export const contactAPI = {
  create: (data) => api.post('/contacts', data),
  getAll: (params = {}) => api.get('/contacts', { params }),
  update: (id, data) => api.put(`/contacts/${id}`, data),
  respond: (id, data) => api.post(`/contacts/${id}/respond`, data),
}

// Customers API
export const customersAPI = {
  create: (data) => api.post('/customers/', data),
  getAll: (params = {}) => api.get('/customers/', { params }),
  getById: (id) => api.get(`/customers/${id}`),
  update: (id, data) => api.put(`/customers/${id}`, data),
  delete: (id) => api.delete(`/customers/${id}`),
  search: (query) => api.get('/customers/search', { params: { q: query } }),
  getBookings: (id, params = {}) => api.get(`/customers/${id}/bookings`, { params })
}

// Expenses API
export const expensesAPI = {
  // Fixed expenses
  getFixed: () => api.get('/expenses/fixed'),
  createFixed: (data) => api.post('/expenses/fixed', data),
  updateFixed: (id, data) => api.put(`/expenses/fixed/${id}`, data),
  deleteFixed: (id) => api.delete(`/expenses/fixed/${id}`),

  // Variable expenses
  getVariable: (params = {}) => api.get('/expenses/variable', { params }),
  createVariable: (data) => api.post('/expenses/variable', data),
  updateVariable: (id, data) => api.put(`/expenses/variable/${id}`, data),
  deleteVariable: (id) => api.delete(`/expenses/variable/${id}`),

  // Taxes
  getTax: (params = {}) => api.get('/expenses/tax', { params }),
  saveTax: (data) => api.post('/expenses/tax', data),
}

// Vacuum Sales API (B2B Pizza Sales)
export const vacuumSalesAPI = {
  create: (data) => api.post('/vacuum-sales/', data),
  getAll: (params = {}) => api.get('/vacuum-sales/', { params }),
  getById: (id) => api.get(`/vacuum-sales/${id}`),
  update: (id, data) => api.put(`/vacuum-sales/${id}`, data),
  delete: (id) => api.delete(`/vacuum-sales/${id}`),
  getSummary: (year, month) => api.get('/vacuum-sales/summary', { params: { year, month } }),
  // Payments
  addPayment: (saleId, data) => api.post(`/vacuum-sales/${saleId}/payments`, data),
  updatePayment: (saleId, paymentId, data) => api.put(`/vacuum-sales/${saleId}/payments/${paymentId}`, data),
  deletePayment: (saleId, paymentId) => api.delete(`/vacuum-sales/${saleId}/payments/${paymentId}`),
}

export const paymentsAPI = {
  createPreference: (data) => api.post('/payments/create-preference', data),
  getStatus: (bookingId) => api.get(`/payments/status/${bookingId}`),
}

export default api