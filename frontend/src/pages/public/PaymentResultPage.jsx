import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Stack
} from '@mui/material'
import {
  CheckCircle,
  Cancel,
  Schedule,
  Home,
  WhatsApp
} from '@mui/icons-material'
import { designTokens } from '../../utils/theme'
import SEO from '../../components/common/SEO'

const WHATSAPP_NUMBER = '56989424566'

export default function PaymentResultPage({ status }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const bookingId = searchParams.get('booking_id')
  const [pollStatus, setPollStatus] = useState(status)

  // Polling para estado "pending"
  useEffect(() => {
    if (status !== 'pending' || !bookingId) return

    const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const API_BASE = isDevelopment
      ? '/api'
      : 'https://main-446811667554.us-central1.run.app/api'

    let intervalId = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/payments/status/${bookingId}`)
        if (res.ok) {
          const data = await res.json()
          if (data.status === 'approved') {
            setPollStatus('success')
            clearInterval(intervalId)
          } else if (data.status === 'rejected' || data.status === 'cancelled') {
            setPollStatus('failure')
            clearInterval(intervalId)
          }
        }
      } catch {
        // ignore polling errors
      }
    }, 5000)

    return () => clearInterval(intervalId)
  }, [status, bookingId])

  const configs = {
    success: {
      icon: <CheckCircle sx={{ fontSize: 80, color: 'success.main' }} />,
      title: '¡Pago recibido exitosamente!',
      subtitle: 'Tu reserva está confirmada',
      message: 'Hemos recibido tu abono. Te contactaremos pronto para coordinar los detalles finales de tu evento.',
      color: 'success.main',
      bgColor: 'rgba(76, 175, 80, 0.08)',
      border: 'rgba(76, 175, 80, 0.3)',
    },
    failure: {
      icon: <Cancel sx={{ fontSize: 80, color: 'error.main' }} />,
      title: 'El pago no pudo procesarse',
      subtitle: 'Tu reserva fue creada pero el abono está pendiente',
      message: 'No te preocupes, tu reserva quedó guardada. Puedes contactarnos para coordinar el pago o intentarlo nuevamente.',
      color: 'error.main',
      bgColor: 'rgba(244, 67, 54, 0.08)',
      border: 'rgba(244, 67, 54, 0.3)',
    },
    pending: {
      icon: <Schedule sx={{ fontSize: 80, color: 'warning.main' }} />,
      title: 'Tu pago está siendo procesado',
      subtitle: 'Esto puede tomar unos minutos',
      message: 'Te notificaremos cuando se confirme el pago. Tu reserva ya está guardada.',
      color: 'warning.main',
      bgColor: 'rgba(255, 152, 0, 0.08)',
      border: 'rgba(255, 152, 0, 0.3)',
    },
  }

  const cfg = configs[pollStatus] || configs.pending

  const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(
    `Hola! Tuve un problema con el pago de mi reserva${bookingId ? ` (ID: ${bookingId.substring(0, 8)})` : ''}. ¿Me pueden ayudar?`
  )}`

  return (
    <>
      <SEO noindex />
      <Box
        sx={{
          minHeight: '70vh',
          display: 'flex',
        alignItems: 'center',
        background: 'linear-gradient(180deg, #FAFAFA 0%, #F5F5F5 100%)',
        py: 6,
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={0}
          sx={{
            p: { xs: 3, md: 5 },
            borderRadius: designTokens.radius.xl || 3,
            background: cfg.bgColor,
            border: `1px solid ${cfg.border}`,
            textAlign: 'center',
          }}
        >
          <Box sx={{ mb: 3 }}>
            {pollStatus === 'pending' && status === 'pending' ? (
              <Box sx={{ position: 'relative', display: 'inline-flex', mb: 1 }}>
                {cfg.icon}
                <CircularProgress
                  size={100}
                  sx={{
                    position: 'absolute',
                    top: -10,
                    left: -10,
                    color: 'warning.main',
                    opacity: 0.4,
                  }}
                />
              </Box>
            ) : (
              cfg.icon
            )}
          </Box>

          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: cfg.color }}>
            {cfg.title}
          </Typography>

          <Typography variant="h6" sx={{ fontWeight: 500, mb: 2, color: 'text.primary' }}>
            {cfg.subtitle}
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
            {cfg.message}
          </Typography>

          {bookingId && (
            <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mb: 3 }}>
              Reserva: {bookingId.substring(0, 8).toUpperCase()}
            </Typography>
          )}

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center">
            {pollStatus === 'failure' && (
              <Button
                variant="outlined"
                size="large"
                startIcon={<WhatsApp />}
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  borderColor: '#25D366',
                  color: '#25D366',
                  '&:hover': {
                    borderColor: '#128C7E',
                    backgroundColor: 'rgba(37,211,102,0.08)',
                  },
                }}
              >
                Contactar por WhatsApp
              </Button>
            )}
            <Button
              variant="contained"
              size="large"
              startIcon={<Home />}
              onClick={() => navigate('/')}
              sx={{
                background: designTokens.colors.aurora.sunset,
                fontWeight: 600,
                '&:hover': {
                  background: `linear-gradient(135deg, ${designTokens.colors.golden[400]} 0%, #FF8A00 100%)`,
                },
              }}
            >
              Volver al inicio
            </Button>
          </Stack>
        </Paper>
      </Container>
    </Box>
    </>
  )
}
