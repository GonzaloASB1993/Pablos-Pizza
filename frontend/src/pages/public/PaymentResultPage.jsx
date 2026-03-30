import React from 'react'
import { Box, Typography, Container, Button } from '@mui/material'
import { CheckCircle, Cancel, HourglassEmpty } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'

const statusConfig = {
  success: {
    icon: <CheckCircle sx={{ fontSize: 80, color: '#4caf50' }} />,
    title: '¡Pago Exitoso!',
    message: 'Tu agendamiento ha sido confirmado. Nos pondremos en contacto contigo pronto.',
    color: '#4caf50'
  },
  failure: {
    icon: <Cancel sx={{ fontSize: 80, color: '#f44336' }} />,
    title: 'Pago Fallido',
    message: 'Hubo un problema con tu pago. Por favor intenta nuevamente.',
    color: '#f44336'
  },
  pending: {
    icon: <HourglassEmpty sx={{ fontSize: 80, color: '#ff9800' }} />,
    title: 'Pago Pendiente',
    message: 'Tu pago está siendo procesado. Te notificaremos cuando se confirme.',
    color: '#ff9800'
  }
}

export default function PaymentResultPage({ status = 'pending' }) {
  const navigate = useNavigate()
  const config = statusConfig[status] || statusConfig.pending

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Box sx={{ textAlign: 'center' }}>
        {config.icon}
        <Typography variant="h4" sx={{ fontWeight: 700, mt: 2, mb: 1, color: config.color }}>
          {config.title}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          {config.message}
        </Typography>
        <Button variant="contained" onClick={() => navigate('/')}>
          Volver al inicio
        </Button>
      </Box>
    </Container>
  )
}
