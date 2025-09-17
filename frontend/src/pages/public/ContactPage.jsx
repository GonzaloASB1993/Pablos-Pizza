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
  CircularProgress
} from '@mui/material'
import { WhatsApp, Phone, Email, Room, ArrowBack, Send } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { CONTACT_INFO } from '../../config/constants'
import { chatAPI } from '../../services/api'
import toast from 'react-hot-toast'

export default function ContactPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: ''
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
      // Crear sala de chat
      const chatRoom = await chatAPI.createRoom({ 
        client_name: formData.name, 
        client_email: formData.email 
      })

      // Crear mensaje inicial con toda la información del formulario
      const initialMessage = `Consulta desde formulario de contacto:

📝 Asunto: ${formData.subject}
📞 Teléfono: ${formData.phone || 'No proporcionado'}

💬 Mensaje:
${formData.message}`

      // Enviar mensaje inicial
      await chatAPI.sendMessage(chatRoom.data.id, {
        message: initialMessage,
        sender_name: formData.name,
        is_admin: false
      })

      toast.success('¡Mensaje enviado exitosamente! Un agente te contactará pronto.', {
        duration: 5000,
        icon: '✅'
      })

      // Limpiar formulario
      setFormData({
        name: '',
        email: '',
        phone: '',
        subject: '',
        message: ''
      })

    } catch (error) {
      console.error('Error al enviar consulta:', error)
      toast.error('Error al enviar la consulta. Intenta nuevamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
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
                textShadow: '2px 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              Contacto
            </Typography>
            <Typography
              variant="h5"
              sx={{
                maxWidth: '800px',
                lineHeight: 1.6,
                opacity: 0.9,
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
            <Card sx={{ mb: 3, borderRadius: 3, boxShadow: '0 8px 32px rgba(0,0,0,0.1)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#333' }}>
                  ¡Conectemos!
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                  Estamos aquí para hacer realidad el evento perfecto. Contáctanos para más información o para resolver cualquier duda.
                </Typography>
              </CardContent>
            </Card>

            <Grid container spacing={2}>
              {/* WhatsApp Card */}
              <Grid item xs={12} sm={6}>
                <Card sx={{
                  borderRadius: 3,
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <WhatsApp sx={{ fontSize: 40, color: '#25D366', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      WhatsApp
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {CONTACT_INFO.WHATSAPP_DISPLAY}
                    </Typography>
                    <Button
                      href={CONTACT_INFO.WHATSAPP_URL}
                      target="_blank"
                      variant="contained"
                      sx={{
                        bgcolor: '#25D366',
                        '&:hover': { bgcolor: '#1DA851' },
                        borderRadius: 2
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
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Phone sx={{ fontSize: 40, color: '#1976d2', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Teléfono
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {CONTACT_INFO.WHATSAPP_DISPLAY}
                    </Typography>
                    <Button
                      href={`tel:${CONTACT_INFO.WHATSAPP_NUMBER}`}
                      variant="outlined"
                      fullWidth
                      sx={{ borderRadius: 2 }}
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
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Email sx={{ fontSize: 40, color: '#d32f2f', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Email
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Pablospizza.cl@gmail.com
                    </Typography>
                    <Button
                      href="mailto:Pablospizza.cl@gmail.com"
                      variant="outlined"
                      fullWidth
                      sx={{ borderRadius: 2 }}
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
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.15)'
                  }
                }}>
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Room sx={{ fontSize: 40, color: '#ed6c02', mb: 1 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Servicio
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      A domicilio en toda la ciudad. Llevamos la diversión a tu ubicación.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Grid>

          {/* Col derecha - formulario */}
          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 3, boxShadow: '0 8px 32px rgba(0,0,0,0.1)' }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#333' }}>
                  Déjanos un mensaje
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
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
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
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
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
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
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
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
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                      />
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
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
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
                          bgcolor: '#1976d2',
                          '&:hover': { bgcolor: '#1565c0' }
                        }}
                      >
                        {isSubmitting ? 'Enviando...' : 'Enviar Mensaje'}
                      </Button>
                    </Grid>
                  </Grid>
                </Box>

                <Alert severity="info" sx={{ mt: 3, borderRadius: 2 }}>
                  <Typography variant="body2">
                    Tu mensaje será enviado directamente a nuestro sistema interno y un agente te contactará dentro de las próximas 24 horas.
                  </Typography>
                </Alert>

                <Card sx={{ mt: 3, backgroundColor: '#FFF7CC', borderRadius: 2 }}>
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                      Horarios de Atención
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 0.5 }}>
                      Lunes a Viernes: 9:00 AM - 8:00 PM
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 0.5 }}>
                      Sábados y Domingos: 10:00 AM - 6:00 PM
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
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
