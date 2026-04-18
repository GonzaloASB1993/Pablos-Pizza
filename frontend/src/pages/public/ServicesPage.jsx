import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Button,
  Paper,
  Avatar,
  Rating,
  Badge,
  IconButton,
  Collapse,
  Fade,
  Zoom
} from '@mui/material'
import SEO from '../../components/common/SEO'
import {
  School,
  Celebration,
  CheckCircle,
  Groups,
  AccessTime,
  Place,
  ArrowForward,
  Star,
  LocalOffer,
  ExpandMore,
  ExpandLess,
  WhatsApp,
  Phone,
  Email,
  Verified,
  TrendingUp,
  EmojiEvents,
  Restaurant
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { listenTestimonials } from '../../services/testimonialsService'
import { CONTACT_INFO } from '../../config/constants'

// Enhanced interactive tag component
const ModernTag = ({ children, color = 'primary', variant = 'filled', icon, size = 'medium' }) => (
  <Chip
    label={children}
    color={color}
    variant={variant === 'outlined' ? 'outlined' : 'filled'}
    icon={icon}
    size={size}
    sx={{
      mr: 1,
      mb: 1,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: theme => `0 4px 20px ${theme.palette[color].main}40`
      }
    }}
  />
)

// Enhanced bullet point with animations
const FeatureBullet = ({ children, delay = 0 }) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay * 100)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <Fade in={isVisible} timeout={800}>
      <Box sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1.5,
        mb: 2,
        p: 1,
        borderRadius: 2,
        transition: 'all 0.3s ease',
        '&:hover': {
          bgcolor: 'rgba(232, 182, 58, 0.05)',
          transform: 'translateX(8px)'
        }
      }}>
        <CheckCircle sx={{
          color: '#e8b63a',
          fontSize: 20,
          mt: 0.2,
          filter: 'drop-shadow(0 2px 4px rgba(232, 182, 58, 0.3))'
        }} />
        <Typography variant="body1" sx={{ fontWeight: 500, lineHeight: 1.6, color: 'rgba(255,255,255,0.85)' }}>
          {children}
        </Typography>
      </Box>
    </Fade>
  )
}

// Service stats component
const ServiceStats = ({ icon, label, value, color = '#e8b63a' }) => (
  <Box sx={{
    textAlign: 'center',
    p: 2,
    borderRadius: 3,
    bgcolor: `${color}15`,
    border: `1px solid ${color}30`,
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: `0 8px 25px ${color}25`
    }
  }}>
    {React.cloneElement(icon, {
      sx: { fontSize: 32, color, mb: 1 }
    })}
    <Typography variant="h4" sx={{ fontWeight: 800, color, mb: 0.5 }}>
      {value}
    </Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.65)' }}>
      {label}
    </Typography>
  </Box>
)

