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
  Chip,
  Fade,
  Paper,
  Stack,
  Avatar,
  Rating,
  IconButton,
  useMediaQuery,
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
  CheckCircle,
  AutoAwesome,
  Close as CloseIcon,
  ZoomIn,
  EmojiEvents,
  Favorite,
  Star
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Autoplay, Pagination, Navigation } from 'swiper/modules'
import { useInView } from 'react-intersection-observer'
import 'swiper/css'
import 'swiper/css/pagination'
import 'swiper/css/navigation'
import { designTokens } from '../../utils/theme'
import { listenTestimonials } from '../../services/testimonialsService'
import { listenGalleryPhotos, getGalleryImageUrls } from '../../services/galleryService'
import BorderBeam from '../../components/common/BorderBeam'
import RollingGallery from '../../components/common/RollingGallery'
import LightRays from '../../components/common/LightRays'
import { ACTIVE_PROMO, PIZZEROS_TIERS } from '../../data/pricing'
import { CTA_VARIANT } from '../../data/stats'
import { useStats } from '../../hooks/useStats'

// ─────────────────────────────────────────────────────────────
// DESIGN TOKENS (local shortcuts)
// ─────────────────────────────────────────────────────────────
const GOLD = '#FFD700'
const GOLD_GRADIENT = 'linear-gradient(135deg, #FFD700 0%, #FF8A00 100%)'

const BG = {
  hero: 'transparent', // photo handles this
  s1: '#0D0D0D',
  s2: '#111111',
  s3: '#0A0A0A',
  s4: '#0F0F0F',
}

// ─────────────────────────────────────────────────────────────
// SECTION DIVIDER — thin golden gradient line
// ─────────────────────────────────────────────────────────────
const SectionDivider = () => (
  <Box
    aria-hidden="true"
    sx={{
      height: 1,
      background: 'linear-gradient(90deg, transparent 0%, rgba(255,215,0,0.15) 20%, rgba(255,215,0,0.45) 50%, rgba(255,215,0,0.15) 80%, transparent 100%)',
    }}
  />
)

// ─────────────────────────────────────────────────────────────
// FLOATING CTA
// ─────────────────────────────────────────────────────────────
const FloatingCTA = ({ navigate, prefersReducedMotion }) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 2500)
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
      <Box
        role="button"
        tabIndex={0}
        aria-label="Agendar evento ahora"
        onKeyDown={handleKeyDown}
        onClick={() => navigate('/agendar')}
        sx={{
          position: 'fixed',
          bottom: { xs: 20, sm: 28 },
          right: { xs: 16, sm: 24 },
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 3,
          py: 1.5,
          background: GOLD_GRADIENT,
          color: '#000',
          borderRadius: designTokens.radius.xl,
          boxShadow: '0 8px 32px rgba(255,215,0,0.4), 0 2px 8px rgba(0,0,0,0.3)',
          zIndex: 1000,
          cursor: 'pointer',
          transition: 'transform 0.2s ease, box-shadow 0.2s ease',
          animation: prefersReducedMotion ? 'none' : 'ctaPulse 3s ease-in-out 3',
          '&:hover': {
            transform: 'translateY(-3px)',
            boxShadow: '0 12px 40px rgba(255,215,0,0.5)',
          },
          '&:focus-visible': {
            outline: `3px solid ${GOLD}`,
            outlineOffset: '3px',
          },
          '@keyframes ctaPulse': {
            '0%, 100%': { transform: 'translateY(0)' },
            '50%': { transform: 'translateY(-6px)' },
          },
        }}
      >
        <Restaurant sx={{ fontSize: 20 }} />
        <Box>
          <Typography variant="caption" sx={{ fontWeight: 800, display: 'block', lineHeight: 1.1, fontSize: '0.8rem' }}>
            ¡Agenda HOY!
          </Typography>
          {ACTIVE_PROMO ? (
            <Typography variant="caption" sx={{ opacity: 0.75, fontSize: '0.7rem', lineHeight: 1 }}>
              {ACTIVE_PROMO.label}
            </Typography>
          ) : null}
        </Box>
      </Box>
    </Fade>
  )
}

// ─────────────────────────────────────────────────────────────
// ANIMATED SECTION — scroll reveal
// ─────────────────────────────────────────────────────────────
const AnimatedSection = ({ children, delay = 0 }) => {
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const { ref, inView } = useInView({ threshold: 0.08, triggerOnce: true, rootMargin: '0px' })

  return (
    <Box ref={ref}>
      <Box
        sx={{
          // Only animate translateY — opacity stays at 1 so backgrounds are always visible.
          // This prevents body-color bleeding through transparent sections during scroll.
          transform: (!prefersReducedMotion && !inView) ? 'translateY(28px)' : 'translateY(0)',
          opacity: (!prefersReducedMotion && !inView) ? 0.85 : 1,
          transition: prefersReducedMotion
            ? 'none'
            : `transform 0.55s cubic-bezier(0.22, 1, 0.36, 1) ${delay}ms, opacity 0.4s ease ${delay}ms`,
          willChange: inView ? 'auto' : 'transform',
        }}
      >
        {children}
      </Box>
    </Box>
  )
}

