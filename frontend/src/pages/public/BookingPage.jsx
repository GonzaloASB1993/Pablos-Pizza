import React, { useMemo, useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  Paper,
  Stack,
  Avatar,
  Stepper,
  Step,
  StepLabel,
  Chip,
  LinearProgress,
  Fade,
  useTheme,
  useMediaQuery,
  Alert,
  Zoom,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  FormGroup,
  FormLabel,
  Autocomplete,
  MenuItem
} from '@mui/material'
import SEO from '../../components/common/SEO'
import PhoneInput from '../../components/forms/PhoneInput'
import {
  ArrowBack,
  AccessTime,
  Chat,
  Restaurant,
  Speed,
  Star,
  Phone,
  WhatsApp,
  CheckCircle,
  MonetizationOn,
  Calculate,
  CalendarToday,
  Schedule,
  LocationOn,
  People,
  Email,
  EmojiEvents,
  Celebration,
  ArrowForward,
  AutoAwesome,
  TrendingUp,
  LocalPizza,
  Group,
  CreditCard,
  Lock,
  Cake,
  School,
  Business
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { designTokens } from '../../utils/theme'
import { createBooking, createPaymentPreference } from '../../services/bookingService'
import { santiagoComunas, isComunaLejana, CARGO_COMUNA_LEJANA, comunasLejanas } from '../../data/chileanRegions'
import { getPizzerosPrice, PIZZEROS_TIERS } from '../../data/pricing'

// Constantes de pricing (sincronizadas con backend)
// PIZZEROS_TIERS y PIZZEROS_BASE_PRICE vienen del import de pricing.js
const PRICING_CONSTANTS = {
  SLICES_PER_PERSON: 5,
  SLICES_PER_PIZZA: 8,
  MIN_PIZZAS: 10,
  PIZZEROS_MINIMUM: PIZZEROS_TIERS[0].price * 10, // derivado, no hardcodeado
  PIZZA_PARTY_BASE_PRICE: 11990,
  PIZZA_PARTY_DISCOUNT_THRESHOLD: 20,
  PIZZA_PARTY_DISCOUNT: 0.10,
  CARGO_COMUNA_LEJANA: CARGO_COMUNA_LEJANA
}

// Opciones de horario generadas dinámicamente
const TIME_OPTIONS = Array.from({ length: 27 }, (_, i) => {
  const hour = Math.floor(i / 2) + 8
  const minute = i % 2 === 0 ? '00' : '30'
  return `${hour.toString().padStart(2, '0')}:${minute}`
})

// Helper functions para pricing
const getPizzaPartyPrice = (pizzas) => {
  if (pizzas >= PRICING_CONSTANTS.PIZZA_PARTY_DISCOUNT_THRESHOLD) {
    return Math.round(PRICING_CONSTANTS.PIZZA_PARTY_BASE_PRICE * (1 - PRICING_CONSTANTS.PIZZA_PARTY_DISCOUNT))
  }
  return PRICING_CONSTANTS.PIZZA_PARTY_BASE_PRICE
}

// Estilos compartidos para MenuItems
const menuItemStyles = {
  '&:hover': {
    backgroundColor: '#FFF9E6',
  },
  '&.Mui-selected': {
    backgroundColor: '#FFD700',
    color: '#000000',
    fontWeight: 600,
    '&:hover': {
      backgroundColor: '#FFD700',
    },
  },
}

const menuProps = {
  PaperProps: {
    sx: {
      backgroundColor: '#FFFFFF',
      border: '2px solid #FFD700',
      borderRadius: 2,
      maxHeight: 300,
    },
  },
}

// Hero Section — alineada con ServicesPage
const HeroSection = () => {
  return (
    <Box
      sx={{
        position: 'relative',
        background: '#0d0d0d',
        color: '#FFFFFF',
        py: { xs: 6, md: 8 },
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'url("data:image/svg+xml,%3Csvg width=\'20\' height=\'20\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cdefs%3E%3Cpattern id=\'grid\' width=\'20\' height=\'20\' patternUnits=\'userSpaceOnUse\'%3E%3Cpath d=\'M 20 0 L 0 0 0 20\' fill=\'none\' stroke=\'rgba(232,182,58,0.05)\' stroke-width=\'1\'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width=\'100%25\' height=\'100%25\' fill=\'url(%23grid)\' /%3E%3C/svg%3E")',
          opacity: 0.3,
        },
      }}
    >
      <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
        <Box sx={{ textAlign: 'center', maxWidth: 680, mx: 'auto' }}>
          <Chip
            label="Respuesta en 24 horas"
            size="small"
            icon={<AccessTime sx={{ fontSize: '14px !important', color: '#0d0d0d !important' }} />}
            sx={{
              mb: 3,
              bgcolor: '#e8b63a',
              color: '#0d0d0d',
              fontWeight: 700,
              fontSize: '0.72rem',
              letterSpacing: '0.06em',
            }}
          />
          <Typography
            variant="h1"
            component="h1"
            sx={{
              fontSize: { xs: '2.4rem', md: '3.5rem' },
              fontWeight: 900,
              color: '#FFFFFF',
              mb: 2,
              lineHeight: 1.1,
            }}
          >
            Reserva tu Evento
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: 'rgba(255,255,255,0.65)',
              maxWidth: 460,
              mx: 'auto',
              fontSize: { xs: '1rem', md: '1.1rem' },
              lineHeight: 1.6,
            }}
          >
            Completá el formulario y te contactamos en menos de 24 horas para coordinar todos los detalles.
          </Typography>
        </Box>
      </Container>
    </Box>
  )
}

// Componente de pasos del formulario
const FormStepper = ({ activeStep, steps }) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))

  if (isMobile) {
    const progress = ((activeStep + 1) / steps.length) * 100
    return (
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 3,
          borderRadius: designTokens.radius.lg,
          background: '#1a1714',
          border: '1px solid rgba(232,182,58,0.2)',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#e8b63a' }}>
            Paso {activeStep + 1} de {steps.length}
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
            {steps[activeStep]}
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 6,
            borderRadius: 3,
            backgroundColor: 'rgba(232,182,58,0.15)',
            '& .MuiLinearProgress-bar': { backgroundColor: '#e8b63a', borderRadius: 3 }
          }}
        />
      </Paper>
    )
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        mb: 3,
        borderRadius: designTokens.radius.lg,
        background: '#1a1714',
        border: '1px solid rgba(232,182,58,0.2)',
      }}
    >
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((label, index) => (
          <Step key={label}>
            <StepLabel
              StepIconProps={{
                style: {
                  color: index <= activeStep ? '#e8b63a' : 'rgba(255,255,255,0.25)'
                }
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 500, color: index <= activeStep ? '#e8b63a' : 'rgba(255,255,255,0.45)' }}>
                {label}
              </Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Paper>
  )
}


