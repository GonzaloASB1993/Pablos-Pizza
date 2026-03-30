import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Chip,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Fade,
  Grow,
  Avatar,
  Rating,
  Divider,
  useMediaQuery,
  Badge,
  Stack,
  Paper
} from '@mui/material'
import SEO from '../../components/common/SEO'
import {
  Close,
  ArrowForward,
  School,
  Celebration,
  PhotoCamera,
  Star,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  EmojiEvents,
  Favorite,
  PlayArrow
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { useNavigate } from 'react-router-dom'
import logo from '../../assets/logo.png'

// API base URL
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://main-4kqeqojbsq-uc.a.run.app'
  : 'https://main-4kqeqojbsq-uc.a.run.app'  // Use production URL for now

// All mock data removed - now using only real data from backend

// Testimonials will be loaded from backend in future implementation
const testimonials = []

// Custom hook for lazy loading images with Intersection Observer
const useLazyLoad = (ref, threshold = 0.1) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.disconnect()
        }
      },
      { threshold, rootMargin: '50px' }
    )

    observer.observe(element)

    return () => {
      if (element) {
        observer.unobserve(element)
      }
    }
  }, [ref, threshold])

  return isVisible
}

const CategoryFilter = ({ activeFilter, onFilterChange, images = [] }) => {
  const filteredCounts = {
    all: images.length,
    workshop: images.filter(img => img.category === 'workshop').length,
    party: images.filter(img => img.category === 'party').length
  }

  const filters = [
    { key: 'all', label: 'Todos', icon: PhotoCamera, count: filteredCounts.all, color: 'primary' },
    { key: 'workshop', label: 'Talleres', icon: School, count: filteredCounts.workshop, color: 'primary' },
    { key: 'party', label: 'Fiestas', icon: Celebration, count: filteredCounts.party, color: 'secondary' }
  ]

  return (
    <Box sx={{
      display: 'flex',
      gap: 2,
      flexWrap: 'wrap',
      justifyContent: 'center',
      p: 3,
      backgroundColor: 'rgba(255, 215, 0, 0.05)',
      borderRadius: '20px',
      border: '1px solid rgba(255, 215, 0, 0.1)'
    }}>
      {filters.map(({ key, label, icon: Icon, count, color }) => (
        <Badge
          key={key}
          badgeContent={count}
          color={color}
          sx={{
            '& .MuiBadge-badge': {
              right: -3,
              top: 8,
              fontSize: '0.75rem',
              fontWeight: 700
            }
          }}
        >
          <Button
            variant={activeFilter === key ? 'contained' : 'outlined'}
            startIcon={<Icon />}
            onClick={() => onFilterChange(key)}
            sx={{
              borderRadius: '30px',
              textTransform: 'none',
              fontWeight: 700,
              px: 4,
              py: 1.5,
              fontSize: '1rem',
              minWidth: '120px',
              transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
              position: 'relative',
              overflow: 'hidden',
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: '-100%',
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                transition: 'left 0.5s',
              },
              '&:hover': {
                transform: 'translateY(-3px) scale(1.02)',
                boxShadow: activeFilter === key
                  ? '0 8px 25px rgba(255, 215, 0, 0.4)'
                  : '0 8px 25px rgba(0, 0, 0, 0.15)',
                '&::before': {
                  left: '100%',
                }
              },
              '&:active': {
                transform: 'translateY(-1px) scale(0.98)',
              },
              ...(activeFilter === key && {
                background: 'linear-gradient(135deg, #FFD700 0%, #CBA900 100%)',
                boxShadow: '0 6px 20px rgba(255, 215, 0, 0.3)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #FFE55C 0%, #D4B800 100%)',
                }
              })
            }}
          >
            {label}
          </Button>
        </Badge>
      ))}
    </Box>
  )
}

