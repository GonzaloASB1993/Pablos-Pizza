import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Fade,
  Slide,
  Paper,
  Stack,
  Avatar,
  Rating,
  IconButton,
  Tooltip,
  useMediaQuery,
  alpha,
  Dialog,
  DialogContent
} from '@mui/material'
import {
  Restaurant,
  WhatsApp,
  ArrowForward,
  School,
  Celebration,
  Star,
  PlayArrow,
  LocalPhone,
  AccessTime,
  LocationOn,
  People,
  TrendingUp,
  EmojiEvents,
  Favorite,
  Instagram,
  CheckCircle,
  AutoAwesome,
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Autoplay, Pagination, Navigation } from 'swiper/modules'
import { useInView } from 'react-intersection-observer'
import 'swiper/css'
import 'swiper/css/pagination'
import 'swiper/css/navigation'
import { designTokens } from '../../utils/theme'
import logo from '../../assets/logo.png'
import { listenTestimonials } from '../../services/testimonialsService'

// Event Categories Data
const eventCategories = [
  {
    id: 'corporate',
    title: 'Eventos Corporativos',
    subtitle: 'Team building delicioso y efectivo',
    tag: 'Empresas',
    icon: '💼',
    mainImage: 'https://images.unsplash.com/photo-1511578314322-379afb476865?w=800',
    gallery: [
      'https://images.unsplash.com/photo-1511578314322-379afb476865?w=800',
      'https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=800',
      'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=800'
    ],
    description: 'Actividades de team building únicas donde tu equipo aprende a hacer pizzas artesanales mientras fortalece vínculos. Ideal para empresas que buscan eventos memorables.',
    services: ['Pizza Party', 'Pizzeros en Acción'],
    duration: '2-3 horas',
    capacity: '15-100 personas',
    features: [
      'Chef profesional guiando',
      'Ingredientes premium',
      'Competencias por equipos',
      'Premios y reconocimientos',
      'Show completo'
    ]
  },
  {
    id: 'birthday',
    title: 'Cumpleaños Especiales',
    subtitle: 'Celebraciones únicas e inolvidables',
    tag: 'Cumpleaños',
    icon: '🎂',
    mainImage: 'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800',
    gallery: [
      'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800',
      'https://images.unsplash.com/photo-1464349095431-e9a21285b5f3?w=800',
      'https://images.unsplash.com/photo-1558636508-e0db3814bd1d?w=800'
    ],
    description: 'Fiestas de cumpleaños donde los niños son los protagonistas. Aprenden, juegan y crean sus propias pizzas en una experiencia educativa y deliciosa.',
    services: ['Pizza Party', 'Pizzeros en Acción'],
    duration: '2-3 horas',
    capacity: '10-50 niños',
    features: [
      'Animación incluida',
      'Gorros de chef para todos',
      'Decoración temática',
      'Ingredientes ilimitados',
      'Certificado de chef'
    ]
  },
  {
    id: 'wedding',
    title: 'Matrimonios',
    subtitle: 'Pizza gourmet para tu día especial',
    tag: 'Eventos',
    icon: '💒',
    mainImage: 'https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=800',
    gallery: [
      'https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=800',
      'https://images.unsplash.com/photo-1520854221256-17451cc331bf?w=800',
      'https://images.unsplash.com/photo-1465495976277-4387d4b0b4c6?w=800'
    ],
    description: 'Estación de pizza artesanal para matrimonios. Una opción gourmet y divertida que encanta a todos los invitados.',
    services: ['Pizza Party'],
    duration: 'Flexible',
    capacity: 'Sin límite',
    features: [
      'Menú personalizado',
      'Horno profesional',
      'Pizzeros uniformados',
      'Ingredientes premium',
      'Setup elegante'
    ]
  },
  {
    id: 'school',
    title: 'Talleres Educativos',
    subtitle: 'Niños aprendiendo técnicas culinarias',
    tag: 'Educación',
    icon: '🎓',
    mainImage: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',
    gallery: [
      'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',
      'https://images.unsplash.com/photo-1544025162-d76694265947?w=800',
      'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=800'
    ],
    description: 'Talleres gastronómicos para colegios donde los niños desarrollan habilidades culinarias, trabajan en equipo y aprenden sobre nutrición.',
    services: ['Pizzeros en Acción'],
    duration: '2-3 horas',
    capacity: '15-30 niños',
    features: [
      'Contenido educativo',
      'Certificado para cada niño',
      'Material didáctico',
      'Chef instructor',
      'Seguridad alimentaria'
    ]
  }
]

