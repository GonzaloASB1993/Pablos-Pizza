import React, { useEffect, useState, useRef, useMemo } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Avatar,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  Fade,
  IconButton,
  useTheme,
  useMediaQuery
} from '@mui/material'
import SEO from '../../components/common/SEO'
import Star from '@mui/icons-material/Star'
import StarBorder from '@mui/icons-material/StarBorder'
import PhotoCamera from '@mui/icons-material/PhotoCamera'
import { addTestimonial, listenTestimonials } from '../../services/testimonialsService'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import { designTokens } from '../../utils/theme'

// Las reseñas se cargan desde Firestore. Si no hay aprobadas, mostramos un estado vacío.

const Stars = ({ value }) => (
  <Box sx={{ display: 'flex', gap: 0.5 }}>
    {Array.from({ length: 5 }).map((_, i) => (
      i < value ? <Star key={i} fontSize="small" sx={{ color: '#FFD700' }} /> : <StarBorder key={i} fontSize="small" sx={{ color: '#FFD700' }} />
    ))}
  </Box>
)

export default function TestimonialsPage() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const [rating, setRating] = useState(0)
  const [files, setFiles] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [comment, setComment] = useState('')
  const [items, setItems] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const autoTestRun = useRef(false)
  const [successOpen, setSuccessOpen] = useState(false)
  const [errorSnack, setErrorSnack] = useState({ open: false, message: '' })
  const [selectedTestimonial, setSelectedTestimonial] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  // Estadísticas dinámicas
  const stats = useMemo(() => {
    const total = items.length
    if (total === 0) return { total: 0, avg: 0, roundedAvg: 0 }
    const sum = items.reduce((acc, r) => acc + (Number(r.rating) || 0), 0)
    const avg = sum / total
    const roundedAvg = Math.round(avg)
    return { total, avg, roundedAvg }
  }, [items])

  useEffect(() => {
    const unsub = listenTestimonials((list) => {
      const filtered = (Array.isArray(list) ? list : []).filter((t) => t.approved === true && t.isTest !== true)
      setItems(filtered)
    }, { approvedOnly: true })
    return () => unsub && unsub()
  }, [])

  // Auto test: si estamos en local y llega ?test=1, crea una reseña de prueba
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    const shouldTest = params.get('test') === '1'
    if (isLocal && shouldTest && !autoTestRun.current) {
      autoTestRun.current = true
      ;(async () => {
        try {
          const token = `auto-test-${Date.now()}`
          await addTestimonial({
            name: 'Auto Test',
            email: 'autotest@local',
            rating: 5,
            comment: 'Reseña de prueba automática',
            files: [],
            token,
            isTest: true
          })
          // Feedback silencioso solo por consola para entorno local
          console.log('✅ Auto test enviado', token)
        } catch (e) {
          console.error('❌ Error auto test', e)
          setErrorSnack({ open: true, message: 'Error al enviar reseña de prueba' })
        }
      })()
    }
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name || !comment || rating === 0) {
      alert('Completa nombre, comentario y tu puntuación.')
      return
    }
    try {
      setSubmitting(true)
      await addTestimonial({ name, email, rating, comment, files })
      setSuccessOpen(true)
      // Reset y cerrar formulario
      setName('')
      setEmail('')
      setComment('')
      setRating(0)
      setFiles([])
      setShowForm(false)
    } catch (err) {
      console.error(err)
      setErrorSnack({ open: true, message: 'Hubo un problema al enviar tu reseña. Intenta nuevamente.' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setName('')
    setEmail('')
    setComment('')
    setRating(0)
    setFiles([])
  }

  const handleTestimonialClick = (testimonial) => {
    setSelectedTestimonial(testimonial)
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setSelectedTestimonial(null)
  }

  return (
    <>
      <SEO
        title="Testimonios y Opiniones de Clientes"
        description="Lee las opiniones de familias que han disfrutado nuestros talleres de pizza para niños y pizza parties en Santiago. Calificación 5 estrellas."
        keywords="opiniones pablo's pizza, reseñas taller pizza niños, testimonios pizza party, experiencias clientes, calificación eventos infantiles"
        url="/testimonios"
      />
      <Box>
        {/* Header Section */}
        <Box sx={{
          position: 'relative',
          background: 'linear-gradient(135deg, #FFD700 0%, #CBA900 50%, #B8860B 100%)',
          color: '#000',
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
            background: 'url("data:image/svg+xml,%3Csvg width="20" height="20" xmlns="http://www.w3.org/2000/svg"%3E%3Cdefs%3E%3Cpattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"%3E%3Cpath d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(0,0,0,0.05)" stroke-width="1"/%3E%3C/pattern%3E%3C/defs%3E%3Crect width="100%25" height="100%25" fill="url(%23grid)" /%3E%3C/svg%3E")',
            opacity: 0.3
          }
        }}>
          <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
            <Fade in timeout={1000}>
              <Box sx={{ textAlign: 'center', maxWidth: '800px', mx: 'auto' }}>
                <Typography
                  variant="h1"
                  sx={{
                    fontWeight: 900,
                    mb: 3,
                    fontSize: { xs: '2.5rem', md: '4rem' },
                    textShadow: '2px 2px 4px rgba(0,0,0,0.1)',
                    background: 'linear-gradient(45deg, #000, #333)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                  }}
                >
                  Testimonios
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
                  Lo que dicen nuestros clientes satisfechos
                </Typography>

                {/* Stats Summary */}
                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: 2,
                  backgroundColor: 'rgba(0, 0, 0, 0.1)',
                  borderRadius: '20px',
                  p: 3,
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(0, 0, 0, 0.1)'
                }}>
                  <Stars value={stats.roundedAvg} />
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {stats.avg.toFixed(1)} / 5.0
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600, opacity: 0.8 }}>
                    {stats.total > 0 ? `${stats.total} reseña${stats.total === 1 ? '' : 's'} verificadas` : 'Próximamente reseñas verificadas'}
                  </Typography>
                </Box>
              </Box>
            </Fade>
          </Container>
        </Box>

        <Container maxWidth="lg" sx={{ pb: 8 }}>
          {/* Listado */}
          {items.length === 0 ? (
            <Card sx={{ mb: 4 }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6">Aún no hay reseñas publicadas</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
                  Sé el primero en contar tu experiencia con Pablo's Pizza.
                </Typography>
              </CardContent>
            </Card>
          ) : (
            <Grid container spacing={3}>
            {items.map((t, idx) => (
              <Grid item xs={12} md={6} key={t.name}>
                <Card sx={{
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 25px rgba(255, 215, 0, 0.2)'
                  }
                }} onClick={() => handleTestimonialClick(t)}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                      <Avatar sx={{ backgroundColor: '#FFD700', color: '#000', fontWeight: 700 }}>{t.name?.charAt(0) || 'U'}</Avatar>
                      <Box>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{t.name}</Typography>
                        <Stars value={t.rating} />
                      </Box>
                    </Box>
                    <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                      "{t.comment || t.text}"
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t.createdAt?.toDate ? t.createdAt.toDate().toLocaleDateString() : (t.date || '')}
                    </Typography>
                    {Array.isArray(t.photos) && t.photos.length > 0 && (
                      <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {(t.photos || [])
                          .filter((url) => typeof url === 'string' && /^https?:\/\//.test(url))
                          .slice(0, 3)
                          .map((url) => (
                            <Box
                              key={url}
                              component="img"
                              src={url}
                              alt={`Foto del evento de ${t.name}`}
                              loading="lazy"
                              onError={(e) => { e.currentTarget.style.display = 'none' }}
                              sx={{ width: 84, height: 84, objectFit: 'cover', borderRadius: 1, border: '1px solid #eee', backgroundColor: 'grey.100' }}
                            />
                          ))}
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
            </Grid>
          )}

          {/* Call to write review con toggle */}
          <Card sx={{ mt: 4 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Stars value={5} />
              <Typography variant="h6" sx={{ mt: 1 }}>¿Ya viviste la experiencia Pablo's Pizza?</Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Cuéntanos qué te pareció. Puedes dejar tu reseña con puntuación y fotos (opcional).
              </Typography>

              {!showForm && (
                <Button variant="contained" onClick={() => setShowForm(true)}>
                  Dejar reseña
                </Button>
              )}

              {showForm && (
                <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 900, mx: 'auto', textAlign: 'left', mt: 2 }}>
                  <Grid container spacing={1.5}>
                    <Grid item xs={12} sm={4}>
                      <TextField label="Nombre" value={name} onChange={(e) => setName(e.target.value)} fullWidth required size="small" margin="dense" />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <TextField label="Email (opcional)" value={email} onChange={(e) => setEmail(e.target.value)} type="email" fullWidth size="small" margin="dense" />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Box>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>Tu puntuación:</Typography>
                        <Box>
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Button key={i} onClick={() => setRating(i + 1)} sx={{ minWidth: 0, p: 0.5 }}>
                              {i < rating ? <Star sx={{ color: '#FFD700' }} /> : <StarBorder sx={{ color: '#FFD700' }} />}
                            </Button>
                          ))}
                        </Box>
                      </Box>
                    </Grid>
                    <Grid item xs={12}>
                      <TextField label="Comentario" value={comment} onChange={(e) => setComment(e.target.value)} fullWidth multiline minRows={3} required size="small" margin="dense" />
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>Agregar fotos (opcional - máximo 5)</Typography>
                      <Button variant="outlined" component="label" startIcon={<PhotoCamera />} size="small">
                        Seleccionar Fotos
                        <input hidden accept="image/*" type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files).slice(0,5))} />
                      </Button>
                      <Typography variant="caption" sx={{ ml: 1 }}>{files.length}/5 fotos</Typography>
                    </Grid>
                    <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Button color="inherit" onClick={handleCancel} size="small">Cancelar</Button>
                      <Button type="submit" variant="contained" size="small" disabled={submitting}>
                        {submitting ? 'Enviando...' : 'Enviar Reseña'}
                      </Button>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </CardContent>
          </Card>
        </Container>
      </Box>

      {/* Confirmación de envío acorde al diseño */}
      <Dialog open={successOpen} onClose={() => setSuccessOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              backgroundColor: designTokens.colors.golden[100],
              color: designTokens.colors.charcoal[900],
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <CheckCircleIcon sx={{ color: designTokens.colors.golden[600] }} />
          </Box>
          ¡Gracias por tu reseña!
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            La recibimos correctamente y la revisaremos a la brevedad para publicarla.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="contained" onClick={() => setSuccessOpen(false)} sx={{
            background: designTokens.colors.aurora.golden,
            color: designTokens.colors.charcoal[900]
          }}>
            Cerrar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal para testimonios */}
      <Dialog
        open={modalOpen}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
        fullScreen={isMobile}
        PaperProps={{
          sx: {
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(20px)',
            borderRadius: 4
          }
        }}
      >
        <DialogContent sx={{ p: 0 }}>
          {selectedTestimonial && (
            <Box sx={{ p: 4 }}>
              {/* Header del modal */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <Avatar sx={{
                  backgroundColor: '#FFD700',
                  color: '#000',
                  fontWeight: 700,
                  width: 56,
                  height: 56,
                  fontSize: '1.5rem'
                }}>
                  {selectedTestimonial.name?.charAt(0) || 'U'}
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h4" sx={{ fontWeight: 800, mb: 1 }}>
                    {selectedTestimonial.name || 'Cliente Anónimo'}
                  </Typography>
                  <Stars value={selectedTestimonial.rating} />
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                    {selectedTestimonial.createdAt?.toDate ? selectedTestimonial.createdAt.toDate().toLocaleDateString() : (selectedTestimonial.date || '')}
                  </Typography>
                </Box>
                <IconButton onClick={handleCloseModal} sx={{ color: 'text.secondary' }}>
                  ✕
                </IconButton>
              </Box>

              {/* Comentario completo */}
              <Typography variant="h6" sx={{ fontStyle: 'italic', mb: 3, lineHeight: 1.6, fontSize: '1.2rem' }}>
                "{selectedTestimonial.comment || selectedTestimonial.text}"
              </Typography>

              {/* Galería de fotos */}
              {Array.isArray(selectedTestimonial.photos) && selectedTestimonial.photos.length > 0 && (
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                    📸 Fotos del cliente
                  </Typography>
                  <Grid container spacing={2}>
                    {selectedTestimonial.photos
                      .filter((url) => typeof url === 'string' && /^https?:\/\//.test(url))
                      .map((url, index) => (
                        <Grid item xs={6} sm={4} md={3} key={index}>
                          <Box
                            component="img"
                            src={url}
                            alt={`Foto ${index + 1} del evento de ${selectedTestimonial.name}`}
                            loading="lazy"
                            onError={(e) => { e.currentTarget.style.display = 'none' }}
                            sx={{
                              width: '100%',
                              height: 150,
                              objectFit: 'cover',
                              borderRadius: 2,
                              border: '2px solid #FFD700',
                              cursor: 'pointer',
                              transition: 'all 0.3s ease',
                              '&:hover': {
                                transform: 'scale(1.05)',
                                boxShadow: '0 8px 25px rgba(255, 215, 0, 0.3)'
                              }
                            }}
                          />
                        </Grid>
                      ))}
                  </Grid>
                </Box>
              )}

              {/* Acciones del modal */}
              <Box sx={{ mt: 4, textAlign: 'center' }}>
                <Button
                  variant="contained"
                  onClick={handleCloseModal}
                  sx={{
                    backgroundColor: '#FFD700',
                    color: '#000',
                    fontWeight: 700,
                    px: 4,
                    py: 1.5,
                    borderRadius: 3,
                    '&:hover': {
                      backgroundColor: '#CBA900'
                    }
                  }}
                >
                  Cerrar
                </Button>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Errores */}
      <Snackbar
        open={errorSnack.open}
        autoHideDuration={4000}
        onClose={() => setErrorSnack({ open: false, message: '' })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" variant="filled" onClose={() => setErrorSnack({ open: false, message: '' })} sx={{ width: '100%' }}>
          {errorSnack.message}
        </Alert>
      </Snackbar>
    </>
  )
}