const ImageCard = ({ image, onImageClick, index }) => {
  const [isHovered, setIsHovered] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)
  const cardRef = useRef(null)
  const isVisible = useLazyLoad(cardRef)

  return (
    <Grow in timeout={400 + index * 150}>
      <Card
        ref={cardRef}
        sx={{
          cursor: 'pointer',
          overflow: 'hidden',
          borderRadius: '20px',
          border: image.featured ? '2px solid #FFD700' : '1px solid rgba(0, 0, 0, 0.08)',
          position: 'relative',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          background: 'linear-gradient(145deg, #ffffff 0%, #fafafa 100%)',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: image.featured
              ? 'linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(203, 169, 0, 0.1) 100%)'
              : 'transparent',
            opacity: isHovered ? 1 : 0.5,
            transition: 'opacity 0.3s ease',
            zIndex: 0,
            pointerEvents: 'none'
          },
          '&:hover': {
            transform: 'translateY(-12px) rotateX(2deg)',
            boxShadow: image.featured
              ? '0 20px 40px rgba(255, 215, 0, 0.25), 0 0 0 1px rgba(255, 215, 0, 0.3)'
              : '0 20px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05)',
          }
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => onImageClick(image)}
      >
        {image.featured && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '4px',
              background: 'linear-gradient(90deg, #FFD700, #CBA900, #FFD700)',
              zIndex: 2
            }}
          />
        )}

        <Box sx={{ position: 'relative', overflow: 'hidden', zIndex: 1 }}>
          {isVisible ? (
            <CardMedia
              component="img"
              image={image.src}
              alt={image.title}
              loading="lazy"
              decoding="async"
              onLoad={() => setImageLoaded(true)}
              sx={{
                height: 260,
                objectFit: 'cover',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                transform: isHovered ? 'scale(1.08) rotate(0.5deg)' : 'scale(1)',
                filter: imageLoaded ? 'none' : 'blur(10px)',
                opacity: imageLoaded ? 1 : 0.6,
              }}
            />
          ) : (
            <Box
              sx={{
                height: 260,
                background: 'linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                animation: 'pulse 1.5s ease-in-out infinite'
              }}
            >
              <PhotoCamera sx={{ fontSize: 40, color: 'rgba(0,0,0,0.2)' }} />
            </Box>
          )}

          {/* Play button overlay for interaction hint */}
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              opacity: isHovered ? 1 : 0,
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              zIndex: 1,
            }}
          >
            <Box
              sx={{
                width: 60,
                height: 60,
                borderRadius: '50%',
                backgroundColor: 'rgba(255, 215, 0, 0.9)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
                transition: 'transform 0.3s ease',
                transform: isHovered ? 'scale(1)' : 'scale(0.8)',
              }}
            >
              <PlayArrow sx={{ color: '#000', fontSize: 28, ml: 0.5 }} />
            </Box>
          </Box>

          {/* Enhanced gradient overlay */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'linear-gradient(180deg, transparent 0%, transparent 40%, rgba(0,0,0,0.8) 100%)',
              opacity: isHovered ? 1 : 0.7,
              transition: 'opacity 0.3s ease',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
              p: 2,
              zIndex: 1,
            }}
          >
            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
              <Chip
                label={`${image.participants} personas`}
                size="small"
                sx={{
                  backgroundColor: 'rgba(255, 255, 255, 0.9)',
                  color: '#000',
                  fontWeight: 600,
                  fontSize: '0.75rem'
                }}
              />
              <Chip
                label={image.ageGroup}
                size="small"
                sx={{
                  backgroundColor: 'rgba(255, 215, 0, 0.9)',
                  color: '#000',
                  fontWeight: 600,
                  fontSize: '0.75rem'
                }}
              />
            </Stack>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>
              {image.date} • {image.highlight}
            </Typography>
          </Box>

          {/* Category and Featured badges */}
          <Box
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              zIndex: 2
            }}
          >
            {image.featured && (
              <Chip
                icon={<EmojiEvents />}
                label="Destacado"
                size="small"
                sx={{
                  backgroundColor: '#FFD700',
                  color: '#000',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  '& .MuiChip-icon': {
                    color: '#000'
                  }
                }}
              />
            )}
            <Chip
              label={image.category === 'workshop' ? 'Taller' : 'Fiesta'}
              size="small"
              color={image.category === 'workshop' ? 'primary' : 'secondary'}
              sx={{
                fontWeight: 700,
                backdropFilter: 'blur(10px)',
                backgroundColor: image.category === 'workshop'
                  ? 'rgba(255, 215, 0, 0.9)'
                  : 'rgba(0, 0, 0, 0.7)',
              }}
            />
          </Box>

        </Box>

        <CardContent sx={{ p: 3, position: 'relative', zIndex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 800,
                fontSize: '1.1rem',
                lineHeight: 1.3,
                flex: 1
              }}
            >
              {image.title}
            </Typography>
            {image.featured && (
              <Chip
                icon={<TrendingUp />}
                label="Popular"
                size="small"
                variant="outlined"
                sx={{
                  ml: 1,
                  borderColor: '#FFD700',
                  color: '#CBA900',
                  fontWeight: 600,
                  fontSize: '0.7rem',
                }}
              />
            )}
          </Box>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              lineHeight: 1.6,
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              mb: 2
            }}
          >
            {image.description}
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 'auto' }}>
            <Typography
              variant="caption"
              sx={{
                color: '#CBA900',
                fontWeight: 700,
                fontSize: '0.8rem'
              }}
            >
              Ver detalles →
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Grow>
  )
}

