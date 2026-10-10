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
