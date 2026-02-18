/**
 * Utilities for formatting currency, numbers, and units in Pablo's Pizza
 */

/**
 * Format currency amount in Chilean Pesos without decimals
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted currency string (e.g., "$1.234")
 */
export const formatCurrency = (amount) => {
  if (amount == null || isNaN(amount)) return '$0'

  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount)
}

/**
 * Format stock/quantity numbers - show decimals only when necessary
 * Handles floating point precision errors by rounding to 2 decimals
 * @param {number} amount - The amount to format
 * @param {boolean} forceInteger - Force integer display
 * @returns {string} - Formatted number string
 */
export const formatStock = (amount, forceInteger = true) => {
  if (amount == null || isNaN(amount)) return '0'

  // Redondear a 2 decimales para evitar errores de precisión flotante
  let rounded = Math.round(amount * 100) / 100

  // Tratar valores muy pequeños como 0
  if (Math.abs(rounded) < 0.01) rounded = 0

  if (forceInteger || rounded % 1 === 0) {
    return Math.round(rounded).toString()
  }

  // Show up to 2 decimals for fractional amounts
  return rounded.toFixed(2).replace(/\.?0+$/, '')
}

/**
 * Safely format cost with fallback for N/A cases
 * @param {number} cost - The cost to format
 * @param {number} fallbackCost - Fallback cost if main cost is null/undefined
 * @returns {string} - Formatted cost or 'N/A'
 */
export const safeFormatCost = (cost, fallbackCost = null) => {
  if (cost != null && !isNaN(cost)) {
    return formatCurrency(cost)
  }

  if (fallbackCost != null && !isNaN(fallbackCost)) {
    return formatCurrency(fallbackCost)
  }

  return 'N/A'
}

/**
 * Format percentage values
 * @param {number} value - The percentage value (0-100)
 * @returns {string} - Formatted percentage string
 */
export const formatPercentage = (value) => {
  if (value == null || isNaN(value)) return '0%'
  return `${Number(value).toFixed(1)}%`
}

/**
 * Unit conversion utilities for recipes
 */
export const unitConversions = {
  // Weight conversions (base: grams)
  weight: {
    'g': 1,
    'kg': 1000,
    'lb': 453.592,
    'oz': 28.3495
  },

  // Volume conversions (base: milliliters)
  volume: {
    'ml': 1,
    'l': 1000,
    'cup': 240,
    'tbsp': 14.7868,
    'tsp': 4.92892
  },

  // Quantity conversions (base: units)
  quantity: {
    'unidades': 1,
    'docenas': 12,
    'pares': 2
  }
}

/**
 * Get unit category (weight, volume, quantity)
 * @param {string} unit - The unit to categorize
 * @returns {string|null} - The category or null if not found
 */
export const getUnitCategory = (unit) => {
  for (const [category, units] of Object.entries(unitConversions)) {
    if (units[unit]) {
      return category
    }
  }
  return null
}

/**
 * Convert between units of the same category
 * @param {number} amount - Amount to convert
 * @param {string} fromUnit - Source unit
 * @param {string} toUnit - Target unit
 * @returns {number|null} - Converted amount or null if conversion not possible
 */
export const convertUnits = (amount, fromUnit, toUnit) => {
  if (!amount || isNaN(amount)) return null

  const fromCategory = getUnitCategory(fromUnit)
  const toCategory = getUnitCategory(toUnit)

  if (!fromCategory || !toCategory || fromCategory !== toCategory) {
    return null // Cannot convert between different categories
  }

  const conversions = unitConversions[fromCategory]
  const baseAmount = amount * conversions[fromUnit]
  const convertedAmount = baseAmount / conversions[toUnit]

  return convertedAmount
}

/**
 * Get available units for conversion based on source unit
 * @param {string} sourceUnit - The source unit
 * @returns {string[]} - Array of compatible units for conversion
 */
export const getCompatibleUnits = (sourceUnit) => {
  const category = getUnitCategory(sourceUnit)
  if (!category) return []

  return Object.keys(unitConversions[category]).filter(unit => unit !== sourceUnit)
}

/**
 * Format unit conversion result for display
 * @param {number} amount - Original amount
 * @param {string} fromUnit - Source unit
 * @param {string} toUnit - Target unit
 * @returns {string} - Formatted conversion string
 */
export const formatUnitConversion = (amount, fromUnit, toUnit) => {
  const converted = convertUnits(amount, fromUnit, toUnit)

  if (converted === null) {
    return `No se puede convertir de ${fromUnit} a ${toUnit}`
  }

  const formattedAmount = formatStock(amount, false)
  const formattedConverted = formatStock(converted, false)

  return `${formattedAmount} ${fromUnit} = ${formattedConverted} ${toUnit}`
}

/**
 * Format date for Chilean locale
 * @param {Date|string} date - Date to format
 * @returns {string} - Formatted date string
 */
export const formatDate = (date) => {
  if (!date) return 'N/A'

  const dateObj = date instanceof Date ? date : new Date(date)

  if (isNaN(dateObj.getTime())) return 'N/A'

  return dateObj.toLocaleDateString('es-CL')
}

/**
 * Format datetime for Chilean locale
 * @param {Date|string} date - Date to format
 * @returns {string} - Formatted datetime string
 */
export const formatDateTime = (date) => {
  if (!date) return 'N/A'

  const dateObj = date instanceof Date ? date : new Date(date)

  if (isNaN(dateObj.getTime())) return 'N/A'

  return dateObj.toLocaleString('es-CL')
}