const ImageModal = ({ open, image, onClose, allImages }) => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [currentIndex, setCurrentIndex] = useState(0)

  React.useEffect(() => {
    if (image && image.allImages) {
      setCurrentIndex(0) // Start with first image of the event
    }
  }, [image])

  const handlePrevious = () => {
    if (image && image.allImages) {
      setCurrentIndex((prev) => (prev > 0 ? prev - 1 : image.allImages.length - 1))
    }
  }

  const handleNext = () => {
    if (image && image.allImages) {
      setCurrentIndex((prev) => (prev < image.allImages.length - 1 ? prev + 1 : 0))
    }
  }

  const currentImageSrc = image && image.allImages ? image.allImages[currentIndex] : null

  if (!image || !currentImageSrc) return null

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{
        sx: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          backgroundImage: 'none'
        }
      }}
    >
      <DialogContent sx={{ p: 0, position: 'relative', display: 'flex', flexDirection: 'column' }}>
        <IconButton
          onClick={onClose}
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            color: 'white',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1,
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.7)'
            }
          }}
        >
          <Close />
        </IconButton>

        {/* Navigation buttons - only show if there are multiple images */}
        {image && image.allImages && image.allImages.length > 1 && (
          <>
            <IconButton
              onClick={handlePrevious}
              sx={{
                position: 'absolute',
                left: 16,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'white',
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                zIndex: 1,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.7)'
                }
              }}
            >
              <ChevronLeft />
            </IconButton>

            <IconButton
              onClick={handleNext}
              sx={{
                position: 'absolute',
                right: 16,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'white',
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                zIndex: 1,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.7)'
                }
              }}
            >
              <ChevronRight />
            </IconButton>
          </>
        )}

        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, height: '100%' }}>
          <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
            <img
              src={currentImageSrc}
              alt={image.title}
              style={{
                maxWidth: '100%',
                maxHeight: '80vh',
                objectFit: 'contain',
                borderRadius: '8px'
              }}
            />
          </Box>

          <Box sx={{
            width: { xs: '100%', md: '450px' },
            p: 4,
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            color: 'black',
            backdropFilter: 'blur(20px)'
          }}>
            {/* Image counter */}
            <Box sx={{ mb: 2, textAlign: 'center' }}>
              <Chip
                label={`Foto ${currentIndex + 1} de ${image.allImages.length}`}
                sx={{
                  backgroundColor: 'rgba(255, 215, 0, 0.9)',
                  color: '#000',
                  fontWeight: 600,
                  fontSize: '0.8rem'
                }}
              />
            </Box>

            {/* Featured badge */}
            {image.featured && (
              <Box sx={{ mb: 2 }}>
                <Chip
                  icon={<EmojiEvents />}
                  label="Experiencia Destacada"
                  sx={{
                    backgroundColor: '#FFD700',
                    color: '#000',
                    fontWeight: 700,
                    fontSize: '0.8rem'
                  }}
                />
              </Box>
            )}

            <Typography variant="h4" gutterBottom sx={{ fontWeight: 800, mb: 2 }}>
              {image.title}
            </Typography>

            {/* Enhanced tags */}
            <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
              <Chip
                label={image.category === 'workshop' ? 'Taller Educativo' : 'Fiesta & Celebración'}
                color={image.category === 'workshop' ? 'primary' : 'secondary'}
                sx={{ fontWeight: 600 }}
              />
              <Chip
                label={`${image.participants} personas`}
                variant="outlined"
                sx={{ fontWeight: 600 }}
              />
              <Chip
                label={image.ageGroup}
                variant="outlined"
                sx={{ fontWeight: 600, borderColor: '#FFD700', color: '#CBA900' }}
              />
            </Stack>


            <Typography variant="body1" paragraph sx={{ lineHeight: 1.7, fontSize: '1.1rem' }}>
              {image.description}
            </Typography>

            {/* Event details */}
            <Box sx={{
              backgroundColor: 'rgba(255, 215, 0, 0.1)',
              borderRadius: '12px',
              p: 3,
              mb: 3
            }}>
              <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 700, color: '#CBA900' }}>
                Detalles del Evento
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Typography variant="body2">
                  <strong>Fecha:</strong> {image.date}
                </Typography>
                <Typography variant="body2">
                  <strong>Destacado por:</strong> {image.highlight}
                </Typography>
                <Typography variant="body2">
                  <strong>Grupo de edad:</strong> {image.ageGroup}
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
              💭 Testimonio destacado
            </Typography>

            {testimonials.slice(0, 1).map((testimonial, idx) => (
              <Box key={idx} sx={{
                mb: 3,
                backgroundColor: 'rgba(0, 0, 0, 0.02)',
                borderRadius: '12px',
                p: 3
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Avatar sx={{
                    width: 40,
                    height: 40,
                    backgroundColor: '#FFD700',
                    color: 'black',
                    fontWeight: 700
                  }}>
                    {testimonial.avatar}
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {testimonial.name}
                    </Typography>
                    <Rating value={testimonial.rating} size="small" readOnly />
                  </Box>
                </Box>
                <Typography
                  variant="body1"
                  sx={{
                    fontStyle: 'italic',
                    lineHeight: 1.6,
                    fontSize: '1rem',
                    color: 'text.secondary'
                  }}
                >
                  "{testimonial.comment}"
                </Typography>
              </Box>
            ))}

            {/* Enhanced action buttons */}
            <Stack spacing={2}>
              <Button
                variant="contained"
                size="large"
                fullWidth
                endIcon={<ArrowForward />}
                onClick={() => {
                  onClose()
                  window.location.href = '/agendar'
                }}
                sx={{
                  py: 1.5,
                  borderRadius: '12px',
                  fontWeight: 700,
                  textTransform: 'none',
                  fontSize: '1.1rem',
                  background: 'linear-gradient(135deg, #FFD700 0%, #CBA900 100%)',
                  color: '#000',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #FFE55C 0%, #D4B800 100%)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 6px 20px rgba(255, 215, 0, 0.4)'
                  }
                }}
              >
                Agendar Experiencia Similar
              </Button>

              <Button
                variant="outlined"
                size="large"
                fullWidth
                onClick={() => {
                  onClose()
                  window.location.href = '/contacto'
                }}
                sx={{
                  py: 1.5,
                  borderRadius: '12px',
                  fontWeight: 700,
                  textTransform: 'none',
                  fontSize: '1.1rem',
                  borderColor: '#FFD700',
                  color: '#CBA900',
                  borderWidth: '2px',
                  '&:hover': {
                    borderColor: '#CBA900',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    transform: 'translateY(-2px)'
                  }
                }}
              >
                Solicitar Más Información
              </Button>
            </Stack>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  )
}