// Enhanced pricing card
const PricingCard = ({ title, prices, description, isPopular = false, children, onSelect }) => (
  <Card sx={{
    height: '100%',
    position: 'relative',
    background: '#1a1714',
    border: isPopular ? '2px solid #e8b63a' : '1px solid rgba(232,182,58,0.15)',
    borderRadius: 4,
    overflow: 'visible',
    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    '&:hover': {
      transform: 'translateY(-8px) scale(1.02)',
      boxShadow: isPopular
        ? '0 20px 40px rgba(232,182,58,0.25)'
        : '0 20px 40px rgba(232,182,58,0.12)'
    }
  }}>
    {isPopular && (
      <Box sx={{
        position: 'absolute',
        top: -12,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1
      }}>
        <Chip
          label="MÁS POPULAR"
          color="primary"
          size="small"
          icon={<TrendingUp />}
          sx={{
            bgcolor: '#e8b63a',
            color: '#000',
            fontWeight: 800,
            boxShadow: '0 4px 15px rgba(232, 182, 58, 0.4)'
          }}
        />
      </Box>
    )}

    <CardContent sx={{ p: 4, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h4" sx={{ fontWeight: 800, mb: 2, textAlign: 'center', color: '#FFFFFF' }}>
        {title}
      </Typography>

      {children}

      <Typography variant="body2" sx={{ mt: 2, textAlign: 'center', flexGrow: 1, color: 'rgba(255,255,255,0.65)' }}>
        {description}
      </Typography>

      <Button
        variant="contained"
        fullWidth
        size="large"
        onClick={onSelect}
        sx={{
          mt: 3,
          py: 1.5,
          borderRadius: 3,
          fontWeight: 700,
          fontSize: '1.1rem',
          bgcolor: '#e8b63a',
          color: '#000',
          '&:hover': { bgcolor: '#d4a32e' }
        }}
      >
        Seleccionar Plan
      </Button>
    </CardContent>
  </Card>
)

// Testimonial card component
const TestimonialCard = ({ review }) => (
  <Card sx={{
    p: 3,
    borderRadius: 4,
    height: '100%',
    bgcolor: '#1a1714',
    border: '1px solid rgba(232,182,58,0.15)',
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: '0 12px 30px rgba(232,182,58,0.15)'
    }
  }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
      <Avatar sx={{ bgcolor: '#e8b63a', color: '#000', fontWeight: 700 }}>
        {review.name ? review.name.charAt(0).toUpperCase() : '?'}
      </Avatar>
      <Box sx={{ flexGrow: 1 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
          {review.name || 'Cliente Anónimo'}
        </Typography>
        <Rating value={review.rating || 0} readOnly size="small" />
      </Box>
      <Verified sx={{ color: '#e8b63a', fontSize: 20 }} />
    </Box>
    <Typography variant="body2" sx={{
      fontStyle: 'italic',
      lineHeight: 1.6,
      color: 'rgba(255,255,255,0.65)'
    }}>
      "{review.comment || 'Excelente experiencia'}"
    </Typography>
  </Card>
)

export default function ServicesPage() {
  const navigate = useNavigate()
  const [testimonials, setTestimonials] = useState([])
  const [expandedService, setExpandedService] = useState(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)

    // Load testimonials
    const unsubscribe = listenTestimonials((reviews) => {
      const approvedReviews = reviews.filter(review => review.approved === true)
      setTestimonials(approvedReviews.slice(0, 6))
    }, { approvedOnly: true })

    return () => unsubscribe && unsubscribe()
  }, [])

  const handleServiceExpand = (service) => {
    setExpandedService(expandedService === service ? null : service)
  }

  const handleQuickContact = (method) => {
    switch(method) {
      case 'whatsapp':
        window.open(`${CONTACT_INFO.WHATSAPP_URL}?text=Hola! Me gustaría información sobre sus servicios`, '_blank')
        break
      case 'phone':
        window.location.href = `tel:${CONTACT_INFO.WHATSAPP_NUMBER}`
        break
      case 'email':
        window.location.href = 'mailto:Pablospizza.cl@gmail.com'
        break
      default:
        navigate('/agendar')
    }
  }

  return (
    <Box sx={{ background: '#0d0d0d', minHeight: '100vh' }}>
      <SEO
        title="Servicios - Talleres y Pizza Parties"
        description="Conoce nuestros servicios: Pizzeros en Acción (talleres educativos para niños) y Pizza Parties (catering gourmet). Precios desde $9.000 por niño. Santiago, Chile."
        keywords="servicios pizza party Santiago, precios taller pizza niños, catering pizza eventos, pizzeros en acción precios, cumpleaños infantiles pizza"
        url="/servicios"
      />
      {/* Enhanced Hero Section with Glass Morphism */}
      <Box sx={{
        position: 'relative',
        background: '#0d0d0d',
        color: '#FFFFFF',
        py: { xs: 4, md: 6 },
        mb: 6,
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'url("data:image/svg+xml,%3Csvg width="20" height="20" xmlns="http://www.w3.org/2000/svg"%3E%3Cdefs%3E%3Cpattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"%3E%3Cpath d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(232,182,58,0.05)" stroke-width="1"/%3E%3C/pattern%3E%3C/defs%3E%3Crect width="100%25" height="100%25" fill="url(%23grid)" /%3E%3C/svg%3E")',
          opacity: 0.3
        }
      }}>
        <Container maxWidth="xl" sx={{ position: 'relative', zIndex: 1 }}>
          <Fade in={isVisible} timeout={1000}>
            <Box sx={{ textAlign: 'center', maxWidth: '800px', mx: 'auto' }}>
              <Typography
                variant="h1"
                sx={{
                  fontWeight: 900,
                  mb: 3,
                  fontSize: { xs: '2.5rem', md: '4rem' },
                  color: '#FFFFFF'
                }}
              >
                Experiencias Únicas
              </Typography>
              <Typography
                variant="h4"
                sx={{
                  mb: 4,
                  fontWeight: 600,
                  color: 'rgba(255,255,255,0.65)',
                  lineHeight: 1.4
                }}
              >
                Que combinan diversión, aprendizaje y sabores inolvidables
              </Typography>


              {/* Quick Action Buttons */}
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate('/agendar')}
                  endIcon={<ArrowForward />}
                  sx={{
                    bgcolor: '#e8b63a',
                    color: '#000',
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    fontWeight: 700,
                    fontSize: '1.1rem',
                    boxShadow: '0 8px 25px rgba(232,182,58,0.3)',
                    '&:hover': {
                      bgcolor: '#d4a32e',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 12px 35px rgba(232,182,58,0.4)'
                    }
                  }}
                >
                  Agendar Ahora
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => handleQuickContact('whatsapp')}
                  startIcon={<WhatsApp />}
                  sx={{
                    borderColor: '#e8b63a',
                    color: '#e8b63a',
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    fontWeight: 700,
                    fontSize: '1.1rem',
                    borderWidth: 2,
                    '&:hover': {
                      bgcolor: 'rgba(232,182,58,0.1)',
                      borderWidth: 2,
                      transform: 'translateY(-2px)'
                    }
                  }}
                >
                  WhatsApp
                </Button>
              </Box>
            </Box>
          </Fade>
        </Container>
      </Box>

      <Container maxWidth="xl" sx={{ pb: 8 }}>
        {/* Services Section with Bento Grid Layout */}
        <Box sx={{ mb: 10 }}>
          <Typography
            variant="h2"
            align="center"
            sx={{ fontWeight: 800, mb: 2, color: '#FFFFFF' }}
          >
            Nuestros Servicios
          </Typography>
          <Typography
            variant="h6"
            align="center"
            sx={{ mb: 6, maxWidth: '600px', mx: 'auto', color: 'rgba(255,255,255,0.65)' }}
          >
            Selecciona la experiencia perfecta para tu celebración especial
          </Typography>

          <Grid container spacing={4}>
            {/* Pizzeros en Acción - Enhanced Card */}
            <Grid item xs={12} lg={6}>
              <Zoom in={isVisible} timeout={1000}>
                <Card sx={{
                  height: 'auto',
                  minHeight: { xs: '400px', md: '500px', lg: '600px' },
                  borderRadius: 6,
                  overflow: 'visible',
                  position: 'relative',
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    transform: 'translateY(-8px) scale(1.02)',
                    boxShadow: '0 25px 50px rgba(232,182,58,0.15)',
                    border: '1px solid rgba(232,182,58,0.35)'
                  }
                }}>
                  <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                    {/* Service Header */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                      <Badge
                        badgeContent="NUEVO"
                        color="secondary"
                        sx={{
                          '& .MuiBadge-badge': {
                            bgcolor: '#e8b63a',
                            color: '#000',
                            fontWeight: 700
                          }
                        }}
                      >
                        <Avatar sx={{
                          bgcolor: '#e8b63a',
                          color: '#000',
                          width: 56,
                          height: 56,
                          boxShadow: '0 8px 20px rgba(232,182,58,0.3)'
                        }}>
                          <School sx={{ fontSize: 28 }} />
                        </Avatar>
                      </Badge>
                      <Box>
                        <Typography variant="h3" sx={{ fontWeight: 800, color: '#FFFFFF' }}>
                          Pizzeros en Acción
                        </Typography>
                        <Typography variant="subtitle1" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                          Experiencia educativa interactiva
                        </Typography>
                      </Box>
                    </Box>

                    <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, fontSize: '1.1rem', color: 'rgba(255,255,255,0.65)' }}>
                      Los niños se convierten en verdaderos chefs por un día. Aprenden técnicas culinarias básicas mientras se divierten creando sus propias pizzas únicas.
                    </Typography>

                    {/* Features List */}
                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, color: '#e8b63a' }}>
                      Lo que incluye:
                    </Typography>
                    <FeatureBullet delay={0}>Técnicas básicas de panadería y amasado</FeatureBullet>
                    <FeatureBullet delay={1}>Creación de masa desde cero</FeatureBullet>
                    <FeatureBullet delay={2}>Selección libre de ingredientes premium</FeatureBullet>
                    <FeatureBullet delay={3}>Cocción supervisada y degustación</FeatureBullet>
                    <FeatureBullet delay={4}>Certificado personalizado de chef junior</FeatureBullet>

                    {/* Tags */}
                    <Box sx={{ mt: 3, mb: 3 }}>
                      <ModernTag icon={<School />}>Educativo</ModernTag>
                      <ModernTag color="secondary" icon={<Celebration />}>Divertido</ModernTag>
                      <ModernTag color="success" icon={<Verified />}>Seguro</ModernTag>
                      <ModernTag color="info" icon={<Groups />}>Interactivo</ModernTag>
                    </Box>

                    {/* Service Details */}
                    <Paper sx={{
                      p: 2,
                      borderRadius: 3,
                      bgcolor: 'rgba(232,182,58,0.08)',
                      border: '1px solid rgba(232,182,58,0.2)'
                    }}>
                      <Grid container spacing={2}>
                        <Grid item xs={6} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Groups sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' }, color: 'rgba(255,255,255,0.5)' }}>
                                Grupo ideal
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, fontSize: { xs: '0.75rem', sm: '0.875rem' }, color: '#FFFFFF' }}>
                                5-15 niños
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                        <Grid item xs={6} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AccessTime sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' }, color: 'rgba(255,255,255,0.5)' }}>
                                Duración
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, fontSize: { xs: '0.75rem', sm: '0.875rem' }, color: '#FFFFFF' }}>
                                2-3 horas
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Place sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' }, color: 'rgba(255,255,255,0.5)' }}>
                                Ubicación
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, fontSize: { xs: '0.75rem', sm: '0.875rem' }, color: '#FFFFFF' }}>
                                Tu espacio
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                      </Grid>
                    </Paper>

                    {/* Action Buttons */}
                    <Box sx={{ mt: 3, display: 'flex', gap: 1, flexDirection: { xs: 'column', sm: 'row' } }}>
                      <Button
                        variant="contained"
                        fullWidth
                        onClick={() => navigate('/agendar?service=pizzeros')}
                        sx={{
                          bgcolor: '#e8b63a',
                          color: '#000',
                          fontWeight: 700,
                          py: 1.5,
                          '&:hover': { bgcolor: '#d4a32e' }
                        }}
                      >
                        Ver Precios
                      </Button>
                      <Button
                        variant="outlined"
                        fullWidth
                        onClick={() => handleServiceExpand('pizzeros')}
                        endIcon={expandedService === 'pizzeros' ? <ExpandLess /> : <ExpandMore />}
                        sx={{
                          borderColor: '#e8b63a',
                          color: '#e8b63a',
                          fontWeight: 600,
                          py: 1.5,
                          '&:hover': { bgcolor: 'rgba(232,182,58,0.1)' }
                        }}
                      >
                        {expandedService === 'pizzeros' ? 'Menos detalles' : 'Ver detalles'}
                      </Button>
                    </Box>

                    {/* Expandable Details */}
                    <Box sx={{ mt: 2 }}>

                      <Collapse in={expandedService === 'pizzeros'}>
                        <Box sx={{ pt: 2 }}>
                          <Typography variant="body2" sx={{ mb: 2, color: 'rgba(255,255,255,0.65)' }}>
                            <strong>Proceso paso a paso:</strong>
                          </Typography>
                          <Box sx={{ pl: 2, borderLeft: '3px solid #e8b63a' }}>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Bienvenida y explicación del proceso (15 min)
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Preparación de la masa y amasado (30 min)
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Estiramiento y formado de la pizza (20 min)
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Selección y aplicación de ingredientes (15 min)
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Horneado y degustación (45 min)
                            </Typography>
                            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                              • Entrega de certificados y despedida (15 min)
                            </Typography>
                          </Box>
                        </Box>
                      </Collapse>
                    </Box>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>

            {/* Pizza Parties - Enhanced Card */}
            <Grid item xs={12} lg={6}>
              <Zoom in={isVisible} timeout={1200}>
                <Card sx={{
                  height: 'auto',
                  minHeight: { xs: '400px', md: '500px', lg: '600px' },
                  borderRadius: 6,
                  overflow: 'visible',
                  position: 'relative',
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    transform: 'translateY(-8px) scale(1.02)',
                    boxShadow: '0 25px 50px rgba(232,182,58,0.15)',
                    border: '1px solid rgba(232,182,58,0.35)'
                  }
                }}>
                  <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                    {/* Service Header */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                      <Badge
                        badgeContent="PREMIUM"
                        color="primary"
                        sx={{
                          '& .MuiBadge-badge': {
                            bgcolor: '#000',
                            color: '#e8b63a',
                            fontWeight: 700
                          }
                        }}
                      >
                        <Avatar sx={{
                          bgcolor: '#000',
                          color: '#e8b63a',
                          width: 56,
                          height: 56,
                          boxShadow: '0 8px 20px rgba(0,0,0,0.2)'
                        }}>
                          <Celebration sx={{ fontSize: 28 }} />
                        </Avatar>
                      </Badge>
                      <Box>
                        <Typography variant="h3" sx={{ fontWeight: 800, color: '#FFFFFF' }}>
                          Pizza Parties
                        </Typography>
                        <Typography variant="subtitle1" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                          Catering completo y profesional
                        </Typography>
                      </Box>
                    </Box>

                    <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.7, fontSize: '1.1rem', color: 'rgba(255,255,255,0.65)' }}>
                      Servicio completo de catering con pizzas artesanales frescas. Llevamos toda la experiencia gastronómica directamente a tu evento.
                    </Typography>

                    {/* Features List */}
                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, color: '#e8b63a' }}>
                      Lo que incluye:
                    </Typography>
                    <FeatureBullet delay={0}>Pizzas artesanales hechas al momento</FeatureBullet>
                    <FeatureBullet delay={1}>Amplia variedad de sabores gourmet</FeatureBullet>
                    <FeatureBullet delay={2}>Servicio completo en tu ubicación</FeatureBullet>
                    <FeatureBullet delay={3}>Personal especializado y uniformado</FeatureBullet>
                    <FeatureBullet delay={4}>Limpieza total al finalizar</FeatureBullet>

                    {/* Tags */}
                    <Box sx={{ mt: 3, mb: 3 }}>
                      <ModernTag color="secondary" icon={<Restaurant />}>A domicilio</ModernTag>
                      <ModernTag color="success" icon={<LocalOffer />}>Pizzas frescas</ModernTag>
                      <ModernTag color="info" icon={<Verified />}>Servicio completo</ModernTag>
                      <ModernTag color="warning" icon={<Star />}>Personalizable</ModernTag>
                    </Box>

                    {/* Service Details */}
                    <Paper sx={{
                      p: 2,
                      borderRadius: 3,
                      bgcolor: 'rgba(232,182,58,0.08)',
                      border: '1px solid rgba(232,182,58,0.2)'
                    }}>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Groups sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                Grupo ideal
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                                10-50+ personas
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AccessTime sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                Duración
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                                Flexible
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Place sx={{ color: '#e8b63a', fontSize: 20 }} />
                            <Box>
                              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                Ubicación
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                                A elección
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                      </Grid>
                    </Paper>

                    {/* Action Buttons */}
                    <Box sx={{ mt: 3, display: 'flex', gap: 1, flexDirection: { xs: 'column', sm: 'row' } }}>
                      <Button
                        variant="contained"
                        fullWidth
                        onClick={() => navigate('/agendar?service=parties')}
                        sx={{
                          bgcolor: '#e8b63a',
                          color: '#000',
                          fontWeight: 700,
                          py: 1.5,
                          '&:hover': { bgcolor: '#d4a32e' }
                        }}
                      >
                        Ver Precios
                      </Button>
                      <Button
                        variant="outlined"
                        fullWidth
                        onClick={() => handleServiceExpand('parties')}
                        endIcon={expandedService === 'parties' ? <ExpandLess /> : <ExpandMore />}
                        sx={{
                          borderColor: '#e8b63a',
                          color: '#e8b63a',
                          fontWeight: 600,
                          py: 1.5,
                          '&:hover': { bgcolor: 'rgba(232,182,58,0.1)' }
                        }}
                      >
                        {expandedService === 'parties' ? 'Menos detalles' : 'Ver detalles'}
                      </Button>
                    </Box>

                    {/* Expandable Details */}
                    <Box sx={{ mt: 2 }}>

                      <Collapse in={expandedService === 'parties'}>
                        <Box sx={{ pt: 2 }}>
                          <Typography variant="body2" sx={{ mb: 2, color: 'rgba(255,255,255,0.65)' }}>
                            <strong>Sabores disponibles:</strong>
                          </Typography>
                          <Box sx={{ pl: 2, borderLeft: '3px solid #e8b63a' }}>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Margherita clásica con albahaca fresca
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Pepperoni premium con queso mozarella
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Vegetariana con verduras de temporada
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1, color: 'rgba(255,255,255,0.65)' }}>
                              • Hawaiana con jamón y piña natural
                            </Typography>
                            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                              • Opciones personalizadas según preferencias
                            </Typography>
                          </Box>
                        </Box>
                      </Collapse>
                    </Box>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          </Grid>
        </Box>

        {/* Enhanced Pricing Section */}
        <Box sx={{ mb: 10 }}>
          <Typography
            variant="h2"
            align="center"
            sx={{ fontWeight: 800, mb: 2, color: '#FFFFFF' }}
          >
            Planes y Precios
          </Typography>
          <Typography
            variant="h6"
            align="center"
            sx={{ mb: 6, maxWidth: '600px', mx: 'auto', color: 'rgba(255,255,255,0.65)' }}
          >
            Precios transparentes sin sorpresas. Todos incluyen materiales y servicio completo.
          </Typography>

          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <PricingCard
                title="Pizzeros en Acción"
                isPopular={true}
                description="Incluye todos los materiales, ingredientes frescos y certificado personalizado"
                onSelect={() => navigate('/agendar?service=pizzeros')}
              >
                <Box sx={{ mb: 3 }}>
                  {[
                    { range: 'Hasta 10 niños', price: '$13.500', unit: 'por niño', desc: 'Mínimo $135.000' },
                    { range: '11 - 14 niños', price: '$10.500', unit: 'por niño', desc: 'Precio estándar' },
                    { range: '15 - 19 niños', price: '$9.500', unit: 'por niño', desc: 'Precio preferencial' },
                    { range: '20+ niños', price: '$9.000', unit: 'por niño', desc: 'Mejor precio', highlight: true }
                  ].map((tier, index) => (
                    <Paper
                      key={index}
                      sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: 3,
                        bgcolor: tier.highlight ? 'rgba(232,182,58,0.12)' : 'rgba(255,255,255,0.04)',
                        border: tier.highlight ? '2px solid rgba(232,182,58,0.35)' : '1px solid rgba(255,255,255,0.08)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.3s ease',
                        '&:hover': {
                          transform: 'translateX(8px)',
                          boxShadow: '0 4px 15px rgba(232,182,58,0.2)'
                        }
                      }}
                    >
                      <Typography variant="body1" sx={{ fontWeight: 600, color: '#FFFFFF' }}>
                        {tier.range}
                      </Typography>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: '#e8b63a' }}>
                          {tier.price}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                          {tier.unit}
                        </Typography>
                        <Typography variant="caption" sx={{ display: 'block', color: tier.highlight ? '#4CAF50' : 'rgba(255,255,255,0.5)', fontWeight: 600 }}>
                          {tier.desc}
                        </Typography>
                      </Box>
                    </Paper>
                  ))}
                </Box>
              </PricingCard>
            </Grid>

            <Grid item xs={12} md={6}>
              <PricingCard
                title="Pizza Parties"
                description="Mínimo 15 pizzas. 10% de descuento para grupos de 20+ personas"
                onSelect={() => navigate('/agendar?service=parties')}
              >
                <Box sx={{ textAlign: 'center', mb: 4 }}>
                  <Typography variant="h2" sx={{
                    fontWeight: 900,
                    color: '#FFFFFF',
                    mb: 1
                  }}>
                    $11.990
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.65)' }}>
                    CLP por pizza
                  </Typography>

                  <Paper sx={{
                    mt: 3,
                    p: 2,
                    borderRadius: 3,
                    bgcolor: 'rgba(76,175,80,0.1)',
                    border: '1px solid rgba(76,175,80,0.3)'
                  }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#4CAF50' }}>
                      ¡Descuento especial!
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                      10% OFF en pedidos de 20+ pizzas
                    </Typography>
                  </Paper>
                </Box>
              </PricingCard>
            </Grid>
          </Grid>

          {/* Additional Info */}
          <Paper sx={{
            mt: 4,
            p: 3,
            borderRadius: 4,
            bgcolor: 'rgba(232,182,58,0.08)',
            border: '1px solid rgba(232,182,58,0.2)',
            textAlign: 'center'
          }}>
            <Typography variant="body1" sx={{ fontWeight: 600, mb: 1, color: '#FFFFFF' }}>
              Información importante sobre precios
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
              * Comunas como Chicureo, Colina o Talagante tienen un adicional de $20.000 por concepto de traslado.
              Todos los precios incluyen IVA y no tienen costos adicionales ocultos.
            </Typography>
          </Paper>
        </Box>

        {/* Social Proof - Testimonials */}
        {testimonials.length > 0 && (
          <Box sx={{ mb: 10 }}>
            <Typography
              variant="h2"
              align="center"
              sx={{ fontWeight: 800, mb: 2, color: '#FFFFFF' }}
            >
              Lo que dicen nuestros clientes
            </Typography>
            <Typography
              variant="h6"
              align="center"
              sx={{ mb: 6, maxWidth: '600px', mx: 'auto', color: 'rgba(255,255,255,0.65)' }}
            >
              Más de 500 familias felices han confiado en nosotros para sus celebraciones especiales
            </Typography>

            <Grid container spacing={3}>
              {testimonials.map((testimonial, index) => (
                <Grid item xs={12} sm={6} md={4} key={testimonial.id || index}>
                  <Fade in={isVisible} timeout={1000 + (index * 200)}>
                    <div>
                      <TestimonialCard review={testimonial} />
                    </div>
                  </Fade>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Enhanced CTA Section */}
        <Paper sx={{
          p: 6,
          borderRadius: 6,
          textAlign: 'center',
          background: '#141414',
          border: '1px solid rgba(232,182,58,0.25)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <Box sx={{ position: 'relative', zIndex: 1 }}>
            <Typography variant="h3" sx={{ fontWeight: 900, mb: 2, color: '#FFFFFF' }}>
              ¿Listo para crear recuerdos inolvidables?
            </Typography>
            <Typography variant="h6" sx={{ mb: 4, color: 'rgba(255,255,255,0.65)', maxWidth: '600px', mx: 'auto' }}>
              Contáctanos ahora y obtén una cotización personalizada. Te garantizamos una experiencia única que toda la familia recordará para siempre.
            </Typography>

            <Box sx={{
              display: 'flex',
              gap: 3,
              justifyContent: 'center',
              flexWrap: 'wrap',
              mb: 4
            }}>
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/agendar')}
                endIcon={<ArrowForward />}
                sx={{
                  bgcolor: '#e8b63a',
                  color: '#000',
                  px: 4,
                  py: 2,
                  borderRadius: 3,
                  fontWeight: 800,
                  fontSize: '1.2rem',
                  minWidth: '200px',
                  boxShadow: '0 8px 25px rgba(232,182,58,0.3)',
                  '&:hover': {
                    bgcolor: '#d4a32e',
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 35px rgba(232,182,58,0.4)'
                  }
                }}
              >
                Agendar Evento
              </Button>

              <Button
                variant="outlined"
                size="large"
                onClick={() => handleQuickContact('whatsapp')}
                startIcon={<WhatsApp />}
                sx={{
                  borderColor: '#e8b63a',
                  color: '#e8b63a',
                  px: 4,
                  py: 2,
                  borderRadius: 3,
                  fontWeight: 700,
                  fontSize: '1.1rem',
                  minWidth: '180px',
                  borderWidth: 2,
                  '&:hover': {
                    bgcolor: 'rgba(232,182,58,0.1)',
                    borderWidth: 2,
                    transform: 'translateY(-4px)'
                  }
                }}
              >
                WhatsApp
              </Button>
            </Box>

            {/* Quick Contact Options */}
            <Box sx={{
              display: 'flex',
              gap: 4,
              justifyContent: 'center',
              flexWrap: 'wrap',
              color: 'rgba(255,255,255,0.65)'
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Phone sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {CONTACT_INFO.WHATSAPP_DISPLAY}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Email sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Pablospizza.cl@gmail.com
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AccessTime sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Respuesta en menos de 2 horas
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
