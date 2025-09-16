import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Alert
} from '@mui/material'
import { Add, Edit, Delete, Upload, Image, Publish, PublishOff, Visibility, VisibilityOff } from '@mui/icons-material'
import { eventsAPI, galleryAPI } from '../../services/api'
import toast from 'react-hot-toast'

const EventsManagement = () => {
  const [events, setEvents] = useState([])
  const [filteredEvents, setFilteredEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingEvent, setEditingEvent] = useState(null)
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  })
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    event_date: '',
    participants: '',
    final_price: '',
    notes: '',
    status: 'completed'
  })
  const [imageFiles, setImageFiles] = useState([])
  const [photoDialog, setPhotoDialog] = useState(false)
  const [selectedEventForPhotos, setSelectedEventForPhotos] = useState(null)
  const [photoFiles, setPhotoFiles] = useState([])
  const [eventPhotos, setEventPhotos] = useState([])
  const [loadingPhotos, setLoadingPhotos] = useState(false)

  useEffect(() => {
    loadEvents()
  }, [])

  useEffect(() => {
    filterEventsByMonth()
  }, [events, selectedMonth])

  const filterEventsByMonth = () => {
    if (!selectedMonth) {
      setFilteredEvents(events)
      return
    }

    const filtered = events.filter(event => {
      if (!event.event_date) return false
      const eventDate = new Date(event.event_date)
      const eventMonth = `${eventDate.getFullYear()}-${String(eventDate.getMonth() + 1).padStart(2, '0')}`
      return eventMonth === selectedMonth
    })

    setFilteredEvents(filtered)
  }

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

  const handleSubmit = async () => {
    try {
      if (editingEvent) {
        await eventsAPI.update(editingEvent.id, formData)
        toast.success('Evento actualizado')
      } else {
        const response = await eventsAPI.create(formData)

        // Upload images if any
        if (imageFiles.length > 0) {
          for (const file of imageFiles) {
            const formDataImage = new FormData()
            formDataImage.append('file', file)
            formDataImage.append('title', `${formData.title} - Imagen`)
            formDataImage.append('description', `Imagen del evento: ${formData.title}`)
            formDataImage.append('event_id', response.data.id)
            formDataImage.append('category', 'events')

            await galleryAPI.upload(formDataImage)
          }
          toast.success('Evento creado con imágenes subidas a la galería')
        } else {
          toast.success('Evento creado')
        }
      }

      setDialogOpen(false)
      resetForm()
      loadEvents()
    } catch (error) {
      console.error('Error saving event:', error)
      toast.error('Error al guardar evento')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      event_date: '',
      participants: '',
      final_price: '',
      notes: '',
      status: 'completed'
    })
    setImageFiles([])
    setEditingEvent(null)
  }

  const handleEdit = (event) => {
    setEditingEvent(event)
    setFormData({
      title: event.title || '',
      description: event.description || '',
      event_date: event.event_date || '',
      participants: event.participants || '',
      final_price: event.final_price || '',
      notes: event.notes || '',
      status: event.status || 'completed'
    })
    setDialogOpen(true)
  }

  const handleImageChange = (event) => {
    const files = Array.from(event.target.files)
    setImageFiles(files)
  }

  const handleOpenPhotoDialog = async (event) => {
    setSelectedEventForPhotos(event)
    setPhotoFiles([])
    setPhotoDialog(true)
    await loadEventPhotos(event.id)
  }

  const handlePhotoUpload = (event) => {
    const files = Array.from(event.target.files)

    console.log('📁 Archivos seleccionados:', files.map(f => ({ name: f.name, type: f.type, size: f.size })))

    if (files.length > 5) {
      toast.error('Puedes subir máximo 5 fotos por evento')
      return
    }

    // Validar que todos los archivos sean imágenes
    const validFiles = files.filter(file => file.type.startsWith('image/'))
    console.log('✅ Archivos válidos:', validFiles.map(f => ({ name: f.name, type: f.type })))
    
    if (validFiles.length !== files.length) {
      const invalidFiles = files.filter(file => !file.type.startsWith('image/'))
      console.log('❌ Archivos inválidos:', invalidFiles.map(f => ({ name: f.name, type: f.type })))
      toast.error('Solo se permiten archivos de imagen')
      return
    }

    setPhotoFiles(validFiles)
  }

  const handleSavePhotos = async () => {
    try {
      if (photoFiles.length === 0) {
        toast.error('Selecciona al menos una imagen')
        return
      }

      for (const file of photoFiles) {
        const formDataImage = new FormData()
        formDataImage.append('file', file)
        formDataImage.append('title', `${selectedEventForPhotos.title} - Imagen`)
        formDataImage.append('description', `Imagen del evento: ${selectedEventForPhotos.title}`)
        formDataImage.append('event_id', selectedEventForPhotos.id)
        formDataImage.append('category', 'events')

        await galleryAPI.upload(formDataImage)
      }

      toast.success(`${photoFiles.length} imagen(es) subida(s) a la galería`)
      setPhotoFiles([])
      
      // Recargar fotos del evento
      await loadEventPhotos(selectedEventForPhotos.id)
    } catch (error) {
      console.error('Error uploading photos:', error)
      toast.error('Error al subir imágenes')
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      completed: 'success',
      cancelled: 'error',
      pending: 'warning'
    }
    return colors[status] || 'default'
  }

  const getEventType = (event) => {
    // Determinar tipo basado en el título o descripción
    if (event.title?.toLowerCase().includes('pizzeros en acción') || 
        event.title?.toLowerCase().includes('workshop') ||
        event.description?.toLowerCase().includes('taller')) {
      return 'Taller'
    } else if (event.title?.toLowerCase().includes('pizza party') ||
               event.description?.toLowerCase().includes('pizza party')) {
      return 'Pizza Party'
    } else {
      return 'Evento'
    }
  }

  const getStatusLabel = (status) => {
    const labels = {
      completed: 'Completado',
      cancelled: 'Cancelado',
      pending: 'Pendiente'
    }
    return labels[status] || status
  }

  // Funciones para manejar fotos del evento
  const loadEventPhotos = async (eventId) => {
    try {
      setLoadingPhotos(true)
      const response = await galleryAPI.getByEvent(eventId)
      setEventPhotos(response.data || [])
    } catch (error) {
      console.error('Error loading event photos:', error)
      toast.error('Error al cargar fotos del evento')
    } finally {
      setLoadingPhotos(false)
    }
  }

  const handlePublishPhoto = async (photoId, isPublished) => {
    try {
      await galleryAPI.publish(photoId, isPublished)
      const action = isPublished ? 'publicada' : 'despublicada'
      toast.success(`Imagen ${action} exitosamente`)
      
      // Recargar fotos del evento
      if (selectedEventForPhotos) {
        await loadEventPhotos(selectedEventForPhotos.id)
      }
    } catch (error) {
      console.error('Error publishing photo:', error)
      toast.error('Error al cambiar estado de publicación')
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Galería de Eventos</Typography>
          <Typography variant="body2" color="text.secondary">
            Gestiona los eventos que aparecen en la página pública. Los eventos se crean automáticamente cuando completas un agendamiento.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            select
            label="Filtrar por mes"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">Todos los meses</MenuItem>
            {(() => {
              const months = []
              const currentDate = new Date()
              for (let i = 0; i < 12; i++) {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1)
                const monthValue = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
                const monthLabel = date.toLocaleDateString('es-ES', { year: 'numeric', month: 'long' })
                months.push(
                  <MenuItem key={monthValue} value={monthValue}>
                    {monthLabel}
                  </MenuItem>
                )
              }
              return months
            })()}
          </TextField>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              resetForm()
              setDialogOpen(true)
            }}
            sx={{ whiteSpace: 'nowrap' }}
          >
            Agregar Evento
          </Button>
        </Box>
      </Box>

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando eventos...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Evento</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Participantes</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Galería</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredEvents.map((event) => (
                    <TableRow key={event.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {event.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {event.description || 'Sin descripción'}
                          </Typography>
                          {event.booking_id && (
                            <Chip label="Auto" size="small" color="info" sx={{ ml: 1 }} />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={getEventType(event)} 
                          color={getEventType(event) === 'Taller' ? 'secondary' : 'primary'}
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {event.event_date ?
                          new Date(event.event_date).toLocaleDateString('es-CL') :
                          'No especificada'
                        }
                      </TableCell>
                      <TableCell>{event.participants || 'N/A'}</TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusLabel(event.status)}
                          color={getStatusColor(event.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          startIcon={<Upload />}
                          color="primary"
                          onClick={() => handleOpenPhotoDialog(event)}
                        >
                          Fotos
                        </Button>
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleEdit(event)}
                        >
                          <Edit />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredEvents.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">
                          {selectedMonth ? `No hay eventos para el mes seleccionado.` : `No hay eventos en la galería. Los eventos se crean automáticamente cuando completas agendamientos.`}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingEvent ? 'Editar Evento' : 'Agregar Nuevo Evento'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Título del Evento"
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Descripción"
                multiline
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Fecha del Evento"
                type="date"
                value={formData.event_date}
                onChange={(e) => setFormData({...formData, event_date: e.target.value})}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Número de Participantes"
                type="number"
                value={formData.participants}
                onChange={(e) => setFormData({...formData, participants: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Precio Final"
                type="number"
                value={formData.final_price}
                onChange={(e) => setFormData({...formData, final_price: e.target.value})}
                InputProps={{
                  startAdornment: '$'
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Estado</InputLabel>
                <Select
                  value={formData.status}
                  onChange={(e) => setFormData({...formData, status: e.target.value})}
                  label="Estado"
                >
                  <MenuItem value="completed">Completado</MenuItem>
                  <MenuItem value="cancelled">Cancelado</MenuItem>
                  <MenuItem value="pending">Pendiente</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notas Adicionales"
                multiline
                rows={2}
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Notas sobre el evento, comentarios, etc."
              />
            </Grid>
            {!editingEvent && (
              <Grid item xs={12}>
                <Box sx={{ border: '1px dashed #ccc', p: 2, borderRadius: 1 }}>
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageChange}
                    style={{ width: '100%' }}
                    id="image-upload"
                  />
                  <label htmlFor="image-upload">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}>
                      <Image />
                      <Typography variant="body2">
                        Subir imágenes del evento (se agregarán automáticamente a la galería)
                      </Typography>
                    </Box>
                  </label>
                  {imageFiles.length > 0 && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      {imageFiles.length} imagen(es) seleccionada(s)
                    </Alert>
                  )}
                </Box>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingEvent ? 'Actualizar' : 'Crear Evento'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Photo Upload Dialog */}
      <Dialog open={photoDialog} onClose={() => setPhotoDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Gestionar Fotos del Evento
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            {selectedEventForPhotos && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>Evento:</strong> {selectedEventForPhotos.title}
                </Typography>
                <Typography variant="body2">
                  <strong>Fecha:</strong> {selectedEventForPhotos.event_date ?
                    new Date(selectedEventForPhotos.event_date).toLocaleDateString('es-CL') :
                    'No especificada'
                  }
                </Typography>
              </Alert>
            )}

            <Box sx={{ border: '2px dashed #ccc', p: 3, borderRadius: 2, textAlign: 'center' }}>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handlePhotoUpload}
                style={{ display: 'none' }}
                id="photo-upload-input"
              />
              <label htmlFor="photo-upload-input">
                <Box sx={{ cursor: 'pointer' }}>
                  <Upload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                  <Typography variant="h6" color="primary">
                    Haz clic para seleccionar imágenes
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Puedes seleccionar hasta 5 imágenes a la vez
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Formatos soportados: JPG, PNG, GIF • Máximo 5 fotos por evento
                  </Typography>
                </Box>
              </label>
            </Box>

            {photoFiles.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Imágenes seleccionadas ({photoFiles.length}):
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {Array.from(photoFiles).map((file, index) => (
                    <Chip
                      key={index}
                      label={file.name}
                      color="primary"
                      variant="outlined"
                      size="small"
                    />
                  ))}
                </Box>
                <Button
                  variant="contained"
                  onClick={handleSavePhotos}
                  disabled={photoFiles.length === 0}
                  startIcon={<Upload />}
                >
                  Subir {photoFiles.length} Foto(s)
                </Button>
              </Box>
            )}

            {/* Sección de fotos existentes */}
            <Typography variant="h6" gutterBottom>
              Fotos del Evento
            </Typography>
            {loadingPhotos ? (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography>Cargando fotos...</Typography>
              </Box>
            ) : eventPhotos.length > 0 ? (
              <Grid container spacing={2}>
                {eventPhotos.map((photo) => (
                  <Grid item xs={12} sm={6} md={4} key={photo.id}>
                    <Card>
                      <Box sx={{ position: 'relative' }}>
                        <img
                          src={photo.url}
                          alt={photo.title}
                          style={{
                            width: '100%',
                            height: 200,
                            objectFit: 'cover'
                          }}
                        />
                        <Chip
                          label={photo.is_published ? 'Publicada' : 'Privada'}
                          color={photo.is_published ? 'success' : 'default'}
                          size="small"
                          sx={{
                            position: 'absolute',
                            top: 8,
                            right: 8,
                            backgroundColor: photo.is_published ? 'success.main' : 'grey.500',
                            color: 'white'
                          }}
                        />
                      </Box>
                      <CardContent>
                        <Typography variant="body2" noWrap>
                          {photo.title}
                        </Typography>
                        <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                          {photo.is_published ? (
                            <Button
                              size="small"
                              variant="outlined"
                              color="warning"
                              startIcon={<VisibilityOff />}
                              onClick={() => handlePublishPhoto(photo.id, false)}
                            >
                              Despublicar
                            </Button>
                          ) : (
                            <Button
                              size="small"
                              variant="contained"
                              color="primary"
                              startIcon={<Visibility />}
                              onClick={() => handlePublishPhoto(photo.id, true)}
                            >
                              Publicar
                            </Button>
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography color="text.secondary">
                  No hay fotos subidas para este evento
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPhotoDialog(false)}>
            Cerrar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default EventsManagement