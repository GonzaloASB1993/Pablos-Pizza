import { useState, useEffect, useMemo } from 'react'
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
    Alert,
    IconButton
} from '@mui/material'
import {
    Add,
    Edit,
    Delete,
    ViewList,
    CalendarMonth,
    CheckCircle,
    Cancel,
    Close
} from '@mui/icons-material'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { es } from 'date-fns/locale'
import { bookingsAPI, eventsAPI } from '../../services/api'
import toast from 'react-hot-toast'
import 'react-big-calendar/lib/css/react-big-calendar.css'

const locales = { 'es': es }
const localizer = dateFnsLocalizer({
    format,
    parse,
    startOfWeek,
    getDay,
    locales,
})

const BookingsManagement = () => {
    const [bookings, setBookings] = useState([])
    const [view, setView] = useState('list')
    const [loading, setLoading] = useState(true)
    const [selectedMonth, setSelectedMonth] = useState("")
    const [editDialog, setEditDialog] = useState(false)
    const [createDialog, setCreateDialog] = useState(false)
    const [deleteDialog, setDeleteDialog] = useState(false)
    const [selectedBooking, setSelectedBooking] = useState(null)
    const [formData, setFormData] = useState({
        status: '',
        notes: '',
        event_date: '',
        event_time: '',
        service_type: '',
        participants: '',
        estimated_price: ''
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

    const filteredBookings = useMemo(() => {
        if (!selectedMonth) return bookings

        return bookings.filter(booking => {
            if (!booking.event_date) return false
            const eventDate = new Date(booking.event_date)
            const eventMonth = `${String(eventDate.getMonth() + 1).padStart(2, '0')}-${eventDate.getFullYear()}`
            return eventMonth === selectedMonth
        })
    }, [bookings, selectedMonth])

    useEffect(() => {
        loadBookings()
    }, [])

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
            notes: booking.notes || '',
            event_date: booking.event_date ? booking.event_date.split('T')[0] : '',
            event_time: booking.event_time || '',
            service_type: booking.service_type || '',
            participants: booking.participants || '',
            estimated_price: booking.estimated_price || '',
            event_cost: booking.event_cost || '',
            event_profit: booking.event_profit || ''
        })
        setEditDialog(true)
    }

    const handleUpdateBooking = async () => {
        try {
            const oldStatus = selectedBooking.status
            const updatePayload = {}

            if (formData.status) updatePayload.status = formData.status
            if (formData.notes) updatePayload.special_requests = formData.notes
            if (formData.event_date) updatePayload.event_date = formData.event_date
            if (formData.event_time) updatePayload.event_time = formData.event_time
            if (formData.service_type) updatePayload.service_type = formData.service_type
            if (formData.participants) updatePayload.participants = parseInt(formData.participants)
            if (formData.estimated_price) updatePayload.estimated_price = parseFloat(formData.estimated_price)

            // Add cost and profit fields when completing
            if (formData.status === 'completed') {
                if (formData.event_cost !== undefined) updatePayload.event_cost = parseFloat(formData.event_cost) || 0
                if (formData.event_profit !== undefined) updatePayload.event_profit = parseFloat(formData.event_profit) || 0
            }

            await bookingsAPI.update(selectedBooking.id, updatePayload)

            if (oldStatus !== 'confirmed' && formData.status === 'confirmed') {
                toast.success('Agendamiento confirmado - Notificaciones enviadas por email y WhatsApp', {
                    duration: 4000,
                    icon: '🎉'
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
            // El backend ya crea eventos automáticamente cuando se marca como completed con costs
            // Solo actualizamos el booking con status completed y costos/ganancias
            const updateData = {
                status: 'completed',
                event_cost: 0, // Trigger automatic event creation
                event_profit: booking.estimated_price || 0
            }

            await bookingsAPI.update(booking.id, updateData)

            toast.success('Agendamiento marcado como completado - Evento creado automáticamente')
            loadBookings()
        } catch (error) {
            console.error('Error completing booking:', error)
            toast.error('Error al marcar como completado')
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
                service_type: newBookingData.service_type || 'workshop',
                event_type: newBookingData.event_type || 'private',
                event_date: newBookingData.event_date,
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

    const handleDeleteBooking = async () => {
        try {
            await bookingsAPI.delete(selectedBooking.id)
            toast.success('Agendamiento eliminado')
            setDeleteDialog(false)
            loadBookings()
        } catch (error) {
            console.error('Error deleting booking:', error)
            toast.error('Error al eliminar agendamiento')
        }
    }

    const calendarEvents = bookings
        .filter(booking => booking.event_date && booking.status !== 'cancelled')
        .map(booking => ({
            id: booking.id,
            title: `${getServiceLabel(booking.service_type)} - ${booking.client_name}`,
            start: new Date(booking.event_date + (booking.event_time ? `T${booking.event_time}` : 'T10:00')),
            end: new Date(booking.event_date + (booking.event_time ? `T${booking.event_time}` : 'T10:00')),
            resource: booking
        }))

    const getMonthOptions = () => {
        const months = []
        for (let i = 0; i < 12; i++) {
            const date = new Date()
            date.setMonth(date.getMonth() + i - 6)
            const monthKey = `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`
            const monthLabel = format(date, 'MMMM yyyy', { locale: es })
            months.push({ key: monthKey, label: monthLabel })
        }
        return months
    }

    const pendingBookings = bookings.filter(b => b.status === 'pending')
    const confirmedBookings = bookings.filter(b => b.status === 'confirmed')
    const completedBookings = bookings.filter(b => b.status === 'completed')

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                    <Typography variant="h4">Gestión de Agendamientos</Typography>
                    <Typography variant="body2" color="text.secondary">
                        Administra las reservas de eventos y talleres
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                        variant="contained"
                        startIcon={<Add />}
                        onClick={handleNewBookingClick}
                    >
                        Nuevo Agendamiento
                    </Button>
                    <ToggleButtonGroup
                        value={view}
                        exclusive
                        onChange={(e, newView) => newView && setView(newView)}
                    >
                        <ToggleButton value="list">
                            <ViewList />
                        </ToggleButton>
                        <ToggleButton value="calendar">
                            <CalendarMonth />
                        </ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            </Box>

            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h6" color="warning.main">{pendingBookings.length}</Typography>
                        <Typography variant="caption">Pendientes</Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h6" color="success.main">{confirmedBookings.length}</Typography>
                        <Typography variant="caption">Confirmados</Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h6" color="info.main">{completedBookings.length}</Typography>
                        <Typography variant="caption">Completados</Typography>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <FormControl fullWidth size="small">
                        <InputLabel>Filtrar por mes</InputLabel>
                        <Select
                            value={selectedMonth}
                            label="Filtrar por mes"
                            onChange={(e) => setSelectedMonth(e.target.value)}
                        >
                            <MenuItem value="">Todos los meses</MenuItem>
                            {getMonthOptions().map(month => (
                                <MenuItem key={month.key} value={month.key}>
                                    {month.label}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>
            </Grid>

            {pendingBookings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Tienes {pendingBookings.length} agendamiento(s) pendiente(s) de confirmación.
                </Alert>
            )}

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
                                        <TableCell>Estado</TableCell>
                                        <TableCell>Participantes</TableCell>
                                        <TableCell>Total</TableCell>
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
                                            <TableCell>
                                                {getServiceLabel(booking.service_type)}
                                            </TableCell>
                                            <TableCell>
                                                {booking.event_date ? format(new Date(booking.event_date), 'dd/MM/yyyy') : '-'}
                                                {booking.event_time && (
                                                    <Typography variant="caption" display="block">
                                                        {booking.event_time}
                                                    </Typography>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={getStatusLabel(booking.status)}
                                                    color={getStatusColor(booking.status)}
                                                    size="small"
                                                />
                                            </TableCell>
                                            <TableCell>{booking.participants}</TableCell>
                                            <TableCell>
                                                <Typography variant="body2" fontWeight="bold">
                                                    ${booking.estimated_price ? booking.estimated_price.toLocaleString() : '-'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" color={booking.event_cost ? 'text.primary' : 'text.secondary'}>
                                                    ${booking.event_cost ? booking.event_cost.toLocaleString() : '-'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Typography
                                                    variant="body2"
                                                    fontWeight="bold"
                                                    color={booking.event_profit > 0 ? 'success.main' : 'text.secondary'}
                                                >
                                                    ${booking.event_profit ? booking.event_profit.toLocaleString() : '-'}
                                                </Typography>
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
                                                            color="info"
                                                            startIcon={<CheckCircle />}
                                                            onClick={() => handleCreateEvent(booking)}
                                                        >
                                                            Completar
                                                        </Button>
                                                    )}
                                                    <Button
                                                        size="small"
                                                        color="error"
                                                        startIcon={<Delete />}
                                                        onClick={() => {
                                                            setSelectedBooking(booking)
                                                            setDeleteDialog(true)
                                                        }}
                                                    >
                                                        Eliminar
                                                    </Button>
                                                </Box>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {filteredBookings.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={6} align="center">
                                                <Typography color="text.secondary">
                                                    No hay agendamientos disponibles
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
                                    day: "Día"
                                }}
                                onSelectEvent={(event) => handleEditClick(event.resource)}
                            />
                        </Box>
                    </CardContent>
                </Card>
            )}

            <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Editar Agendamiento
                    <IconButton
                        onClick={() => setEditDialog(false)}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                        <Close />
                    </IconButton>
                </DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                                <InputLabel>Estado</InputLabel>
                                <Select
                                    value={formData.status}
                                    label="Estado"
                                    onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                                >
                                    <MenuItem value="pending">Pendiente</MenuItem>
                                    <MenuItem value="confirmed">Confirmado</MenuItem>
                                    <MenuItem value="completed">Completado</MenuItem>
                                    <MenuItem value="cancelled">Cancelado</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Participantes"
                                value={formData.participants}
                                onChange={(e) => setFormData(prev => ({ ...prev, participants: e.target.value }))}
                                type="number"
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Fecha del Evento"
                                type="date"
                                value={formData.event_date}
                                onChange={(e) => setFormData(prev => ({ ...prev, event_date: e.target.value }))}
                                InputLabelProps={{ shrink: true }}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Hora del Evento"
                                type="time"
                                value={formData.event_time}
                                onChange={(e) => setFormData(prev => ({ ...prev, event_time: e.target.value }))}
                                InputLabelProps={{ shrink: true }}
                            />
                        </Grid>
                        {formData.status === 'completed' && (
                            <>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Costo del Evento"
                                        type="number"
                                        value={formData.event_cost || ''}
                                        onChange={(e) => {
                                            const cost = parseFloat(e.target.value) || 0;
                                            const price = parseFloat(formData.estimated_price) || 0;
                                            setFormData(prev => ({
                                                ...prev,
                                                event_cost: cost,
                                                event_profit: price - cost
                                            }));
                                        }}
                                        InputProps={{
                                            startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                        }}
                                    />
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <TextField
                                        fullWidth
                                        label="Utilidad"
                                        type="number"
                                        value={formData.event_profit || ''}
                                        InputProps={{
                                            startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                            readOnly: true,
                                        }}
                                        sx={{
                                            '& .MuiInputBase-input': {
                                                color: (formData.event_profit || 0) > 0 ? 'success.main' : 'text.secondary',
                                                fontWeight: 'bold'
                                            }
                                        }}
                                    />
                                </Grid>
                            </>
                        )}
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Notas adicionales"
                                multiline
                                rows={3}
                                value={formData.notes}
                                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditDialog(false)}>Cancelar</Button>
                    <Button onClick={handleUpdateBooking} variant="contained">
                        Actualizar
                    </Button>
                </DialogActions>
            </Dialog>

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
                            <FormControl fullWidth>
                                <InputLabel>Tipo de Servicio</InputLabel>
                                <Select
                                    name="service_type"
                                    value={newBookingData.service_type}
                                    label="Tipo de Servicio"
                                    onChange={handleNewBookingChange}
                                >
                                    <MenuItem value="workshop">Pizzeros en Acción</MenuItem>
                                    <MenuItem value="pizza_party">Pizza Party</MenuItem>
                                </Select>
                            </FormControl>
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
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Número de Participantes"
                                name="participants"
                                type="number"
                                value={newBookingData.participants}
                                onChange={handleNewBookingChange}
                                required
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Ubicación"
                                name="location"
                                value={newBookingData.location}
                                onChange={handleNewBookingChange}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Solicitudes Especiales"
                                name="special_requests"
                                multiline
                                rows={3}
                                value={newBookingData.special_requests}
                                onChange={handleNewBookingChange}
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

            <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
                <DialogTitle>Confirmar Eliminación</DialogTitle>
                <DialogContent>
                    <Typography>
                        ¿Estás seguro de que quieres eliminar este agendamiento?
                        Esta acción no se puede deshacer.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialog(false)}>Cancelar</Button>
                    <Button onClick={handleDeleteBooking} color="error" variant="contained">
                        Eliminar
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default BookingsManagement