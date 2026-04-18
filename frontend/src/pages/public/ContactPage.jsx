import React, { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  Link,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material'
import SEO from '../../components/common/SEO'
import { WhatsApp, Phone, Email, Room, ArrowBack, Send } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { CONTACT_INFO } from '../../config/constants'
import { contactAPI } from '../../services/api'
import toast from 'react-hot-toast'

export default function ContactPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: '',
    priority: 'normal'
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      // Crear mensaje de contacto
      const contactData = {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        subject: formData.subject,
        message: formData.message,
        priority: formData.priority
      }

      await contactAPI.create(contactData)

      toast.success('¡Mensaje enviado exitosamente! Te contactaremos pronto por WhatsApp.', {
        duration: 5000,
        icon: '✅'
      })

      // Limpiar formulario
      setFormData({
        name: '',
        email: '',
        phone: '',
        subject: '',
        message: '',
        priority: 'normal'
      })

    } catch (error) {
      console.error('Error al enviar consulta:', error)
      toast.error('Error al enviar la consulta. Intenta nuevamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Box sx={{ background: '#0d0d0d', minHeight: '100vh' }}>
      <SEO
        title="Contacto - Consultas y Cotizaciones"
        description="Contáctanos para cotizar tu taller de pizza o pizza party en Santiago. WhatsApp +56 9 8942 4566. Respuesta en menos de 2 horas."
        keywords="contacto pablo's pizza, whatsapp pizza party, cotizar evento infantil, consultas taller pizza, teléfono catering pizza Santiago"
        url="/contacto"
      />
      {/* Header Section */}
      <Box sx={{
        position: 'relative',
        background: '#0d0d0d',
        color: '#FFFFFF',
        py: { xs: 4, md: 6 },
        mb: 6,
        overflow: 'hidden',
        borderBottom: '1px solid rgba(232,182,58,0.15)',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle at 60% 50%, rgba(232,182,58,0.08) 0%, transparent 60%)',
          opacity: 0.8
        }
      }}>
        <Container maxWidth="xl" sx={{ position: 'relative', zIndex: 1 }}>
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center'
          }}>
            <Typography
              variant="h1"
              sx={{
                fontWeight: 900,
                fontSize: { xs: '2.5rem', md: '4rem' },
                mb: 2,
                color: '#FFFFFF'
              }}
            >
              Contacto
            </Typography>
            <Typography
              variant="h5"
              sx={{
                maxWidth: '800px',
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.65)',
                fontSize: { xs: '1.1rem', md: '1.3rem' }
              }}
            >
              ¿Tienes una pregunta o quieres agendar un evento? Estamos aquí para ayudarte a hacer realidad la celebración perfecta.
            </Typography>
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ pb: 8 }}>
        <Grid container spacing={4}>
          {/* Col izquierda - Información de contacto */}
          <Grid item xs={12} md={6}>
            <Card sx={{
              mb: 3,
              borderRadius: 3,
              background: '#1a1714',
              border: '1px solid rgba(232,182,58,0.15)'
            }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#FFFFFF' }}>
                  ¡Conectemos!
                </Typography>
                <Typography variant="body1" sx={{ lineHeight: 1.7, color: 'rgba(255,255,255,0.65)' }}>
                  Estamos aquí para hacer realidad el evento perfecto. Contáctanos para más información o para resolver cualquier duda.
                </Typography>
              </CardContent>
            </Card>

            <Grid container spacing={2}>
              {/* WhatsApp Card */}
              <Grid item xs={12} sm={6}>
                <Card sx={{
                  borderRadius: 3,
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(232,182,58,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: { xs: 2, sm: 3 }, textAlign: 'center' }}>
                    <WhatsApp sx={{ fontSize: { xs: 32, sm: 40 }, color: '#25D366', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, fontSize: { xs: '1rem', sm: '1.25rem' }, color: '#FFFFFF' }}>
                      WhatsApp
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, fontSize: { xs: '0.75rem', sm: '0.875rem' }, color: 'rgba(255,255,255,0.65)' }}>
                      {CONTACT_INFO.WHATSAPP_DISPLAY}
                    </Typography>
                    <Button
                      href={CONTACT_INFO.WHATSAPP_URL}
                      target="_blank"
                      variant="contained"
                      sx={{
                        bgcolor: '#25D366',
                        '&:hover': { bgcolor: '#1DA851' },
                        borderRadius: 2,
                        fontSize: { xs: '0.8rem', sm: '0.875rem' },
                        py: { xs: 1, sm: 1.5 }
                      }}
                      fullWidth
                    >
                      Chatear ahora
                    </Button>
                  </CardContent>
                </Card>
              </Grid>

              {/* Teléfono Card */}
              <Grid item xs={12} sm={6}>
                <Card sx={{
                  borderRadius: 3,
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(232,182,58,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Phone sx={{ fontSize: 40, color: '#e8b63a', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: '#FFFFFF' }}>
                      Teléfono
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, color: 'rgba(255,255,255,0.65)' }}>
                      {CONTACT_INFO.WHATSAPP_DISPLAY}
                    </Typography>
                    <Button
                      href={`tel:${CONTACT_INFO.WHATSAPP_NUMBER}`}
                      variant="outlined"
                      fullWidth
                      sx={{
                        borderRadius: 2,
                        borderColor: 'rgba(232,182,58,0.5)',
                        color: '#e8b63a',
                        '&:hover': {
                          borderColor: '#e8b63a',
                          bgcolor: 'rgba(232,182,58,0.08)'
                        }
                      }}
                    >
                      Llamar
                    </Button>
                  </CardContent>
                </Card>
              </Grid>

              {/* Email Card */}
              <Grid item xs={12} sm={6}>
                <Card sx={{
                  borderRadius: 3,
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(232,182,58,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Email sx={{ fontSize: 40, color: '#e8b63a', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: '#FFFFFF' }}>
                      Email
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, color: 'rgba(255,255,255,0.65)' }}>
                      Pablospizza.cl@gmail.com
                    </Typography>
                    <Button
                      href="mailto:Pablospizza.cl@gmail.com"
                      variant="outlined"
                      fullWidth
                      sx={{
                        borderRadius: 2,
                        borderColor: 'rgba(232,182,58,0.5)',
                        color: '#e8b63a',
                        '&:hover': {
                          borderColor: '#e8b63a',
                          bgcolor: 'rgba(232,182,58,0.08)'
                        }
                      }}
                    >
                      Escribir
                    </Button>
                  </CardContent>
                </Card>
              </Grid>

              {/* Servicio Card */}
              <Grid item xs={12} sm={6}>
                <Card sx={{
                  borderRadius: 3,
                  background: '#1a1714',
                  border: '1px solid rgba(232,182,58,0.15)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(232,182,58,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Room sx={{ fontSize: 40, color: '#e8b63a', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: '#FFFFFF' }}>
                      Servicio
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)' }}>
                      A domicilio en toda la ciudad. Llevamos la diversión a tu ubicación.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Grid>

          {/* Col derecha - formulario */}
          <Grid item xs={12} md={6}>
            <Card sx={{
              borderRadius: 3,
              background: '#1a1714',
              border: '1px solid rgba(232,182,58,0.15)'
            }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#FFFFFF' }}>
                  Déjanos un mensaje
                </Typography>
                <Typography variant="body2" sx={{ mb: 3, color: 'rgba(255,255,255,0.65)' }}>
                  Completa el formulario y nos comunicaremos contigo por WhatsApp
                </Typography>

                <Box component="form" onSubmit={handleSubmit}>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Nombre *"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        fullWidth
                        required
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' }
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Email *"
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        fullWidth
                        required
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' }
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Teléfono"
                        name="phone"
                        value={formData.phone}
                        onChange={handleInputChange}
                        fullWidth
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' }
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        label="Asunto *"
                        name="subject"
                        value={formData.subject}
                        onChange={handleInputChange}
                        fullWidth
                        required
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' }
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <FormControl
                        fullWidth
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' },
                          '& .MuiSvgIcon-root': { color: 'rgba(255,255,255,0.6)' }
                        }}
                      >
                        <InputLabel>Prioridad</InputLabel>
                        <Select
                          name="priority"
                          value={formData.priority}
                          onChange={handleInputChange}
                          label="Prioridad"
                          MenuProps={{
                            PaperProps: {
                              sx: {
                                background: '#1a1714',
                                border: '1px solid rgba(232,182,58,0.2)',
                                '& .MuiMenuItem-root': {
                                  color: '#FFFFFF',
                                  '&:hover': { bgcolor: 'rgba(232,182,58,0.08)' },
                                  '&.Mui-selected': { bgcolor: 'rgba(232,182,58,0.15)' }
                                }
                              }
                            }
                          }}
                        >
                          <MenuItem value="low">Baja - Consulta general</MenuItem>
                          <MenuItem value="normal">Normal - Información de evento</MenuItem>
                          <MenuItem value="high">Alta - Quiero agendar pronto</MenuItem>
                          <MenuItem value="urgent">Urgente - Evento en menos de 7 días</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        label="Mensaje *"
                        name="message"
                        value={formData.message}
                        onChange={handleInputChange}
                        fullWidth
                        multiline
                        minRows={4}
                        required
                        variant="outlined"
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            borderRadius: 2,
                            color: '#FFFFFF',
                            '& fieldset': { borderColor: 'rgba(232,182,58,0.3)' },
                            '&:hover fieldset': { borderColor: 'rgba(232,182,58,0.6)' },
                            '&.Mui-focused fieldset': { borderColor: '#e8b63a' }
                          },
                          '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.6)' },
                          '& .MuiInputLabel-root.Mui-focused': { color: '#e8b63a' }
                        }}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <Button
                        type="submit"
                        variant="contained"
                        fullWidth
                        size="large"
                        disabled={isSubmitting}
                        startIcon={isSubmitting ? <CircularProgress size={20} /> : <Send />}
                        sx={{
                          py: 1.5,
                          borderRadius: 2,
                          fontSize: '1.1rem',
                          fontWeight: 600,
                          bgcolor: '#e8b63a',
                          color: '#0d0d0d',
                          '&:hover': { bgcolor: '#d4a030' },
                          '&.Mui-disabled': {
                            bgcolor: 'rgba(232,182,58,0.3)',
                            color: 'rgba(255,255,255,0.4)'
                          }
                        }}
                      >
                        {isSubmitting ? 'Enviando...' : 'Enviar Mensaje'}
                      </Button>
                    </Grid>
                  </Grid>
                </Box>

                <Alert
                  severity="info"
                  sx={{
                    mt: 3,
                    borderRadius: 2,
                    bgcolor: 'rgba(232,182,58,0.08)',
                    border: '1px solid rgba(232,182,58,0.2)',
                    color: 'rgba(255,255,255,0.8)',
                    '& .MuiAlert-icon': { color: '#e8b63a' }
                  }}
                >
                  <Typography variant="body2">
                    Tu mensaje será enviado directamente a nuestro sistema interno y un agente te contactará dentro de las próximas 24 horas.
                  </Typography>
                </Alert>

                <Card sx={{
                  mt: 3,
                  background: 'rgba(232,182,58,0.06)',
                  border: '1px solid rgba(232,182,58,0.2)',
                  borderRadius: 2
                }}>
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600, color: '#e8b63a' }}>
                      Horarios de Atención
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 0.5, color: 'rgba(255,255,255,0.8)' }}>
                      Lunes a Viernes: 9:00 AM - 8:00 PM
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 0.5, color: 'rgba(255,255,255,0.8)' }}>
                      Sábados y Domingos: 10:00 AM - 6:00 PM
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                      *Eventos disponibles todos los días
                    </Typography>
                  </CardContent>
                </Card>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}
