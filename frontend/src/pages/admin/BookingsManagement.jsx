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
  Chip,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert
} from '@mui/material'
import { Add, Edit, Delete, ViewList, CalendarMonth, CheckCircle, Cancel } from '@mui/icons-material'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { es } from 'date-fns/locale'
import { bookingsAPI, eventsAPI } from '../../services/api'
import toast from 'react-hot-toast'
import 'react-big-calendar/lib/css/react-big-calendar.css'

// Calendar localizer setup
const locales = {
  'es': es,
}

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
})

const BookingsManagement = () => {
  const [bookings, setBookings] = useState([])
  const [filteredBookings, setFilteredBookings] = useState([])
  const [view, setView] = useState('list')
  const [loading, setLoading] = useState(true)
  const [selectedMonth, setSelectedMonth] = useState("")
  const [editDialog, setEditDialog] = useState(false)
  const [createDialog, setCreateDialog] = useState(false)
  const [completeDialog, setCompleteDialog] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState(false)
  const [selectedBooking, setSelectedBooking] = useState(null)
  const [formData, setFormData] = useState({
    status: '',
    notes: ''
  })
  const [completeData, setCompleteData] = useState({
    eventCost: '',
    eventProfit: ''
  })
  const [newBookingData, setNewBookingData] = useState({
    client_name: '',
    client_email: '',
    client_phone: '',
    service_type: '',
    event_type: '',
    event_date: '',
    event_time: '',
    duration_hours: 4,
    participants: '',
    location: '',
    special_requests: ''
  })

  // Load bookings from API
  useEffect(() => {
    loadBookings()
  }, [])

  useEffect(() => {
    filterBookingsByMonth()
  }, [bookings, selectedMonth])

  const filterBookingsByMonth = () => {
    if (!selectedMonth) {
      setFilteredBookings(bookings)
      return
    }

    const filtered = bookings.filter(booking => {
      if (!booking.event_date) return false
      const eventDate = new Date(booking.event_date)
      const eventMonth = `${String(eventDate.getMonth() + 1).padStart(2, '0')}-${eventDate.getFullYear()}`
      return eventMonth === selectedMonth
    })

    setFilteredBookings(filtered)
  }

  const loadBookings = async () => {
    try {
      setLoading(true)
      const response = await bookingsAPI.getAll()
      setBookings(response.data)
    } catch (error) {
      console.error('Error loading bookings:', error)
      toast.error('Error al cargar agendamientos')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      confirmed: 'success',
      completed: 'info',
      cancelled: 'error'
    }
    return colors[status] || 'default'
  }

  const getServiceLabel = (type) => {
    return type === 'workshop' ? 'Pizzeros en Acción' : 'Pizza Party'
  }

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pendiente',
      confirmed: 'Confirmado',
      completed: 'Completado',
      cancelled: 'Cancelado'
    }
    return labels[status] || status
  }

  const handleEditClick = (booking) => {
    setSelectedBooking(booking)
    setFormData({
      status: booking.status,
      notes: booking.notes || ''
    })
    setEditDialog(true)
  }

  const handleUpdateBooking = async () => {
    try {
      const oldStatus = selectedBooking.status
      // Solo enviar campos que el backend acepta
      const updatePayload = {}
      if (formData.status) updatePayload.status = formData.status
      // Opcional: persistir notas en special_requests para no perderlas
      if (formData.notes) {
        updatePayload.special_requests = formData.notes
      }

      await bookingsAPI.update(selectedBooking.id, updatePayload)

      // Mostrar notificación especial si se confirma el evento
      if (oldStatus !== 'confirmed' && formData.status === 'confirmed') {
        toast.success('Agendamiento confirmado - Notificaciones enviadas por email y WhatsApp', {
          duration: 4000,
          icon: '📧📱'
        })
      } else {
        toast.success('Agendamiento actualizado')
      }

      setEditDialog(false)
      loadBookings()
    } catch (error) {
      console.error('Error updating booking:', error)
      toast.error('Error al actualizar agendamiento')
    }
  }

  const handleCreateEvent = async (booking) => {
    try {
      const eventData = {
        booking_id: booking.id,
        title: `${getServiceLabel(booking.service_type)} - ${booking.client_name}`,
        description: booking.special_requests || '',
        status: 'completed'
      }

      await eventsAPI.create(eventData)

      // Update booking status to completed
      await bookingsAPI.update(booking.id, { status: 'completed' })

      toast.success('Evento creado y agendamiento marcado como completado')
      loadBookings()
    } catch (error) {
      console.error('Error creating event:', error)
      toast.error('Error al crear evento')
    }
  }

  const handleNewBookingClick = () => {
    setNewBookingData({
      client_name: '',
      client_email: '',
      client_phone: '',
      service_type: '',
      event_type: '',
      event_date: '',
      event_time: '',
      duration_hours: 4,
      participants: '',
      location: '',
      special_requests: ''
    })
    setCreateDialog(true)
  }

  const handleNewBookingChange = (event) => {
    const { name, value } = event.target
    setNewBookingData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleCreateBooking = async () => {
    try {
      const bookingData = {
        client_name: newBookingData.client_name,
        client_email: newBookingData.client_email,
        client_phone: newBookingData.client_phone,
        // Mapear enums esperados por backend
        service_type: newBookingData.service_type || 'workshop', // 'workshop' | 'pizza_party'
        event_type: newBookingData.event_type || 'private', // 'birthday' | 'corporate' | 'school' | 'private'
        event_date: newBookingData.event_date, // ISO date string
        event_time: newBookingData.event_time,
        duration_hours: parseInt(newBookingData.duration_hours || 4),
        participants: parseInt(newBookingData.participants || 0),
        location: newBookingData.location,
        special_requests: newBookingData.special_requests || ''
      }

      await bookingsAPI.create(bookingData)
      toast.success('Agendamiento creado exitosamente')
      setCreateDialog(false)
      loadBookings()
    } catch (error) {
      console.error('Error creating booking:', error)
      toast.error('Error al crear agendamiento')
    }
  }

  const handleCompleteEventClick = (booking) => {
    setSelectedBooking(booking)
    setCompleteData({
      eventCost: '',
      eventProfit: ''
    })
    setCompleteDialog(true)
  }

  const handleCompleteDataChange = (event) => {
    const { name, value } = event.target
    setCompleteData(prev => {
      const updated = { ...prev, [name]: value }

      // Calcular utilidad automáticamente si tenemos precio estimado y costo
      if (name === 'eventCost' && selectedBooking?.estimated_price && value) {
        const cost = parseFloat(value)
        const revenue = selectedBooking.estimated_price
        const profit = revenue - cost
        updated.eventProfit = profit.toString()
      }

      return updated
    })
  }

  const handleCompleteEvent = async () => {
    try {
      // Preparar datos para enviar al backend
      const updateData = { 
        status: 'completed'
      }

      // Agregar event_cost y event_profit si están disponibles
      if (completeData.eventCost && completeData.eventCost.trim() !== '') {
        updateData.event_cost = parseFloat(completeData.eventCost)
      }
      
      if (completeData.eventProfit && completeData.eventProfit.trim() !== '') {
        updateData.event_profit = parseFloat(completeData.eventProfit)
      }

      console.log('Enviando datos al backend:', updateData)

      // Actualizar en backend
      await bookingsAPI.update(selectedBooking.id, updateData)

      toast.success('Evento completado con costo y utilidad guardados')
      setCompleteDialog(false)
      
      // Limpiar datos del formulario
      setCompleteData({
        eventCost: '',
        eventProfit: ''
      })
      
      loadBookings()
    } catch (error) {
      console.error('Error completing event:', error)
      toast.error('Error al completar evento')
    }
  }

  const handleDeleteClick = (booking) => {
    setSelectedBooking(booking)
    setDeleteDialog(true)
  }

  const handleDeleteBooking = async () => {
    try {
      await bookingsAPI.cancel(selectedBooking.id)
      toast.success('Agendamiento eliminado exitosamente')
      setDeleteDialog(false)
      setSelectedBooking(null)
      loadBookings()
    } catch (error) {
      console.error('Error deleting booking:', error)
      toast.error('Error al eliminar agendamiento')
    }
  }

  // Prepare calendar events
  const calendarEvents = bookings.map(booking => {
    // Si event_date ya es un datetime completo, usarlo directamente
    const eventDate = new Date(booking.event_date)
    return {
      id: booking.id,
      title: `${booking.client_name} - ${getServiceLabel(booking.service_type)}`,
      start: eventDate,
      end: new Date(eventDate.getTime() + (booking.duration_hours || 4) * 60 * 60 * 1000), // Agregar duración
      resource: booking
    }
  })

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Gestión de Agendamientos</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            select
            label="Filtrar por mes"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            size="small"
            sx={{ minWidth: 140 }}
          >
            <MenuItem value="">Todos los meses</MenuItem>
            {(() => {
              const months = []
              const currentDate = new Date()
              for (let i = 0; i < 12; i++) {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1)
                const monthValue = `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`
                const monthLabel = `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`
                months.push(
                  <MenuItem key={monthValue} value={monthValue}>
                    {monthLabel}
                  </MenuItem>
                )
              }
              return months
            })()}
          </TextField>
          <ToggleButtonGroup
            value={view}
            exclusive
            onChange={(e, newView) => newView && setView(newView)}
            size="small"
          >
            <ToggleButton value="list">
              <ViewList sx={{ mr: 1 }} />
              Lista
            </ToggleButton>
            <ToggleButton value="calendar">
              <CalendarMonth sx={{ mr: 1 }} />
              Calendario
            </ToggleButton>
          </ToggleButtonGroup>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleNewBookingClick}
            sx={{ whiteSpace: 'nowrap' }}
          >
            Agregar
          </Button>
        </Box>
      </Box>

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando agendamientos...</Typography>
          </CardContent>
        </Card>
      ) : (
        <>
          {view === 'list' ? (
            <Card>
              <CardContent>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Cliente</TableCell>
                        <TableCell>Servicio</TableCell>
                        <TableCell>Fecha</TableCell>
                        <TableCell>Participantes</TableCell>
                        <TableCell>Estado</TableCell>
                        <TableCell>Precio</TableCell>
                        <TableCell>Costo</TableCell>
                        <TableCell>Utilidad</TableCell>
                        <TableCell>Acciones</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredBookings.map((booking) => (
                        <TableRow key={booking.id}>
                          <TableCell>
                            <Box>
                              <Typography variant="body2" fontWeight="bold">
                                {booking.client_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {booking.client_phone}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>{getServiceLabel(booking.service_type)}</TableCell>
                          <TableCell>
                            <Box>
                              <Typography variant="body2">
                                {new Date(booking.event_date).toLocaleDateString('es-CL')}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {booking.event_time || 'Hora por definir'}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>{booking.participants}</TableCell>
                          <TableCell>
                            <Chip
                              label={getStatusLabel(booking.status)}
                              color={getStatusColor(booking.status)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            ${Math.round(booking.estimated_price || 0).toLocaleString('es-CL') || 'N/A'}
                          </TableCell>
                          <TableCell>
                            {booking.event_cost !== undefined && booking.event_cost !== null ?
                              `$${Math.round(booking.event_cost).toLocaleString('es-CL')}` :
                              (booking.status === 'completed' ? 'N/A' : '-')
                            }
                          </TableCell>
                          <TableCell>
                            {booking.event_profit !== undefined && booking.event_profit !== null ?
                              (
                                <Typography
                                  color={booking.event_profit >= 0 ? 'success.main' : 'error.main'}
                                  fontWeight="bold"
                                >
                                  ${Math.round(booking.event_profit).toLocaleString('es-CL')}
                                </Typography>
                              ) :
                              (booking.status === 'completed' ? 'N/A' : '-')
                            }
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              <Button
                                size="small"
                                startIcon={<Edit />}
                                onClick={() => handleEditClick(booking)}
                              >
                                Editar
                              </Button>
                              {booking.status === 'confirmed' && (
                                <Button
                                  size="small"
                                  color="success"
                                  startIcon={<CheckCircle />}
                                  onClick={() => handleCompleteEventClick(booking)}
                                >
                                  Completar Evento
                                </Button>
                              )}
                              <Button
                                size="small"
                                color="error"
                                startIcon={<Delete />}
                                onClick={() => handleDeleteClick(booking)}
                                disabled={booking.status === 'completed'}
                              >
                                Eliminar
                              </Button>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                      {filteredBookings.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={9} align="center">
                            <Typography color="text.secondary">
                              {selectedMonth ? `No hay agendamientos para el mes seleccionado.` : `No hay agendamientos disponibles`}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <Box sx={{ height: 600 }}>
                  <Calendar
                    localizer={localizer}
                    events={calendarEvents}
                    startAccessor="start"
                    endAccessor="end"
                    culture="es"
                    messages={{
                      next: "Siguiente",
                      previous: "Anterior",
                      today: "Hoy",
                      month: "Mes",
                      week: "Semana",
                      day: "Día",
                      agenda: "Agenda",
                      date: "Fecha",
                      time: "Hora",
                      event: "Evento",
                      noEventsInRange: "No hay eventos en este rango",
                      showMore: total => `+ Ver más (${total})`
                    }}
                    onSelectEvent={(event) => handleEditClick(event.resource)}
                  />
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Editar Agendamiento</DialogTitle>
        <DialogContent>
          {selectedBooking && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Cliente:</strong> {selectedBooking.client_name}<br />
                    <strong>Servicio:</strong> {getServiceLabel(selectedBooking.service_type)}<br />
                    <strong>Fecha:</strong> {new Date(selectedBooking.event_date).toLocaleDateString('es-CL')}<br />
                    <strong>Participantes:</strong> {selectedBooking.participants}
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Estado</InputLabel>
                  <Select
                    value={formData.status}
                    onChange={(e) => setFormData({...formData, status: e.target.value})}
                    label="Estado"
                  >
                    <MenuItem value="pending">Pendiente</MenuItem>
                    <MenuItem value="confirmed">Confirmado</MenuItem>
                    <MenuItem value="completed">Completado</MenuItem>
                    <MenuItem value="cancelled">Cancelado</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Notas"
                  multiline
                  rows={3}
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  placeholder="Notas adicionales sobre el agendamiento..."
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(false)}>Cancelar</Button>
          <Button onClick={handleUpdateBooking} variant="contained">
            Guardar Cambios
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create New Booking Dialog */}
      <Dialog open={createDialog} onClose={() => setCreateDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Crear Nuevo Agendamiento</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Nombre del Cliente"
                name="client_name"
                value={newBookingData.client_name}
                onChange={handleNewBookingChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Email"
                name="client_email"
                type="email"
                value={newBookingData.client_email}
                onChange={handleNewBookingChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Teléfono"
                name="client_phone"
                value={newBookingData.client_phone}
                onChange={handleNewBookingChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Tipo de Servicio</InputLabel>
                <Select
                  name="service_type"
                  value={newBookingData.service_type}
                  onChange={handleNewBookingChange}
                  label="Tipo de Servicio"
                >
                  <MenuItem value="workshop">Pizzeros en Acción</MenuItem>
                  <MenuItem value="pizza_party">Pizza Party</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Tipo de Evento</InputLabel>
                <Select
                  name="event_type"
                  value={newBookingData.event_type}
                  onChange={handleNewBookingChange}
                  label="Tipo de Evento"
                >
                  <MenuItem value="birthday">Cumpleaños</MenuItem>
                  <MenuItem value="corporate">Corporativo</MenuItem>
                  <MenuItem value="school">Escolar</MenuItem>
                  <MenuItem value="private">Evento Privado</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Número de Participantes"
                name="participants"
                type="number"
                value={newBookingData.participants}
                onChange={handleNewBookingChange}
                inputProps={{ min: 1, max: 50 }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Fecha del Evento"
                name="event_date"
                type="date"
                value={newBookingData.event_date}
                onChange={handleNewBookingChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Hora del Evento"
                name="event_time"
                type="time"
                value={newBookingData.event_time}
                onChange={handleNewBookingChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Ubicación del Evento"
                name="location"
                value={newBookingData.location}
                onChange={handleNewBookingChange}
                required
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Solicitudes Especiales"
                name="special_requests"
                value={newBookingData.special_requests}
                onChange={handleNewBookingChange}
                multiline
                rows={3}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialog(false)}>Cancelar</Button>
          <Button onClick={handleCreateBooking} variant="contained">
            Crear Agendamiento
          </Button>
        </DialogActions>
      </Dialog>

      {/* Complete Event Dialog */}
      <Dialog open={completeDialog} onClose={() => setCompleteDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Completar Evento</DialogTitle>
        <DialogContent>
          {selectedBooking && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Cliente:</strong> {selectedBooking.client_name}<br />
                    <strong>Servicio:</strong> {getServiceLabel(selectedBooking.service_type)}<br />
                    <strong>Fecha:</strong> {new Date(selectedBooking.event_date).toLocaleDateString('es-CL')}<br />
                    <strong>Participantes:</strong> {selectedBooking.participants}<br />
                    <strong>Precio Estimado:</strong> ${selectedBooking.estimated_price?.toLocaleString('es-CL')} CLP
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Costo del Evento"
                  name="eventCost"
                  type="number"
                  value={completeData.eventCost}
                  onChange={handleCompleteDataChange}
                  helperText="Costo total de materiales, personal, transporte, etc."
                  InputProps={{
                    startAdornment: <span style={{ marginRight: '8px' }}>$</span>
                  }}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Utilidad del Evento"
                  name="eventProfit"
                  type="number"
                  value={completeData.eventProfit}
                  onChange={handleCompleteDataChange}
                  helperText="Se calcula automáticamente: Precio - Costo"
                  InputProps={{
                    startAdornment: <span style={{ marginRight: '8px' }}>$</span>
                  }}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  Al completar el evento, se marcará como "Completado" y se agregará a la galería de eventos.
                </Typography>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompleteDialog(false)}>Cancelar</Button>
          <Button onClick={handleCompleteEvent} variant="contained" color="success">
            Completar Evento
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          {selectedBooking && (
            <Box sx={{ py: 2 }}>
              <Typography variant="body1" gutterBottom>
                ¿Estás seguro de que deseas eliminar este agendamiento?
              </Typography>
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  <strong>Cliente:</strong> {selectedBooking.client_name}<br />
                  <strong>Servicio:</strong> {getServiceLabel(selectedBooking.service_type)}<br />
                  <strong>Fecha:</strong> {new Date(selectedBooking.event_date).toLocaleDateString('es-CL')}<br />
                  <strong>Hora:</strong> {selectedBooking.event_time}<br />
                  <strong>Estado:</strong> {getStatusLabel(selectedBooking.status)}
                </Typography>
              </Box>
              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  Esta acción no se puede deshacer. El agendamiento será eliminado permanentemente.
                </Typography>
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)}>Cancelar</Button>
          <Button
            onClick={handleDeleteBooking}
            variant="contained"
            color="error"
            startIcon={<Delete />}
          >
            Eliminar Agendamiento
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default BookingsManagement