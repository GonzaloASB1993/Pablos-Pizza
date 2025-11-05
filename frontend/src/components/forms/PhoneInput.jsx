import React, { useState } from 'react'
import { TextField, InputAdornment, Typography, Box } from '@mui/material'
import { Phone, CheckCircle, Error } from '@mui/icons-material'

/**
 * PhoneInput Component - Chilean Phone Number Input with Validation
 *
 * Ensures correct format: +56 9 XXXX XXXX (9 digits after +56)
 * Stores as: +56XXXXXXXXX (no spaces)
 * Displays as: 9 1234 5678 (with spaces for readability)
 */
const PhoneInput = ({
  value,
  onChange,
  label = "Teléfono / WhatsApp",
  required = true,
  helperText = "Formato: 9 1234 5678",
  fullWidth = true,
  ...otherProps
}) => {
  const [focused, setFocused] = useState(false)

  // Extract the number part (without +56)
  const getDisplayValue = (phoneValue) => {
    if (!phoneValue) return ''

    // Remove +56 prefix if present
    let cleaned = phoneValue.replace(/^\+56/, '').replace(/\D/g, '')

    // Format for display: 9 1234 5678
    if (cleaned.length <= 1) return cleaned
    if (cleaned.length <= 5) return `${cleaned.slice(0, 1)} ${cleaned.slice(1)}`
    return `${cleaned.slice(0, 1)} ${cleaned.slice(1, 5)} ${cleaned.slice(5, 9)}`
  }

  // Check if the number is valid (exactly 9 digits, starting with 9)
  const isValid = (phoneValue) => {
    if (!phoneValue) return null // No validation status if empty
    const cleaned = phoneValue.replace(/^\+56/, '').replace(/\D/g, '')
    return cleaned.length === 9 && cleaned.startsWith('9')
  }

  const handleChange = (e) => {
    const input = e.target.value

    // Remove all non-digit characters
    const digitsOnly = input.replace(/\D/g, '')

    // Limit to 9 digits
    const limited = digitsOnly.slice(0, 9)

    // Store with +56 prefix
    const formatted = limited ? `+56${limited}` : ''

    onChange(formatted)
  }

  const displayValue = getDisplayValue(value)
  const validationStatus = isValid(value)

  return (
    <TextField
      {...otherProps}
      label={label}
      fullWidth={fullWidth}
      required={required}
      value={displayValue}
      onChange={handleChange}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      placeholder="9 1234 5678"
      inputProps={{
        inputMode: 'numeric',
        pattern: '[0-9 ]*',
      }}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Phone sx={{ fontSize: 20, color: 'text.secondary' }} />
              <Typography
                sx={{
                  fontWeight: 600,
                  color: 'text.primary',
                  minWidth: '32px'
                }}
              >
                +56
              </Typography>
            </Box>
          </InputAdornment>
        ),
        endAdornment: validationStatus !== null && (
          <InputAdornment position="end">
            {validationStatus ? (
              <CheckCircle sx={{ color: 'success.main', fontSize: 20 }} />
            ) : displayValue.length > 0 && (
              <Error sx={{ color: 'error.main', fontSize: 20 }} />
            )}
          </InputAdornment>
        ),
      }}
      helperText={
        validationStatus === false && displayValue.length > 0
          ? "Debe ser un número móvil válido (9 dígitos, comenzando con 9)"
          : helperText
      }
      error={validationStatus === false && displayValue.length > 0}
    />
  )
}

export default PhoneInput