// Componente principal
export default function BookingPage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  // Estados del formulario
  const [activeStep, setActiveStep] = useState(0)
  const [services, setServices] = useState([])
  const [pizzerosParticipants, setPizzerosParticipants] = useState(0)
  const [partyGuests, setPartyGuests] = useState(0)
  const [pizzaQuantity, setPizzaQuantity] = useState(10)
  const [selectedComuna, setSelectedComuna] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    eventType: '',
    date: '',
    time: '',
    location: '',
    specialRequests: ''
  })
  const [showPriceAnimation, setShowPriceAnimation] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showSuccessModal, setShowSuccessModal] = useState(false)
  const [bookingResult, setBookingResult] = useState(null)
  const [submitError, setSubmitError] = useState('')

  const steps = ['Información Personal', 'Detalles del Evento', 'Confirmación']

  // Efecto para mostrar animación de precio
  useEffect(() => {
    const totalParticipants = getTotalParticipants()
    if (services.length > 0 && totalParticipants > 0) {
      setShowPriceAnimation(true)
      const timer = setTimeout(() => setShowPriceAnimation(false), 1000)
      return () => clearTimeout(timer)
    }
  }, [services, pizzerosParticipants, partyGuests])

  // Función para calcular pizzas sugeridas basado en cantidad de personas
  const calculateSuggestedPizzas = (guests) => {
    if (guests <= 0) return PRICING_CONSTANTS.MIN_PIZZAS
    const suggested = Math.ceil((guests * PRICING_CONSTANTS.SLICES_PER_PERSON) / PRICING_CONSTANTS.SLICES_PER_PIZZA)
    return Math.max(PRICING_CONSTANTS.MIN_PIZZAS, suggested)
  }

  // Función para calcular total de participantes
  const getTotalParticipants = () => {
    if (services.length === 0) return 0

    if (services.includes('pizzeros') && services.includes('party')) {
      // Ambos servicios: usar el máximo entre los dos
      return Math.max(pizzerosParticipants, partyGuests)
    } else if (services.includes('pizzeros')) {
      return pizzerosParticipants
    } else if (services.includes('party')) {
      return partyGuests
    }
    return 0
  }

  // Función para obtener participantes por servicio
  const getParticipantsByService = () => {
    const result = {}
    if (services.includes('pizzeros')) {
      result.pizzeros = pizzerosParticipants
    }
    if (services.includes('party')) {
      result.party = partyGuests // Ahora usa partyGuests (personas) en lugar de partyParticipants
      result.pizzas = pizzaQuantity // Agregamos las pizzas como dato separado
    }
    return result
  }

  // Calcula precio estimado igual que PremiumEstimatedPrice para uso en el paso 3
  const calculateEstimatedPrice = () => {
    let total = 0
    services.forEach(service => {
      if (service === 'pizzeros' && pizzerosParticipants > 0) {
        const price = getPizzerosPrice(pizzerosParticipants)
        total += Math.max(PRICING_CONSTANTS.PIZZEROS_MINIMUM, pizzerosParticipants * price)
      } else if (service === 'party' && pizzaQuantity > 0) {
        total += pizzaQuantity * getPizzaPartyPrice(pizzaQuantity)
      }
    })
    if (isComunaLejana(selectedComuna)) total += PRICING_CONSTANTS.CARGO_COMUNA_LEJANA
    return Math.round(total)
  }

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1)
  }

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1)
  }

  const buildBookingData = () => {
    const comunaLejanaExtra = isComunaLejana(selectedComuna) ? CARGO_COMUNA_LEJANA : 0
    return {
      ...formData,
      services,
      participants: getTotalParticipants(),
      participantsByService: getParticipantsByService(),
      eventType: formData.eventType,
      selectedComuna: selectedComuna,
      comunaLejanaExtra: comunaLejanaExtra,
      source: 'website'
    }
  }

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault()
    setIsSubmitting(true)
    setSubmitError('')
    try {
      const result = await createBooking(buildBookingData())
      setBookingResult(result)
      setShowSuccessModal(true)
    } catch (error) {
      console.error('Error creating booking:', error)
      setSubmitError(error.message || 'Hubo un problema al enviar tu reserva. Por favor intenta nuevamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handlePayAndBook = async () => {
    setIsSubmitting(true)
    setSubmitError('')
    try {
      const result = await createBooking(buildBookingData())
      const estimatedPrice = calculateEstimatedPrice()
      const abonoAmount = Math.round(estimatedPrice * 0.15)
      const preference = await createPaymentPreference({
        booking_id: result.id,
        amount: abonoAmount,
        description: "Abono Reserva Pablo's Pizza"
      })
      window.location.href = preference.init_point
    } catch (error) {
      console.error('Error creating booking+payment:', error)
      setSubmitError(error.message || 'Hubo un problema al procesar tu reserva. Por favor intenta nuevamente.')
      setIsSubmitting(false)
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleServiceToggle = (serviceType) => {
    setServices(prev => {
      const newServices = prev.includes(serviceType)
        ? prev.filter(s => s !== serviceType)
        : [...prev, serviceType]

      // Reset participant counts when service is removed
      if (!newServices.includes('pizzeros')) {
        setPizzerosParticipants(0)
      }
      if (!newServices.includes('party')) {
        setPartyGuests(0)
        setPizzaQuantity(10)
      }

      return newServices
    })
  }

  return (
    <Box sx={{ minHeight: '100vh', background: '#0d0d0d' }}>
      <SEO
        title="Reserva tu Taller de Pizza o Pizza Party"
        description="Agenda tu taller de pizza para niños o pizza party en Santiago. Cotiza online, elige fecha y servicios. Respuesta en 24 horas. Precios desde $9.000 por niño."
        keywords="reservar taller pizza niños, cotizar pizza party Santiago, agendar cumpleaños pizza, reserva evento infantil, cotización catering pizza"
        url="/agendar"
      />
      {/* Hero Section */}
      <HeroSection />

      {/* Botón de navegación flotante */}
      <Container maxWidth="lg" sx={{ pb: 8 }}>
        <Box sx={{ mb: 3, pt: 3 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBack />}
            onClick={() => navigate(-1)}
            size="small"
          >
            Volver
          </Button>
        </Box>

        <Grid container spacing={4}>
          {/* Formulario Principal */}
          <Grid item xs={12} lg={8}>
            <Fade in timeout={1000}>
              <Box>
                {/* Stepper */}
                <FormStepper activeStep={activeStep} steps={steps} />


                {/* Formulario por pasos */}
                <Card
                  sx={{
                    borderRadius: designTokens.radius.lg,
                    background: '#1a1714',
                    border: '1px solid rgba(232,182,58,0.15)',
                    boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
                    overflow: 'visible',
                    // Cascade: dark form fields
                    '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                    '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' },
                    '& .MuiOutlinedInput-root': {
                      color: '#FFFFFF',
                      '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                      '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.4)' },
                      '&.Mui-focused fieldset': { borderColor: '#e8b63a' },
                    },
                    '& .MuiFormHelperText-root': { color: 'rgba(255,255,255,0.4)' },
                    '& .MuiSelect-icon': { color: 'rgba(255,255,255,0.4)' },
                    '& .MuiAutocomplete-popupIndicator': { color: 'rgba(255,255,255,0.4)' },
                    '& .MuiAutocomplete-clearIndicator': { color: 'rgba(255,255,255,0.4)' },
                    '& .MuiCheckbox-root': { color: 'rgba(255,255,255,0.3)' },
                    '& .MuiCheckbox-root.Mui-checked': { color: '#e8b63a' },
                    '& .MuiFormLabel-root': { color: 'rgba(255,255,255,0.5)' },
                    '& .MuiFormControlLabel-label': { color: '#FFFFFF' },
                    '& .MuiInputAdornment-root': { color: 'rgba(255,255,255,0.4)' },
                    '& .MuiInputAdornment-root .MuiTypography-root': { color: 'rgba(255,255,255,0.7)' },
                    '& .MuiInputAdornment-root .MuiSvgIcon-root': { color: 'rgba(255,255,255,0.4)' },
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box component="form" onSubmit={handleSubmit}>
                      {/* Paso 1: Información Personal */}
                      {activeStep === 0 && (
                        <Fade in timeout={500}>
                          <Box>
                            <Box sx={{ mb: 3, textAlign: 'center' }}>
                              <Avatar
                                sx={{
                                  width: 60,
                                  height: 60,
                                  margin: '0 auto 12px',
                                  bgcolor: '#e8b63a',
                                  color: '#0d0d0d',
                                  boxShadow: '0 8px 20px rgba(232,182,58,0.3)',
                                }}
                              >
                                <People sx={{ fontSize: 32 }} />
                              </Avatar>
                              <Typography variant="h5" sx={{ mb: 1.5, fontWeight: 700, color: '#FFFFFF' }}>
                                Información Personal
                              </Typography>
                              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                                Necesitamos tus datos para coordinar tu evento perfecto
                              </Typography>
                            </Box>

                            <Grid container spacing={3}>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Tu nombre completo"
                                  fullWidth
                                  required
                                  value={formData.name}
                                  onChange={(e) => handleInputChange('name', e.target.value)}
                                  InputProps={{
                                    startAdornment: (
                                      <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                        <People />
                                      </Box>
                                    ),
                                  }}
                                />
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Email"
                                  type="email"
                                  fullWidth
                                  required
                                  value={formData.email}
                                  onChange={(e) => handleInputChange('email', e.target.value)}
                                  InputProps={{
                                    startAdornment: (
                                      <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                        <Email />
                                      </Box>
                                    ),
                                  }}
                                />
                              </Grid>
                              <Grid item xs={12}>
                                <PhoneInput
                                  value={formData.phone}
                                  onChange={(value) => handleInputChange('phone', value)}
                                  helperText="Preferiblemente WhatsApp para confirmación rápida"
                                />
                              </Grid>
                            </Grid>

                            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                              <Button
                                variant="contained"
                                onClick={handleNext}
                                disabled={!formData.name || !formData.email || !formData.phone}
                                endIcon={<ArrowForward />}
                                size="large"
                                sx={{
                                  px: 4,
                                  py: 1.5,
                                  minHeight: 48,
                                  borderRadius: designTokens.radius.lg,
                                  fontWeight: 600
                                }}
                              >
                                Continuar
                              </Button>
                            </Box>
                          </Box>
                        </Fade>
                      )}

                      {/* Paso 2: Detalles del Evento */}
                      {activeStep === 1 && (
                        <Fade in timeout={500}>
                          <Box>
                            <Box sx={{ mb: 3, textAlign: 'center' }}>
                              <Avatar
                                sx={{
                                  width: 60,
                                  height: 60,
                                  margin: '0 auto 12px',
                                  bgcolor: '#e8b63a',
                                  color: '#0d0d0d',
                                  boxShadow: '0 8px 20px rgba(232,182,58,0.3)',
                                }}
                              >
                                <Celebration sx={{ fontSize: 32 }} />
                              </Avatar>
                              <Typography variant="h5" sx={{ mb: 1.5, fontWeight: 700, color: '#FFFFFF' }}>
                                Detalles del Evento
                              </Typography>
                              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                                Cuéntanos sobre tu evento para crear la experiencia perfecta
                              </Typography>
                            </Box>

                            <Grid container spacing={3}>
                              <Grid item xs={12}>
                                <Paper
                                  elevation={0}
                                  sx={{
                                    p: 2.5,
                                    borderRadius: 2,
                                    border: '1px solid rgba(232,182,58,0.2)',
                                    background: 'rgba(232,182,58,0.05)'
                                  }}
                                >
                                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                    <Restaurant sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }} />
                                    <FormLabel component="legend" sx={{ fontWeight: 600, fontSize: '1rem', color: '#FFFFFF' }}>
                                      Tipos de Servicio (puedes elegir ambos)
                                    </FormLabel>
                                  </Box>
                                  <FormGroup row>
                                    <FormControlLabel
                                      control={
                                        <Checkbox
                                          checked={services.includes('pizzeros')}
                                          onChange={() => handleServiceToggle('pizzeros')}
                                          sx={{
                                            color: 'rgba(255,255,255,0.3)',
                                            '&.Mui-checked': {
                                              color: '#e8b63a',
                                            },
                                          }}
                                        />
                                      }
                                      label={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <LocalPizza sx={{ fontSize: 18, color: '#e8b63a' }} />
                                          <Typography sx={{ fontWeight: 500 }}>
                                            Pizzeros en Acción
                                          </Typography>
                                        </Box>
                                      }
                                    />
                                    <FormControlLabel
                                      control={
                                        <Checkbox
                                          checked={services.includes('party')}
                                          onChange={() => handleServiceToggle('party')}
                                          sx={{
                                            color: 'rgba(255,255,255,0.3)',
                                            '&.Mui-checked': {
                                              color: '#e8b63a',
                                            },
                                          }}
                                        />
                                      }
                                      label={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <Celebration sx={{ fontSize: 18, color: '#e8b63a' }} />
                                          <Typography sx={{ fontWeight: 500 }}>
                                            Pizza Party
                                          </Typography>
                                        </Box>
                                      }
                                    />
                                  </FormGroup>
                                  <Typography variant="body2" sx={{ mt: 1, color: 'rgba(255,255,255,0.5)' }}>
                                    Los clientes pueden combinar ambos servicios para una experiencia completa
                                  </Typography>
                                </Paper>
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Tipo de Evento"
                                  select
                                  fullWidth
                                  required
                                  value={formData.eventType}
                                  onChange={(e) => handleInputChange('eventType', e.target.value)}
                                  SelectProps={{
                                    MenuProps: menuProps,
                                  }}
                                  InputProps={{
                                    startAdornment: (
                                      <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                        <EmojiEvents />
                                      </Box>
                                    ),
                                  }}
                                >
                                  <MenuItem value="" sx={menuItemStyles}>Tipo de evento...</MenuItem>
                                  <MenuItem value="cumple" sx={{ ...menuItemStyles, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Cake sx={{ fontSize: 18, color: '#e8b63a' }} /> Cumpleaños
                                  </MenuItem>
                                  <MenuItem value="escolar" sx={{ ...menuItemStyles, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <School sx={{ fontSize: 18, color: '#e8b63a' }} /> Escolar
                                  </MenuItem>
                                  <MenuItem value="corporativo" sx={{ ...menuItemStyles, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Business sx={{ fontSize: 18, color: '#e8b63a' }} /> Corporativo
                                  </MenuItem>
                                  <MenuItem value="otro" sx={menuItemStyles}>Otro</MenuItem>
                                </TextField>
                              </Grid>
                              {/* Campos de participantes dinámicos */}
                              {services.includes('pizzeros') && services.includes('party') && (
                                <>
                                  <Grid item xs={12} sm={4}>
                                    <TextField
                                      label="¿Cuántos niños participan en Pizzeros en Acción?"
                                      type="number"
                                      fullWidth
                                      required
                                      value={pizzerosParticipants || ''}
                                      onChange={(e) => setPizzerosParticipants(parseInt(e.target.value || '0', 10))}
                                      inputProps={{ min: 1, max: 200 }}
                                      InputProps={{
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <People />
                                          </Box>
                                        ),
                                      }}
                                      helperText="Mínimo 10 niños - Descuentos desde 15 participantes"
                                    />
                                  </Grid>
                                  <Grid item xs={12} sm={4}>
                                    <TextField
                                      label="¿Cuántas personas para pizza party?"
                                      type="number"
                                      fullWidth
                                      required
                                      value={partyGuests || ''}
                                      onChange={(e) => {
                                        const guests = parseInt(e.target.value || '0', 10)
                                        setPartyGuests(guests)
                                        // Auto-calcular pizzas sugeridas
                                        const suggested = calculateSuggestedPizzas(guests)
                                        setPizzaQuantity(suggested)
                                      }}
                                      inputProps={{ min: 1, max: 500 }}
                                      InputProps={{
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <People />
                                          </Box>
                                        ),
                                      }}
                                      helperText="Cantidad de invitados para pizza party"
                                    />
                                  </Grid>
                                  <Grid item xs={12} sm={4}>
                                    <TextField
                                      label="Pizzas sugeridas"
                                      type="number"
                                      fullWidth
                                      required
                                      value={pizzaQuantity || ''}
                                      onChange={(e) => {
                                        const quantity = parseInt(e.target.value || '10', 10)
                                        setPizzaQuantity(Math.max(10, quantity))
                                      }}
                                      inputProps={{ min: 10, max: 200 }}
                                      InputProps={{
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <Restaurant />
                                          </Box>
                                        ),
                                      }}
                                      helperText="Puedes ajustar la cantidad. Mínimo 10 pizzas"
                                    />
                                  </Grid>
                                </>
                              )}
                              {services.includes('pizzeros') && !services.includes('party') && (
                                <Grid item xs={12} sm={6}>
                                  <TextField
                                    label="¿Cuántos niños participan?"
                                    type="number"
                                    fullWidth
                                    required
                                    value={pizzerosParticipants || ''}
                                    onChange={(e) => setPizzerosParticipants(parseInt(e.target.value || '0', 10))}
                                    inputProps={{ min: 1, max: 200 }}
                                    InputProps={{
                                      startAdornment: (
                                        <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                          <People />
                                        </Box>
                                      ),
                                    }}
                                    helperText="Mínimo 10 niños - Descuentos desde 15 participantes"
                                  />
                                </Grid>
                              )}
                              {services.includes('party') && !services.includes('pizzeros') && (
                                <>
                                  <Grid item xs={12} sm={6}>
                                    <TextField
                                      label="Cantidad de personas"
                                      type="number"
                                      fullWidth
                                      required
                                      value={partyGuests || ''}
                                      onChange={(e) => {
                                        const guests = parseInt(e.target.value || '0', 10)
                                        setPartyGuests(guests)
                                        // Auto-calculate suggested pizzas
                                        if (guests > 0) {
                                          const suggested = calculateSuggestedPizzas(guests)
                                          setPizzaQuantity(Math.max(10, suggested))
                                        }
                                      }}
                                      inputProps={{ min: 1, max: 200 }}
                                      InputProps={{
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <People />
                                          </Box>
                                        ),
                                      }}
                                      helperText="Número de invitados al evento"
                                    />
                                  </Grid>
                                  <Grid item xs={12} sm={6}>
                                    <TextField
                                      label="Pizzas sugeridas"
                                      type="number"
                                      fullWidth
                                      required
                                      value={pizzaQuantity || ''}
                                      onChange={(e) => {
                                        const quantity = parseInt(e.target.value || '10', 10)
                                        setPizzaQuantity(Math.max(10, quantity))
                                      }}
                                      inputProps={{ min: 10, max: 200 }}
                                      InputProps={{
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <Restaurant />
                                          </Box>
                                        ),
                                      }}
                                      helperText="Mínimo 10 pizzas - Ajustable según tus necesidades"
                                    />
                                  </Grid>
                                </>
                              )}
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Fecha del Evento"
                                  type="date"
                                  fullWidth
                                  required
                                  value={formData.date}
                                  onChange={(e) => handleInputChange('date', e.target.value)}
                                  InputLabelProps={{ shrink: true }}
                                  InputProps={{
                                    startAdornment: (
                                      <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                        <CalendarToday />
                                      </Box>
                                    ),
                                  }}
                                />
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Hora del Evento"
                                  select
                                  fullWidth
                                  required
                                  value={formData.time}
                                  onChange={(e) => handleInputChange('time', e.target.value)}
                                  SelectProps={{
                                    MenuProps: menuProps,
                                  }}
                                  InputProps={{
                                    startAdornment: (
                                      <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                        <Schedule />
                                      </Box>
                                    ),
                                  }}
                                  helperText="Solo horarios disponibles :00 y :30"
                                >
                                  <MenuItem value="" sx={menuItemStyles}>Seleccionar hora...</MenuItem>
                                  {TIME_OPTIONS.map(time => (
                                    <MenuItem key={time} value={time} sx={menuItemStyles}>{time}</MenuItem>
                                  ))}
                                </TextField>
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <Autocomplete
                                  options={santiagoComunas}
                                  getOptionLabel={(option) => option}
                                  value={selectedComuna}
                                  onChange={(event, newValue) => {
                                    setSelectedComuna(newValue)
                                    // Update location with comuna and region
                                    if (newValue) {
                                      handleInputChange('location', `${newValue}, Región Metropolitana, Chile`)
                                    }
                                  }}
                                  renderOption={(props, option) => (
                                    <Box component="li" {...props}>
                                      {option}
                                      {isComunaLejana(option) && (
                                        <Chip
                                          label="+$20.000"
                                          size="small"
                                          sx={{
                                            ml: 1,
                                            height: 20,
                                            fontSize: '0.7rem',
                                            backgroundColor: 'warning.light',
                                            color: 'warning.dark'
                                          }}
                                        />
                                      )}
                                    </Box>
                                  )}
                                  renderInput={(params) => (
                                    <TextField
                                      {...params}
                                      label="Comuna de Santiago"
                                      required
                                      InputProps={{
                                        ...params.InputProps,
                                        startAdornment: (
                                          <Box sx={{ mr: 1, color: 'rgba(255,255,255,0.4)' }}>
                                            <LocationOn />
                                          </Box>
                                        ),
                                      }}
                                      helperText={
                                        isComunaLejana(selectedComuna)
                                          ? `⚠️ ${selectedComuna} tiene cargo adicional de $20.000`
                                          : "Selecciona la comuna donde se realizará el evento"
                                      }
                                      FormHelperTextProps={{
                                        sx: isComunaLejana(selectedComuna) ? { color: 'warning.main', fontWeight: 500 } : {}
                                      }}
                                    />
                                  )}
                                />
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <TextField
                                  label="Dirección Específica"
                                  fullWidth
                                  required
                                  value={formData.location}
                                  onChange={(e) => handleInputChange('location', e.target.value)}
                                  placeholder="Ej: Av. Las Condes 123"
                                  helperText="Dirección completa del evento en Santiago"
                                />
                              </Grid>
                              <Grid item xs={12}>
                                <TextField
                                  label="Solicitudes Especiales"
                                  fullWidth
                                  multiline
                                  minRows={3}
                                  value={formData.specialRequests}
                                  onChange={(e) => handleInputChange('specialRequests', e.target.value)}
                                  placeholder="Alergias alimentarias, decoraciones especiales, música, etc."
                                />
                              </Grid>
                            </Grid>

                            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
                              <Button
                                onClick={handleBack}
                                startIcon={<ArrowBack />}
                                size="large"
                                sx={{
                                  px: 4,
                                  py: 1.5,
                                  minHeight: 48,
                                  borderRadius: designTokens.radius.lg,
                                  fontWeight: 600
                                }}
                              >
                                Anterior
                              </Button>
                              <Button
                                variant="contained"
                                onClick={handleNext}
                                disabled={services.length === 0 || getTotalParticipants() === 0 || !formData.eventType || !formData.date || !formData.time || !selectedComuna || !formData.location}
                                endIcon={<ArrowForward />}
                                size="large"
                                sx={{
                                  px: 4,
                                  py: 1.5,
                                  minHeight: 48,
                                  borderRadius: designTokens.radius.lg,
                                  fontWeight: 600
                                }}
                              >
                                Ver Resumen
                              </Button>
                            </Box>
                          </Box>
                        </Fade>
                      )}

                      {/* Paso 3: Confirmación */}
                      {activeStep === 2 && (
                        <Fade in timeout={500}>
                          <Box>
                            <Box sx={{ mb: 3, textAlign: 'center' }}>
                              <Avatar
                                sx={{
                                  width: 60,
                                  height: 60,
                                  margin: '0 auto 12px',
                                  bgcolor: '#e8b63a',
                                  color: '#0d0d0d',
                                  boxShadow: '0 8px 20px rgba(232,182,58,0.3)',
                                }}
                              >
                                <CheckCircle sx={{ fontSize: 32 }} />
                              </Avatar>
                              <Typography variant="h5" sx={{ mb: 1.5, fontWeight: 700, color: '#FFFFFF' }}>
                                Confirmar Reserva
                              </Typography>
                              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                                Revisa los detalles de tu evento antes de enviar
                              </Typography>
                            </Box>

                            {/* Resumen del evento */}
                            <Paper
                              elevation={0}
                              sx={{
                                p: 3,
                                mb: 3,
                                borderRadius: designTokens.radius.lg,
                                background: 'rgba(232,182,58,0.06)',
                                border: '1px solid rgba(232,182,58,0.2)',
                              }}
                            >
                              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#e8b63a' }}>
                                Resumen de tu Evento
                              </Typography>

                              <Grid container spacing={2}>
                                <Grid item xs={12} sm={6}>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 0.5 }}>Contacto:</Typography>
                                  <Typography variant="body1" sx={{ fontWeight: 600, color: '#FFFFFF' }}>{formData.name}</Typography>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>{formData.email}</Typography>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>{formData.phone}</Typography>
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 0.5 }}>Evento:</Typography>
                                  <Typography variant="body1" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                                    {services.map(s => s === 'pizzeros' ? 'Pizzeros en Acción' : 'Pizza Party').join(' + ')}
                                  </Typography>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>{formData.eventType}</Typography>
                                  {services.includes('pizzeros') && services.includes('party') ? (
                                    <>
                                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>Pizzeros en Acción: {pizzerosParticipants} niños</Typography>
                                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>Pizza Party: {pizzaQuantity} pizzas</Typography>
                                    </>
                                  ) : services.includes('pizzeros') ? (
                                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>Pizzeros en Acción: {pizzerosParticipants} niños</Typography>
                                  ) : services.includes('party') ? (
                                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>Pizza Party: {pizzaQuantity} pizzas</Typography>
                                  ) : null}
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>{formData.date} a las {formData.time}</Typography>
                                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>{formData.location}</Typography>
                                </Grid>
                              </Grid>
                            </Paper>

                            {/* Sección de Abono MercadoPago */}
                            {calculateEstimatedPrice() > 0 && (
                              <Paper
                                elevation={0}
                                sx={{
                                  p: 3,
                                  mb: 3,
                                  borderRadius: designTokens.radius.lg,
                                  background: 'rgba(33,150,243,0.07)',
                                  border: '1px solid rgba(33,150,243,0.2)',
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                  <CreditCard sx={{ mr: 1, color: '#64b5f6' }} />
                                  <Typography variant="h6" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                                    Abono para confirmar tu reserva
                                  </Typography>
                                </Box>
                                <Grid container spacing={0.5} sx={{ mb: 2 }}>
                                  <Grid item xs={7}>
                                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>Precio estimado:</Typography>
                                  </Grid>
                                  <Grid item xs={5} sx={{ textAlign: 'right' }}>
                                    <Typography variant="body2" sx={{ fontWeight: 500, color: 'rgba(255,255,255,0.85)' }}>
                                      ${calculateEstimatedPrice().toLocaleString('es-CL')} CLP
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={7}>
                                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>Abono online (15%):</Typography>
                                  </Grid>
                                  <Grid item xs={5} sx={{ textAlign: 'right' }}>
                                    <Typography variant="body1" sx={{ fontWeight: 700, color: '#64b5f6' }}>
                                      ${Math.round(calculateEstimatedPrice() * 0.15).toLocaleString('es-CL')} CLP
                                    </Typography>
                                  </Grid>
                                </Grid>
                                <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.1)' }} />

                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                                  <Lock sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)' }} />
                                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                    Pago seguro vía
                                  </Typography>
                                  <Box
                                    sx={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: 0.4,
                                      backgroundColor: '#009EE3',
                                      color: '#fff',
                                      borderRadius: '4px',
                                      px: 0.8,
                                      py: 0.2,
                                      fontSize: '0.7rem',
                                      fontWeight: 700,
                                      letterSpacing: 0.2,
                                      lineHeight: 1.4,
                                    }}
                                  >
                                    Mercado Pago
                                  </Box>
                                </Box>

                                <Alert
                                  severity="warning"
                                  sx={{
                                    borderRadius: designTokens.radius.md,
                                    py: 0.5,
                                    '& .MuiAlert-message': { fontSize: '0.8rem' }
                                  }}
                                >
                                  El abono debe pagarse <strong>al menos 1 semana antes</strong> del evento para confirmar tu fecha. Sin el abono, la fecha queda tentativa.
                                </Alert>
                              </Paper>
                            )}

                            {/* Alert de información */}
                            <Alert
                              icon={<WhatsApp />}
                              severity="info"
                              sx={{ mb: 3, borderRadius: designTokens.radius.lg }}
                            >
                              Te contactaremos vía WhatsApp en las próximas 24 horas para confirmar disponibilidad y coordinar los detalles finales.
                            </Alert>

                            {/* Error alert si existe */}
                            {submitError && (
                              <Alert
                                severity="error"
                                sx={{ mb: 3, borderRadius: designTokens.radius.lg }}
                                onClose={() => setSubmitError('')}
                              >
                                {submitError}
                              </Alert>
                            )}

                            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
                              <Button
                                onClick={handleBack}
                                startIcon={<ArrowBack />}
                                size="large"
                                disabled={isSubmitting}
                                sx={{
                                  px: 4,
                                  py: 1.5,
                                  minHeight: 48,
                                  borderRadius: designTokens.radius.lg,
                                  fontWeight: 600
                                }}
                              >
                                Anterior
                              </Button>
                              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                                <Button
                                  type="submit"
                                  variant="outlined"
                                  size="large"
                                  disabled={isSubmitting}
                                  startIcon={<WhatsApp />}
                                  sx={{
                                    px: 3,
                                    py: 1.5,
                                    minHeight: 48,
                                    borderRadius: designTokens.radius.lg,
                                    fontWeight: 600,
                                    borderColor: designTokens.colors.golden[500],
                                    color: designTokens.colors.charcoal[800],
                                    '&:hover': {
                                      borderColor: designTokens.colors.golden[600],
                                      backgroundColor: 'rgba(255,215,0,0.08)',
                                    },
                                    '&:disabled': { opacity: 0.6 },
                                  }}
                                >
                                  Reservar sin Abonar
                                </Button>
                                {calculateEstimatedPrice() > 0 && (
                                  <Button
                                    type="button"
                                    variant="contained"
                                    size="large"
                                    disabled={isSubmitting}
                                    onClick={handlePayAndBook}
                                    startIcon={isSubmitting ? <AutoAwesome className="spin" /> : <CreditCard />}
                                    sx={{
                                      px: 3,
                                      py: 1.5,
                                      minHeight: 48,
                                      borderRadius: designTokens.radius.lg,
                                      fontWeight: 600,
                                      background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
                                      '&:hover': {
                                        background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
                                        transform: 'translateY(-2px)',
                                        boxShadow: '0 6px 20px rgba(25,118,210,0.4)',
                                      },
                                      '&:disabled': {
                                        background: 'rgba(0,0,0,0.12)',
                                        color: 'rgba(0,0,0,0.38)',
                                      },
                                      '& .spin': {
                                        animation: 'spin 1s linear infinite'
                                      }
                                    }}
                                  >
                                    {isSubmitting ? 'Procesando...' : `Pagar Abono ($${Math.round(calculateEstimatedPrice() * 0.15).toLocaleString('es-CL')})`}
                                  </Button>
                                )}
                              </Stack>
                            </Box>
                          </Box>
                        </Fade>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            </Fade>
          </Grid>

          {/* Panel Lateral Premium */}
          <Grid item xs={12} lg={4}>
            <Box sx={{ position: 'sticky', top: 100 }}>
              <Fade in timeout={1200}>
                <Box>
                  {/* Calculadora de Precio Premium */}
                  <Card
                    sx={{
                      mb: 3,
                      borderRadius: designTokens.radius.lg,
                      background: '#1a1714',
                      border: '1px solid',
                      borderColor: showPriceAnimation ? '#e8b63a' : 'rgba(232,182,58,0.15)',
                      boxShadow: showPriceAnimation
                        ? '0 8px 32px rgba(232,182,58,0.2), 0 4px 16px rgba(0,0,0,0.3)'
                        : '0 4px 20px rgba(0,0,0,0.25)',
                      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                      transform: showPriceAnimation ? 'scale(1.01)' : 'scale(1)',
                      overflow: 'hidden',
                      position: 'relative',
                      '&::before': showPriceAnimation ? {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: '3px',
                        background: 'linear-gradient(90deg, transparent, #e8b63a, transparent)',
                        animation: 'shimmer 2s ease-in-out infinite',
                      } : {},
                    }}
                  >
                    <CardContent sx={{ p: 2.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Avatar
                          sx={{
                            width: 40,
                            height: 40,
                            mr: 2,
                            bgcolor: '#e8b63a',
                            color: '#0d0d0d',
                          }}
                        >
                          <Calculate />
                        </Avatar>
                        <Typography variant="h6" sx={{ fontWeight: 700, color: '#FFFFFF' }}>
                          Precio Estimado
                        </Typography>
                      </Box>

                      <PremiumEstimatedPrice
                    services={services}
                    pizzerosParticipants={pizzerosParticipants}
                    pizzaQuantity={pizzaQuantity}
                    participants={getTotalParticipants()}
                    selectedComuna={selectedComuna}
                  />

                      {services.length > 0 && getTotalParticipants() > 0 && (
                        <Zoom in timeout={500}>
                          <Box sx={{ mt: 2 }}>
                            <LinearProgress
                              variant="determinate"
                              value={100}
                              sx={{
                                height: 6,
                                borderRadius: designTokens.radius.full,
                                backgroundColor: 'rgba(232,182,58,0.15)',
                                '& .MuiLinearProgress-bar': {
                                  background: '#e8b63a',
                                  borderRadius: designTokens.radius.full,
                                }
                              }}
                            />
                            <Typography variant="body2" sx={{ mt: 1, textAlign: 'center', fontWeight: 500, color: 'rgba(255,255,255,0.6)' }}>
                              Precio calculado automáticamente
                            </Typography>
                          </Box>
                        </Zoom>
                      )}
                    </CardContent>
                  </Card>


                  {/* Contacto Rápido */}
                  <Card
                    sx={{
                      borderRadius: designTokens.radius.lg,
                      background: '#1a1714',
                      border: '1px solid rgba(37,211,102,0.25)',
                    }}
                  >
                    <CardContent sx={{ p: 3, textAlign: 'center' }}>
                      <Avatar
                        sx={{
                          width: 50,
                          height: 50,
                          margin: '0 auto 16px',
                          bgcolor: '#25D366',
                          color: 'white',
                          boxShadow: '0 8px 20px rgba(37,211,102,0.25)',
                        }}
                      >
                        <WhatsApp sx={{ fontSize: 26 }} />
                      </Avatar>

                      <Typography variant="h6" sx={{ mb: 1, fontWeight: 700, color: '#FFFFFF' }}>
                        ¿Tienes preguntas?
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 3, color: 'rgba(255,255,255,0.6)', lineHeight: 1.6 }}>
                        Chatea con nosotros por WhatsApp y resuelve tus dudas al instante
                      </Typography>

                      <Button
                        variant="contained"
                        fullWidth
                        startIcon={<WhatsApp />}
                        href="https://wa.me/56989424566?text=Hola! Tengo preguntas sobre el servicio de pizzeros"
                        target="_blank"
                        sx={{
                          background: '#25D366',
                          color: 'white',
                          py: 1.5,
                          minHeight: 48,
                          borderRadius: designTokens.radius.lg,
                          fontWeight: 700,
                          fontSize: '0.95rem',
                          boxShadow: '0 4px 15px rgba(37,211,102,0.3)',
                          '&:hover': {
                            background: '#22C55E',
                            transform: 'translateY(-2px)',
                            boxShadow: '0 8px 25px rgba(37,211,102,0.4)',
                          }
                        }}
                      >
                        Chatear Ahora
                      </Button>

                      <Stack direction="row" spacing={1} sx={{ mt: 2.5, justifyContent: 'center' }}>
                        <Chip
                          icon={<AccessTime sx={{ fontSize: '14px !important', color: '#0d0d0d !important' }} />}
                          label="Respuesta 24h"
                          size="small"
                          sx={{ bgcolor: '#e8b63a', color: '#0d0d0d', fontWeight: 600, fontSize: '0.7rem' }}
                        />
                        <Chip
                          icon={<CheckCircle sx={{ fontSize: '14px !important', color: 'white !important' }} />}
                          label="100% Confiable"
                          size="small"
                          sx={{ bgcolor: '#25D366', color: 'white', fontWeight: 600, fontSize: '0.7rem' }}
                        />
                      </Stack>
                    </CardContent>
                  </Card>
                </Box>
              </Fade>
            </Box>
          </Grid>
        </Grid>
      </Container>



      {/* Modal de Confirmación Moderno */}
      <Dialog
        open={showSuccessModal}
        onClose={() => {
          setShowSuccessModal(false)
          navigate('/')
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            backgroundColor: '#FFFFFF'
          }
        }}
      >
        {/* HEADER FIJO - No hace scroll */}
        <DialogTitle
          sx={{
            backgroundColor: '#000000',
            color: '#FFD700',
            textAlign: 'center',
            py: 3,
            position: 'sticky',
            top: 0,
            zIndex: 10
          }}
        >
          <CheckCircle sx={{ fontSize: 60, color: '#4CAF50', mb: 2 }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#FFD700' }}>
            ¡Reserva Confirmada! 🎉
          </Typography>
          <Typography variant="body2" sx={{ color: '#FFFFFF', mt: 1 }}>
            Tu evento ha sido registrado exitosamente
          </Typography>
        </DialogTitle>

        {/* CONTENIDO CON SCROLL */}
        <DialogContent
          sx={{
            p: 3,
            maxHeight: '60vh',
            overflowY: 'auto',
            '&::-webkit-scrollbar': {
              width: '8px'
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#FFD700',
              borderRadius: '4px'
            }
          }}
        >
          {/* Sección de Detalles */}
          <Box sx={{ mb: 3 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 'bold',
                mb: 2,
                color: '#000',
                borderBottom: '2px solid #FFD700',
                pb: 1
              }}
            >
              📋 Detalles de tu Reserva
            </Typography>

            {/* Grid de información */}
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LocalPizza sx={{ color: '#FFD700' }} />
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666' }}>
                      Servicio
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {services.map(s => s === 'pizzeros' ? 'Pizzeros en Acción' : 'Pizza Party').join(' + ')}
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Group sx={{ color: '#FFD700' }} />
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666' }}>
                      Participantes
                    </Typography>
                    {services.includes('pizzeros') && services.includes('party') ? (
                      <>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          Pizzeros: {pizzerosParticipants} niños
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          Party: {partyGuests} personas / {pizzaQuantity} pizzas
                        </Typography>
                      </>
                    ) : services.includes('pizzeros') ? (
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {pizzerosParticipants} niños
                      </Typography>
                    ) : services.includes('party') ? (
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {partyGuests} personas / {pizzaQuantity} pizzas
                      </Typography>
                    ) : (
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {getTotalParticipants()} personas
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CalendarToday sx={{ color: '#FFD700' }} />
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666' }}>
                      Fecha
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {formData.date}
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AccessTime sx={{ color: '#FFD700' }} />
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666' }}>
                      Hora
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {formData.time}
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LocationOn sx={{ color: '#FFD700' }} />
                  <Box>
                    <Typography variant="caption" sx={{ color: '#666' }}>
                      Ubicación
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {formData.location}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            </Grid>
          </Box>

          {/* Mensaje de WhatsApp */}
          <Box
            sx={{
              backgroundColor: '#E8F5E9',
              borderRadius: 2,
              p: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              mb: 2
            }}
          >
            <WhatsApp sx={{ fontSize: 30, color: '#25D366' }} />
            <Typography variant="body2" sx={{ color: '#1B5E20' }}>
              Te contactaremos por WhatsApp en las próximas 24 horas para confirmar todos los detalles
            </Typography>
          </Box>

          {/* Email de confirmación */}
          <Typography
            variant="body2"
            sx={{
              textAlign: 'center',
              color: '#666',
              mt: 2
            }}
          >
            📧 Recibirás un email de confirmación con todos los detalles
          </Typography>
        </DialogContent>

        {/* BOTONES FIJOS - Siempre visibles */}
        <DialogActions
          sx={{
            background: '#1a1714',
            p: 2,
            position: 'sticky',
            bottom: 0,
            borderTop: '1px solid rgba(232,182,58,0.15)',
            gap: 2,
            justifyContent: 'center'
          }}
        >
          <Button
            variant="contained"
            onClick={() => {
              setShowSuccessModal(false)
              navigate('/')
            }}
            sx={{
              backgroundColor: '#000000',
              color: '#FFD700',
              fontWeight: 'bold',
              px: 4,
              py: 1.5,
              '&:hover': {
                backgroundColor: '#333333'
              }
            }}
          >
            ✓ Entendido
          </Button>
          <Button
            variant="outlined"
            onClick={() => window.open('https://wa.me/56989424566?text=Hola! Acabo de hacer una reserva', '_blank')}
            startIcon={<WhatsApp />}
            sx={{
              borderColor: '#25D366',
              color: '#25D366',
              fontWeight: 'bold',
              px: 4,
              py: 1.5,
              '&:hover': {
                borderColor: '#25D366',
                backgroundColor: 'rgba(37, 211, 102, 0.1)'
              }
            }}
          >
            Ir a WhatsApp
          </Button>
        </DialogActions>
      </Dialog>

      {/* Estilos CSS para animaciones */}
      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); box-shadow: 0 8px 32px rgba(76, 175, 80, 0.3); }
          50% { transform: scale(1.05); box-shadow: 0 12px 40px rgba(76, 175, 80, 0.4); }
          100% { transform: scale(1); box-shadow: 0 8px 32px rgba(76, 175, 80, 0.3); }
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        @keyframes rippleEffect {
          0% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
          }
          100% {
            transform: translate(-50%, -50%) scale(1.8);
            opacity: 0;
          }
        }
      `}</style>
    </Box>
  )
}

// Componente de precio estimado premium con animaciones
function PremiumEstimatedPrice({ services, pizzerosParticipants, participants, pizzaQuantity, selectedComuna }) {
  const { totals, grandTotal, breakdown, cargoLejana, totalConCargo } = useMemo(() => {
    if (!services || services.length === 0) {
      return { totals: {}, grandTotal: 0, breakdown: [], cargoLejana: 0, totalConCargo: 0 }
    }

    const calculatedTotals = {}
    const calculatedBreakdown = []
    let grandTotal = 0

    services.forEach(service => {
      let unitBase = 0
      let unitFinal = 0
      let label = ''
      let serviceParticipants = 0

      if (service === 'pizzeros') {
        serviceParticipants = pizzerosParticipants
        if (serviceParticipants === 0) return

        unitBase = PIZZEROS_TIERS[0].price
        unitFinal = getPizzerosPrice(serviceParticipants)
        label = 'Pizzeros en Acción'

        // Aplicar mínimo para rango 0-10
        if (serviceParticipants <= 10) {
          const total = Math.max(PRICING_CONSTANTS.PIZZEROS_MINIMUM, serviceParticipants * unitFinal)
          calculatedTotals[service] = { total, unitFinal, unitBase, discountPct: 0, label, isMinimum: true }
          calculatedBreakdown.push({
            service,
            label,
            unitBase,
            unitFinal,
            total,
            discountPct: 0,
            serviceParticipants,
            isMinimum: true
          })
          grandTotal += total
          return
        }
      } else if (service === 'party') {
        serviceParticipants = pizzaQuantity || 0
        if (serviceParticipants === 0) return

        unitBase = PRICING_CONSTANTS.PIZZA_PARTY_BASE_PRICE
        unitFinal = getPizzaPartyPrice(serviceParticipants)
        label = 'Pizza Party'
      }

      if (serviceParticipants > 0) {
        const total = unitFinal * serviceParticipants
        const discountPct = unitBase > 0 ? Math.max(0, Math.round(100 - (unitFinal / unitBase) * 100)) : 0

        calculatedTotals[service] = { total, unitFinal, unitBase, discountPct, label }
        calculatedBreakdown.push({
          service,
          label,
          unitBase,
          unitFinal,
          total,
          discountPct,
          serviceParticipants
        })
        grandTotal += total
      }
    })

    // Calcular cargo por comuna lejana
    const cargoLejana = isComunaLejana(selectedComuna) ? PRICING_CONSTANTS.CARGO_COMUNA_LEJANA : 0
    const totalConCargo = grandTotal + cargoLejana

    return { totals: calculatedTotals, grandTotal, breakdown: calculatedBreakdown, cargoLejana, totalConCargo }
  }, [services, pizzerosParticipants, pizzaQuantity, selectedComuna])

  const clp = (n) => n.toLocaleString('es-CL')

  if (!services || services.length === 0 || (pizzerosParticipants === 0 && pizzaQuantity === 0)) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <MonetizationOn sx={{ fontSize: 48, color: 'rgba(232,182,58,0.4)', mb: 2 }} />
        <Typography variant="body1" sx={{ mb: 1, color: 'rgba(255,255,255,0.5)' }}>
          Selecciona servicios y participantes
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.35)' }}>
          para ver tu precio estimado en tiempo real
        </Typography>
      </Box>
    )
  }

  return (
    <Box>
      {/* Precio Principal - Limpio sin sombras */}
      <Box sx={{ textAlign: 'center', mb: 3 }}>
        <Typography
          variant="h3"
          sx={{
            fontWeight: 900,
            color: '#e8b63a',
            mb: 1,
          }}
        >
          ${clp(totalConCargo)}
        </Typography>
        <Typography variant="body1" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.6)' }}>
          {breakdown.map(b => `${b.label} (${b.serviceParticipants} ${b.service === 'pizzeros' ? 'niños' : 'pizzas'})`).join(' + ')}
        </Typography>
        {cargoLejana > 0 && (
          <Typography variant="body2" sx={{ color: 'warning.main', mt: 0.5 }}>
            + Cargo comuna lejana ({selectedComuna})
          </Typography>
        )}
      </Box>

      {/* Desglose de precios por servicio */}
      <Box sx={{
        p: 2,
        borderRadius: 3,
        backgroundColor: 'rgba(232,182,58,0.06)',
        border: '1px solid rgba(232,182,58,0.2)',
      }}>
        {breakdown.map((item, index) => (
          <Box key={item.service} sx={{ mb: index < breakdown.length - 1 ? 2 : 0 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: '#e8b63a' }}>
              {item.label}
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                {item.isMinimum ? 'Tarifa mínima:' : 'Precio base:'}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>
                {item.isMinimum
                  ? `$${clp(item.total)} (hasta 10 niños)`
                  : `$${clp(item.unitBase)} x ${item.serviceParticipants}`
                }
              </Typography>
            </Box>

            {item.discountPct > 0 && !item.isMinimum && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" sx={{ color: '#4CAF50' }}>
                  Descuento {item.discountPct}%:
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: '#4CAF50' }}>
                  -${clp((item.unitBase - item.unitFinal) * item.serviceParticipants)}
                </Typography>
              </Box>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.65)' }}>
                Subtotal {item.label}:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 700, color: '#e8b63a' }}>
                ${clp(item.total)}
              </Typography>
            </Box>

            {index < breakdown.length - 1 && <Divider sx={{ mt: 1, borderColor: 'rgba(255,255,255,0.08)' }} />}
          </Box>
        ))}

        <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.08)' }} />

        {/* Cargo por comuna lejana */}
        {cargoLejana > 0 && (
          <Box sx={{
            mb: 2,
            p: 1.5,
            borderRadius: 2,
            backgroundColor: 'rgba(255,152,0,0.08)',
            border: '1px solid rgba(255,152,0,0.25)'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600, color: '#FFB74D' }}>
                  🚗 Cargo comuna lejana
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.45)' }}>
                  {selectedComuna} - Fuera de zona central
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ fontWeight: 700, color: '#FFB74D' }}>
                +${clp(cargoLejana)}
              </Typography>
            </Box>
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: 'rgba(255,255,255,0.85)' }}>
            Total Final:
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 800, color: '#e8b63a' }}>
            ${clp(totalConCargo)}
          </Typography>
        </Box>
      </Box>

      {/* Badge de descuento si hay algún descuento */}
      {breakdown.some(item => item.discountPct > 0) && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Chip
            icon={<TrendingUp sx={{ color: 'white !important' }} />}
            label="¡Descuentos aplicados!"
            sx={{
              bgcolor: '#4CAF50',
              color: 'white',
              fontWeight: 700,
            }}
          />
        </Box>
      )}

      {/* Información adicional */}
      <Box sx={{ mt: 2, textAlign: 'center' }}>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.4)' }}>
          Precio incluye pizzeros profesionales, ingredientes premium y show completo
        </Typography>
      </Box>

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.8; }
          100% { opacity: 1; }
        }
      `}</style>
    </Box>
  )
}

// Componente auxiliar mantenido para compatibilidad
function EstimatedPrice({ service, participants }) {
  const services = service ? [service] : []
  return <PremiumEstimatedPrice services={services} participants={participants} />
}
