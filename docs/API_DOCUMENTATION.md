# 📚 Documentación API - Pablo's Pizza

Esta documentación describe todos los endpoints disponibles en la API de Pablo's Pizza.

## 🌐 URL Base
```
Desarrollo: http://localhost:8000/api
Producción: https://pablos-pizza-api.com/api
```

## 🔐 Autenticación

La API usa Firebase Authentication con tokens JWT.

### Obtener Token
```javascript
// En el frontend
const token = await user.getIdToken();

// Usar en headers
headers: {
  'Authorization': `Bearer ${token}`
}
```

### Endpoints Públicos vs Protegidos
- 🌍 **Públicos:** No requieren autenticación
- 🔒 **Protegidos:** Requieren token de administrador

---

## 📅 Agendamientos (Bookings)

### 🌍 POST /bookings/
Crear nuevo agendamiento (público)

**Request Body:**
```json
{
  "client_name": "María García",
  "client_email": "maria@email.com",
  "client_phone": "+521234567890",
  "service_type": "workshop", // "workshop" | "pizza_party"
  "event_type": "birthday", // "birthday" | "corporate" | "school" | "private"
  "event_date": "2024-12-15T00:00:00Z",
  "event_time": "15:00",
  "duration_hours": 2,
  "participants": 10,
  "location": "Casa de María, Calle 123, Ciudad",
  "special_requests": "Sin gluten para 2 niños"
}
```

**Response:**
```json
{
  "id": "abc123",
  "client_name": "María García",
  "client_email": "maria@email.com",
  "client_phone": "+521234567890",
  "service_type": "workshop",
  "event_type": "birthday",
  "event_date": "2024-12-15T00:00:00Z",
  "event_time": "15:00",
  "duration_hours": 2,
  "participants": 10,
  "location": "Casa de María, Calle 123, Ciudad",
  "special_requests": "Sin gluten para 2 niños",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_price": 250.00
}
```

### 🔒 GET /bookings/
Obtener todos los agendamientos

**Query Parameters:**
- `status_filter`: `pending` | `confirmed` | `completed` | `cancelled`
- `limit`: Número máximo de resultados (default: 100)

### 🔒 GET /bookings/{booking_id}
Obtener agendamiento específico

### 🔒 PUT /bookings/{booking_id}
Actualizar agendamiento

**Request Body:**
```json
{
  "status": "confirmed",
  "event_time": "16:00",
  "participants": 12
}
```

### 🔒 DELETE /bookings/{booking_id}
Cancelar agendamiento

### 🔒 GET /bookings/calendar/{year}/{month}
Obtener eventos del calendario

**Response:**
```json
[
  {
    "id": "abc123",
    "title": "workshop - María García",
    "date": "2024-12-15",
    "time": "15:00",
    "participants": 10,
    "location": "Casa de María",
    "status": "confirmed"
  }
]
```

---

## 🎉 Eventos (Events)

### 🔒 POST /events/
Crear registro de evento realizado

**Request Body:**
```json
{
  "booking_id": "abc123",
  "actual_participants": 12,
  "start_time": "2024-12-15T15:00:00Z",
  "end_time": "2024-12-15T17:00:00Z",
  "notes": "Evento muy exitoso, niños muy participativos",
  "photos": ["url1.jpg", "url2.jpg"],
  "financials": {
    "income": 300.00,
    "expenses": [
      {"description": "Ingredientes", "amount": 80.00},
      {"description": "Transporte", "amount": 30.00}
    ],
    "total_expenses": 110.00,
    "profit": 190.00
  }
}
```

### 🔒 GET /events/
Obtener todos los eventos realizados

### 🔒 GET /events/{event_id}
Obtener evento específico

### 🔒 PUT /events/{event_id}/financials
Actualizar información financiera

### 🔒 POST /events/{event_id}/request-review
Enviar solicitud de reseña por WhatsApp

---

## 📸 Galería (Gallery)

### 🔒 POST /gallery/upload
Subir imagen a la galería

**Request:** Multipart form data
```
file: [archivo de imagen]
event_id: "abc123" (opcional)
title: "Taller de Pizza Cumpleaños María"
description: "Los niños disfrutaron mucho haciendo sus pizzas"
is_featured: false
```

### 🌍 GET /gallery/
Obtener imágenes de la galería