// ─────────────────────────────────────────────────────────────
// TESTIMONIAL CARD — editorial dark (no glass, no grey)
// ─────────────────────────────────────────────────────────────
function TestimonialCard({ testimonial, sanitizeReviewText }) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)

  const handleImageClick = () => {
    if (testimonial.imageUrl) setLightboxOpen(true)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleImageClick()
    }
  }

  return (
    <>
      <Box
        sx={{
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: '#141414',
          borderLeft: `3px solid ${GOLD}`,
          borderRadius: '0 12px 12px 0',
          p: { xs: 3.5, sm: 5 },
          mx: { xs: 1, sm: 0 },
          transition: 'background-color 0.25s ease, box-shadow 0.25s ease',
          '&:hover': {
            backgroundColor: '#191919',
            boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
          },
        }}
      >
        {/* Decorative oversized quote mark — purely visual */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            top: -8,
            right: 20,
            fontSize: '9rem',
            fontFamily: 'Georgia, "Times New Roman", serif',
            color: GOLD,
            opacity: 0.055,
            lineHeight: 1,
            userSelect: 'none',
            pointerEvents: 'none',
            fontWeight: 700,
          }}
        >
          "
        </Box>

        {/* Stars — prominent, at top */}
        <Rating
          value={Number(testimonial.rating) || 0}
          readOnly
          size="medium"
          sx={{
            color: GOLD,
            mb: 2.5,
            '& .MuiRating-iconFilled': {
              filter: 'drop-shadow(0 1px 4px rgba(255,215,0,0.45))',
            },
          }}
          aria-label={`Calificación: ${testimonial.rating} de 5 estrellas`}
        />

        {/* Quote text — serif italic */}
        <Typography
          sx={{
            fontFamily: 'Georgia, "Times New Roman", serif',
            fontStyle: 'italic',
            lineHeight: 1.85,
            color: 'rgba(255,255,255,0.84)',
            fontSize: { xs: '1rem', sm: '1.1rem' },
            mb: testimonial.imageUrl ? 3 : 3.5,
            position: 'relative',
            zIndex: 1,
          }}
        >
          {sanitizeReviewText(testimonial.comment || testimonial.text || '')}
        </Typography>

        {/* Testimonial image thumbnail */}
        {testimonial.imageUrl && (
          <Box
            onClick={handleImageClick}
            onKeyDown={handleKeyDown}
            tabIndex={0}
            role="button"
            aria-label="Ampliar imagen del testimonio"
            sx={{
              position: 'relative',
              width: { xs: 96, sm: 112 },
              height: { xs: 96, sm: 112 },
              borderRadius: 1.5,
              overflow: 'hidden',
              cursor: 'pointer',
              border: `1px solid rgba(255,215,0,0.2)`,
              mb: 3.5,
              transition: 'all 0.25s ease',
              '&:hover': {
                borderColor: GOLD,
                transform: 'scale(1.05)',
                '& .zoom-overlay': { opacity: 1 },
              },
              '&:focus-visible': { outline: `3px solid ${GOLD}`, outlineOffset: '2px' },
            }}
          >
            {!imageLoaded && (
              <Skeleton variant="rectangular" width="100%" height="100%"
                sx={{ position: 'absolute', top: 0, left: 0, bgcolor: '#1e1e1e' }} />
            )}
            <Box
              component="img"
              src={testimonial.imageUrl}
              alt={`Imagen de testimonio de ${testimonial.name}`}
              loading="lazy"
              onLoad={() => setImageLoaded(true)}
              sx={{ width: '100%', height: '100%', objectFit: 'cover', display: imageLoaded ? 'block' : 'none' }}
            />
            <Box className="zoom-overlay" sx={{
              position: 'absolute', inset: 0,
              backgroundColor: 'rgba(0,0,0,0.72)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: 0, transition: 'opacity 0.25s ease',
            }}>
              <ZoomIn sx={{ color: GOLD, fontSize: 22 }} />
            </Box>
          </Box>
        )}

        {/* Thin divider */}
        <Box sx={{ height: 1, backgroundColor: 'rgba(255,255,255,0.07)', mb: 3 }} />

        {/* Author */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              width: 42,
              height: 42,
              background: GOLD_GRADIENT,
              fontSize: '1rem',
              fontWeight: 800,
              color: '#000',
              flexShrink: 0,
            }}
          >
            {testimonial.name?.charAt(0)?.toUpperCase() || 'U'}
          </Avatar>
          <Box>
            <Typography sx={{ fontWeight: 700, color: '#fff', fontSize: '0.92rem', lineHeight: 1.25 }}>
              {testimonial.name || 'Cliente'}
            </Typography>
            {testimonial.createdAt && (() => {
              try {
                let date
                if (testimonial.createdAt.toDate) date = testimonial.createdAt.toDate()
                else if (testimonial.createdAt.seconds) date = new Date(testimonial.createdAt.seconds * 1000)
                else date = new Date(testimonial.createdAt)
                if (isNaN(date.getTime())) return null
                return (
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.72rem' }}>
                    {date.toLocaleDateString('es-CL', { year: 'numeric', month: 'long' })}
                  </Typography>
                )
              } catch { return null }
            })()}
          </Box>
        </Box>
      </Box>

      {/* Lightbox */}
      <Dialog
        open={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { backgroundColor: 'rgba(0,0,0,0.97)', borderRadius: 2 } }}
        aria-labelledby="lightbox-title"
      >
        <DialogContent sx={{ p: 2, position: 'relative' }}>
          <IconButton
            onClick={() => setLightboxOpen(false)}
            aria-label="Cerrar imagen ampliada"
            sx={{
              position: 'absolute', top: 16, right: 16,
              backgroundColor: 'rgba(255,215,0,0.9)', color: '#000', zIndex: 10,
              '&:hover': { backgroundColor: GOLD, transform: 'scale(1.1)' },
            }}
          >
            <CloseIcon />
          </IconButton>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: { xs: 300, sm: 500 } }}>
            <Box
              component="img"
              src={testimonial.imageUrl}
              alt={`Imagen ampliada de testimonio de ${testimonial.name}`}
              sx={{ maxWidth: '100%', maxHeight: '80vh', objectFit: 'contain', borderRadius: 1 }}
            />
          </Box>
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="subtitle1" sx={{ color: GOLD, fontWeight: 600 }}>
              Testimonio de {testimonial.name}
            </Typography>
            <Rating value={Number(testimonial.rating) || 0} readOnly size="small" sx={{ color: GOLD, mt: 1 }} />
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ─────────────────────────────────────────────────────────────
// HOMEPAGE
// ─────────────────────────────────────────────────────────────
export default function HomePage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

  const [heroLoaded, setHeroLoaded] = useState(false)
  const [animationsEnabled, setAnimationsEnabled] = useState(false)
  const [reviews, setReviews] = useState([])
  const [reviewsLoading, setReviewsLoading] = useState(true)
  const [reviewsError, setReviewsError] = useState(null)
  const [galleryPhotos, setGalleryPhotos] = useState([])
  const [galleryLoading, setGalleryLoading] = useState(true)

  const { stats } = useStats()

  const heroTitleRef = useRef(null)
  const heroSubtitleRef = useRef(null)
  const heroCtaRef = useRef(null)
  const heroStatsRef = useRef(null)

  const publicBase = import.meta.env.BASE_URL || '/'

  // ── dark body background (public homepage only) ──────────────
  useEffect(() => {
    const prev = document.body.style.backgroundColor
    document.body.style.backgroundColor = '#080808'
    document.documentElement.style.backgroundColor = '#080808'
    return () => {
      document.body.style.backgroundColor = prev
      document.documentElement.style.backgroundColor = ''
    }
  }, [])

  // ── animations ──────────────────────────────────────────────
  useEffect(() => {
    setHeroLoaded(true)
    if (!prefersReducedMotion) {
      const enable = () => setTimeout(() => setAnimationsEnabled(true), 300)
      if (document.readyState === 'complete') enable()
      else window.addEventListener('load', enable, { once: true })
    }
  }, [prefersReducedMotion])

  // GSAP hero text reveal
  useEffect(() => {
    if (!animationsEnabled || prefersReducedMotion) return
    const els = [heroTitleRef, heroSubtitleRef, heroCtaRef, heroStatsRef].map(r => r.current).filter(Boolean)
    gsap.fromTo(
      els,
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.9, ease: 'power3.out', stagger: 0.12 }
    )
  }, [animationsEnabled, prefersReducedMotion])

  // ── data ────────────────────────────────────────────────────
  useEffect(() => {
    setReviewsLoading(true)
    const unsub = listenTestimonials(
      (list) => {
        const filtered = (Array.isArray(list) ? list : []).filter(t => t.approved === true && t.isTest !== true)
        setReviews(filtered)
        setReviewsLoading(false)
        setReviewsError(null)
      },
      {
        approvedOnly: true,
        onError: (err) => {
          setReviewsError(err.message || 'Error al cargar testimonios')
          setReviewsLoading(false)
        },
      }
    )
    return () => unsub && unsub()
  }, [])

  useEffect(() => {
    setGalleryLoading(true)
    const unsub = listenGalleryPhotos(
      (photos) => {
        setGalleryPhotos(photos)
        setGalleryLoading(false)
      },
      { onError: () => setGalleryLoading(false) }
    )
    return () => unsub && unsub()
  }, [])

  const reviewStats = useMemo(() => {
    const total = reviews.length
    if (total === 0) return { total: 0, avg: 0, roundedAvg: 0 }
    const sum = reviews.reduce((acc, r) => acc + (Number(r.rating) || 0), 0)
    const avg = sum / total
    return { total, avg, roundedAvg: Math.round(avg) }
  }, [reviews])

  const sanitizeReviewText = (s) => {
    if (!s) return ''
    let out = String(s)
    const entities = { '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#34;': '"', '&#39;': "'", '&#x27;': "'", '&nbsp;': ' ' }
    out = out.replace(/(&lt;|&gt;|&amp;|&quot;|&#34;|&#39;|&#x27;|&nbsp;)/g, m => entities[m] || m)
    out = out.replace(/```[\s\S]*?```/g, '').replace(/```[\s\S]*$/g, '').replace(/`+/g, '')
    out = out.replace(/<\/?(code|pre)[^>]*>/gi, '').replace(/<[^>]*>/g, '')
    out = out.split('\n').filter(line => !/^\s{4,}|^\t/.test(line)).join(' ')
    out = out.replace(/;position:absolute[^}]*}/gi, '').replace(/\{[^}]*position\s*:\s*absolute[^}]*\}/gi, '')
    out = out.replace(/;[a-z-]+:[^;]*/gi, '').replace(/[a-z-]+\s*:\s*[^;]+;/gi, '')
    return out.replace(/\s+/g, ' ').trim()
  }

  // ── render ───────────────────────────────────────────────────
  return (
    <>
      <SEO
        title="Talleres de Pizza para Niños en Santiago"
        description="Talleres de pizza para niños y pizza parties en Santiago. Experiencias gastronómicas educativas donde los niños aprenden a hacer pizzas artesanales. Servicio a domicilio para cumpleaños."
        keywords="talleres pizza niños Santiago, pizza party cumpleaños, eventos infantiles Santiago, taller cocina niños, catering pizza, fiestas infantiles Chile, pizzeros en acción"
        url="/"
      />

      {/* ══════════════════════════════════════════════════
          HERO — Cinematic full-screen photo
      ══════════════════════════════════════════════════ */}
      <Box
        component="section"
        aria-label="Bienvenidos a Pablo's Pizza"
        sx={{
          minHeight: '100vh',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
          pb: { xs: 7, md: 10 },
          overflow: 'hidden',
        }}
      >
        {/* Background photo */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `url(${publicBase}images/hero-bg.jpg)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center 30%',
            transform: 'scale(1.04)',
            willChange: 'transform',
          }}
        />

        {/* Multi-layer gradient overlay */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            inset: 0,
            background: `
              linear-gradient(to top,
                rgba(0,0,0,0.97) 0%,
                rgba(0,0,0,0.78) 35%,
                rgba(0,0,0,0.45) 65%,
                rgba(0,0,0,0.25) 100%
              )
            `,
          }}
        />

        {/* Radial golden accent */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            top: '8%',
            right: '8%',
            width: { xs: 200, md: 400 },
            height: { xs: 200, md: 400 },
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255,215,0,0.1) 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />

        {/* Content */}
        <Container maxWidth="xl" sx={{ position: 'relative', zIndex: 2 }}>
          {/* Location badge */}
          <Fade in={heroLoaded} timeout={700}>
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 1.5,
                mb: { xs: 3, md: 4 },
                px: 2,
                py: 0.75,
                border: '1px solid rgba(255,215,0,0.35)',
                borderRadius: designTokens.radius.full,
                backdropFilter: 'blur(8px)',
                backgroundColor: 'rgba(0,0,0,0.2)',
              }}
            >
              <Box
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  backgroundColor: GOLD,
                  animation: prefersReducedMotion ? 'none' : 'pingDot 2s ease-in-out infinite',
                  '@keyframes pingDot': {
                    '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                    '50%': { opacity: 0.6, transform: 'scale(1.4)' },
                  },
                }}
              />
              <Typography
                variant="caption"
                sx={{ color: 'rgba(255,255,255,0.85)', letterSpacing: 3, fontSize: '0.68rem', fontWeight: 700 }}
              >
                SANTIAGO · CHILE
              </Typography>
            </Box>
          </Fade>

          {/* Giant headline */}
          <Box ref={heroTitleRef} sx={{ opacity: animationsEnabled ? undefined : 1 }}>
            <Typography
              component="h1"
              sx={{
                fontSize: { xs: '3.8rem', sm: '5.5rem', md: '8rem', lg: '10rem' },
                fontWeight: 900,
                lineHeight: 0.88,
                letterSpacing: { xs: '-0.03em', md: '-0.05em' },
                mb: { xs: 3, md: 4 },
                color: '#fff',
                textTransform: 'uppercase',
              }}
            >
              CREAMOS
              <br />
              <Box
                component="span"
                sx={{
                  background: GOLD_GRADIENT,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 2,
                }}
              >
                MAGIA
                <AutoAwesome
                  aria-hidden="true"
                  sx={{
                    fontSize: { xs: '1.5rem', md: '3rem' },
                    color: GOLD,
                    WebkitTextFillColor: 'initial',
                    verticalAlign: 'middle',
                    animation: prefersReducedMotion ? 'none' : 'sparkle 3s ease-in-out infinite',
                    '@keyframes sparkle': {
                      '0%, 100%': { opacity: 1, transform: 'rotate(0deg) scale(1)' },
                      '50%': { opacity: 0.7, transform: 'rotate(20deg) scale(1.15)' },
                    },
                  }}
                />
              </Box>
            </Typography>
          </Box>

          {/* Subtitle */}
          <Box ref={heroSubtitleRef} sx={{ opacity: animationsEnabled ? undefined : 1 }}>
            <Typography
              variant="h5"
              sx={{
                color: 'rgba(255,255,255,0.65)',
                fontWeight: 400,
                mb: { xs: 4, md: 5 },
                maxWidth: { xs: '100%', md: 580 },
                lineHeight: 1.55,
                fontSize: { xs: '1rem', sm: '1.15rem', md: '1.25rem' },
              }}
            >
              Talleres de pizza artesanal y pizza party para niños en Santiago.
              Cada evento, un recuerdo imborrable.
            </Typography>
          </Box>

          {/* CTAs */}
          <Box ref={heroCtaRef} sx={{ opacity: animationsEnabled ? undefined : 1 }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: { xs: 5, md: 6 } }}>
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/agendar')}
                endIcon={<ArrowForward />}
                sx={{
                  px: { xs: 4, md: 5 },
                  py: 1.75,
                  fontSize: '1rem',
                  fontWeight: 800,
                  background: GOLD_GRADIENT,
                  color: '#000',
                  borderRadius: designTokens.radius.xl,
                  boxShadow: '0 8px 32px rgba(255,215,0,0.4)',
                  letterSpacing: 0.3,
                  '&:hover': {
                    transform: 'translateY(-3px)',
                    boxShadow: '0 14px 44px rgba(255,215,0,0.5)',
                  },
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                }}
              >
                Agendar Evento
              </Button>
              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate('/servicios')}
                sx={{
                  px: 4,
                  py: 1.75,
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: 'rgba(255,255,255,0.85)',
                  borderColor: 'rgba(255,255,255,0.25)',
                  borderRadius: designTokens.radius.xl,
                  backdropFilter: 'blur(10px)',
                  '&:hover': {
                    borderColor: 'rgba(255,215,0,0.5)',
                    color: GOLD,
                    backgroundColor: 'rgba(255,215,0,0.06)',
                  },
                  transition: 'all 0.2s ease',
                }}
              >
                Ver Servicios
              </Button>
            </Stack>
          </Box>

          {/* Stats bar */}
          <Box
            ref={heroStatsRef}
            sx={{ opacity: animationsEnabled ? undefined : 1 }}
          >
            <Box
              sx={{
                display: 'flex',
                gap: { xs: 4, md: 6 },
                pt: 4,
                borderTop: '1px solid rgba(255,255,255,0.1)',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              {[
                { number: stats.kidsServed, label: 'Niños felices', icon: <Favorite sx={{ fontSize: 16, color: GOLD }} /> },
                { number: '50+', label: 'Eventos exitosos', icon: <EmojiEvents sx={{ fontSize: 16, color: GOLD }} /> },
                { number: '★ 5.0', label: 'Calificación', icon: <Star sx={{ fontSize: 16, color: GOLD }} /> },
              ].map(({ number, label, icon }) => (
                <Box key={label} sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    {icon}
                    <Typography
                      sx={{
                        fontSize: { xs: '1.4rem', md: '1.75rem' },
                        fontWeight: 900,
                        color: '#fff',
                        lineHeight: 1,
                        letterSpacing: '-0.02em',
                      }}
                    >
                      {number}
                    </Typography>
                  </Box>
                  <Typography
                    variant="caption"
                    sx={{ color: 'rgba(255,255,255,0.45)', letterSpacing: 1.5, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}
                  >
                    {label}
                  </Typography>
                </Box>
              ))}

              {/* WhatsApp link */}
              <Box sx={{ ml: 'auto', display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1.5 }}>
                <Box
                  component="a"
                  href="https://wa.me/56989424566"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Contactar por WhatsApp"
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 2.5,
                    py: 1,
                    borderRadius: designTokens.radius.full,
                    border: '1px solid rgba(37,211,102,0.35)',
                    color: '#25D366',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      backgroundColor: 'rgba(37,211,102,0.1)',
                      borderColor: '#25D366',
                    },
                  }}
                >
                  <WhatsApp sx={{ fontSize: 18 }} />
                  +56 9 8942 4566
                </Box>
              </Box>
            </Box>
          </Box>
        </Container>

        {/* Fade into next section */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 140,
            background: `linear-gradient(to bottom, transparent 0%, ${BG.s1} 100%)`,
            zIndex: 1,
          }}
        />
      </Box>

      <SectionDivider />

      {/* ══════════════════════════════════════════════════
          SECCIÓN 1 — PIZZEROS EN ACCIÓN
      ══════════════════════════════════════════════════ */}
      <AnimatedSection>
        <Box
          component="section"
          aria-label="Talleres Pizzeros en Acción"
          sx={{
            minHeight: { xs: 'auto', md: '100vh' },
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            backgroundColor: BG.s1,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Background image — right side */}
          <Box
            aria-hidden="true"
            sx={{
              position: 'absolute',
              top: 0, right: 0, bottom: 0,
              width: { xs: '0%', md: '55%' },
              backgroundImage: `url(${publicBase}images/talleres/taller-corporativo.webp)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center left',
              zIndex: 0,
              display: { xs: 'none', md: 'block' },
            }}
          />
          {/* Gradient fade */}
          <Box
            aria-hidden="true"
            sx={{
              position: 'absolute',
              top: 0, right: 0, bottom: 0,
              width: { xs: '0%', md: '55%' },
              background: `linear-gradient(to right, ${BG.s1} 0%, rgba(13,13,13,0.5) 45%, rgba(13,13,13,0) 100%)`,
              zIndex: 1,
              display: { xs: 'none', md: 'block' },
            }}
          />

          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2, py: { xs: 8, md: 10 } }}>
            <Grid container spacing={4} alignItems="center">
              <Grid item xs={12} md={6}>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5, mb: 4 }}>
                  <Box
                    sx={{
                      width: 72,
                      height: 72,
                      borderRadius: '50%',
                      background: GOLD_GRADIENT,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      boxShadow: '0 8px 24px rgba(255,215,0,0.3)',
                    }}
                  >
                    <School sx={{ fontSize: 38, color: '#000' }} />
                  </Box>
                  <Box>
                    <Typography
                      variant="h2"
                      sx={{
                        color: '#fff',
                        fontWeight: 800,
                        fontSize: { xs: '1.75rem', md: '2.25rem' },
                        lineHeight: 1.1,
                        mb: 0.75,
                      }}
                    >
                      Pizzeros en Acción
                    </Typography>
                    <Chip
                      label="EXPERIENCIA EDUCATIVA"
                      size="small"
                      sx={{
                        background: GOLD_GRADIENT,
                        color: '#000',
                        fontWeight: 700,
                        fontSize: '0.7rem',
                        letterSpacing: 0.5,
                      }}
                    />
                  </Box>
                </Box>

                <Typography
                  variant="body1"
                  sx={{ color: 'rgba(255,255,255,0.75)', mb: 3.5, lineHeight: 1.75, fontSize: { xs: '1rem', md: '1.05rem' } }}
                >
                  <Box component="span" sx={{ color: GOLD, fontWeight: 700 }}>Talleres gastronómicos a domicilio</Box>{' '}
                  donde los niños se transforman en verdaderos chefs profesionales.
                  90 minutos de amasado real con harina 00 italiana Caputo,
                  guiados por un chef con 10 años de experiencia.
                </Typography>

                {/* Features */}
                <Stack spacing={1.5} sx={{ mb: 4 }}>
                  {[
                    'Educación culinaria profesional',
                    'Chef experto guiando cada paso',
                    'Interactivo y divertido para todas las edades',
                    '100% seguro con protocolos de higiene',
                  ].map((feature) => (
                    <Box key={feature} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <CheckCircle sx={{ color: '#4CAF50', fontSize: 20, flexShrink: 0 }} />
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.82)', fontWeight: 500, fontSize: '0.95rem' }}>
                        {feature}
                      </Typography>
                    </Box>
                  ))}
                </Stack>

                {/* Price */}
                <Box
                  sx={{
                    p: 3,
                    background: 'rgba(255,215,0,0.07)',
                    border: `1px solid rgba(255,215,0,0.3)`,
                    borderRadius: 2,
                    mb: 4,
                  }}
                >
                  <Typography variant="h3" sx={{ color: GOLD, fontWeight: 900, lineHeight: 1 }}>
                    $13.500{' '}
                    <Typography component="span" variant="body1" sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 400 }}>
                      por niño
                    </Typography>
                  </Typography>
                  <Typography sx={{ color: 'rgba(255,255,255,0.65)', fontWeight: 500, mt: 1, fontSize: '0.9rem' }}>
                    Desde ${PIZZEROS_TIERS[PIZZEROS_TIERS.length - 1].price.toLocaleString('es-CL')} con grupos de 20+ niños
                  </Typography>
                </Box>

                {/* CTAs */}
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate('/agendar')}
                    sx={{
                      background: GOLD_GRADIENT,
                      color: '#000',
                      fontWeight: 700,
                      px: 4,
                      py: 1.5,
                      borderRadius: designTokens.radius.xl,
                      '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 8px 24px rgba(255,215,0,0.35)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Cotizar Evento
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => navigate('/servicios')}
                    sx={{
                      borderColor: 'rgba(255,255,255,0.25)',
                      color: 'rgba(255,255,255,0.8)',
                      borderRadius: designTokens.radius.xl,
                      px: 4,
                      py: 1.5,
                      '&:hover': { borderColor: GOLD, color: GOLD, backgroundColor: 'rgba(255,215,0,0.06)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Ver Menú
                  </Button>
                </Stack>
              </Grid>

              {/* Mobile image */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'block', md: 'none' } }}>
                <Box
                  component="img"
                  src={`${publicBase}images/talleres/taller-corporativo.webp`}
                  loading="lazy"
                  alt="Niños participando en taller de pizza Pizzeros en Acción"
                  sx={{
                    width: '100%',
                    height: 280,
                    objectFit: 'cover',
                    borderRadius: 2,
                    border: '1px solid rgba(255,215,0,0.15)',
                  }}
                />
              </Grid>

              <Grid item md={6} sx={{ display: { xs: 'none', md: 'block' } }} />
            </Grid>
          </Container>
        </Box>
      </AnimatedSection>

      <SectionDivider />

      {/* ══════════════════════════════════════════════════
          SECCIÓN 2 — PIZZA PARTY
      ══════════════════════════════════════════════════ */}
      <AnimatedSection delay={80}>
        <Box
          component="section"
          aria-label="Pizza Party — Catering gourmet"
          sx={{
            minHeight: { xs: 'auto', md: '100vh' },
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            backgroundColor: BG.s2,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Background image — left side */}
          <Box
            aria-hidden="true"
            sx={{
              position: 'absolute',
              top: 0, left: 0, bottom: 0,
              width: { xs: '0%', md: '55%' },
              backgroundImage: `url(${publicBase}images/pizza-party.webp)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center right',
              zIndex: 0,
              display: { xs: 'none', md: 'block' },
            }}
          />
          {/* Gradient fade */}
          <Box
            aria-hidden="true"
            sx={{
              position: 'absolute',
              top: 0, left: 0, bottom: 0,
              width: { xs: '0%', md: '55%' },
              background: `linear-gradient(to left, ${BG.s2} 0%, rgba(17,17,17,0.5) 45%, rgba(17,17,17,0) 100%)`,
              zIndex: 1,
              display: { xs: 'none', md: 'block' },
            }}
          />

          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2, py: { xs: 8, md: 10 } }}>
            <Grid container spacing={4} alignItems="center">
              {/* Mobile image */}
              <Grid item xs={12} md={6} sx={{ display: { xs: 'block', md: 'none' } }}>
                <Box
                  component="img"
                  src={`${publicBase}images/pizza-party.webp`}
                  loading="lazy"
                  alt="Pizza Party — Catering gourmet con pizzas artesanales"
                  sx={{
                    width: '100%',
                    height: 280,
                    objectFit: 'cover',
                    borderRadius: 2,
                    border: '1px solid rgba(255,215,0,0.15)',
                  }}
                />
              </Grid>

              <Grid item md={6} sx={{ display: { xs: 'none', md: 'block' } }} />

              {/* Content */}
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5, mb: 4 }}>
                  <Box
                    sx={{
                      width: 72,
                      height: 72,
                      borderRadius: '50%',
                      background: GOLD_GRADIENT,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      boxShadow: '0 8px 24px rgba(255,215,0,0.3)',
                    }}
                  >
                    <Celebration sx={{ fontSize: 38, color: '#000' }} />
                  </Box>
                  <Box>
                    <Typography
                      variant="h2"
                      sx={{ color: '#fff', fontWeight: 800, fontSize: { xs: '1.75rem', md: '2.25rem' }, lineHeight: 1.1, mb: 0.75 }}
                    >
                      Pizza Party
                    </Typography>
                    <Chip
                      label="CATERING GOURMET"
                      size="small"
                      sx={{ background: GOLD_GRADIENT, color: '#000', fontWeight: 700, fontSize: '0.7rem', letterSpacing: 0.5 }}
                    />
                  </Box>
                </Box>

                <Typography
                  variant="body1"
                  sx={{ color: 'rgba(255,255,255,0.75)', mb: 3.5, lineHeight: 1.75, fontSize: { xs: '1rem', md: '1.05rem' } }}
                >
                  <Box component="span" sx={{ color: GOLD, fontWeight: 700 }}>Catering gourmet especializado</Box>{' '}
                  en pizzas artesanales para eventos con preparación en vivo.
                  Servicio integral a domicilio — los padres no cocinan ni limpian,
                  el equipo llega 45 min antes y lo deja todo listo.
                </Typography>

                {/* Price */}
                <Box
                  sx={{
                    p: 3,
                    background: 'rgba(255,215,0,0.07)',
                    border: `1px solid rgba(255,215,0,0.3)`,
                    borderRadius: 2,
                    mb: 3.5,
                  }}
                >
                  <Typography variant="h3" sx={{ color: GOLD, fontWeight: 900, lineHeight: 1 }}>
                    $11.990{' '}
                    <Typography component="span" variant="body1" sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 400 }}>
                      por persona
                    </Typography>
                  </Typography>
                  <Typography sx={{ color: 'rgba(255,255,255,0.65)', fontWeight: 500, mt: 1, fontSize: '0.9rem' }}>
                    Mínimo 15 personas · Descuentos garantizados
                  </Typography>
                </Box>

                {/* Features */}
                <Stack spacing={1.5} sx={{ mb: 4 }}>
                  {[
                    'Catering premium todo incluido',
                    'Preparación en vivo espectacular',
                    'Ingredientes gourmet importados',
                    'Atención personalizada garantizada',
                  ].map((feature) => (
                    <Box key={feature} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <CheckCircle sx={{ color: '#4CAF50', fontSize: 20, flexShrink: 0 }} />
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.82)', fontWeight: 500, fontSize: '0.95rem' }}>
                        {feature}
                      </Typography>
                    </Box>
                  ))}
                </Stack>

                {/* CTAs */}
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate('/agendar')}
                    sx={{
                      background: GOLD_GRADIENT,
                      color: '#000',
                      fontWeight: 700,
                      px: 4,
                      py: 1.5,
                      borderRadius: designTokens.radius.xl,
                      '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 8px 24px rgba(255,215,0,0.35)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Cotizar Evento
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => navigate('/servicios')}
                    sx={{
                      borderColor: 'rgba(255,215,0,0.35)',
                      color: GOLD,
                      borderRadius: designTokens.radius.xl,
                      px: 4,
                      py: 1.5,
                      '&:hover': { borderColor: GOLD, backgroundColor: 'rgba(255,215,0,0.08)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Ver Menú
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </Container>
        </Box>
      </AnimatedSection>

      <SectionDivider />

      {/* ══════════════════════════════════════════════════
          SECCIÓN 3 — TESTIMONIOS
      ══════════════════════════════════════════════════ */}
      <AnimatedSection>
        <Box
          component="section"
          aria-label="Testimonios de clientes"
          sx={{
            py: { xs: 8, md: 12 },
            backgroundColor: BG.s3,
          }}
        >
          <Container maxWidth="md">
            {/* Header — editorial asymmetric layout */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'space-between',
                mb: { xs: 5, md: 7 },
                pb: 4,
                borderBottom: '1px solid rgba(255,255,255,0.07)',
                flexWrap: 'wrap',
                gap: 3,
              }}
            >
              <Box>
                <Typography
                  variant="overline"
                  sx={{ color: GOLD, letterSpacing: 5, fontWeight: 700, fontSize: '0.68rem', mb: 1.5, display: 'block' }}
                >
                  LO QUE DICEN
                </Typography>
                <Typography
                  variant="h2"
                  sx={{ color: '#fff', fontWeight: 900, fontSize: { xs: '2rem', md: '2.75rem' }, lineHeight: 1 }}
                >
                  Nuestros
                  <br />
                  Clientes
                </Typography>
              </Box>

              {/* Big rating number — editorial accent */}
              <Box sx={{ textAlign: 'right' }}>
                <Typography
                  sx={{
                    fontFamily: 'Georgia, "Times New Roman", serif',
                    fontSize: { xs: '3.5rem', md: '5rem' },
                    fontWeight: 700,
                    color: GOLD,
                    lineHeight: 1,
                    letterSpacing: '-0.03em',
                  }}
                >
                  {reviewStats.avg > 0 ? reviewStats.avg.toFixed(1) : '5.0'}
                </Typography>
                <Rating
                  value={reviewStats.roundedAvg || 5}
                  readOnly
                  size="small"
                  sx={{ color: GOLD, mt: 0.5 }}
                  aria-label={`Calificación promedio: ${reviewStats.avg.toFixed(1)} de 5 estrellas`}
                />
                <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.4)', letterSpacing: 2, fontSize: '0.65rem', mt: 0.5 }}>
                  {reviewStats.total > 0 ? `${reviewStats.total} RESEÑAS` : 'CALIFICACIÓN'}
                </Typography>
              </Box>
            </Box>

            {/* Loading */}
            {reviewsLoading && (
              <Box sx={{ maxWidth: 700, mx: 'auto' }}>
                <Skeleton variant="rectangular" height={320}
                  sx={{ borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.05)' }} />
              </Box>
            )}

            {/* Error */}
            {reviewsError && !reviewsLoading && (
              <Alert severity="error" sx={{ backgroundColor: 'rgba(244,67,54,0.1)', color: '#ef9a9a', border: '1px solid rgba(244,67,54,0.25)' }}>
                No pudimos cargar los testimonios. Por favor intenta más tarde.
              </Alert>
            )}

            {/* Empty state */}
            {!reviewsLoading && !reviewsError && reviews.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="h6" sx={{ color: 'rgba(255,255,255,0.6)', mb: 3 }}>
                  ¡Sé el primero en dejarnos tu opinión!
                </Typography>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/testimonios')}
                  sx={{ borderColor: 'rgba(255,215,0,0.4)', color: GOLD, '&:hover': { borderColor: GOLD, backgroundColor: 'rgba(255,215,0,0.08)' } }}
                >
                  Dejar Testimonio
                </Button>
              </Box>
            )}

            {/* Carousel */}
            {!reviewsLoading && !reviewsError && reviews.length > 0 && (
              <>
                <Box sx={{ maxWidth: 740, mx: 'auto', position: 'relative' }}>
                  <Swiper
                    modules={[Autoplay, Pagination, Navigation]}
                    spaceBetween={0}
                    slidesPerView={1}
                    autoplay={{ delay: 6500, disableOnInteraction: false, pauseOnMouseEnter: true }}
                    pagination={{ clickable: true, dynamicBullets: true }}
                    navigation={{ nextEl: '.testimonial-next', prevEl: '.testimonial-prev' }}
                    loop={reviews.length > 1}
                    style={{ background: 'transparent', paddingBottom: '52px' }}
                    keyboard={{ enabled: true, onlyInViewport: true }}
                    a11y={{
                      enabled: true,
                      prevSlideMessage: 'Testimonio anterior',
                      nextSlideMessage: 'Siguiente testimonio',
                    }}
                  >
                    {reviews.map((t, index) => (
                      <SwiperSlide key={t.id || `${t.name}-${index}`} style={{ background: 'transparent' }}>
                        <TestimonialCard testimonial={t} sanitizeReviewText={sanitizeReviewText} />
                      </SwiperSlide>
                    ))}
                  </Swiper>

                  {/* Nav buttons — solid dark, no backdropFilter */}
                  {['testimonial-prev', 'testimonial-next'].map((cls, i) => (
                    <IconButton
                      key={cls}
                      className={cls}
                      aria-label={i === 0 ? 'Ver testimonio anterior' : 'Ver siguiente testimonio'}
                      sx={{
                        position: 'absolute',
                        [i === 0 ? 'left' : 'right']: { xs: -12, sm: -28 },
                        top: '42%',
                        transform: 'translateY(-50%)',
                        zIndex: 10,
                        backgroundColor: '#1a1a1a',
                        border: `1px solid rgba(255,215,0,0.35)`,
                        color: GOLD,
                        width: { xs: 40, sm: 46 },
                        height: { xs: 40, sm: 46 },
                        '&:hover': {
                          backgroundColor: GOLD,
                          color: '#000',
                          borderColor: GOLD,
                          transform: 'translateY(-50%) scale(1.1)',
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <ArrowForward sx={{ transform: i === 0 ? 'rotate(180deg)' : 'none', fontSize: { xs: 16, sm: 20 } }} />
                    </IconButton>
                  ))}
                </Box>

                <Box sx={{ textAlign: 'center', mt: 6 }}>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/testimonios')}
                    endIcon={<ArrowForward />}
                    size="large"
                    sx={{
                      px: 5,
                      py: 1.5,
                      borderColor: 'rgba(255,215,0,0.35)',
                      color: 'rgba(255,255,255,0.8)',
                      fontWeight: 600,
                      borderRadius: designTokens.radius.xl,
                      '&:hover': { borderColor: GOLD, color: GOLD, backgroundColor: 'rgba(255,215,0,0.06)' },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Ver Más Testimonios
                  </Button>
                </Box>
              </>
            )}
          </Container>

          {/* Swiper CSS — fully transparent, no grey anywhere */}
          <style>{`
            .swiper-button-next, .swiper-button-prev { display: none !important; }
            .swiper, .swiper-wrapper, .swiper-slide {
              background: transparent !important;
            }
            .swiper-pagination {
              background: transparent !important;
            }
            .swiper-pagination-bullet {
              background: rgba(255, 255, 255, 0.18) !important;
              opacity: 1 !important;
              width: 7px !important;
              height: 7px !important;
              transition: all 0.3s ease !important;
            }
            .swiper-pagination-bullet-active {
              background: #FFD700 !important;
              width: 22px !important;
              border-radius: 4px !important;
            }
            .swiper-slide {
              opacity: 0 !important;
              transition: opacity 0.4s ease-in-out !important;
            }
            .swiper-slide-active { opacity: 1 !important; }
          `}</style>
        </Box>
      </AnimatedSection>

      <SectionDivider />

      {/* ══════════════════════════════════════════════════
          SECCIÓN 4 — GALERÍA ROLLING
      ══════════════════════════════════════════════════ */}
      <AnimatedSection delay={80}>
        <Box
          component="section"
          aria-label="Galería de eventos"
          sx={{
            py: { xs: 8, md: 12 },
            backgroundColor: BG.s4,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* LightRays */}
          <Box
            aria-hidden="true"
            sx={{ position: 'absolute', inset: 0, zIndex: 0, opacity: 0.5 }}
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
            <Box sx={{ textAlign: 'center', mb: { xs: 5, md: 7 } }}>
              <Typography
                variant="overline"
                sx={{ color: GOLD, letterSpacing: 4, fontWeight: 700, fontSize: '0.75rem', mb: 1.5, display: 'block' }}
              >
                NUESTROS EVENTOS
              </Typography>
              <Typography
                variant="h2"
                sx={{ color: '#fff', fontWeight: 900, mb: 2, fontSize: { xs: '2rem', md: '3rem' }, lineHeight: 1.1 }}
              >
                Así son nuestros eventos
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.5)', maxWidth: 500, mx: 'auto' }}>
                Capturamos cada sonrisa, cada momento de aprendizaje y diversión
              </Typography>
            </Box>

            {galleryLoading ? (
              <Box sx={{ textAlign: 'center', py: 6 }}>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.4)' }}>
                  Cargando galería...
                </Typography>
              </Box>
            ) : (
              <RollingGallery
                autoplay={true}
                pauseOnHover={true}
                images={getGalleryImageUrls(galleryPhotos)}
              />
            )}

            <Box sx={{ textAlign: 'center', mt: 6 }}>
              <Button
                variant="outlined"
                size="large"
                endIcon={<ArrowForward />}
                onClick={() => navigate('/galeria')}
                sx={{
                  borderColor: 'rgba(255,215,0,0.4)',
                  color: GOLD,
                  fontWeight: 700,
                  px: 5,
                  py: 1.5,
                  borderRadius: designTokens.radius.xl,
                  '&:hover': { borderColor: GOLD, backgroundColor: 'rgba(255,215,0,0.08)' },
                  transition: 'all 0.2s ease',
                }}
              >
                Ver Galería Completa
              </Button>
            </Box>
          </Container>
        </Box>
      </AnimatedSection>

      {/* ══════════════════════════════════════════════════
          CTA FINAL — Golden
      ══════════════════════════════════════════════════ */}
      <Box
        component="section"
        aria-label="Agenda tu evento"
        sx={{
          background: GOLD_GRADIENT,
          color: '#000',
          py: { xs: 10, md: 14 },
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative circles */}
        <Box aria-hidden="true" sx={{ position: 'absolute', top: -60, right: -60, width: 280, height: 280, borderRadius: '50%', backgroundColor: 'rgba(0,0,0,0.06)', filter: 'blur(50px)' }} />
        <Box aria-hidden="true" sx={{ position: 'absolute', bottom: -40, left: -40, width: 200, height: 200, borderRadius: '50%', backgroundColor: 'rgba(0,0,0,0.04)', filter: 'blur(40px)' }} />
        {/* Subtle grid pattern */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(rgba(0,0,0,0.08) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
            opacity: 0.5,
          }}
        />

        <Container maxWidth="md" sx={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <Typography
            variant="overline"
            sx={{ letterSpacing: 4, fontWeight: 800, fontSize: '0.75rem', opacity: 0.7, mb: 2, display: 'block' }}
          >
            EMPECEMOS
          </Typography>
          <Typography variant="h2" sx={{ fontWeight: 900, mb: 2.5, fontSize: { xs: '2rem', md: '3rem' }, lineHeight: 1.1 }}>
            ¿Listo para Agendar
            <br />
            Tu Evento?
          </Typography>
          <Typography variant="h6" sx={{ mb: 6, opacity: 0.75, maxWidth: 580, mx: 'auto', fontWeight: 400, lineHeight: 1.6, fontSize: { xs: '1rem', md: '1.1rem' } }}>
            Agenda tu taller o pizza party hoy mismo. Máximo 15 niños por chef —
            atención real, no caos — y el equipo llega 45 min antes a preparar todo.
          </Typography>

          {/* Quick stats */}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={{ xs: 3, sm: 6 }}
            justifyContent="center"
            sx={{ mb: 6 }}
          >
            {[
              { number: '24h', label: 'Respuesta garantizada' },
              { number: '100%', label: 'Satisfacción garantizada' },
              { number: stats.kidsServed, label: 'Familias felices' },
            ].map(({ number, label }) => (
              <Box key={label} sx={{ textAlign: 'center' }}>
                <Typography sx={{ fontSize: { xs: '2rem', md: '2.5rem' }, fontWeight: 900, lineHeight: 1 }}>
                  {number}
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.65, mt: 0.5 }}>
                  {label}
                </Typography>
              </Box>
            ))}
          </Stack>

          {/* CTAs */}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2.5} justifyContent="center" sx={{ mb: 5 }}>
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/agendar')}
              endIcon={<Restaurant />}
              sx={{
                px: 6,
                py: 2,
                fontSize: '1.05rem',
                fontWeight: 800,
                backgroundColor: '#000',
                color: '#fff',
                borderRadius: designTokens.radius.xl,
                boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
                '&:hover': { backgroundColor: '#111', transform: 'translateY(-3px)', boxShadow: '0 14px 40px rgba(0,0,0,0.35)' },
                transition: 'all 0.2s ease',
              }}
            >
              Agendar Evento Ahora
            </Button>
            <Button
              component="a"
              href="https://wa.me/56989424566"
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              size="large"
              startIcon={<WhatsApp />}
              sx={{
                px: 5,
                py: 2,
                fontSize: '1rem',
                fontWeight: 700,
                borderWidth: 2,
                borderColor: 'rgba(0,0,0,0.3)',
                color: '#000',
                borderRadius: designTokens.radius.xl,
                '&:hover': { backgroundColor: 'rgba(0,0,0,0.08)', borderColor: '#000' },
                transition: 'all 0.2s ease',
              }}
            >
              Chat por WhatsApp
            </Button>
          </Stack>

          <Typography variant="body2" sx={{ opacity: 0.55, fontSize: '0.85rem' }}>
            +56 9 8942 4566 &nbsp;·&nbsp; Lun–Dom 9:00–20:00 &nbsp;·&nbsp; Santiago y alrededores
          </Typography>
        </Container>
      </Box>

      {/* Floating CTA */}
      {CTA_VARIANT === 'floating' && <FloatingCTA navigate={navigate} prefersReducedMotion={prefersReducedMotion} />}

      {/* Bottom-bar sticky CTA — variante A/B */}
      {CTA_VARIANT === 'bottombar' && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            zIndex: 1200,
            background: '#0d0d0d',
            borderTop: '1px solid rgba(232,182,58,0.3)',
            py: 1.5,
            px: { xs: 2, md: 4 },
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', flexShrink: 0 }}>
            Desde $9.000 por niño
          </Typography>
          <Button
            variant="contained"
            href="/agendar"
            sx={{
              bgcolor: '#e8b63a',
              color: '#0d0d0d',
              fontWeight: 700,
              px: 3,
              borderRadius: 1,
              '&:hover': { bgcolor: '#FFD700' },
            }}
          >
            Reservar fecha
          </Button>
        </Box>
      )}
    </>
  )
}
