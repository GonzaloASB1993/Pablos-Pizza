import axios from 'axios'
import toast from 'react-hot-toast'

console.log('🎯 API.JS LOADED - Version 2.0')

// API Configuration - simplified for production
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const BASE_URL = isDevelopment
  ? 'http://localhost:8000/api'  // Development
  : 'https://main-4kqeqojbsq-uc.a.run.app/api'  // Production

console.log('🔧 API Configuration:', {
  hostname: window.location.hostname,
  isDevelopment,
  BASE_URL
})

// Create axios instance
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request logging
api.interceptors.request.use(
  (config) => {
    console.log('🚀 API Request:', {
      method: config.method.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      data: config.data
    })
    return config
  },
  (error) => {
    console.error('❌ Request Error:', error)
    return Promise.reject(error)
  }
)

// Mock data storage in localStorage for demo
const getMockData = (key) => {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '[]')

    // Initialize default data if empty
    if (data.length === 0) {
      switch (key) {
        case 'inventory':
          const defaultInventory = [
            {
              id: 1,
              name: 'Harina de Trigo',
              category: 'ingredients',
              current_stock: 25,
              min_stock: 10,
              max_stock: 50,
              unit: 'kg',
              supplier: 'Molinos del Norte',
              cost_per_unit: 1200,
              notes: 'Harina tipo 000 para pizzas',
              created_at: new Date().toISOString()
            },
            {
              id: 2,
              name: 'Queso Mozzarella',
              category: 'ingredients',
              current_stock: 5,
              min_stock: 8,
              max_stock: 20,
              unit: 'kg',
              supplier: 'Lácteos Premium',
              cost_per_unit: 8500,
              notes: 'Mantener refrigerado',
              created_at: new Date().toISOString()
            },
            {
              id: 3,
              name: 'Salsa de Tomate',
              category: 'ingredients',
              current_stock: 15,
              min_stock: 5,
              max_stock: 30,
              unit: 'litros',
              supplier: 'Conservas del Sur',
              cost_per_unit: 2500,
              notes: 'Salsa especial para pizzas',
              created_at: new Date().toISOString()
            }
          ]
          setMockData('inventory', defaultInventory)
          return defaultInventory
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
          console.log('📧 Enviando email de confirmación a:', bookings[index].client_email)
          console.log('📱 Enviando WhatsApp de confirmación a:', bookings[index].client_phone)

          // Simular delay de envío
          setTimeout(() => {
            console.log('✅ Notificaciones enviadas exitosamente')
          }, 1000)
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
  inventory: {
    getAll: async () => {
      const inventory = getMockData('inventory')
      return { data: inventory }
    },
    create: async (data) => {
      const inventory = getMockData('inventory')
      const newItem = {
        ...data,
        id: Date.now(),
        created_at: new Date().toISOString()
      }
      inventory.push(newItem)
      setMockData('inventory', inventory)
      return { data: newItem }
    },
    update: async (id, data) => {
      const inventory = getMockData('inventory')
      const index = inventory.findIndex(item => item.id === parseInt(id))
      if (index !== -1) {
        inventory[index] = { ...inventory[index], ...data }
        setMockData('inventory', inventory)
      }
      return { data: inventory[index] }
    },
    delete: async (id) => {
      const inventory = getMockData('inventory')
      const index = inventory.findIndex(item => item.id === parseInt(id))
      if (index !== -1) {
        inventory.splice(index, 1)
        setMockData('inventory', inventory)
        return { data: { message: 'Producto eliminado' } }
      } else {
        throw new Error('Producto no encontrado')
      }
    }
  },
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
    console.log('✅ API Response:', {
      status: response.status,
      url: response.config.url,
      data: response.data
    })
    return response
  },
  (error) => {
    console.error('❌ API Error Details:', {
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      url: error.config?.url,
      fullURL: `${error.config?.baseURL}${error.config?.url}`,
      responseData: error.response?.data,
      responseText: typeof error.response?.data === 'string' ? error.response.data.substring(0, 200) : 'Not string'
    })
    
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
  // Conectar a backend real con debugging extra
  create: async (data) => {
    const url = '/bookings/'
    const fullUrl = `${BASE_URL}${url}`
    
    console.log('🎯 BOOKING CREATE DEBUG:', {
      BASE_URL,
      url,
      fullUrl,
      data
    })
    
    try {
      const response = await api.post(url, data)
      console.log('✅ BOOKING CREATE SUCCESS:', response.data)
      return response
    } catch (error) {
      console.error('❌ BOOKING CREATE ERROR:', {
        message: error.message,
        response: error.response,
        config: error.config
      })
      throw error
    }
  },
  getAll: (params = {}) => api.get('/bookings/', { params }),
  getById: (id) => api.get(`/bookings/${id}`),
  update: (id, data) => api.put(`/bookings/${id}`, data),
  cancel: (id) => api.delete(`/bookings/${id}`),
  getCalendarEvents: (year, month) => api.get(`/bookings/calendar/${year}/${month}`),
  // Aún no existe endpoint real para disponibilidad; mantener mock temporalmente
  checkAvailability: (selectedDate, selectedTime) => mockAPI.bookings.checkAvailability(selectedDate, selectedTime),
}

export const eventsAPI = {
  create: (data) => api.post('/events/', data),
  getAll: (params = {}) => api.get('/events/', { params }),
  getById: (id) => api.get(`/events/${id}`),
  update: (id, data) => api.put(`/events/${id}`, data),
  requestReview: (id) => api.post(`/events/${id}/request-review`),
  getByBooking: (bookingId) => api.get(`/events/booking/${bookingId}`),
}

export const galleryAPI = {
  upload: (formData) => api.post('/gallery/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getAll: (params = {}) => api.get('/gallery/', { params }),
  getById: (id) => api.get(`/gallery/${id}`),
  update: (id, data) => api.put(`/gallery/${id}`, data),
  delete: (id) => api.delete(`/gallery/${id}`),
  publish: (id, isPublished) => api.put(`/gallery/${id}/publish`, { is_published: isPublished }),
  getFeatured: (params = {}) => api.get('/gallery/featured/homepage', { params }),
  getByEvent: (eventId) => api.get('/gallery/', { params: { event_id: eventId } }),
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
  create: (data) => mockAPI.inventory.create(data),
  getAll: (params = {}) => mockAPI.inventory.getAll(params),
  update: (id, data) => mockAPI.inventory.update(id, data),
  delete: (id) => mockAPI.inventory.delete(id),
  updateStock: (id, data) => mockAPI.inventory.update(id, data),
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