**Query Parameters:**
- `event_id`: Filtrar por evento
- `featured_only`: Solo imágenes destacadas
- `limit`: Número máximo (default: 50)

### 🌍 GET /gallery/featured/homepage
Obtener imágenes destacadas para la página principal

### 🔒 PUT /gallery/{image_id}
Actualizar metadatos de imagen

### 🔒 DELETE /gallery/{image_id}
Eliminar imagen

---

## ⭐ Reseñas (Reviews)

### 🌍 POST /reviews/
Crear nueva reseña (público)

**Request Body:**
```json
{
  "client_name": "María García",
  "client_email": "maria@email.com",
  "event_id": "abc123",
  "rating": 5,
  "comment": "¡Experiencia increíble! Los niños se divirtieron mucho y aprendieron. Pablo y su equipo son geniales. 100% recomendado."
}
```

### 🌍 GET /reviews/
Obtener reseñas

**Query Parameters:**
- `approved_only`: Solo aprobadas (default: true)
- `limit`: Número máximo (default: 50)

### 🌍 GET /reviews/stats
Estadísticas de reseñas

**Response:**
```json
{
  "total_reviews": 45,
  "average_rating": 4.8,
  "rating_distribution": {
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 12,
    "5": 30
  }
}
```

### 🌍 GET /reviews/featured/top
Reseñas destacadas para homepage

### 🔒 PUT /reviews/{review_id}/approve
Aprobar reseña

### 🔒 DELETE /reviews/{review_id}
Eliminar reseña

---

## 📦 Inventario (Inventory)

### 🔒 POST /inventory/
Crear item de inventario

**Request Body:**
```json
{
  "name": "Harina 00",
  "category": "ingredientes",
  "current_stock": 25,
  "min_stock": 5,
  "unit": "kg",
  "cost_per_unit": 2.50
}
```

### 🔒 GET /inventory/
Obtener inventario

**Query Parameters:**
- `category`: Filtrar por categoría
- `needs_restock`: Solo items que necesitan restock

### 🔒 PUT /inventory/{item_id}/stock
Actualizar stock

**Request Body:**
```json
{
  "new_stock": 10,
  "operation": "set" // "set" | "add" | "subtract"
}
```

### 🔒 GET /inventory/categories
Obtener categorías disponibles

### 🔒 GET /inventory/alerts
Items que necesitan restock

---

## 📊 Reportes (Reports)

### 🔒 GET /reports/monthly/{year}/{month}
Reporte mensual

**Response:**
```json
{
  "month": 12,
  "year": 2024,
  "total_events": 15,
  "total_income": 4500.00,
  "total_expenses": 1800.00,
  "total_profit": 2700.00,
  "avg_participants": 12.3,
  "most_popular_service": "workshop",
  "client_retention_rate": 35.5
}
```

### 🔒 GET /reports/annual/{year}
Resumen anual

### 🔒 GET /reports/dashboard
Estadísticas para dashboard

**Response:**
```json
{
  "today": {
    "new_bookings": 3,
    "date": "2024-01-15"
  },
  "current_month": {
    "month_name": "Enero",
    "events": 12,
    "income": 3600.00,
    "profit": 2400.00
  },
  "upcoming_events": 8,
  "alerts": {
    "low_stock_items": 3,
    "pending_reviews": 5
  }
}
```

### 🔒 GET /reports/export/monthly/{year}/{month}
Exportar reporte mensual

**Query Parameters:**
- `format`: `excel` (default)

### 🔒 GET /reports/clients/top
Clientes más frecuentes

---

## 📢 Notificaciones (Notifications)

### 🔒 POST /notifications/send
Enviar notificación manual

**Request Body:**
```json
{
  "recipient_phone": "+521234567890",
  "message": "¡Hola! Te confirmamos tu evento para mañana a las 3 PM. ¡Nos vemos! 🍕",
  "notification_type": "manual"
}
```

### 🔒 GET /notifications/
Historial de notificaciones

**Query Parameters:**
- `status_filter`: `sent` | `failed` | `pending`
- `days_back`: Días hacia atrás (default: 7)

### 🔒 GET /notifications/stats
Estadísticas de notificaciones

### 🔒 POST /notifications/test
Enviar notificación de prueba

### 🔒 POST /notifications/reminders/send-daily
Enviar recordatorios diarios automáticos

### 🔒 POST /notifications/bulk-send
Enviar notificación masiva

