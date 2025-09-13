import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ImageList,
  ImageListItem,
  Chip,
  IconButton,
  Alert
} from '@mui/material'
import { Visibility, Image, Close } from '@mui/icons-material'
import { galleryAPI, eventsAPI } from '../../services/api'
import toast from 'react-hot-toast'

const GalleryManagement = () => {
  const [events, setEvents] = useState([])
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [eventPhotos, setEventPhotos] = useState([])
  const [loading, setLoading] = useState(true)
  const [photoDialog, setPhotoDialog] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  useEffect(() => {
    loadEvents()
  }, [])

  const loadEvents = async () => {
    try {
      setLoading(true)
      const response = await eventsAPI.getAll()
      setEvents(response.data)
    } catch (error) {
      console.error('Error loading events:', error)
      toast.error('Error al cargar eventos')
    } finally {
      setLoading(false)
    }
  }

  const loadEventPhotos = async (eventId) => {
    try {
      const response = await galleryAPI.getByEvent(eventId)
      setEventPhotos(response.data)
    } catch (error) {
      console.error('Error loading event photos:', error)
      toast.error('Error al cargar fotos del evento')
      setEventPhotos([])
    }
  }

  const handleViewPhotos = async (event) => {
    setSelectedEvent(event)
    await loadEventPhotos(event.id)
    setPhotoDialog(true)
  }

  const handlePhotoClick = (photo) => {
    setSelectedPhoto(photo)
  }

  const getStatusColor = (status) => {
    const colors = {
      completed: 'success',
      cancelled: 'error',
      pending: 'warning'
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status) => {
    const labels = {
      completed: 'Completado',
      cancelled: 'Cancelado',
      pending: 'Pendiente'
    }
    return labels[status] || status
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Gestión de Galería
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Administra las imágenes de eventos. Las fotos se suben desde el menú de eventos.
        </Typography>
      </Box>

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando eventos...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {events.map((event) => (
            <Grid item xs={12} sm={6} md={4} key={event.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardMedia
                  component="div"
                  sx={{
                    height: 200,
                    backgroundColor: '#f5f5f5',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Image sx={{ fontSize: 60, color: '#ccc' }} />
                </CardMedia>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                    <Typography variant="h6" component="h3" gutterBottom>
                      {event.title}
                    </Typography>
                    <Chip
                      label={getStatusLabel(event.status)}
                      color={getStatusColor(event.status)}
                      size="small"
                    />
                  </Box>

                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {event.description || 'Sin descripción'}
                  </Typography>

                  {event.event_date && (
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      📅 {new Date(event.event_date).toLocaleDateString('es-CL')}
                    </Typography>
                  )}

                  {event.participants && (
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      👥 {event.participants} participantes
                    </Typography>
                  )}

                  <Box sx={{ mt: 2 }}>
                    <Button
                      variant="outlined"
                      startIcon={<Visibility />}
                      onClick={() => handleViewPhotos(event)}
                      fullWidth
                    >
                      Ver Fotos
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}

          {events.length === 0 && (
            <Grid item xs={12}>
              <Alert severity="info">
                No hay eventos disponibles. Los eventos se crean automáticamente cuando completas agendamientos o los creas manualmente desde el menú de eventos.
              </Alert>
            </Grid>
          )}
        </Grid>
      )}

      {/* Photo Gallery Dialog */}
      <Dialog
        open={photoDialog}
        onClose={() => setPhotoDialog(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { minHeight: '80vh' } }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h5">
                Fotos del Evento
              </Typography>
              {selectedEvent && (
                <Typography variant="body2" color="text.secondary">
                  {selectedEvent.title} • {selectedEvent.event_date ?
                    new Date(selectedEvent.event_date).toLocaleDateString('es-CL') :
                    'Sin fecha'
                  }
                </Typography>
              )}
            </Box>
            <IconButton onClick={() => setPhotoDialog(false)}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {eventPhotos.length > 0 ? (
            <ImageList variant="masonry" cols={3} gap={8}>
              {eventPhotos.map((photo) => (
                <ImageListItem
                  key={photo.id}
                  sx={{ cursor: 'pointer' }}
                  onClick={() => handlePhotoClick(photo)}
                >
                  <img
                    src={photo.url}
                    alt={photo.title}
                    loading="lazy"
                    style={{ borderRadius: 8 }}
                  />
                </ImageListItem>
              ))}
            </ImageList>
          ) : (
            <Alert severity="info">
              <Typography variant="body1">
                Este evento no tiene fotos todavía.
              </Typography>
              <Typography variant="body2">
                Puedes subir fotos desde el menú "Eventos" haciendo clic en el botón "Fotos" del evento correspondiente.
              </Typography>
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPhotoDialog(false)}>
            Cerrar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Individual Photo Dialog */}
      {selectedPhoto && (
        <Dialog
          open={!!selectedPhoto}
          onClose={() => setSelectedPhoto(null)}
          maxWidth="md"
          fullWidth
        >
          <DialogContent sx={{ p: 0, position: 'relative' }}>
            <IconButton
              onClick={() => setSelectedPhoto(null)}
              sx={{
                position: 'absolute',
                right: 8,
                top: 8,
                bgcolor: 'rgba(0,0,0,0.5)',
                color: 'white',
                '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' },
                zIndex: 1
              }}
            >
              <Close />
            </IconButton>
            <img
              src={selectedPhoto.url}
              alt={selectedPhoto.title}
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
            />
            {selectedPhoto.title && (
              <Box sx={{ p: 2 }}>
                <Typography variant="h6">
                  {selectedPhoto.title}
                </Typography>
                {selectedPhoto.description && (
                  <Typography variant="body2" color="text.secondary">
                    {selectedPhoto.description}
                  </Typography>
                )}
              </Box>
            )}
          </DialogContent>
        </Dialog>
      )}
    </Box>
  )
}

export default GalleryManagement