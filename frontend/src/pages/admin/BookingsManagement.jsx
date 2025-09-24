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
    IconButton,
    Tabs,
    Tab,
    CircularProgress,
    Tooltip
} from '@mui/material'
import {
    Add,
    Edit,
    Delete,
    ViewList,
    CalendarMonth,
    CheckCircle,
    Cancel,
    Close,
    PendingActions,
    EventAvailable,
    Assignment,
    TrendingUp,
    Refresh
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
    const [view, setView] = useState('cards')
    const [loading, setLoading] = useState(true)
    const [updating, setUpdating] = useState(false)
    const [selectedMonth, setSelectedMonth] = useState("")
    const [tabValue, setTabValue] = useState(0)
    const [editDialog, setEditDialog] = useState(false)
    const [createDialog, setCreateDialog] = useState(false)
    const [deleteDialog, setDeleteDialog] = useState(false)
    const [costDialog, setCostDialog] = useState(false)
    const [selectedBooking, setSelectedBooking] = useState(null)
    const [costData, setCostData] = useState({
        event_cost: '',
        event_profit: '',
        notes: ''
    })
    const [formData, setFormData] = useState({
        status: '',
        notes: '',
        event_date: '',
        event_time: '',
        service_type: '',
        participants: '',
        estimated_price: '',
        client_name: '',
        client_email: '',
        client_phone: '',
        location: ''
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
        if (!type) return 'No especificado'

        // Manejar múltiples servicios separados por coma
        if (type.includes(',')) {
            const services = type.split(',').map(s => s.trim())
            return services.map(s => s === 'workshop' ? 'Pizzeros en Acción' : 'Pizza Party').join(' + ')
        }

        // Servicio único
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
            event_date: booking.event_date ? new Date(booking.event_date + 'T00:00:00').toISOString().split('T')[0] : '',
            event_time: booking.event_time || '',
            service_type: booking.service_type || '',
            participants: booking.participants || '',
            estimated_price: booking.estimated_price || '',
            event_cost: booking.event_cost || '',
            event_profit: booking.event_profit || '',
            client_name: booking.client_name || '',
            client_email: booking.client_email || '',
            client_phone: booking.client_phone || '',
            location: booking.location || ''
        })
        setEditDialog(true)
    }

    const handleUpdateBooking = async () => {
        try {
            setUpdating(true)
            console.log('🔧 DEBUG: Starting handleUpdateBooking')
            console.log('🔧 DEBUG: selectedBooking:', selectedBooking)
            console.log('🔧 DEBUG: formData:', formData)

            const oldStatus = selectedBooking.status
            const updatePayload = {}

            if (formData.status) updatePayload.status = formData.status
            if (formData.notes) updatePayload.special_requests = formData.notes
            if (formData.event_date) {
                // Ensure the date is sent in the correct format to avoid timezone issues
                const localDate = new Date(formData.event_date + 'T12:00:00')
                updatePayload.event_date = localDate.toISOString().split('T')[0]
            }
            if (formData.event_time) updatePayload.event_time = formData.event_time
            if (formData.service_type) updatePayload.service_type = formData.service_type
            if (formData.participants) updatePayload.participants = parseInt(formData.participants)

            // Fixed estimated_price handling with better validation
            console.log('🔧 DEBUG: formData.estimated_price raw:', formData.estimated_price, 'type:', typeof formData.estimated_price)
            const priceValue = formData.estimated_price
            if (priceValue !== '' && priceValue !== null && priceValue !== undefined) {
                const parsedPrice = parseFloat(priceValue)
                console.log('🔧 DEBUG: parsedPrice:', parsedPrice, 'isNaN:', isNaN(parsedPrice))
                if (!isNaN(parsedPrice)) {
                    updatePayload.estimated_price = parsedPrice
                    console.log('🔧 DEBUG: Added estimated_price to payload:', parsedPrice)
                }
            }

            if (formData.client_name) updatePayload.client_name = formData.client_name
            if (formData.client_email) updatePayload.client_email = formData.client_email
            if (formData.client_phone) updatePayload.client_phone = formData.client_phone
            if (formData.location) updatePayload.location = formData.location

            // Add cost and profit fields when completing
            if (formData.status === 'completed') {
                if (formData.event_cost !== undefined) updatePayload.event_cost = parseFloat(formData.event_cost) || 0
                if (formData.event_profit !== undefined) updatePayload.event_profit = parseFloat(formData.event_profit) || 0
            }

            console.log('🔧 DEBUG: Final updatePayload:', updatePayload)
            console.log('🔧 DEBUG: Calling bookingsAPI.update with id:', selectedBooking.id)

            const response = await bookingsAPI.update(selectedBooking.id, updatePayload)
            console.log('🔧 DEBUG: Update response:', response)

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
            console.error('🔧 DEBUG: Error updating booking:', error)
            console.error('🔧 DEBUG: Error details:', {
                message: error.message,
                response: error.response,
                status: error.response?.status,
                data: error.response?.data
            })
            toast.error('Error al actualizar agendamiento: ' + (error.response?.data?.detail || error.message))
        } finally {
            setUpdating(false)
        }
    }

    const handleOpenCostDialog = (booking) => {
        setSelectedBooking(booking)
        setCostData({
            event_cost: booking.estimated_price || '',
            event_profit: booking.estimated_price || '',
            notes: ''
        })
        setCostDialog(true)
    }

    const handleCompleteWithCost = async () => {
        try {
            const updateData = {
                status: 'completed',
                event_cost: parseFloat(costData.event_cost) || 0,
                event_profit: parseFloat(costData.event_profit) || 0,
                notes: costData.notes || selectedBooking.notes
            }

            await bookingsAPI.update(selectedBooking.id, updateData)

            toast.success('¡Evento completado con costos registrados!')
            setCostDialog(false)
            setCostData({ event_cost: '', event_profit: '', notes: '' })
            loadBookings()
        } catch (error) {
            console.error('Error completing booking:', error)
            toast.error('Error al completar evento')
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
        .map(booking => {
            // Parse the event date - it could be in ISO format already or just a date string
            let eventDate
            if (booking.event_date.includes('T')) {
                // Already has time in ISO format
                eventDate = new Date(booking.event_date)
            } else {
                // Just a date string, add time
                eventDate = new Date(booking.event_date + (booking.event_time ? `T${booking.event_time}` : 'T10:00'))
            }

            return {
                id: booking.id,
                title: `${getServiceLabel(booking.service_type)} - ${booking.client_name}`,
                start: eventDate,
                end: new Date(eventDate.getTime() + (2 * 60 * 60 * 1000)), // Add 2 hours for end time
                resource: booking
            }
        })

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
    const cancelledBookings = bookings.filter(b => b.status === 'cancelled')

    const getBookingsByStatus = (status) => {
        return bookings.filter(booking => booking.status === status)
    }

    const BookingCard = ({ booking }) => (
        <Card sx={{ mb: 2, borderLeft: `4px solid ${getStatusColor(booking.status) === 'warning' ? '#ff9800' : getStatusColor(booking.status) === 'success' ? '#4caf50' : getStatusColor(booking.status) === 'info' ? '#2196f3' : '#f44336'}` }}>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {booking.client_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            📧 {booking.client_email}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            📞 {booking.client_phone}
                        </Typography>
                        {booking.location && (
                            <Typography variant="body2" color="text.secondary">
                                📍 {booking.location}
                            </Typography>
                        )}
                    </Box>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                        <Chip
                            label={getServiceLabel(booking.service_type)}
                            sx={{ backgroundColor: booking.service_type === 'workshop' ? '#e3f2fd' : '#fff3e0', color: booking.service_type === 'workshop' ? '#1976d2' : '#ed6c02' }}
                            size="small"
                        />
                        <Chip
                            label={getStatusLabel(booking.status)}
                            color={getStatusColor(booking.status)}
                            size="small"
                        />
                    </Box>
                </Box>

                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    {booking.event_date ? format(new Date(booking.event_date), 'dd/MM/yyyy', { locale: es }) : 'Fecha por definir'}
                    {booking.event_time && ` a las ${booking.event_time}`}
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <Typography variant="body2">
                        <strong>Participantes:</strong> {booking.participants}
                    </Typography>
                    <Typography variant="body2">
                        <strong>Precio:</strong> ${booking.estimated_price ? booking.estimated_price.toLocaleString() : 'Por definir'}
                    </Typography>
                </Box>

                {booking.special_requests && (
                    <Typography variant="body2" sx={{ mb: 2, fontStyle: 'italic', color: 'text.secondary' }}>
                        "{booking.special_requests}"
                    </Typography>
                )}

                <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                    Creado: {format(new Date(booking.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                </Typography>

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button size="small" variant="outlined" startIcon={<Edit />} onClick={() => handleEditClick(booking)}>
                        Editar
                    </Button>
                    {booking.status === 'confirmed' && (
                        <Button
                            size="small"
                            variant="contained"
                            color="info"
                            startIcon={<CheckCircle />}
                            onClick={() => handleOpenCostDialog(booking)}
                        >
                            Completar
                        </Button>
                    )}
                    <Button
                        size="small"
                        variant="outlined"
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
            </CardContent>
        </Card>
    )

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    Gestión de Agendamientos
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={loadBookings}
                        disabled={loading}
                    >
                        Actualizar
                    </Button>
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
                        size="small"
                    >
                        <ToggleButton value="cards">
                            <ViewList />
                        </ToggleButton>
                        <ToggleButton value="table">
                            <Assignment />
                        </ToggleButton>
                        <ToggleButton value="calendar">
                            <CalendarMonth />
                        </ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            </Box>

            {/* Statistics Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#fff3e0' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <PendingActions sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                                {pendingBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Pendientes
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#e8f5e8' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <CheckCircle sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                                {confirmedBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Confirmados
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#e3f2fd' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <EventAvailable sx={{ fontSize: 40, color: '#2196f3', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#2196f3' }}>
                                {completedBookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Completados
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={3}>
                    <Card sx={{ bgcolor: '#fce4ec' }}>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <TrendingUp sx={{ fontSize: 40, color: '#e91e63', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 700, color: '#e91e63' }}>
                                {bookings.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {pendingBookings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Tienes {pendingBookings.length} agendamiento(s) pendiente(s) de confirmación.
                </Alert>
            )}

            {/* Tabs for different statuses - only show in cards view */}
            {view === 'cards' && (
                <Paper sx={{ mb: 3 }}>
                    <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
                        <Tab label={`Pendientes (${pendingBookings.length})`} />
                        <Tab label={`Confirmados (${confirmedBookings.length})`} />
                        <Tab label={`Completados (${completedBookings.length})`} />
                    </Tabs>
                </Paper>
            )}

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : view === 'cards' ? (
                <Box>
                    {tabValue === 0 && (
                        <Box>
                            {pendingBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos pendientes</Alert>
                            ) : (
                                pendingBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}

                    {tabValue === 1 && (
                        <Box>
                            {confirmedBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos confirmados</Alert>
                            ) : (
                                confirmedBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}

                    {tabValue === 2 && (
                        <Box>
                            {completedBookings.length === 0 ? (
                                <Alert severity="info">No hay agendamientos completados</Alert>
                            ) : (
                                completedBookings.map(booking => (
                                    <BookingCard key={booking.id} booking={booking} />
                                ))
                            )}
                        </Box>
                    )}
                </Box>
            ) : view === 'table' ? (
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
                                                            onClick={() => handleOpenCostDialog(booking)}
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
                            <FormControl fullWidth>
                                <InputLabel>Tipo de Servicio</InputLabel>
                                <Select
                                    value={formData.service_type}
                                    label="Tipo de Servicio"
                                    onChange={(e) => setFormData(prev => ({ ...prev, service_type: e.target.value }))}
                                >
                                    <MenuItem value="workshop">Pizzeros en Acción</MenuItem>
                                    <MenuItem value="pizza_party">Pizza Party</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Nombre del Cliente"
                                value={formData.client_name}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Email del Cliente"
                                type="email"
                                value={formData.client_email}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_email: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Teléfono del Cliente"
                                value={formData.client_phone}
                                onChange={(e) => setFormData(prev => ({ ...prev, client_phone: e.target.value }))}
                            />
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
                                select
                                value={formData.event_time}
                                onChange={(e) => setFormData(prev => ({ ...prev, event_time: e.target.value }))}
                                SelectProps={{ native: true }}
                                helperText="Solo horarios :00 y :30"
                            >
                                <option value="">Seleccionar hora...</option>
                                <option value="08:00">08:00</option>
                                <option value="08:30">08:30</option>
                                <option value="09:00">09:00</option>
                                <option value="09:30">09:30</option>
                                <option value="10:00">10:00</option>
                                <option value="10:30">10:30</option>
                                <option value="11:00">11:00</option>
                                <option value="11:30">11:30</option>
                                <option value="12:00">12:00</option>
                                <option value="12:30">12:30</option>
                                <option value="13:00">13:00</option>
                                <option value="13:30">13:30</option>
                                <option value="14:00">14:00</option>
                                <option value="14:30">14:30</option>
                                <option value="15:00">15:00</option>
                                <option value="15:30">15:30</option>
                                <option value="16:00">16:00</option>
                                <option value="16:30">16:30</option>
                                <option value="17:00">17:00</option>
                                <option value="17:30">17:30</option>
                                <option value="18:00">18:00</option>
                                <option value="18:30">18:30</option>
                                <option value="19:00">19:00</option>
                                <option value="19:30">19:30</option>
                                <option value="20:00">20:00</option>
                                <option value="20:30">20:30</option>
                            </TextField>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Ubicación"
                                value={formData.location}
                                onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                fullWidth
                                label="Precio Estimado"
                                type="number"
                                value={formData.estimated_price}
                                onChange={(e) => {
                                    const newValue = e.target.value
                                    console.log('🔧 DEBUG: Precio field onChange:', newValue, 'type:', typeof newValue)
                                    setFormData(prev => ({ ...prev, estimated_price: newValue }))
                                }}
                                InputProps={{
                                    startAdornment: <Typography variant="body2" sx={{ mr: 1 }}>$</Typography>,
                                }}
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
                    <Button
                        onClick={() => {
                            console.log('🎯 DEBUG: Actualizar button clicked!')
                            handleUpdateBooking()
                        }}
                        variant="contained"
                        disabled={updating}
                        startIcon={updating ? <CircularProgress size={20} /> : null}
                    >
                        {updating ? 'Actualizando...' : 'Actualizar'}
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
                                select
                                value={newBookingData.event_time}
                                onChange={handleNewBookingChange}
                                SelectProps={{ native: true }}
                                helperText="Solo horarios :00 y :30"
                            >
                                <option value="">Seleccionar hora...</option>
                                <option value="08:00">08:00</option>
                                <option value="08:30">08:30</option>
                                <option value="09:00">09:00</option>
                                <option value="09:30">09:30</option>
                                <option value="10:00">10:00</option>
                                <option value="10:30">10:30</option>
                                <option value="11:00">11:00</option>
                                <option value="11:30">11:30</option>
                                <option value="12:00">12:00</option>
                                <option value="12:30">12:30</option>
                                <option value="13:00">13:00</option>
                                <option value="13:30">13:30</option>
                                <option value="14:00">14:00</option>
                                <option value="14:30">14:30</option>
                                <option value="15:00">15:00</option>
                                <option value="15:30">15:30</option>
                                <option value="16:00">16:00</option>
                                <option value="16:30">16:30</option>
                                <option value="17:00">17:00</option>
                                <option value="17:30">17:30</option>
                                <option value="18:00">18:00</option>
                                <option value="18:30">18:30</option>
                                <option value="19:00">19:00</option>
                                <option value="19:30">19:30</option>
                                <option value="20:00">20:00</option>
                                <option value="20:30">20:30</option>
                            </TextField>
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

            {/* Cost Dialog */}
            <Dialog open={costDialog} onClose={() => setCostDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Completar Evento - Registrar Costos
                </DialogTitle>
                <DialogContent>
                    <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                            Cliente: {selectedBooking?.client_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                            Evento: {selectedBooking?.event_type} - {selectedBooking?.participants} participantes
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                            Fecha: {selectedBooking?.event_date} {selectedBooking?.event_time}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                            Precio estimado inicial: ${selectedBooking?.estimated_price}
                        </Typography>

                        <Grid container spacing={3}>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Costo Real del Evento"
                                    type="number"
                                    fullWidth
                                    value={costData.event_cost}
                                    onChange={(e) => setCostData({...costData, event_cost: e.target.value})}
                                    helperText="Incluye ingredientes, transporte, equipos, etc."
                                    InputProps={{
                                        startAdornment: '$'
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Precio Final Cobrado"
                                    type="number"
                                    fullWidth
                                    value={costData.event_profit}
                                    onChange={(e) => setCostData({...costData, event_profit: e.target.value})}
                                    helperText="Monto total cobrado al cliente"
                                    InputProps={{
                                        startAdornment: '$'
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    <Typography variant="body2">
                                        <strong>Ganancia estimada:</strong> $
                                        {costData.event_profit && costData.event_cost
                                            ? (parseFloat(costData.event_profit) - parseFloat(costData.event_cost)).toFixed(2)
                                            : '0.00'
                                        }
                                    </Typography>
                                </Alert>
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    label="Notas del Evento (Opcional)"
                                    multiline
                                    rows={3}
                                    fullWidth
                                    value={costData.notes}
                                    onChange={(e) => setCostData({...costData, notes: e.target.value})}
                                    helperText="Observaciones, problemas, comentarios del cliente, etc."
                                />
                            </Grid>
                        </Grid>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCostDialog(false)}>
                        Cancelar
                    </Button>
                    <Button
                        onClick={handleCompleteWithCost}
                        variant="contained"
                        color="success"
                        disabled={!costData.event_cost || !costData.event_profit}
                        startIcon={<CheckCircle />}
                    >
                        Completar Evento
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