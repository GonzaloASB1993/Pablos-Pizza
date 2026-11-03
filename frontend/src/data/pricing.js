// Fuente única de verdad para todos los precios del sitio.
// Actualizar este archivo propaga los cambios a Home, Servicios y Agendar.

export const PIZZEROS_TIERS = [
  { range: 'Hasta 10 niños', price: 13500, unit: 'por niño', label: 'Hasta 10 niños' },
  { range: '11–14 niños',    price: 10500, unit: 'por niño', label: '11–14 niños' },
  { range: '15–19 niños',    price:  9500, unit: 'por niño', label: '15–19 niños', highlight: true },
  { range: '20+ niños',      price:  9000, unit: 'por niño', label: '20+ niños',   highlight: true },
]

export const PIZZEROS_BASE_PRICE = PIZZEROS_TIERS[0].price

export function getPizzerosPrice(participants) {
  if (participants >= 20) return PIZZEROS_TIERS[3].price
  if (participants >= 15) return PIZZEROS_TIERS[2].price
  if (participants >= 11) return PIZZEROS_TIERS[1].price
  return PIZZEROS_TIERS[0].price
}

// Descuentos del FloatingCTA — null = sin descuento activo
export const ACTIVE_PROMO = null
// Ejemplo cuando hay promo: { label: '10% dcto este mes', expiry: '2026-04-30' }

// Recargo nocturno: % sobre el subtotal de servicios (no sobre el cargo de comuna lejana).
// El servidor decide el porcentaje real al crear la reserva; esto solo lo muestra.
export const DEFAULT_RECARGO_NOCTURNO_PCT = 20

// 22:00-23:59 y 00:00-07:59 (antes de las 08:00 solo llega por el panel o Pablito)
export function isNightTime(hhmm) {
  const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(String(hhmm ?? '').trim())
  if (!match) return false
  const hour = Number(match[1])
  return hour >= 22 || hour < 8
}

// Math.round coincide con (subtotal * pct + 50) // 100 del backend
export function calcRecargoNocturno(subtotal, pct) {
  const value = Number(pct)
  if (!value || !subtotal) return 0
  return Math.round((subtotal * value) / 100)
}

const DIAS_SEMANA = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']

// "00:00" del sábado significa que el equipo llega el viernes en la noche. La fecha NO se corre:
// solo se aclara en pantalla. `ymd` es 'YYYY-MM-DD' y se parsea como fecha LOCAL
// (new Date('YYYY-MM-DD') usa UTC y en Chile mostraría el día anterior).
export function formatEventTime(time, ymd) {
  if (time !== '00:00') return time || ''
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(ymd ?? ''))
  if (!match) return '00:00 (medianoche)'
  const eventDay = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  if (Number.isNaN(eventDay.getTime())) return '00:00 (medianoche)'
  const previous = new Date(eventDay.getFullYear(), eventDay.getMonth(), eventDay.getDate() - 1)
  return `00:00 (${DIAS_SEMANA[previous.getDay()]} en la noche)`
}