// Cantidad de imágenes a mostrar inicialmente y por cada "cargar más"
const IMAGES_PER_PAGE = 6

export default function GalleryPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState('all')
  const [selectedImage, setSelectedImage] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [galleryImages, setGalleryImages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [visibleCount, setVisibleCount] = useState(IMAGES_PER_PAGE)

  useEffect(() => {
    loadGalleryImages()
  }, [])

  const loadGalleryImages = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_BASE_URL}/api/gallery/public`)

      // Transform events with images to expected format
      const transformedImages = response.data.map(item => ({
        id: item.id,
        src: item.images?.[0] || logo, // Use first image as cover
        allImages: item.images || [logo], // Store all images for navigation
        title: item.title,
        category: item.category === 'workshop' ? 'workshop' : 'party',
        description: item.description,
        date: item.date ? new Date(item.date).toLocaleDateString('es-ES', {
          year: 'numeric',
          month: 'long'
        }) : 'Fecha no especificada',
        participants: item.participants || 0,
        featured: item.featured || false,
        highlight: item.highlight || 'Experiencia única',
        ageGroup: item.age_group || 'Todas las edades'
      }))

      setGalleryImages(transformedImages)
    } catch (error) {
      console.error('Error loading gallery:', error)
      setError('Error al cargar la galería')
      // No fallback - show empty gallery with error message
      setGalleryImages([])
    } finally {
      setLoading(false)
    }
  }

  const filteredImages = activeFilter === 'all'
    ? galleryImages
    : galleryImages.filter(img => img.category === activeFilter)

  // Imágenes visibles (paginadas)
  const visibleImages = filteredImages.slice(0, visibleCount)
  const hasMoreImages = visibleCount < filteredImages.length

  // Reset visible count when filter changes
  const handleFilterChange = (filter) => {
    setActiveFilter(filter)
    setVisibleCount(IMAGES_PER_PAGE)
  }

  const loadMoreImages = () => {
    setVisibleCount(prev => prev + IMAGES_PER_PAGE)
  }

  const handleImageClick = (image) => {
    setSelectedImage(image)
    setCurrentImageIndex(0) // Start with first image
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setSelectedImage(null)
    setCurrentImageIndex(0)
  }

  const handleNextImage = () => {
    if (selectedImage && currentImageIndex < selectedImage.allImages.length - 1) {
      setCurrentImageIndex(currentImageIndex + 1)
    }
  }

  const handlePrevImage = () => {
    if (selectedImage && currentImageIndex > 0) {
      setCurrentImageIndex(currentImageIndex - 1)
    }
  }

  return (
    <Box>
      <SEO
        title="Galería de Eventos y Talleres"
        description="Mira las fotos de nuestros talleres de pizza para niños y pizza parties en Santiago. Momentos mágicos, sonrisas y diversión en cada evento."
        keywords="fotos taller pizza niños, galería pizza party, eventos infantiles fotos, cumpleaños pizza fotos, momentos talleres cocina"
        url="/galeria"
      />
      {/* Enhanced Hero Section */}
      <Box sx={{
        background: 'linear-gradient(135deg, #FFD700 0%, #CBA900 50%, #B8860B 100%)',
        color: '#000',
        py: { xs: 4, md: 6 },
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center'
      }}>
        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2 }}>
          <Fade in timeout={1000}>
            <Box sx={{ textAlign: 'center', position: 'relative' }}>

              <Typography
                variant="h1"
                sx={{
                  fontWeight: 900,
                  fontSize: { xs: '2.5rem', md: '4rem' },
                  mb: 3,
                  textShadow: '2px 2px 4px rgba(0,0,0,0.1)',
                  background: 'linear-gradient(45deg, #000, #333)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                Galería de Eventos
              </Typography>

              <Typography
                variant="h4"
                sx={{
                  mb: 4,
                  fontWeight: 600,
                  color: 'rgba(0,0,0,0.8)',
                  lineHeight: 1.4
                }}
              >
                Descubre la magia de nuestros talleres y celebraciones
              </Typography>


            </Box>
          </Fade>
        </Container>

        {/* Enhanced background decorations */}
        <Box
          sx={{
            position: 'absolute',
            top: '-20%',
            right: '-10%',
            width: '600px',
            height: '600px',
            background: 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 40%, transparent 70%)',
            borderRadius: '50%',
            animation: 'float 6s ease-in-out infinite',
            zIndex: 1
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: '-15%',
            left: '-8%',
            width: '400px',
            height: '400px',
            background: 'radial-gradient(circle, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.05) 40%, transparent 70%)',
            borderRadius: '50%',
            animation: 'float 8s ease-in-out infinite reverse',
            zIndex: 1
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            top: '30%',
            left: '10%',
            width: '200px',
            height: '200px',
            background: 'linear-gradient(45deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05))',
            borderRadius: '30% 70% 70% 30% / 30% 30% 70% 70%',
            animation: 'morph 10s ease-in-out infinite',
            zIndex: 1
          }}
        />

        {/* CSS for animations */}
        <style>{`
          @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(5deg); }
          }
          @keyframes morph {
            0%, 100% { border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%; }
            25% { border-radius: 58% 42% 75% 25% / 76% 46% 54% 24%; }
            50% { border-radius: 50% 50% 33% 67% / 55% 27% 73% 45%; }
            75% { border-radius: 33% 67% 58% 42% / 63% 68% 32% 37%; }
          }
          @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 0.3; }
          }
        `}</style>
      </Box>

      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 8 } }}>
        {/* Category Filters */}
        <Box sx={{ mb: 6 }}>
          <Typography variant="h4" align="center" gutterBottom sx={{ fontWeight: 700 }}>
            Explora Nuestros Eventos
          </Typography>
          <Typography variant="body1" align="center" color="text.secondary" sx={{ mb: 4 }}>
            Filtra por tipo de evento para encontrar la inspiración perfecta para tu próxima celebración
          </Typography>
          <CategoryFilter activeFilter={activeFilter} onFilterChange={handleFilterChange} images={galleryImages} />
        </Box>

        {/* All Images Gallery with Uniform Layout */}
        <Box sx={{ mb: 6 }}>
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 4, textAlign: 'center' }}>
            🍕 Nuestras Experiencias
          </Typography>

          {loading ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">
                Cargando galería...
              </Typography>
            </Box>
          ) : error ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="error" gutterBottom>
                {error}
              </Typography>
              <Button variant="outlined" onClick={loadGalleryImages}>
                Reintentar
              </Button>
            </Box>
          ) : filteredImages.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">
                No hay eventos en la galería aún.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Los eventos aparecerán aquí una vez que sean completados y publicados por nuestro equipo.
              </Typography>
            </Box>
          ) : (
            <>
              {/* Uniform grid with featured items shown first */}
              <Grid container spacing={3}>
                {[
                  // Featured items first
                  ...visibleImages.filter(img => img.featured),
                  // Non-featured items after
                  ...visibleImages.filter(img => !img.featured)
                ].map((image, index) => (
                  <Grid item xs={12} sm={6} md={4} key={image.id}>
                    <ImageCard
                      image={image}
                      onImageClick={handleImageClick}
                      index={index}
                    />
                  </Grid>
                ))}
              </Grid>

              {/* Load More Button */}
              {hasMoreImages && (
                <Box sx={{ textAlign: 'center', mt: 6 }}>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={loadMoreImages}
                    sx={{
                      borderRadius: '25px',
                      px: 4,
                      py: 1.5,
                      fontWeight: 600,
                      textTransform: 'none',
                      borderColor: '#FFD700',
                      color: '#CBA900',
                      '&:hover': {
                        borderColor: '#CBA900',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        transform: 'translateY(-2px)'
                      }
                    }}
                  >
                    Ver Más Experiencias
                  </Button>
                </Box>
              )}
            </>
          )}
        </Box>


        {/* Enhanced Call to Action */}
        <Paper sx={{
          mt: 8,
          p: 6,
          borderRadius: 6,
          textAlign: 'center',
          background: 'linear-gradient(135deg, #FFD700 0%, #CBA900 100%)',
          color: '#000',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'url("data:image/svg+xml,%3Csvg width="40" height="40" xmlns="http://www.w3.org/2000/svg"%3E%3Cdefs%3E%3Cpattern id="dots" width="40" height="40" patternUnits="userSpaceOnUse"%3E%3Ccircle cx="20" cy="20" r="2" fill="rgba(0,0,0,0.1)"/%3E%3C/pattern%3E%3C/defs%3E%3Crect width="100%25" height="100%25" fill="url(%23dots)" /%3E%3C/svg%3E")',
            opacity: 0.3
          }
        }}>
          <Box sx={{ position: 'relative', zIndex: 1 }}>
            <Typography variant="h3" sx={{ fontWeight: 900, mb: 2 }}>
              ¿Listo para crear recuerdos inolvidables?
            </Typography>
            <Typography variant="h6" sx={{ mb: 4, opacity: 0.8, maxWidth: '600px', mx: 'auto' }}>
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
                  bgcolor: '#000',
                  color: '#FFD700',
                  px: 4,
                  py: 2,
                  borderRadius: 3,
                  fontWeight: 800,
                  fontSize: '1.2rem',
                  minWidth: '200px',
                  boxShadow: '0 8px 25px rgba(0,0,0,0.3)',
                  '&:hover': {
                    bgcolor: '#333',
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 35px rgba(0,0,0,0.4)'
                  }
                }}
              >
                Agendar Evento
              </Button>

              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate('/servicios')}
                sx={{
                  borderColor: '#000',
                  color: '#000',
                  px: 4,
                  py: 2,
                  borderRadius: 3,
                  fontWeight: 700,
                  fontSize: '1.1rem',
                  minWidth: '180px',
                  borderWidth: 2,
                  '&:hover': {
                    bgcolor: 'rgba(0,0,0,0.1)',
                    borderWidth: 2,
                    transform: 'translateY(-4px)'
                  }
                }}
              >
                Ver Servicios
              </Button>
            </Box>

            {/* Quick Contact Options */}
            <Box sx={{
              display: 'flex',
              gap: 4,
              justifyContent: 'center',
              flexWrap: 'wrap',
              opacity: 0.8
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Star sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  5★ Satisfacción garantizada
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <School sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  2000+ Niños felices
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Celebration sx={{ fontSize: 20 }} />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  500+ Eventos realizados
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>
      </Container>

      {/* Image Modal */}
      <ImageModal
        open={modalOpen}
        image={selectedImage}
        onClose={handleCloseModal}
        allImages={filteredImages}
      />
    </Box>
  )
}
