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
  alpha
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
  AutoAwesome
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { designTokens } from '../../utils/theme'
import logo from '../../assets/logo.png'
import { listenTestimonials } from '../../services/testimonialsService'

// Hero Logo 3D con efectos glassmorphism
const Hero3DLogo = () => (
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
        animation: 'glow 4s ease-in-out infinite alternate',
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
        animation: 'orbit 20s linear infinite',
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
const FloatingCTA = ({ navigate }) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 2000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <Fade in={isVisible}>
      <Paper
        elevation={8}
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
          animation: 'bounce 2s infinite',
          cursor: 'pointer',
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

export default function HomePage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [heroLoaded, setHeroLoaded] = useState(false)
  const [reviews, setReviews] = useState([])
  // Base para assets en carpeta public (compatible con subcarpetas de despliegue)
  const publicBase = (import.meta.env.BASE_URL || '/')

  useEffect(() => {
    setHeroLoaded(true)
  }, [])

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
            animation: 'float 6s ease-in-out infinite',
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
            animation: 'float 8s ease-in-out infinite reverse',
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
                <Fade in={heroLoaded} timeout={1200}>
                  <Box>
                    <Hero3DLogo />
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
            animation: 'bounce 2s infinite',
          }}
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

      {/* Servicios en Bento Grid Moderno */}
      <Container maxWidth="xl" sx={{ py: { xs: 8, md: 12 } }}>
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography
            variant="h2"
            sx={{
              mb: 3,
              background: designTokens.colors.aurora.golden,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Nuestros Servicios
          </Typography>
          <Typography
            variant="h6"
            color="text.secondary"
            sx={{ maxWidth: 600, mx: 'auto' }}
          >
            Experiencias únicas diseñadas para crear momentos mágicos y educativos
          </Typography>
        </Box>

        {/* Bento Grid Layout */}
        <Grid container spacing={4}>
          {/* Pizzeros en Acción - ahora 50% */}
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                height: { xs: 550, sm: 480, md: 400 },
                background: `linear-gradient(135deg, ${designTokens.colors.golden[50]} 0%, ${designTokens.colors.golden[100]} 100%)`,
                position: 'relative',
                overflow: 'hidden',
                border: `2px solid ${designTokens.colors.golden[200]}`,
                '&:hover': {
                  transform: 'translateY(-8px)',
                  boxShadow: `0 20px 60px rgba(255, 215, 0, 0.3)`,
                  transition: 'all 0.4s ease-in-out',
                }
              }}
            >
              {/* Elementos decorativos mejorados */}
              <Box
                sx={{
                  position: 'absolute',
                  top: -40,
                  right: -40,
                  width: 120,
                  height: 120,
                  borderRadius: '50%',
                  background: `radial-gradient(circle, ${designTokens.colors.golden[300]}60 0%, transparent 70%)`,
                  opacity: 0.8,
                  animation: 'float 6s ease-in-out infinite',
                  '@keyframes float': {
                    '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
                    '50%': { transform: 'translateY(-20px) rotate(180deg)' }
                  }
                }}
              />

              <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: { xs: 2.5, sm: 3, md: 4 }, position: 'relative', zIndex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <Avatar
                    sx={{
                      width: { xs: 56, sm: 64, md: 72 },
                      height: { xs: 56, sm: 64, md: 72 },
                      backgroundColor: designTokens.colors.golden[500],
                      color: designTokens.colors.charcoal[900],
                      boxShadow: '0 8px 32px rgba(255, 215, 0, 0.4)',
                    }}
                  >
                    <School sx={{ fontSize: 36 }} />
                  </Avatar>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 800, color: designTokens.colors.charcoal[900], fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2rem' } }}>
                      Pizzeros en Acción
                    </Typography>
                    <Typography variant="subtitle1" sx={{ color: designTokens.colors.golden[700], fontWeight: 600 }}>
                      🏆 Experiencia Educativa Premium
                    </Typography>
                  </Box>
                </Box>

                <Typography
                  variant="body1"
                  sx={{ mb: 3, lineHeight: 1.8, color: designTokens.colors.charcoal[700], fontSize: { xs: '1rem', md: '1.1rem' } }}
                >
                  <strong>Talleres gastronómicos únicos</strong> donde los niños se convierten en verdaderos chefs.
                  Aprenden técnicas culinarias, desarrollan habilidades motoras y trabajan en equipo
                  mientras crean pizzas artesanales con ingredientes premium.
                </Typography>

                {/* Información de precios destacada */}
                <Box
                  sx={{
                    p: 2,
                    backgroundColor: alpha(designTokens.colors.golden[200], 0.3),
                    borderRadius: designTokens.radius.lg,
                    mb: 3,
                    border: `1px solid ${designTokens.colors.golden[300]}`
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600, color: designTokens.colors.charcoal[800] }}>
                    💰 Desde $13.500 por niño • Descuentos por grupo
                  </Typography>
                  <Typography variant="caption" sx={{ color: designTokens.colors.charcoal[600] }}>
                    10% desc. +15 niños • 15% desc. +25 niños
                  </Typography>
                </Box>

                <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mb: 3 }}>
                  {[
                    { icon: '🎓', text: 'Educativo' },
                    { icon: '👨‍🍳', text: 'Chef Experto' },
                    { icon: '🎪', text: 'Interactivo' },
                    { icon: '🛡️', text: '100% Seguro' }
                  ].map((tag) => (
                    <Chip
                      key={tag.text}
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <span>{tag.icon}</span>
                          <span>{tag.text}</span>
                        </Box>
                      }
                      variant="outlined"
                      sx={{
                        borderColor: designTokens.colors.golden[400],
                        color: designTokens.colors.golden[700],
                        fontWeight: 600,
                        backgroundColor: alpha(designTokens.colors.golden[100], 0.5),
                      }}
                    />
                  ))}
                </Stack>

                <Stack direction="row" spacing={2} sx={{ mt: 'auto' }}>
                  <Button
                    variant="contained"
                    onClick={() => navigate('/agendar')}
                    startIcon={<Restaurant />}
                    sx={{
                      background: designTokens.colors.aurora.golden,
                      color: designTokens.colors.charcoal[900],
                      fontWeight: 700,
                      px: 3,
                      py: 1.5,
                      '&:hover': {
                        background: designTokens.colors.golden[600],
                        transform: 'scale(1.05)',
                      }
                    }}
                  >
                    ¡Reservar Ya!
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/servicios')}
                    endIcon={<ArrowForward />}
                    sx={{
                      borderColor: designTokens.colors.golden[500],
                      color: designTokens.colors.golden[800],
                      fontWeight: 700,
                      borderWidth: 2,
                      '&:hover': {
                        borderColor: designTokens.colors.golden[600],
                        backgroundColor: alpha(designTokens.colors.golden[100], 0.3),
                        transform: 'scale(1.02)',
                      }
                    }}
                  >
                    Ver Detalles
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Pizza Party - ahora con estilo amarillo consistente */}
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                height: { xs: 550, sm: 480, md: 400 },
                background: `linear-gradient(135deg, ${designTokens.colors.golden[100]} 0%, ${designTokens.colors.golden[50]} 100%)`,
                color: designTokens.colors.charcoal[900],
                position: 'relative',
                overflow: 'hidden',
                border: `2px solid ${designTokens.colors.golden[200]}`,
                '&:hover': {
                  transform: 'translateY(-8px)',
                  boxShadow: `0 20px 60px rgba(255, 215, 0, 0.3)`,
                  transition: 'all 0.4s ease-in-out',
                }
              }}
            >
              {/* Elementos decorativos mejorados */}
              <Box
                sx={{
                  position: 'absolute',
                  top: -30,
                  right: -30,
                  width: 140,
                  height: 140,
                  borderRadius: '50%',
                  background: `conic-gradient(${designTokens.colors.golden[300]}40 0deg, transparent 120deg, ${designTokens.colors.golden[200]}20 240deg, transparent 360deg)`,
                  opacity: 0.7,
                  animation: 'spin 20s linear infinite',
                  '@keyframes spin': {
                    '0%': { transform: 'rotate(0deg)' },
                    '100%': { transform: 'rotate(360deg)' }
                  }
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  bottom: -40,
                  left: -40,
                  width: 160,
                  height: 160,
                  borderRadius: '50%',
                  background: `radial-gradient(circle, ${designTokens.colors.golden[200]}25 0%, transparent 60%)`,
                  opacity: 0.5,
                  animation: 'pulse 4s ease-in-out infinite',
                  '@keyframes pulse': {
                    '0%, 100%': { transform: 'scale(1)' },
                    '50%': { transform: 'scale(1.1)' }
                  }
                }}
              />

              <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: { xs: 2.5, sm: 3, md: 4 }, position: 'relative', zIndex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <Avatar
                    sx={{
                      width: { xs: 56, sm: 64, md: 72 },
                      height: { xs: 56, sm: 64, md: 72 },
                      backgroundColor: designTokens.colors.golden[500],
                      color: designTokens.colors.charcoal[900],
                      boxShadow: '0 8px 32px rgba(255, 215, 0, 0.4)',
                    }}
                  >
                    <Celebration sx={{ fontSize: 36 }} />
                  </Avatar>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 800, color: designTokens.colors.charcoal[900], fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2rem' } }}>
                      Pizza Parties
                    </Typography>
                    <Typography variant="subtitle1" sx={{ color: designTokens.colors.golden[700], fontWeight: 600 }}>
                      🌟 Celebraciones Memorables
                    </Typography>
                  </Box>
                </Box>

                <Typography
                  variant="body1"
                  sx={{ mb: 3, lineHeight: 1.8, color: designTokens.colors.charcoal[700], fontSize: { xs: '1rem', md: '1.1rem' } }}
                >
                  <strong>Catering gourmet especializado</strong> en pizzas artesanales para eventos únicos.
                  Servicio integral que incluye preparación en vivo, ingredientes premium y
                  atención personalizada para hacer de tu celebración algo extraordinario.
                </Typography>

                {/* Información de precios destacada */}
                <Box
                  sx={{
                    p: 2,
                    backgroundColor: alpha(designTokens.colors.golden[200], 0.3),
                    borderRadius: designTokens.radius.lg,
                    mb: 3,
                    border: `1px solid ${designTokens.colors.golden[300]}`
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600, color: designTokens.colors.charcoal[800] }}>
                    💰 Desde $11.990 por persona • Min. 15 personas
                  </Typography>
                  <Typography variant="caption" sx={{ color: designTokens.colors.charcoal[600] }}>
                    10% desc. +20 personas • Incluye preparación en vivo
                  </Typography>
                </Box>

                {/* Tags estilo premium mejorado */}
                <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
                  {[
                    { icon: '🎉', text: 'Premium' },
                    { icon: '🍕', text: 'En Vivo' },
                    { icon: '✨', text: 'Gourmet' },
                    { icon: '🎊', text: 'Todo Incluido' }
                  ].map((tag) => (
                    <Chip
                      key={tag.text}
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <span>{tag.icon}</span>
                          <span>{tag.text}</span>
                        </Box>
                      }
                      variant="outlined"
                      sx={{
                        borderColor: designTokens.colors.golden[400],
                        color: designTokens.colors.golden[700],
                        fontWeight: 600,
                        backgroundColor: alpha(designTokens.colors.golden[100], 0.5),
                      }}
                    />
                  ))}
                </Stack>

                <Stack direction="row" spacing={2} sx={{ mt: 'auto' }}>
                  <Button
                    variant="contained"
                    onClick={() => navigate('/agendar')}
                    startIcon={<Restaurant />}
                    sx={{
                      background: designTokens.colors.aurora.golden,
                      color: designTokens.colors.charcoal[900],
                      fontWeight: 700,
                      px: 3,
                      py: 1.5,
                      '&:hover': {
                        background: designTokens.colors.golden[600],
                        transform: 'scale(1.05)',
                      }
                    }}
                  >
                    ¡Cotizar Ya!
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/servicios')}
                    endIcon={<ArrowForward />}
                    sx={{
                      borderColor: designTokens.colors.golden[500],
                      color: designTokens.colors.golden[800],
                      fontWeight: 700,
                      borderWidth: 2,
                      '&:hover': {
                        borderColor: designTokens.colors.golden[600],
                        backgroundColor: alpha(designTokens.colors.golden[100], 0.3),
                        transform: 'scale(1.02)',
                      }
                    }}
                  >
                    Ver Menú
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Stats Cards Mejoradas */}
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                height: 220,
                background: `linear-gradient(135deg, ${designTokens.colors.aurora.sunset} 0%, #f97316 100%)`,
                color: 'white',
                textAlign: 'center',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 12px 40px rgba(251, 146, 60, 0.4)',
                  transition: 'all 0.3s ease-in-out',
                }
              }}
            >
              {/* Elemento decorativo */}
              <Box
                sx={{
                  position: 'absolute',
                  top: -50,
                  right: -50,
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.1)',
                  animation: 'float 3s ease-in-out infinite',
                }}
              />
              <Box sx={{ position: 'relative', zIndex: 1 }}>
                <Typography variant="h2" sx={{ fontWeight: 900, mb: 1, fontSize: '3.5rem' }}>
                  15+
                </Typography>
                <Typography variant="h6" sx={{ opacity: 0.9, fontWeight: 700, mb: 0.5 }}>
                  🍕 Pizzas Mínimo
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.8, fontSize: '0.9rem' }}>
                  Para garantizar calidad premium
                </Typography>
              </Box>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card
              sx={{
                height: 220,
                background: `linear-gradient(135deg, ${designTokens.colors.golden[500]} 0%, ${designTokens.colors.golden[600]} 100%)`,
                color: designTokens.colors.charcoal[900],
                textAlign: 'center',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 12px 40px rgba(255, 215, 0, 0.4)`,
                  transition: 'all 0.3s ease-in-out',
                }
              }}
            >
              {/* Elemento decorativo */}
              <Box
                sx={{
                  position: 'absolute',
                  top: -30,
                  left: -30,
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: 'rgba(0, 0, 0, 0.1)',
                  animation: 'pulse 2s ease-in-out infinite',
                }}
              />
              <Box sx={{ position: 'relative', zIndex: 1 }}>
                <Typography variant="h2" sx={{ fontWeight: 900, mb: 1, fontSize: '3.5rem' }}>
                  2-3h
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
                  ⏰ Duración Típica
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.8, fontSize: '0.9rem' }}>
                  Experiencia completa y divertida
                </Typography>
              </Box>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card
              sx={{
                height: 220,
                background: `linear-gradient(135deg, ${designTokens.colors.semantic.success} 0%, #10b981 100%)`,
                color: 'white',
                textAlign: 'center',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 12px 40px rgba(34, 197, 94, 0.4)',
                  transition: 'all 0.3s ease-in-out',
                }
              }}
            >
              {/* Elemento decorativo */}
              <Box
                sx={{
                  position: 'absolute',
                  bottom: -40,
                  right: -40,
                  width: 120,
                  height: 120,
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.1)',
                  animation: 'bounce 4s ease-in-out infinite',
                }}
              />
              <Box sx={{ position: 'relative', zIndex: 1 }}>
                <Typography variant="h2" sx={{ fontWeight: 900, mb: 1, fontSize: '3.5rem' }}>
                  100%
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
                  ✨ Satisfacción
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9, fontSize: '0.9rem' }}>
                  Garantía total o te devolvemos tu dinero
                </Typography>
              </Box>
            </Card>
          </Grid>
        </Grid>

        {/* CTA Section */}
        <Box sx={{ textAlign: 'center', mt: 8 }}>
          <Paper
            elevation={0}
            sx={{
              p: 6,
              backgroundColor: 'rgba(255, 215, 0, 0.05)',
              border: `2px solid rgba(255, 215, 0, 0.2)`,
              borderRadius: designTokens.radius.xxl,
            }}
          >
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
              ¿Listo para una experiencia inolvidable? ✨
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 600, mx: 'auto' }}>
              Agenda tu taller o pizza party hoy mismo. Nuestro equipo de chefs expertos
              está listo para crear momentos mágicos para ti y tus niños.
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} justifyContent="center">
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/agendar')}
                endIcon={<Restaurant />}
                sx={{
                  px: 4,
                  py: 2,
                  fontSize: '1.125rem',
                  background: designTokens.colors.aurora.golden,
                  color: designTokens.colors.charcoal[900],
                }}
              >
                Agendar Evento
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate('/servicios')}
                endIcon={<ArrowForward />}
                sx={{ px: 4, py: 2 }}
              >
                Ver Todos los Servicios
              </Button>
            </Stack>
          </Paper>
        </Box>
      </Container>

      {/* Testimonios Premium con Social Proof */}
      <Box sx={{ backgroundColor: designTokens.colors.charcoal[50], py: { xs: 6, md: 8 } }}>
        <Container maxWidth="lg">
          <Box sx={{ textAlign: 'center', mb: 5 }}>
            <Typography
              variant="h3"
              sx={{
                mb: 3,
                background: designTokens.colors.aurora.golden,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Lo Que Dicen Nuestros Clientes
            </Typography>
            <Stack direction="row" spacing={3} justifyContent="center" alignItems="center">
              <Box sx={{ textAlign: 'center' }}>
                <Rating value={reviewStats.roundedAvg} readOnly sx={{ color: designTokens.colors.golden[500], mb: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {reviewStats.avg.toFixed(1)} / 5.0
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Promedio de reseñas
                </Typography>
              </Box>
              {/* Segundo bloque ahora muestra el total de reseñas verificadas */}
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: designTokens.colors.golden[600] }}>
                  {reviewStats.total}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Reseña{reviewStats.total === 1 ? '' : 's'} verificadas
                </Typography>
              </Box>
            </Stack>
          </Box>

          <Grid container spacing={3}>
            {reviews.slice(0, 3).map((t, index) => (
              <Grid item xs={12} md={4} key={t.id || `${t.name}-${index}`}>
                <Fade in timeout={600 + (index * 200)}>
                  <Card
                    sx={{
                      height: '100%',
                      p: 2.5,
                      background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,1) 100%)',
                      backdropFilter: 'blur(10px)',
                      border: `1px solid rgba(255, 215, 0, 0.1)`,
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      '&:hover': {
                        transform: 'translateY(-8px)',
                        boxShadow: designTokens.shadows.glowHover,
                      }
                    }}
                  >
                    <CardContent sx={{ p: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                        <Avatar
                          sx={{
                            width: 48,
                            height: 48,
                            backgroundColor: designTokens.colors.golden[500],
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            color: designTokens.colors.charcoal[900]
                          }}
                        >
                          {t.name?.charAt(0) || 'U'}
                        </Avatar>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                            {t.name || 'Cliente'}
                          </Typography>
                          {/* rol omitido para datos reales */}
                        </Box>
                        <Rating
                          value={Number(t.rating) || 0}
                          readOnly
                          size="small"
                          sx={{ color: designTokens.colors.golden[500] }}
                        />
                      </Box>

                      <Typography
                        variant="body2"
                        sx={{
                          fontStyle: 'italic',
                          lineHeight: 1.6,
                          color: designTokens.colors.charcoal[700],
                          position: 'relative'
                        }}
                      >
                        {sanitizeReviewText(t.comment || t.text || '')}
                      </Typography>
                    </CardContent>
                  </Card>
                </Fade>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ textAlign: 'center', mt: 6 }}>
            <Button
              variant="outlined"
              onClick={() => navigate('/testimonios')}
              endIcon={<ArrowForward />}
              size="large"
              sx={{ px: 4 }}
            >
              Ver Más Testimonios
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Galería Visual Moderna */}
      <Container maxWidth="xl" sx={{ py: { xs: 8, md: 12 } }}>
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography
            variant="h2"
            sx={{
              mb: 3,
              background: designTokens.colors.aurora.golden,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Momentos Mágicos
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
            Capturamos cada sonrisa, cada momento de aprendizaje y diversión
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {[
            {
              title: 'Talleres Educativos',
              img: `${publicBase}momentoS/p1.jpg`,
              desc: 'Niños aprendiendo técnicas culinarias básicas',
              category: 'Educación'
            },
            {
              title: 'Pizza Parties',
              img: `${publicBase}momentoS/p2.jpg`,
              desc: 'Celebraciones familiares llenas de sabor',
              category: 'Eventos'
            },
            {
              title: 'Cumpleaños Especiales',
              img: `${publicBase}momentoS/p3.jpg`,
              desc: 'Celebraciones únicas e inolvidables',
              category: 'Cumpleaños'
            },
            {
              title: 'Eventos Corporativos',
              img: `${publicBase}momentoS/p4.jpg`,
              desc: 'Team building delicioso y efectivo',
              category: 'Empresas'
            }
          ].map((moment, index) => (
            <Grid item xs={12} sm={6} md={3} key={moment.title}>
              <Fade in timeout={800 + (index * 150)}>
                <Card
                  sx={{
                    position: 'relative',
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      transform: 'translateY(-12px) scale(1.02)',
                      '& .overlay': {
                        backgroundColor: 'rgba(0, 0, 0, 0.4)',
                      },
                      '& .content': {
                        transform: 'translateY(0)',
                      }
                    }
                  }}
                >
                  <CardMedia
                    component="img"
                    height={280}
                    image={moment.img}
                    alt={moment.title}
                    loading="lazy"
                    sx={{ objectFit: 'cover', width: '100%', display: 'block' }}
                  />
                  <Box
                    className="overlay"
                    sx={{
                      position: 'absolute',
                      inset: 0,
                      backgroundColor: 'rgba(0, 0, 0, 0.2)',
                      transition: 'all 0.3s ease',
                      display: 'flex',
                      alignItems: 'flex-end',
                    }}
                  >
                    <Box
                      className="content"
                      sx={{
                        p: 3,
                        color: 'white',
                        width: '100%',
                        transform: 'translateY(20px)',
                        transition: 'all 0.3s ease',
                      }}
                    >
                      <Chip
                        label={moment.category}
                        size="small"
                        sx={{
                          backgroundColor: designTokens.colors.golden[500],
                          color: designTokens.colors.charcoal[900],
                          fontWeight: 600,
                          mb: 2,
                        }}
                      />
                      <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                        {moment.title}
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.9 }}>
                        {moment.desc}
                      </Typography>
                    </Box>
                  </Box>
                </Card>
              </Fade>
            </Grid>
          ))}
        </Grid>

        <Box sx={{ textAlign: 'center', mt: 6 }}>
          <Button
            variant="outlined"
            onClick={() => navigate('/galeria')}
            endIcon={<ArrowForward />}
            size="large"
            sx={{ px: 4 }}
          >
            Ver Galería Completa
          </Button>
        </Box>
      </Container>

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
      <FloatingCTA navigate={navigate} />
    </>
  )
}
