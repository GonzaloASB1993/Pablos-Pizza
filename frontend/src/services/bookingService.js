// Servicio para manejo de bookings/agendamientos (frontend público)
// En dev, forzamos '/api' para usar el proxy de Vite y evitar CORS. En prod, usamos VITE_API_URL si existe.
const API_BASE = import.meta.env.DEV ? '/api' : (import.meta.env.VITE_API_URL || '/api')

export const createBooking = async (bookingData) => {
  try {
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

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      // Mejorar mensaje cuando FastAPI devuelve detail como lista de errores
      if (Array.isArray(errorData.detail)) {
        const msg = errorData.detail
          .map((e) => `${Array.isArray(e.loc) ? e.loc.join('.') : ''} ${e.msg}`.trim())
          .join(' | ')
        throw new Error(msg || 'Error de validación (422)')
      }
      throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`)
    }

    const booking = await response.json()
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