**Request Body:**
```json
{
  "message": "¡Oferta especial! 20% de descuento en talleres de pizza este mes. ¡Reserva ya! 🍕",
  "notification_type": "promotion",
  "recipient_filter": "recent_clients" // "all" | "recent_clients" | "active_bookings"
}
```

---

## 💬 Chat (Chat)

### 🌍 POST /chat/rooms
Crear sala de chat (público)

**Request Body:**
```json
{
  "client_name": "María García",
  "client_email": "maria@email.com"
}
```

### 🔒 GET /chat/rooms
Obtener salas de chat (admin)

### 🌍 GET /chat/rooms/{room_id}/messages
Obtener mensajes de una sala

### 🌍 POST /chat/rooms/{room_id}/messages
Enviar mensaje

**Request Body:**
```json
{
  "message": "Hola, quisiera información sobre talleres para 15 niños",
  "sender_name": "María García",
  "is_admin": false
}
```

### 🔒 PUT /chat/rooms/{room_id}/close
Cerrar sala de chat

### 🌍 GET /chat/rooms/{room_id}/status
Estado de la sala

---

## 🔗 WebSocket Endpoints

### Chat Cliente
```
ws://localhost:8000/api/chat/ws/{room_id}
```

### Chat Admin
```
ws://localhost:8000/api/chat/ws/admin
```

**Eventos WebSocket:**
```json
// Nuevo mensaje
{
  "type": "message",
  "message": {
    "id": "msg123",
    "sender_name": "María",
    "message": "Hola!",
    "timestamp": "2024-01-15T10:30:00Z",
    "is_admin": false
  }
}

// Nueva sala (solo admin)
{
  "type": "new_room",
  "room": {
    "id": "room123",
    "client_name": "María García",
    "client_email": "maria@email.com"
  }
}

// Sala cerrada
{
  "type": "room_closed",
  "message": "El chat ha sido cerrado por un administrador"
}
```

---

## 🚨 Códigos de Error

### Errores HTTP Estándar

**400 Bad Request**
```json
{
  "detail": "Datos de entrada inválidos"
}
```

**401 Unauthorized**
```json
{
  "detail": "Token inválido o expirado"
}
```

**404 Not Found**
```json
{
  "detail": "Recurso no encontrado"
}
```

**422 Validation Error**
```json
{
  "detail": [
    {
      "loc": ["body", "client_email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error**
```json
{
  "detail": "Error interno del servidor"
}
```

---

## 📝 Ejemplos de Uso

### Flujo Completo de Agendamiento

```javascript
// 1. Cliente crea agendamiento
const booking = await fetch('/api/bookings/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_name: 'María García',
    client_email: 'maria@email.com',
    client_phone: '+521234567890',
    service_type: 'workshop',
    event_type: 'birthday',
    event_date: '2024-12-15T00:00:00Z',
    event_time: '15:00',
    duration_hours: 2,
    participants: 10,
    location: 'Casa de María',
    special_requests: 'Sin gluten para 2 niños'
  })
});

// 2. Admin confirma agendamiento
await fetch(`/api/bookings/${booking.id}`, {
  method: 'PUT',
  headers: { 
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json' 
  },
  body: JSON.stringify({ status: 'confirmed' })
});

// 3. Después del evento, registrar como completado
await fetch('/api/events/', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json' 
  },
  body: JSON.stringify({
    booking_id: booking.id,
    actual_participants: 12,
    start_time: '2024-12-15T15:00:00Z',
    end_time: '2024-12-15T17:00:00Z',
    financials: {
      income: 300.00,
      expenses: [
        { description: 'Ingredientes', amount: 80.00 }
      ],
      total_expenses: 80.00,
      profit: 220.00
    }
  })
});

// 4. Solicitar reseña
await fetch(`/api/events/${event.id}/request-review`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${adminToken}` }
});
```

---

## 🔧 Configuración de Rate Limiting

La API incluye límites de velocidad para prevenir abuso:

- **Endpoints públicos:** 100 requests/hora por IP
- **Endpoints de admin:** 1000 requests/hora por usuario
- **Chat WebSocket:** 50 mensajes/minuto por sala

---

## 📋 Documentación Interactiva

Cuando el servidor esté corriendo, visita:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Estas interfaces permiten probar los endpoints directamente desde el navegador.

---

¡Esta documentación está viva! Se actualiza automáticamente con los cambios en el código. 🚀