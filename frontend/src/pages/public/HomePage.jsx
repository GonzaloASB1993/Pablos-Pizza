import React, { useState, useEffect, useMemo, useRef } from 'react'
import { gsap } from 'gsap'
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
  DialogContent,
  Skeleton,
  Alert
} from '@mui/material'
import SEO from '../../components/common/SEO'
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
  CheckCircle as CheckCircleIcon,
  ZoomIn
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
import { listenGalleryPhotos, getGalleryImageUrls } from '../../services/galleryService'
import BorderBeam from '../../components/common/BorderBeam'
import RollingGallery from '../../components/common/RollingGallery'
import LightRays from '../../components/common/LightRays'


// Hero Logo 3D con efectos GSAP mejorados
const Hero3DLogo = ({ prefersReducedMotion, animationsEnabled }) => {
  const logoRef = useRef(null)
  const glowRef = useRef(null)
  const ringRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    if (prefersReducedMotion || !animationsEnabled) return

    const logo = logoRef.current
    const glow = glowRef.current
    const ring = ringRef.current
    const container = containerRef.current

    if (!logo || !glow || !ring) return

    // ENTRADA ELASTIC - El logo entra con efecto de rebote suave
    gsap.fromTo(
      logo,
      {
        scale: 0,
        opacity: 0,
        rotation: -180,
      },
      {
        scale: 1,
        opacity: 1,
        rotation: 0,
        duration: 1.4,
        ease: 'elastic.out(1, 0.6)',
        delay: 0.3,
      }
    )

    // GLOW PULSE - El resplandor pulsa sutilmente
    gsap.to(glow, {
      scale: 1.1,
      opacity: 0.8,
      duration: 2,
      ease: 'sine.inOut',
      repeat: -1,
      yoyo: true,
    })

    // ORBITAL RING - Rotación continua suave
    gsap.to(ring, {
      rotation: 360,
      duration: 20,
      ease: 'none',
      repeat: -1,
    })

    // HOVER EFFECT MEJORADO - Efecto magnético al pasar el mouse
    const handleMouseMove = (e) => {
      if (!container) return

      const rect = container.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2

      const deltaX = (e.clientX - centerX) / 20
      const deltaY = (e.clientY - centerY) / 20

      gsap.to(logo, {
        x: deltaX,
        y: deltaY,
        rotationY: deltaX / 2,
        rotationX: -deltaY / 2,
        duration: 0.3,
        ease: 'power2.out',
      })
    }

    const handleMouseLeave = () => {
      gsap.to(logo, {
        x: 0,
        y: 0,
        rotationY: 0,
        rotationX: 0,
        duration: 0.5,
        ease: 'elastic.out(1, 0.5)',
      })
    }

    const handleTouchMove = (e) => {
      if (!container || !e.touches[0]) return
      const rect = container.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const deltaX = (e.touches[0].clientX - centerX) / 20
      const deltaY = (e.touches[0].clientY - centerY) / 20
      gsap.to(logo, {
        x: deltaX,
        y: deltaY,
        rotationY: deltaX / 2,
        rotationX: -deltaY / 2,
        duration: 0.3,
        ease: 'power2.out',
      })
    }

    const handleTouchEnd = () => {
      gsap.to(logo, {
        x: 0,
        y: 0,
        rotationY: 0,
        rotationX: 0,
        duration: 0.5,
        ease: 'elastic.out(1, 0.5)',
      })
    }

    container.addEventListener('mousemove', handleMouseMove)
    container.addEventListener('mouseleave', handleMouseLeave)
    container.addEventListener('touchmove', handleTouchMove, { passive: true })
    container.addEventListener('touchend', handleTouchEnd)

    return () => {
      container.removeEventListener('mousemove', handleMouseMove)
      container.removeEventListener('mouseleave', handleMouseLeave)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [prefersReducedMotion, animationsEnabled])

  return (
    <Box
      ref={containerRef}
      sx={{
        position: 'relative',
        display: 'inline-block',
        perspective: '1000px',
      }}
    >
      {/* Resplandor de fondo */}
      <Box
        ref={glowRef}
        sx={{
          position: 'absolute',
          inset: -40,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${designTokens.colors.golden[400]} 0%, ${designTokens.colors.golden[200]}40 40%, transparent 70%)`,
          filter: 'blur(20px)',
          opacity: 0.8,
          willChange: 'transform, opacity',
        }}
      />

      {/* Anillo orbital animado */}
      <Box
        ref={ringRef}
        sx={{
          position: 'absolute',
          inset: -15,
          borderRadius: '50%',
          border: `3px solid ${designTokens.colors.golden[400]}`,
          borderTop: `3px solid ${designTokens.colors.golden[600]}`,
          willChange: 'transform',
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
        ref={logoRef}
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
          cursor: 'pointer',
          willChange: 'transform',
          transformStyle: 'preserve-3d',
        }}
      />
    </Box>
  )
}

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
        aria-label="Agendar evento ahora - 10% descuento este mes"
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
          animation: prefersReducedMotion ? 'none' : 'bounce 2s ease 3',
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
              10% descuento este mes
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Fade>
  )
}

// Componente AnimatedSection con animaciones de scroll (ida y vuelta)
const AnimatedSection = ({ children, delay = 0 }) => {
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

  const { ref, inView } = useInView({
    threshold: 0.15,
    triggerOnce: true,
    rootMargin: '50px'
  })

  return (
    <Box
      ref={ref}
      sx={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(30px)',
        transition: prefersReducedMotion
          ? 'none'
          : `opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1) ${delay}ms, transform 0.5s cubic-bezier(0.4, 0, 0.2, 1) ${delay}ms`,
        willChange: inView ? 'auto' : 'opacity, transform'
      }}
    >
      {children}
    </Box>
  )
}

// Componente de carga progresiva de imágenes con blur-up
const ProgressiveImage = ({ src, alt, loading = 'lazy', sx, ...props }) => {
  const [loaded, setLoaded] = useState(false)
  const [currentSrc, setCurrentSrc] = useState(`${src}?w=40&blur=20`)

  useEffect(() => {
    const img = new Image()
    const optimizedSrc = `${src}?w=800&q=75&auto=format&fit=crop`
    img.src = optimizedSrc
    img.onload = () => {
      setCurrentSrc(optimizedSrc)
      setLoaded(true)
    }
  }, [src])

  return (
    <Box
      component="img"
      src={currentSrc}
      alt={alt}
      loading={loading}
      sx={{
        filter: loaded ? 'none' : 'blur(8px)',
        transition: 'filter 0.3s ease-out',
        ...sx
      }}
      {...props}
    />
  )
}


// Testimonial Card Component with Image Lightbox
function TestimonialCard({ testimonial, sanitizeReviewText }) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)

  const handleImageClick = () => {
    if (testimonial.imageUrl) {
      setLightboxOpen(true)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleImageClick()
    }
  }

  return (
    <>
      <Card
        sx={{
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: '#FFFFFF',
          color: '#000',
          minHeight: 'auto',
          maxWidth: 650,
          mx: 'auto',
          p: { xs: 2.5, sm: 3 },
          border: '2px solid rgba(255, 215, 0, 0.3)',
          borderRadius: 2,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            borderColor: '#FFD700',
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(255, 215, 0, 0.2)'
          }
        }}
      >
        <CardContent sx={{ p: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Header: Avatar, Name, and Rating */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar
              sx={{
                width: 48,
                height: 48,
                backgroundColor: designTokens.colors.golden[500],
                fontSize: '1.25rem',
                fontWeight: 700,
                color: designTokens.colors.charcoal[900],
                boxShadow: `0 2px 8px ${designTokens.colors.golden[500]}4D`
              }}
            >
              {testimonial.name?.charAt(0)?.toUpperCase() || 'U'}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2, mb: 0.5, fontSize: '1rem' }}>
                {testimonial.name || 'Cliente'}
              </Typography>
              <Rating
                value={Number(testimonial.rating) || 0}
                readOnly
                size="small"
                sx={{ color: designTokens.colors.golden[500] }}
                aria-label={`Calificación: ${testimonial.rating} de 5 estrellas`}
              />
            </Box>
          </Box>

          {/* Testimonial Text */}
          <Box sx={{ position: 'relative', pl: 2 }}>
            <Typography
              component="span"
              sx={{
                position: 'absolute',
                left: -8,
                top: -8,
                fontSize: '2rem',
                color: designTokens.colors.golden[500],
                opacity: 0.3,
                fontFamily: 'Georgia, serif',
                lineHeight: 1,
                userSelect: 'none'
              }}
            >
              "
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontStyle: 'italic',
                lineHeight: 1.7,
                color: '#333',
                fontSize: { xs: '0.95rem', sm: '1rem' }
              }}
            >
              {sanitizeReviewText(testimonial.comment || testimonial.text || '')}
            </Typography>
          </Box>

          {/* Testimonial Image Thumbnail (if available) */}
          {testimonial.imageUrl && (
            <Box
              onClick={handleImageClick}
              onKeyDown={handleKeyDown}
              tabIndex={0}
              role="button"
              aria-label="Click para ampliar imagen del testimonio"
              sx={{
                position: 'relative',
                width: { xs: 120, sm: 150 },
                height: { xs: 120, sm: 150 },
                borderRadius: 2,
                overflow: 'hidden',
                cursor: 'pointer',
                border: '2px solid rgba(255, 215, 0, 0.3)',
                transition: 'all 0.3s ease',
                alignSelf: 'flex-start',
                mt: 1,
                '&:hover': {
                  borderColor: '#FFD700',
                  transform: 'scale(1.05)',
                  '& .zoom-overlay': {
                    opacity: 1
                  }
                },
                '&:focus-visible': {
                  outline: '3px solid #FFD700',
                  outlineOffset: '2px'
                }
              }}
            >
              {!imageLoaded && (
                <Skeleton
                  variant="rectangular"
                  width="100%"
                  height="100%"
                  sx={{ position: 'absolute', top: 0, left: 0 }}
                />
              )}
              <Box
                component="img"
                src={testimonial.imageUrl}
                alt={`Imagen de testimonio de ${testimonial.name}`}
                loading="lazy"
                onLoad={() => setImageLoaded(true)}
                sx={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: imageLoaded ? 'block' : 'none'
                }}
              />
              {/* Zoom Overlay */}
              <Box
                className="zoom-overlay"
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: 'rgba(0, 0, 0, 0.6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: 0,
                  transition: 'opacity 0.3s ease'
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5 }}>
                  <ZoomIn aria-hidden="true" sx={{ color: '#FFD700', fontSize: 24 }} />
                  <Typography variant="caption" sx={{ color: '#FFD700', fontWeight: 700, fontSize: '0.75rem' }}>
                    Ampliar
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}

          {/* Date (if available) */}
          {testimonial.createdAt && (() => {
            try {
              // Handle both Firestore Timestamp and regular date strings
              let date;
              if (testimonial.createdAt.toDate) {
                // Firestore Timestamp
                date = testimonial.createdAt.toDate();
              } else if (testimonial.createdAt.seconds) {
                // Firestore Timestamp object format
                date = new Date(testimonial.createdAt.seconds * 1000);
              } else {
                // Regular date string or number
                date = new Date(testimonial.createdAt);
              }

              // Check if date is valid
              if (isNaN(date.getTime())) {
                return null;
              }

              return (
                <Typography variant="caption" sx={{ color: 'rgba(0,0,0,0.5)', textAlign: 'right', fontSize: '0.75rem' }}>
                  {date.toLocaleDateString('es-CL', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </Typography>
              );
            } catch (e) {
              return null;
            }
          })()}
        </CardContent>

        {/* Border Beam Effect */}
        <BorderBeam
          size={200}
          duration={8}
          borderWidth={1.5}
          colorFrom="#FFD700"
          colorTo="#FFA500"
        />
      </Card>

      {/* Image Lightbox Modal */}
      <Dialog
        open={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8)',
            borderRadius: 2
          }
        }}
        aria-labelledby="lightbox-title"
      >
        <DialogContent sx={{ p: 2, position: 'relative' }}>
          {/* Close Button */}
          <IconButton
            onClick={() => setLightboxOpen(false)}
            aria-label="Cerrar imagen ampliada"
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              backgroundColor: 'rgba(255, 215, 0, 0.9)',
              color: '#000',
              zIndex: 10,
              '&:hover': {
                backgroundColor: '#FFD700',
                transform: 'scale(1.1)'
              }
            }}
          >
            <CloseIcon />
          </IconButton>

          {/* Full Size Image */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: { xs: 300, sm: 500 }
            }}
          >
            <Box
              component="img"
              src={testimonial.imageUrl}
              alt={`Imagen ampliada de testimonio de ${testimonial.name}`}
              sx={{
                maxWidth: '100%',
                maxHeight: '80vh',
                objectFit: 'contain',
                borderRadius: 1
              }}
            />
          </Box>

          {/* Image Caption */}
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="subtitle1" sx={{ color: designTokens.colors.golden[500], fontWeight: 600 }}>
              Testimonio de {testimonial.name}
            </Typography>
            <Rating
              value={Number(testimonial.rating) || 0}
              readOnly
              size="small"
              sx={{ color: designTokens.colors.golden[500], mt: 1 }}
            />
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}


export default function HomePage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const [heroLoaded, setHeroLoaded] = useState(false)
  const [reviews, setReviews] = useState([])
  const [reviewsLoading, setReviewsLoading] = useState(true)
  const [reviewsError, setReviewsError] = useState(null)
  const [animationsEnabled, setAnimationsEnabled] = useState(false)
  const [galleryPhotos, setGalleryPhotos] = useState([])
  const [galleryLoading, setGalleryLoading] = useState(true)
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
    setReviewsLoading(true)
    const unsub = listenTestimonials(
      (list) => {
        const filtered = (Array.isArray(list) ? list : []).filter((t) => t.approved === true && t.isTest !== true)
        setReviews(filtered)
        setReviewsLoading(false)
        setReviewsError(null)
      },
      {
        approvedOnly: true,
        onError: (err) => {
          setReviewsError(err.message || 'Error al cargar testimonios')
          setReviewsLoading(false)
        }
      }
    )
    return () => unsub && unsub()
  }, [])

  // Suscribirse a fotos de la galería para el rolling gallery
  useEffect(() => {
    setGalleryLoading(true)
    const unsub = listenGalleryPhotos(
      (photos) => {
        setGalleryPhotos(photos)
        setGalleryLoading(false)
      },
      {
        onError: (err) => {
          console.error('Error loading gallery photos:', err)
          setGalleryLoading(false)
        }
      }
    )
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

    // 7) Elimina CSS inline y propiedades de estilo
    out = out.replace(/;position:absolute[^}]*}/gi, '')
    out = out.replace(/\{[^}]*position\s*:\s*absolute[^}]*\}/gi, '')
    out = out.replace(/;[a-z-]+:[^;]*/gi, '')
    out = out.replace(/[a-z-]+\s*:\s*[^;]+;/gi, '')

    // 8) Normaliza espacios
    out = out.replace(/\s+/g, ' ').trim()
    return out
  }

  return (
    <>
      <SEO
        title="Talleres de Pizza para Niños en Santiago"
        description="Talleres de pizza para niños y pizza parties en Santiago. Experiencias gastronómicas educativas donde los niños aprenden a hacer pizzas artesanales. Servicio a domicilio para cumpleaños."
        keywords="talleres pizza niños Santiago, pizza party cumpleaños, eventos infantiles Santiago, taller cocina niños, catering pizza, fiestas infantiles Chile, pizzeros en acción"
        url="/"
      />
      {/* Hero Section Premium con Aurora Gradient */}
      <Box
        sx={{
          minHeight: { xs: 'auto', md: '100vh' },
          py: { xs: 6, md: 8 },
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
                      Crean Magia{' '}
                      <AutoAwesome aria-hidden="true" sx={{ fontSize: '0.75em', verticalAlign: 'middle', color: designTokens.colors.golden[400], WebkitTextFillColor: 'initial' }} />
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
              backgroundImage: `url(${publicBase}images/talleres/taller-corporativo.webp)`,
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
                  src={`${publicBase}images/talleres/taller-corporativo.webp`}
                  loading="lazy"
                  alt="Niños participando en taller de pizza Pizzeros en Acción, aprendiendo técnicas culinarias"
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
      <AnimatedSection delay={100}>
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
              backgroundImage: `url(${publicBase}images/pizza-party.webp)`,
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
                  src={`${publicBase}images/pizza-party.webp`}
                  loading="lazy"
                  alt="Pizza Party - Catering gourmet con pizzas artesanales en eventos"
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
      <AnimatedSection delay={0}>
        <Box
          component="section"
          aria-label="Testimonios de clientes"
          sx={{
            minHeight: '100vh',
            backgroundColor: '#FFFFFF',
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
                  <Rating value={reviewStats.roundedAvg} readOnly sx={{ color: '#FFD700', mb: 1 }} aria-label={`Calificación promedio: ${reviewStats.avg.toFixed(1)} de 5 estrellas`} />
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#000' }}>
                    {reviewStats.avg.toFixed(1)} / 5.0
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(0,0,0,0.6)' }}>
                    Promedio de reseñas
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: '#FFD700' }}>
                    {reviewStats.total}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(0,0,0,0.6)' }}>
                    Reseña{reviewStats.total === 1 ? '' : 's'} verificadas
                  </Typography>
                </Box>
              </Stack>
            </Box>

            {/* Loading State */}
            {reviewsLoading && (
              <Box sx={{ maxWidth: 800, mx: 'auto' }}>
                <Skeleton
                  variant="rectangular"
                  height={450}
                  sx={{
                    borderRadius: 3,
                    backgroundColor: 'rgba(0, 0, 0, 0.06)'
                  }}
                />
              </Box>
            )}

            {/* Error State */}
            {reviewsError && !reviewsLoading && (
              <Alert
                severity="error"
                sx={{
                  backgroundColor: 'rgba(244, 67, 54, 0.1)',
                  color: '#d32f2f',
                  border: '1px solid rgba(244, 67, 54, 0.3)'
                }}
              >
                No pudimos cargar los testimonios. Por favor intenta más tarde.
              </Alert>
            )}

            {/* Empty State */}
            {!reviewsLoading && !reviewsError && reviews.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="h6" sx={{ color: '#000', mb: 2 }}>
                  ¡Sé el primero en dejarnos tu opinión!
                </Typography>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/testimonios')}
                  sx={{
                    borderColor: '#FFD700',
                    color: '#FFD700',
                    '&:hover': {
                      borderColor: '#FFC700',
                      backgroundColor: 'rgba(255, 215, 0, 0.1)'
                    }
                  }}
                >
                  Dejar Testimonio
                </Button>
              </Box>
            )}

            {/* Reviews Carousel - ONE AT A TIME */}
            {!reviewsLoading && !reviewsError && reviews.length > 0 && (
              <>
                <Box sx={{ maxWidth: 900, mx: 'auto', position: 'relative' }}>
                  <Swiper
                    modules={[Autoplay, Pagination, Navigation]}
                    spaceBetween={0}
                    slidesPerView={1}
                    autoplay={{
                      delay: 6000,
                      disableOnInteraction: false,
                      pauseOnMouseEnter: true
                    }}
                    pagination={{
                      clickable: true,
                      dynamicBullets: true
                    }}
                    navigation={{
                      nextEl: '.testimonial-next',
                      prevEl: '.testimonial-prev'
                    }}
                    loop={reviews.length > 1}
                    style={{ paddingBottom: '60px' }}
                    keyboard={{
                      enabled: true,
                      onlyInViewport: true
                    }}
                    a11y={{
                      enabled: true,
                      prevSlideMessage: 'Testimonio anterior',
                      nextSlideMessage: 'Siguiente testimonio',
                      firstSlideMessage: 'Este es el primer testimonio',
                      lastSlideMessage: 'Este es el último testimonio'
                    }}
                  >
                    {reviews.map((t, index) => (
                    <SwiperSlide key={t.id || `${t.name}-${index}`}>
                      <TestimonialCard testimonial={t} sanitizeReviewText={sanitizeReviewText} />
                    </SwiperSlide>
                    ))}
                  </Swiper>

                  {/* Custom Navigation Buttons */}
                  <IconButton
                    className="testimonial-prev"
                    aria-label="Ver testimonio anterior"
                    sx={{
                      position: 'absolute',
                      left: { xs: -10, sm: -20 },
                      top: '50%',
                      transform: 'translateY(-50%)',
                      zIndex: 10,
                      backgroundColor: '#FFFFFF',
                      border: '2px solid #FFD700',
                      color: '#FFD700',
                      width: { xs: 40, sm: 50 },
                      height: { xs: 40, sm: 50 },
                      boxShadow: '0 4px 12px rgba(255, 215, 0, 0.2)',
                      '&:hover': {
                        backgroundColor: '#FFD700',
                        color: '#000',
                        transform: 'translateY(-50%) scale(1.1)',
                      },
                      transition: 'all 0.3s ease',
                    }}
                  >
                    <ArrowForward sx={{ transform: 'rotate(180deg)', fontSize: { xs: 20, sm: 24 } }} />
                  </IconButton>

                  <IconButton
                    className="testimonial-next"
                    aria-label="Ver siguiente testimonio"
                    sx={{
                      position: 'absolute',
                      right: { xs: -10, sm: -20 },
                      top: '50%',
                      transform: 'translateY(-50%)',
                      zIndex: 10,
                      backgroundColor: '#FFFFFF',
                      border: '2px solid #FFD700',
                      color: '#FFD700',
                      width: { xs: 40, sm: 50 },
                      height: { xs: 40, sm: 50 },
                      boxShadow: '0 4px 12px rgba(255, 215, 0, 0.2)',
                      '&:hover': {
                        backgroundColor: '#FFD700',
                        color: '#000',
                        transform: 'translateY(-50%) scale(1.1)',
                      },
                      transition: 'all 0.3s ease',
                    }}
                  >
                    <ArrowForward sx={{ fontSize: { xs: 20, sm: 24 } }} />
                  </IconButton>
                </Box>

                <Box sx={{ textAlign: 'center', mt: 6 }}>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/testimonios')}
                    endIcon={<ArrowForward />}
                    size="large"
                    sx={{
                      px: 4,
                      py: 1.5,
                      borderColor: '#FFD700',
                      color: '#000',
                      fontWeight: 600,
                      borderWidth: 2,
                      '&:hover': {
                        borderColor: '#FFD700',
                        backgroundColor: '#FFD700',
                        color: '#000',
                        borderWidth: 2
                      }
                    }}
                  >
                    Ver Más Testimonios
                  </Button>
                </Box>
              </>
            )}
          </Container>

          {/* CSS para personalizar Swiper */}
          <style>{`
            .swiper-button-next,
            .swiper-button-prev {
              display: none !important;
            }
            .swiper-pagination-bullet {
              background: rgba(0, 0, 0, 0.3) !important;
              opacity: 1 !important;
              width: 10px !important;
              height: 10px !important;
              transition: all 0.3s ease !important;
            }
            .swiper-pagination-bullet-active {
              background: #FFD700 !important;
              width: 24px !important;
              border-radius: 5px !important;
            }
            .swiper-slide {
              opacity: 0;
              transition: opacity 0.5s ease-in-out;
            }
            .swiper-slide-active {
              opacity: 1;
            }
          `}</style>
        </Box>
      </AnimatedSection>

      {/* Rolling Gallery Section */}
      <AnimatedSection delay={100}>
        <Box
          component="section"
          sx={{
            minHeight: '100vh',
            py: 8,
            backgroundColor: '#000000',
            display: 'flex',
            alignItems: 'center',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* LightRays Background */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 0,
              opacity: 0.6
            }}
          >
            <LightRays
              raysOrigin="top-center"
              raysColor="#FFD700"
              raysSpeed={0.3}
              lightSpread={1.5}
              rayLength={2}
              pulsating={true}
              fadeDistance={1.0}
              saturation={1.0}
              followMouse={true}
              mouseInfluence={0.2}
              noiseAmount={0.1}
              distortion={0.15}
            />
          </Box>

          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
            {/* Header */}
            <Box
              sx={{
                textAlign: 'center',
                mb: 6
              }}
            >
              <Typography
                variant="h2"
                sx={{
                  fontWeight: 'bold',
                  color: '#FFD700',
                  mb: 2,
                  fontSize: { xs: '2rem', md: '3rem' }
                }}
              >
                Momentos Mágicos
              </Typography>
              <Typography variant="h6" sx={{ color: '#FFFFFF', mb: 4 }}>
                Capturamos cada sonrisa, cada momento de aprendizaje y diversión
              </Typography>
            </Box>

            {/* Rolling Gallery */}
            {!galleryLoading && (
              <RollingGallery
                autoplay={true}
                pauseOnHover={true}
                images={getGalleryImageUrls(galleryPhotos)}
              />
            )}

            {/* Loading State */}
            {galleryLoading && (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="body1" sx={{ color: '#FFFFFF' }}>
                  Cargando galería...
                </Typography>
              </Box>
            )}

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
        </Box>
      </AnimatedSection>

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
