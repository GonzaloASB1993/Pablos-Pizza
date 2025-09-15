// Servicio para manejo de bookings/agendamientos (frontend público)
// Configuración corregida para production
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const API_BASE = isDevelopment 
  ? '/api'  // En development usa proxy
  : 'https://main-4kqeqojbsq-uc.a.run.app/api'  // En production usa URL completa

console.log('🔧 BookingService Configuration:', {
  hostname: window.location.hostname,
  isDevelopment,
  API_BASE
})

export const createBooking = async (bookingData) => {
  console.log('🎯 BOOKING SERVICE START:', {
    data: bookingData,
    apiBase: API_BASE,
    url: `${API_BASE}/bookings/`
  })
  
  try {
    console.log('🎯 CREATE BOOKING START:', {
      API_BASE,
      fullURL: `${API_BASE}/bookings/`,
      bookingData
    })

    const mapEventType = (t) => {
      switch ((t || '').toLowerCase()) {
        case 'cumple':
        case 'cumpleaños':
        case 'birthday':
          return 'birthday'
        case 'escolar':
        case 'school':
          return 'school'
        case 'corporativo':
        case 'corporate':
          return 'corporate'
        case 'otro':
        case 'private':
        default:
          return 'private'
      }
    }

    const response = await fetch(`${API_BASE}/bookings/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client_name: bookingData.name,
        client_email: bookingData.email,
        client_phone: bookingData.phone,
        // Backend espera valores del enum ServiceType: 'workshop' | 'pizza_party'
        service_type: bookingData.service === 'pizzeros' ? 'workshop' : 'pizza_party',
        // Backend espera enum EventType: 'birthday' | 'corporate' | 'school' | 'private'
        event_type: mapEventType(bookingData.eventType),
        // event_date debe ser ISO string o fecha parseable por Pydantic
        event_date: `${bookingData.date}T${bookingData.time || '12:00'}:00`,
        event_time: bookingData.time,
        // El esquema usa 'location' (no event_location)
        location: bookingData.location,
        // duración por defecto 4 horas si no viene del formulario
        duration_hours: bookingData.durationHours || 4,
        participants: Number(bookingData.participants) || 0,
        special_requests: bookingData.specialRequests || ''
      })
    })

    console.log('🚀 FETCH RESPONSE:', {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries())
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ RESPONSE NOT OK:', {
        status: response.status,
        statusText: response.statusText,
        errorText: errorText.substring(0, 200)
      })
      
      try {
        const errorData = JSON.parse(errorText)
        // Mejorar mensaje cuando FastAPI devuelve detail como lista de errores
        if (Array.isArray(errorData.detail)) {
          const msg = errorData.detail
            .map((e) => `${Array.isArray(e.loc) ? e.loc.join('.') : ''} ${e.msg}`.trim())
            .join(' | ')
          throw new Error(msg || 'Error de validación (422)')
        }
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`)
      } catch (parseError) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }
    }

    const booking = await response.json()
    console.log('✅ BOOKING CREATED:', booking)
    return booking
  } catch (error) {
    console.error('Error creating booking:', error)
    throw error
  }
}

export const getBookings = async () => {
  try {
    const response = await fetch(`${API_BASE}/bookings/`)

    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching bookings:', error)
    throw error
  }
}

// Instrucciones para el entorno backend (no es parte del código)
// 1. Abrir terminal y navegar a la carpeta del backend:
//    cd "C:\Users\gonza\OneDrive\Escritorio\Pablos Pizza\backend"
// 2. Crear y activar el entorno virtual:
//    python -m venv venv
//    .\venv\Scripts\Activate.ps1
// 3. Instalar dependencias:
//    pip install -r requirements.txt
// 4. Correr el servidor:
//    uvicorn main:app --reload --port 8000

// Instrucciones para el entorno frontend
// 1. Abrir terminal y navegar a la carpeta del frontend:
//    cd "C:\Users\gonza\OneDrive\Escritorio\Pablos Pizza\frontend"
// 2. Correr el servidor de desarrollo:
//    npm run dev