// Hero Logo 3D con efectos glassmorphism
const Hero3DLogo = ({ prefersReducedMotion, animationsEnabled }) => (
  <Box
    sx={{
      position: 'relative',
      display: 'inline-block',
      perspective: '1000px',
    }}
  >
    {/* Resplandor de fondo */}
    <Box
      sx={{
        position: 'absolute',
        inset: -40,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${designTokens.colors.golden[400]} 0%, ${designTokens.colors.golden[200]}40 40%, transparent 70%)`,
        filter: 'blur(20px)',
        animation: (prefersReducedMotion || !animationsEnabled) ? 'none' : 'glow 4s ease-in-out infinite alternate',
      }}
    />

    {/* Anillo orbital animado */}
    <Box
      sx={{
        position: 'absolute',
        inset: -15,
        borderRadius: '50%',
        border: `3px solid ${designTokens.colors.golden[400]}`,
        borderTop: `3px solid ${designTokens.colors.golden[600]}`,
        animation: (prefersReducedMotion || !animationsEnabled) ? 'none' : 'orbit 20s linear infinite',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: -6,
          right: 10,
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: designTokens.colors.golden[500],
          boxShadow: `0 0 20px ${designTokens.colors.golden[300]}`,
        }
      }}
    />

    {/* Logo principal con glassmorphism */}
    <Box
      component="img"
      src={logo}
      alt="Pablo's Pizza Logo"
      sx={{
        width: '100%',
        maxWidth: { xs: 200, sm: 280, md: 380, lg: 420 },
        aspectRatio: '1',
        borderRadius: '50%',
        objectFit: 'cover',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        border: `4px solid rgba(255, 215, 0, 0.3)`,
        boxShadow: `
          0 25px 50px -12px rgba(0, 0, 0, 0.25),
          0 0 0 1px rgba(255, 215, 0, 0.1),
          inset 0 1px 0 rgba(255, 255, 255, 0.1)
        `,
        filter: 'drop-shadow(0 10px 30px rgba(255, 215, 0, 0.3))',
        transition: 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
        cursor: 'pointer',
        '&:hover': {
          transform: 'rotateY(15deg) rotateX(5deg) scale(1.05)',
          boxShadow: `
            0 35px 70px -12px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(255, 215, 0, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.2),
            0 0 40px rgba(255, 215, 0, 0.4)
          `,
        }
      }}
    />

    <style>{`
      @keyframes glow {
        0%, 100% { opacity: 0.8; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.05); }
      }
      @keyframes orbit {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
    `}</style>
  </Box>
)

// Componente de estadísticas impactantes
const StatsCard = ({ number, label, icon, color = 'golden' }) => (
  <Fade in timeout={1000}>
    <Paper
      elevation={0}
      sx={{
        p: { xs: 1.5, sm: 2 },
        textAlign: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(10px)',
        border: `1px solid rgba(255, 215, 0, 0.2)`,
        borderRadius: designTokens.radius.lg,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          transform: 'translateY(-6px) scale(1.01)',
          backgroundColor: 'rgba(255, 255, 255, 0.15)',
          boxShadow: designTokens.shadows.glowHover,
        }
      }}
    >
      <Box sx={{ mb: { xs: 0.5, sm: 1 } }}>
        {React.cloneElement(icon, {
          sx: {
            fontSize: { xs: 24, sm: 36 },
            color: designTokens.colors.golden[400],
            filter: 'drop-shadow(0 4px 8px rgba(255, 215, 0, 0.3))',
          }
        })}
      </Box>
      <Typography
        variant="h4"
        sx={{
          fontWeight: 700,
          fontSize: { xs: '1.25rem', sm: '2rem' },
          background: designTokens.colors.aurora.golden,
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          mb: 0.5
        }}
      >
        {number}
      </Typography>
      <Typography variant="body2" sx={{
        color: 'rgba(255, 255, 255, 0.9)',
        fontWeight: 500,
        fontSize: { xs: '0.75rem', sm: '0.875rem' }
      }}>
        {label}
      </Typography>
    </Paper>
  </Fade>
)

// Componente de CTA flotante con urgencia
const FloatingCTA = ({ navigate, prefersReducedMotion }) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 2000)
    return () => clearTimeout(timer)
  }, [])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      navigate('/agendar')
    }
  }

  return (
    <Fade in={isVisible}>
      <Paper
        elevation={8}
        role="button"
        tabIndex={0}
        aria-label="Agendar evento ahora - 20% descuento este mes"
        onKeyDown={handleKeyDown}
        sx={{
          position: 'fixed',
          bottom: { xs: 16, sm: 24 },
          right: { xs: 16, sm: 24 },
          p: 2,
          backgroundColor: designTokens.colors.golden[500],
          color: designTokens.colors.charcoal[900],
          borderRadius: designTokens.radius.xl,
          boxShadow: designTokens.shadows.glowHover,
          zIndex: 1000,
          animation: prefersReducedMotion ? 'none' : 'bounce 2s infinite',
          cursor: 'pointer',
          '&:focus-visible': {
            outline: '3px solid #000',
            outlineOffset: '2px',
          },
          '@keyframes bounce': {
            '0%, 20%, 50%, 80%, 100%': { transform: 'translateY(0)' },
            '40%': { transform: 'translateY(-8px)' },
            '60%': { transform: 'translateY(-4px)' },
          }
        }}
        onClick={() => navigate('/agendar')}
      >
        <Stack direction="row" alignItems="center" spacing={2}>
          <Restaurant sx={{ fontSize: 24 }} />
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1 }}>
              ¡Agenda HOY!
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              20% descuento este mes
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Fade>
  )
}

// Componente AnimatedSection con animaciones repetibles
const AnimatedSection = ({ children, delay = 0 }) => {
  const { ref, inView } = useInView({
    threshold: 0.3,
    triggerOnce: false  // Se repite cada vez que entra en viewport
  })

  return (
    <Box
      ref={ref}
      sx={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(50px)',
        transition: `all 0.8s ease-out ${delay}ms`
      }}
    >
      {children}
    </Box>
  )
}

// Event Detail Modal Component
function EventDetailModal({ event, open, onClose }) {
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'))

  if (!event) return null

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={fullScreen}
      PaperProps={{
        sx: {
          borderRadius: fullScreen ? 0 : 3,
          maxHeight: fullScreen ? '100vh' : '90vh'
        }
      }}
      aria-labelledby="event-detail-title"
      aria-describedby="event-detail-description"
    >
      {/* Header con botón cerrar */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          backgroundColor: '#000',
          color: '#FFD700',
          p: 2,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 10
        }}
      >
        <Typography id="event-detail-title" variant="h5" sx={{ fontWeight: 'bold' }}>
          {event.icon} {event.title}
        </Typography>
        <IconButton
          onClick={onClose}
          sx={{ color: '#FFD700' }}
          aria-label="Cerrar modal"
        >
          <CloseIcon />
        </IconButton>
      </Box>

      <DialogContent sx={{ p: 0 }} id="event-detail-description">
        {/* Carousel de imágenes */}
        <Box sx={{ mb: 3 }}>
          <Swiper
            modules={[Autoplay, Pagination, Navigation]}
            spaceBetween={0}
            slidesPerView={1}
            autoplay={{ delay: 4000 }}
            pagination={{ clickable: true }}
            navigation
            loop
            aria-label="Galería de imágenes del evento"
          >
            {event.gallery.map((image, index) => (
              <SwiperSlide key={index}>
                <Box
                  component="img"
                  src={image}
                  alt={`${event.title} ${index + 1}`}
                  sx={{
                    width: '100%',
                    height: '400px',
                    objectFit: 'cover'
                  }}
                />
              </SwiperSlide>
            ))}
          </Swiper>
        </Box>

        {/* Contenido del modal */}
        <Box sx={{ p: 3 }}>
          {/* Descripción */}
          <Typography variant="body1" sx={{ mb: 3, lineHeight: 1.8 }}>
            {event.description}
          </Typography>

          {/* Info rápida */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <Box sx={{ p: 2, backgroundColor: '#FFF9E6', borderRadius: 2 }}>
                <Typography variant="caption" sx={{ color: '#666' }}>
                  Duración
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {event.duration}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ p: 2, backgroundColor: '#FFF9E6', borderRadius: 2 }}>
                <Typography variant="caption" sx={{ color: '#666' }}>
                  Capacidad
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {event.capacity}
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Servicios disponibles */}
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            Servicios Disponibles
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
            {event.services.map((service) => (
              <Chip
                key={service}
                label={service}
                sx={{
                  backgroundColor: '#FFD700',
                  fontWeight: 'bold'
                }}
              />
            ))}
          </Box>

          {/* Features */}
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
            ¿Qué Incluye?
          </Typography>
          <Grid container spacing={1}>
            {event.features.map((feature, index) => (
              <Grid item xs={12} key={index}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircleIcon sx={{ color: '#4CAF50' }} />
                  <Typography variant="body2">{feature}</Typography>
                </Box>
              </Grid>
            ))}
          </Grid>

          {/* CTA */}
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              href="/agendar"
              sx={{
                backgroundColor: '#FFD700',
                color: '#000',
                fontWeight: 'bold',
                px: 6,
                py: 2,
                '&:hover': {
                  backgroundColor: '#FFC700'
                }
              }}
            >
              Cotizar Este Evento
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  )
}

// Event Gallery Section Component
function EventGallerySection({ navigate }) {
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  const { ref, inView } = useInView({
    threshold: 0.2,
    triggerOnce: false
  })

  const handleCardClick = (event) => {
    setSelectedEvent(event)
    setModalOpen(true)
  }

  const handleKeyDown = (e, event) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleCardClick(event)
    }
  }

  return (
    <Box
      ref={ref}
      component="section"
      sx={{
        minHeight: '100vh',
        py: 8,
        backgroundColor: '#F5F5F5',
        display: 'flex',
        alignItems: 'center'
      }}
    >
      <Container maxWidth="lg">
        {/* Header con animación */}
        <Box
          sx={{
            textAlign: 'center',
            mb: 6,
            opacity: inView ? 1 : 0,
            transform: inView ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 0.8s ease-out'
          }}
        >
          <Typography
            variant="h2"
            sx={{
              fontWeight: 'bold',
              color: '#FFD700',
              mb: 2
            }}
          >
            Momentos Mágicos
          </Typography>
          <Typography variant="h6" sx={{ color: '#666' }}>
            Capturamos cada sonrisa, cada momento de aprendizaje y diversión
          </Typography>
        </Box>

        {/* Grid de cards en fila */}
        <Grid container spacing={3}>
          {eventCategories.map((event, index) => (
            <Grid
              item
              xs={12}
              sm={6}
              md={3}
              key={event.id}
              sx={{
                opacity: inView ? 1 : 0,
                transform: inView ? 'translateY(0)' : 'translateY(30px)',
                transition: `all 0.8s ease-out ${index * 0.2}s`
              }}
            >
              <Card
                onClick={() => handleCardClick(event)}
                onKeyDown={(e) => handleKeyDown(e, event)}
                tabIndex={0}
                role="button"
                aria-label={`Ver detalles de ${event.title}: ${event.description}`}
                sx={{
                  height: '400px',
                  position: 'relative',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  borderRadius: 3,
                  transition: 'transform 0.3s ease',
                  '&:hover': {
                    transform: 'scale(1.02)',
                    '& .overlay': {
                      backgroundColor: 'rgba(0,0,0,0.5)'
                    },
                    '& .content': {
                      transform: 'translateY(-10px)'
                    }
                  },
                  '&:focus-visible': {
                    outline: '3px solid #FFD700',
                    outlineOffset: '4px',
                  }
                }}
              >
                {/* Imagen de fondo */}
                <CardMedia
                  component="img"
                  image={event.mainImage}
                  alt={event.title}
                  sx={{
                    position: 'absolute',
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover'
                  }}
                />

                {/* Overlay oscuro para mejor contraste */}
                <Box
                  className="overlay"
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.6)',
                    transition: 'background-color 0.3s ease',
                    zIndex: 1
                  }}
                />

                {/* Contenido con mejor contraste */}
                <CardContent
                  className="content"
                  sx={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    zIndex: 2,
                    color: '#FFF',
                    p: 3,
                    transition: 'transform 0.3s ease'
                  }}
                >
                  <Chip
                    label={event.tag}
                    icon={<span>{event.icon}</span>}
                    sx={{
                      backgroundColor: '#FFD700',
                      color: '#000',
                      fontWeight: 'bold',
                      mb: 2
                    }}
                  />

                  <Typography
                    variant="h4"
                    sx={{
                      fontWeight: 'bold',
                      color: '#FFF',
                      mb: 1,
                      textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
                    }}
                  >
                    {event.title}
                  </Typography>

                  <Typography
                    variant="body1"
                    sx={{
                      color: '#FFF',
                      textShadow: '1px 1px 2px rgba(0,0,0,0.8)'
                    }}
                  >
                    {event.subtitle}
                  </Typography>

                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      mt: 2,
                      color: '#FFD700',
                      fontWeight: 'bold'
                    }}
                  >
                    👆 Click para ver más detalles
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Botón Ver Galería Completa */}
        <Box sx={{ textAlign: 'center', mt: 6 }}>
          <Button
            variant="outlined"
            size="large"
            endIcon={<ArrowForward />}
            onClick={() => navigate('/galeria')}
            sx={{
              borderColor: '#FFD700',
              color: '#FFD700',
              fontWeight: 'bold',
              px: 4,
              py: 1.5,
              '&:hover': {
                borderColor: '#FFD700',
                backgroundColor: 'rgba(255,215,0,0.1)'
              }
            }}
          >
            Ver Galería Completa
          </Button>
        </Box>
      </Container>

      {/* Modal con detalles del evento */}
      <EventDetailModal
        event={selectedEvent}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </Box>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const [heroLoaded, setHeroLoaded] = useState(false)
  const [reviews, setReviews] = useState([])
  const [animationsEnabled, setAnimationsEnabled] = useState(false)
  // Base para assets en carpeta public (compatible con subcarpetas de despliegue)
  const publicBase = (import.meta.env.BASE_URL || '/')

  useEffect(() => {
    setHeroLoaded(true)

    // Progressive animation loading - only enable after page load
    if (!prefersReducedMotion) {
      if (document.readyState === 'complete') {
        setTimeout(() => setAnimationsEnabled(true), 500)
      } else {
        window.addEventListener('load', () => {
          setTimeout(() => setAnimationsEnabled(true), 500)
        })
      }
    }
  }, [prefersReducedMotion])

  // Suscribirse a reseñas aprobadas para la sección de Home
  useEffect(() => {
    const unsub = listenTestimonials((list) => {
      const filtered = (Array.isArray(list) ? list : []).filter((t) => t.approved === true && t.isTest !== true)
      setReviews(filtered)
    }, { approvedOnly: true })
    return () => unsub && unsub()
  }, [])

  // Estadísticas dinámicas de reseñas
  const reviewStats = useMemo(() => {
    const total = reviews.length
    if (total === 0) return { total: 0, avg: 0, roundedAvg: 0 }
    const sum = reviews.reduce((acc, r) => acc + (Number(r.rating) || 0), 0)
    const avg = sum / total
    const roundedAvg = Math.round(avg)
    return { total, avg, roundedAvg }
  }, [reviews])

  // Sanea el comentario para evitar que se muestre "como código" si incluye backticks, bloques o etiquetas HTML
  const sanitizeReviewText = (s) => {
    if (!s) return ''
    let out = String(s)

    // 1) Decodifica entidades HTML comunes primero (por si vienen como texto escapado)
    const entities = {
      '&lt;': '<',
      '&gt;': '>',
      '&amp;': '&',
      '&quot;': '"',
      '&#34;': '"',
      '&#39;': "'",
      '&#x27;': "'",
      '&nbsp;': ' '
    }
    out = out.replace(/(&lt;|&gt;|&amp;|&quot;|&#34;|&#39;|&#x27;|&nbsp;)/g, (m) => entities[m] || m)

    // 2) Remueve bloques de código tipo Markdown ```...``` (cerrados)
    out = out.replace(/```[\s\S]*?```/g, '')
    // 3) Si hay un fence sin cierre, elimina desde el fence al final
    out = out.replace(/```[\s\S]*$/g, '')
    // 4) Remueve backticks sueltos
    out = out.replace(/`+/g, '')
    // 5) Remueve etiquetas <code>, <pre> y cualquier HTML residual
    out = out.replace(/<\/?(code|pre)[^>]*>/gi, '')
    out = out.replace(/<[^>]*>/g, '')
    // 6) Elimina líneas que parecen bloques de código indentados (4 espacios o tab)
    out = out
      .split('\n')
      .filter((line) => !/^\s{4,}|^\t/.test(line))
      .join(' ')

    // 7) Normaliza espacios
    out = out.replace(/\s+/g, ' ').trim()
    return out
  }

  return (
    <>
      {/* Hero Section Premium con Aurora Gradient */}
      <Box
        sx={{
          minHeight: '100vh',
          background: `
            radial-gradient(circle at 20% 20%, ${designTokens.colors.golden[500]}15 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, ${designTokens.colors.golden[400]}10 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, ${designTokens.colors.golden[300]}08 0%, transparent 50%),
            linear-gradient(135deg, #0F0F0F 0%, #1A1A1A 50%, #0F0F0F 100%)
          `,
          color: 'white',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          py: { xs: 8, md: 4 },
        }}
      >
        {/* Elementos decorativos flotantes */}
        <Box
          sx={{
            position: 'absolute',
            top: '10%',
            left: '10%',
            width: 100,
            height: 100,
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 215, 0, 0.05)',
            filter: 'blur(40px)',
            animation: (prefersReducedMotion || !animationsEnabled) ? 'none' : 'float 6s ease-in-out infinite',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: '20%',
            right: '15%',
            width: 150,
            height: 150,
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 215, 0, 0.03)',
            filter: 'blur(60px)',
            animation: (prefersReducedMotion || !animationsEnabled) ? 'none' : 'float 8s ease-in-out infinite reverse',
          }}
        />

        <Container maxWidth="xl">
          <Grid container spacing={6} alignItems="center" sx={{ minHeight: '80vh' }}>
            {/* Contenido textual */}
            <Grid item xs={12} lg={6}>
              <Fade in={heroLoaded} timeout={800}>
                <Box>
                  {/* Badge de nuevo/destacado */}
                  <Slide direction="up" in={heroLoaded} timeout={1000}>
                    <Paper
                      sx={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 1,
                        px: 3,
                        py: 1,
                        mb: 3,
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        backdropFilter: 'blur(10px)',
                        border: `1px solid rgba(255, 215, 0, 0.3)`,
                        borderRadius: designTokens.radius.full,
                        color: designTokens.colors.golden[300],
                      }}
                    >
                      <AutoAwesome sx={{ fontSize: 20 }} />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        ¡Experiencias Premium para Niños!
                      </Typography>
                    </Paper>
                  </Slide>

                  <Typography
                    variant="h1"
                    sx={{
                      fontSize: { xs: '2rem', sm: '2.8rem', md: '4rem', lg: '4.5rem' },
                      fontWeight: 800,
                      lineHeight: { xs: 1.1, sm: 1.2, md: 1.1 },
                      mb: 3,
                      background: `linear-gradient(135deg, #FFFFFF 0%, ${designTokens.colors.golden[300]} 100%)`,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    Talleres de Pizza que
                    <br />
                    <Box
                      component="span"
                      sx={{
                        background: designTokens.colors.aurora.golden,
                        backgroundClip: 'text',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                      }}
                    >
                      Crean Magia ✨
                    </Box>
                  </Typography>

                  <Typography
                    variant="h5"
                    sx={{
                      color: 'rgba(255,255,255,0.9)',
                      mb: 3,
                      fontWeight: 400,
                      lineHeight: 1.4,
                    }}
                  >
                    Experiencias gastronómicas educativas donde los niños aprenden,
                    se divierten y crean recuerdos inolvidables
                  </Typography>

                  {/* Estadísticas rápidas */}
                  <Grid container spacing={3} sx={{ mb: 4 }}>
                    <Grid item xs={6} sm={4}>
                      <StatsCard
                        number="500+"
                        label="Niños Felices"
                        icon={<Favorite />}
                      />
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <StatsCard
                        number="50+"
                        label="Eventos Exitosos"
                        icon={<EmojiEvents />}
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <StatsCard
                        number="5★"
                        label="Calificación"
                        icon={<Star />}
                      />
                    </Grid>
                  </Grid>

                  {/* CTAs principales */}
                  <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    spacing={3}
                    sx={{ mb: 4 }}
                  >
                    <Button
                      variant="contained"
                      size="large"
                      onClick={() => navigate('/agendar')}
                      endIcon={<ArrowForward />}
                      sx={{
                        px: 4,
                        py: 2,
                        fontSize: '1.125rem',
                        fontWeight: 700,
                        background: designTokens.colors.aurora.golden,
                        color: designTokens.colors.charcoal[900],
                        borderRadius: designTokens.radius.xl,
                        boxShadow: designTokens.shadows.glowHover,
                        '&:hover': {
                          transform: 'translateY(-4px) scale(1.02)',
                        },
                      }}
                    >
                      Agendar Evento Ahora
                    </Button>

                    <Button
                      variant="outlined"
                      size="large"
                      onClick={() => navigate('/servicios')}
                      sx={{
                        px: 4,
                        py: 2,
                        fontSize: '1rem',
                        fontWeight: 600,
                        borderWidth: 2,
                        borderColor: 'rgba(255, 255, 255, 0.3)',
                        color: 'rgba(255, 255, 255, 0.9)',
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        backdropFilter: 'blur(10px)',
                        borderRadius: designTokens.radius.xl,
                        '&:hover': {
                          borderColor: designTokens.colors.golden[400],
                          backgroundColor: 'rgba(255, 215, 0, 0.1)',
                          color: designTokens.colors.golden[300],
                          transform: 'translateY(-2px)',
                        },
                      }}
                    >
                      Ver Servicios
                    </Button>
                  </Stack>

                  {/* Contacto rápido */}
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                      O contáctanos directo:
                    </Typography>
                    <Tooltip title="WhatsApp: +56 9 8942 4566">
                      <IconButton
                        href="https://wa.me/56989424566"
                        target="_blank"
                        sx={{
                          backgroundColor: 'rgba(37, 211, 102, 0.2)',
                          color: '#25D366',
                          '&:hover': {
                            backgroundColor: 'rgba(37, 211, 102, 0.3)',
                            transform: 'scale(1.1)',
                          },
                        }}
                      >
                        <WhatsApp />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Llámanos: +56 9 8942 4566">
                      <IconButton
                        href="tel:+56989424566"
                        sx={{
                          backgroundColor: 'rgba(255, 215, 0, 0.2)',
                          color: designTokens.colors.golden[400],
                          '&:hover': {
                            backgroundColor: 'rgba(255, 215, 0, 0.3)',
                            transform: 'scale(1.1)',
                          },
                        }}
                      >
                        <LocalPhone />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              </Fade>
            </Grid>

            {/* Logo 3D animado */}
            <Grid item xs={12} lg={6}>
              <Box sx={{ textAlign: 'center', position: 'relative' }}>
                <Fade in={heroLoaded} timeout={prefersReducedMotion ? 0 : 1200}>
                  <Box>
                    <Hero3DLogo prefersReducedMotion={prefersReducedMotion} animationsEnabled={animationsEnabled} />
                  </Box>
                </Fade>
              </Box>
            </Grid>
          </Grid>
        </Container>

        {/* Indicador de scroll */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 32,
            left: '50%',
            transform: 'translateX(-50%)',
            animation: prefersReducedMotion ? 'none' : 'bounce 2s infinite',
          }}
          aria-label="Desliza hacia abajo para ver más contenido"
        >
          <Box
            sx={{
              width: 2,
              height: 40,
              backgroundColor: 'rgba(255, 215, 0, 0.5)',
              borderRadius: 1,
              position: 'relative',
              '&::after': {
                content: '""',
                position: 'absolute',
                bottom: 0,
                left: -4,
                width: 10,
                height: 10,
                borderLeft: '2px solid rgba(255, 215, 0, 0.7)',
                borderBottom: '2px solid rgba(255, 215, 0, 0.7)',
                transform: 'rotate(-45deg)',
              }
            }}
          />
        </Box>

        {/* Animaciones CSS adicionales */}
        <style>{`
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-20px); }
          }
          @keyframes bounce {
            0%, 20%, 50%, 80%, 100% { transform: translateX(-50%) translateY(0); }
            40% { transform: translateX(-50%) translateY(-10px); }
            60% { transform: translateX(-50%) translateY(-5px); }
          }
        `}</style>
      </Box>

      {/* SECCIÓN 1: PIZZEROS EN ACCIÓN - Imagen Full con Gradiente */}
      <AnimatedSection>
        <Box
          component="section"
          sx={{
            minHeight: '100vh',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#FFFFFF',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* IMAGEN DE FONDO - Cubre lado derecho */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: { xs: '0%', md: '55%' },
              backgroundImage: `url(${publicBase}images/talleres/taller-corporativo.jpg)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center left',
              zIndex: 0,
              display: { xs: 'none', md: 'block' }
            }}
          />

          {/* GRADIENTE DE DIFUMINADO */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: { xs: '0%', md: '55%' },
              background: 'linear-gradient(to right, rgba(255,255,255,1) 0%, rgba(255,255,255,0.4) 40%, rgba(255,255,255,0) 100%)',
              zIndex: 1,
              display: { xs: 'none', md: 'block' }
            }}
          />

          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2, py: 8 }}>
            <Grid container spacing={4} alignItems="center">
              {/* Columna izquierda: Contenido de texto */}
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: '50%',
                      backgroundColor: '#FFD700',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <School sx={{ fontSize: 42, color: '#000' }} />
                  </Box>
                  <Box>
                    <Typography variant="h2" sx={{ color: '#000', fontWeight: 'bold', fontSize: { xs: '1.75rem', md: '2.25rem' } }}>
                      Pizzeros en Acción
                    </Typography>
                    <Chip label="EXPERIENCIA EDUCATIVA" sx={{ backgroundColor: '#FFD700', color: '#000', fontWeight: 700, mt: 1 }} />
                  </Box>
                </Box>

                <Typography variant="body1" sx={{ color: '#000', mb: 3, lineHeight: 1.7, fontSize: { xs: '1rem', md: '1.1rem' } }}>
                  <span style={{ color: '#FFD700', fontWeight: 700 }}>Talleres gastronómicos únicos</span> donde los niños se transforman en verdaderos chefs profesionales.
                  Aprenden técnicas culinarias auténticas mientras crean pizzas artesanales con ingredientes de primera calidad.
                </Typography>

                <Box sx={{ mb: 4 }}>
                  <Stack spacing={1.5}>
                    {[
                      '🎓 Educación culinaria profesional',
                      '👨‍🍳 Chef experto guiando cada paso',
                      '🎪 Interactivo y divertido para todas las edades',
                      '🛡️ 100% seguro con protocolos de higiene'
                    ].map((feature, idx) => (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CheckCircle sx={{ color: '#4CAF50', fontSize: 24 }} />
                        <Typography variant="body1" sx={{ color: '#000', fontWeight: 500 }}>
                          {feature}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>

                <Box
                  sx={{
                    p: 3,
                    background: 'rgba(255, 215, 0, 0.1)',
                    border: '2px solid #FFD700',
                    borderRadius: 2,
                    mb: 3
                  }}
                >
                  <Typography variant="h3" sx={{ color: '#FFD700', fontWeight: 900 }}>
                    $13.500 <Typography component="span" variant="body1" sx={{ color: '#000' }}>por niño</Typography>
                  </Typography>
                  <Typography sx={{ color: '#000', fontWeight: 600, mt: 1 }}>
                    ⭐ Descuentos: 10% +15 niños • 15% +25 niños
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate('/agendar')}
                    sx={{
                      backgroundColor: '#FFD700',
                      color: '#000',
                      fontWeight: 700,
                      px: 4,
                      py: 1.5,
                      '&:hover': { backgroundColor: '#FFC700' }
                    }}
                  >
                    Cotizar Evento
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => navigate('/servicios')}
                    sx={{
                      borderColor: '#000',
                      color: '#000',
                      borderWidth: 2,
                      px: 4,
                      py: 1.5,
                      '&:hover': { borderColor: '#FFD700', color: '#FFD700', borderWidth: 2 }
                    }}
                  >
                    Ver Menú
                  </Button>
                </Box>
              </Grid>

              {/* Columna derecha: Imagen (solo mobile) */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'block', md: 'none' } }}>
                <Box
                  component="img"
                  src={`${publicBase}images/talleres/taller-corporativo.jpg`}
                  alt="Niños en taller de pizza"
                  sx={{
                    width: '100%',
                    height: '280px',
                    objectFit: 'cover',
                    borderRadius: 2,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
                  }}
                />
              </Grid>

              {/* Columna derecha: Espacio vacío (desktop - imagen está como fondo) */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'none', md: 'block' } }}>
                {/* Espacio reservado para la imagen de fondo con gradiente */}
              </Grid>
            </Grid>
          </Container>
        </Box>
      </AnimatedSection>

      {/* SECCIÓN 2: PIZZA PARTY - Imagen Full con Gradiente */}
      <AnimatedSection delay={200}>
        <Box
          component="section"
          sx={{
            minHeight: '100vh',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#000000',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* IMAGEN DE FONDO - Cubre lado izquierdo */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              bottom: 0,
              width: { xs: '0%', md: '55%' },
              backgroundImage: `url(${publicBase}images/pizza-party.png)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center right',
              zIndex: 0,
              display: { xs: 'none', md: 'block' }
            }}
          />

          {/* GRADIENTE DE DIFUMINADO */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              bottom: 0,
              width: { xs: '0%', md: '55%' },
              background: 'linear-gradient(to left, rgba(0,0,0,1) 0%, rgba(0,0,0,0.4) 40%, rgba(0,0,0,0) 100%)',
              zIndex: 1,
              display: { xs: 'none', md: 'block' }
            }}
          />

          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2, py: 8 }}>
            <Grid container spacing={4} alignItems="center">
              {/* Columna izquierda: Imagen (solo mobile) */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'block', md: 'none' } }}>
                <Box
                  component="img"
                  src={`${publicBase}images/pizza-party.png`}
                  alt="Fiesta de pizza"
                  sx={{
                    width: '100%',
                    height: '280px',
                    objectFit: 'cover',
                    borderRadius: 2,
                    boxShadow: '0 8px 32px rgba(255,215,0,0.3)'
                  }}
                />
              </Grid>

              {/* Columna izquierda: Espacio vacío (desktop - imagen está como fondo) */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'none', md: 'block' } }}>
                {/* Espacio reservado para la imagen de fondo con gradiente */}
              </Grid>

              {/* Columna derecha: Contenido de texto */}
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <Box
                    sx={{
                      width: 80,
                      height: 80,
                      borderRadius: '50%',
                      backgroundColor: '#FFD700',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <Celebration sx={{ fontSize: 42, color: '#000' }} />
                  </Box>
                  <Box>
                    <Typography variant="h2" sx={{ color: '#FFF', fontWeight: 'bold', fontSize: { xs: '1.75rem', md: '2.25rem' } }}>
                      Pizza Party
                    </Typography>
                    <Chip label="CATERING GOURMET" sx={{ backgroundColor: '#FFD700', color: '#000', fontWeight: 700, mt: 1 }} />
                  </Box>
                </Box>

                <Typography variant="body1" sx={{ color: '#FFF', mb: 3, lineHeight: 1.7, fontSize: { xs: '1rem', md: '1.1rem' } }}>
                  <span style={{ color: '#FFD700', fontWeight: 700 }}>Catering gourmet especializado</span> en pizzas artesanales para eventos únicos y memorables.
                  Servicio integral con preparación en vivo e ingredientes de primera calidad para hacer de tu celebración algo extraordinario.
                </Typography>

                <Box
                  sx={{
                    p: 3,
                    background: 'rgba(255, 215, 0, 0.1)',
                    border: '2px solid #FFD700',
                    borderRadius: 2,
                    mb: 3
                  }}
                >
                  <Typography variant="h3" sx={{ color: '#FFD700', fontWeight: 900 }}>
                    $11.990 <Typography component="span" variant="body1" sx={{ color: '#FFF' }}>por persona</Typography>
                  </Typography>
                  <Typography sx={{ color: '#FFF', fontWeight: 600, mt: 1 }}>
                    ⭐ Mínimo 15 personas • Descuentos garantizados
                  </Typography>
                </Box>

                <Box sx={{ mb: 4 }}>
                  <Stack spacing={1.5}>
                    {[
                      '🎉 Catering premium todo incluido',
                      '🍕 Preparación en vivo espectacular',
                      '✨ Ingredientes gourmet importados',
                      '🎊 Atención personalizada garantizada'
                    ].map((feature, idx) => (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CheckCircle sx={{ color: '#4CAF50', fontSize: 24 }} />
                        <Typography variant="body1" sx={{ color: '#FFF', fontWeight: 500 }}>
                          {feature}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>

                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate('/agendar')}
                    sx={{
                      backgroundColor: '#FFD700',
                      color: '#000',
                      fontWeight: 700,
                      px: 4,
                      py: 1.5,
                      '&:hover': { backgroundColor: '#FFC700' }
                    }}
                  >
                    Cotizar Evento
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => navigate('/servicios')}
                    sx={{
                      borderColor: '#FFD700',
                      color: '#FFD700',
                      borderWidth: 2,
                      px: 4,
                      py: 1.5,
                      '&:hover': { borderColor: '#FFC700', color: '#FFC700', borderWidth: 2 }
                    }}
                  >
                    Ver Menú
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Container>
        </Box>
      </AnimatedSection>

      {/* Testimonios Premium con Carousel */}
      <AnimatedSection delay={400}>
        <Box
          component="section"
          sx={{
            minHeight: '100vh',
            backgroundColor: '#000',
            py: 8,
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <Container maxWidth="lg">
            <Box sx={{ textAlign: 'center', mb: 6 }}>
              <Typography variant="h2" sx={{ color: '#FFD700', fontWeight: 900, mb: 3, fontSize: { xs: '2rem', md: '3rem' } }}>
                Lo que Dicen Nuestros Clientes
              </Typography>
              <Stack direction="row" spacing={3} justifyContent="center" alignItems="center">
                <Box sx={{ textAlign: 'center' }}>
                  <Rating value={reviewStats.roundedAvg} readOnly sx={{ color: '#FFD700', mb: 1 }} />
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#FFF' }}>
                    {reviewStats.avg.toFixed(1)} / 5.0
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                    Promedio de reseñas
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#FFD700' }}>
                    {reviewStats.total}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                    Reseña{reviewStats.total === 1 ? '' : 's'} verificadas
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Swiper
              modules={[Autoplay, Pagination, Navigation]}
              spaceBetween={30}
              slidesPerView={1}
              breakpoints={{
                640: { slidesPerView: 2 },
                1024: { slidesPerView: 3 }
              }}
              autoplay={{
                delay: 5000,
                disableOnInteraction: false
              }}
              pagination={{ clickable: true }}
              navigation
              loop={reviews.length >= 3}
              style={{ paddingBottom: '50px' }}
            >
              {reviews.map((t, index) => (
                <SwiperSlide key={t.id || `${t.name}-${index}`}>
                  <Card
                    sx={{
                      backgroundColor: '#FFFFFF',
                      color: '#000',
                      height: '280px',
                      p: 3,
                      border: '2px solid rgba(255, 215, 0, 0.3)',
                      borderRadius: 2,
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        borderColor: '#FFD700',
                        transform: 'translateY(-8px)',
                        boxShadow: '0 8px 32px rgba(255, 215, 0, 0.4)'
                      }
                    }}
                  >
                    <CardContent sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                        <Avatar
                          sx={{
                            width: 48,
                            height: 48,
                            backgroundColor: '#FFD700',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            color: '#000'
                          }}
                        >
                          {t.name?.charAt(0) || 'U'}
                        </Avatar>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                            {t.name || 'Cliente'}
                          </Typography>
                        </Box>
                        <Rating
                          value={Number(t.rating) || 0}
                          readOnly
                          size="small"
                          sx={{ color: '#FFD700' }}
                        />
                      </Box>

                      <Typography
                        variant="body2"
                        sx={{
                          fontStyle: 'italic',
                          lineHeight: 1.6,
                          color: '#333',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 6,
                          WebkitBoxOrient: 'vertical',
                          flex: 1
                        }}
                      >
                        "{sanitizeReviewText(t.comment || t.text || '')}"
                      </Typography>
                    </CardContent>
                  </Card>
                </SwiperSlide>
              ))}
            </Swiper>

            <Box sx={{ textAlign: 'center', mt: 6 }}>
              <Button
                variant="outlined"
                onClick={() => navigate('/testimonios')}
                endIcon={<ArrowForward />}
                size="large"
                sx={{
                  px: 4,
                  borderColor: '#FFD700',
                  color: '#FFD700',
                  borderWidth: 2,
                  '&:hover': {
                    borderColor: '#FFC700',
                    color: '#FFC700',
                    borderWidth: 2
                  }
                }}
              >
                Ver Más Testimonios
              </Button>
            </Box>
          </Container>

          {/* CSS para personalizar Swiper */}
          <style>{`
            .swiper-button-next,
            .swiper-button-prev {
              color: #FFD700 !important;
            }
            .swiper-pagination-bullet {
              background: #FFD700 !important;
            }
            .swiper-pagination-bullet-active {
              background: #FFD700 !important;
            }
          `}</style>
        </Box>
      </AnimatedSection>

      {/* Galería Visual Moderna - Nueva Sección Interactiva */}
      <EventGallerySection navigate={navigate} />

      {/* CTA Final Premium */}
      <Box
        sx={{
          background: designTokens.colors.aurora.golden,
          color: designTokens.colors.charcoal[900],
          py: { xs: 8, md: 12 },
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Elementos decorativos */}
        <Box
          sx={{
            position: 'absolute',
            top: -50,
            right: -50,
            width: 200,
            height: 200,
            borderRadius: '50%',
            backgroundColor: 'rgba(0, 0, 0, 0.05)',
            filter: 'blur(40px)',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -30,
            left: -30,
            width: 150,
            height: 150,
            borderRadius: '50%',
            backgroundColor: 'rgba(0, 0, 0, 0.03)',
            filter: 'blur(30px)',
          }}
        />

        <Container maxWidth="lg" sx={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <Typography variant="h2" gutterBottom sx={{ fontWeight: 800, mb: 3 }}>
            ¿Listo para Crear Recuerdos Mágicos? ✨
          </Typography>
          <Typography variant="h5" sx={{ mb: 4, opacity: 0.9, maxWidth: 700, mx: 'auto' }}>
            Agenda tu taller de pizza o pizza party hoy mismo. Nuestro equipo de chefs expertos
            está listo para hacer de tu evento algo verdaderamente especial.
          </Typography>

          {/* Stats rápidas */}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={4}
            justifyContent="center"
            sx={{ mb: 6 }}
          >
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                24h
              </Typography>
              <Typography variant="body1" sx={{ opacity: 0.8 }}>
                Respuesta garantizada
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                100%
              </Typography>
              <Typography variant="body1" sx={{ opacity: 0.8 }}>
                Satisfacción garantizada
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                500+
              </Typography>
              <Typography variant="body1" sx={{ opacity: 0.8 }}>
                Familias felices
              </Typography>
            </Box>
          </Stack>

          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={3}
            justifyContent="center"
            sx={{ mb: 4 }}
          >
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/agendar')}
              endIcon={<Restaurant />}
              sx={{
                px: 6,
                py: 2.5,
                fontSize: '1.2rem',
                fontWeight: 700,
                backgroundColor: designTokens.colors.charcoal[900],
                color: 'white',
                borderRadius: designTokens.radius.xl,
                boxShadow: designTokens.shadows.large,
                '&:hover': {
                  backgroundColor: designTokens.colors.charcoal[800],
                  transform: 'translateY(-4px)',
                },
              }}
            >
              Agendar Evento Ahora
            </Button>

            <Button
              variant="outlined"
              size="large"
              href="https://wa.me/56989424566"
              target="_blank"
              startIcon={<WhatsApp />}
              sx={{
                px: 6,
                py: 2.5,
                fontSize: '1rem',
                fontWeight: 600,
                borderWidth: 2,
                borderColor: designTokens.colors.charcoal[700],
                color: designTokens.colors.charcoal[900],
                borderRadius: designTokens.radius.xl,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.1)',
                  transform: 'translateY(-2px)',
                },
              }}
            >
              Chat por WhatsApp
            </Button>
          </Stack>

          <Typography variant="body2" sx={{ opacity: 0.7 }}>
            📞 +56 9 8942 4566 | 🕒 Lun-Dom 9:00-20:00 | 📍 Santiago y alrededores
          </Typography>
        </Container>
      </Box>

      {/* Floating CTA */}
      <FloatingCTA navigate={navigate} prefersReducedMotion={prefersReducedMotion} />
    </>
  )
}
