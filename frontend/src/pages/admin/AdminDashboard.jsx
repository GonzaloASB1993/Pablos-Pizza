import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material'
import {
  TrendingUp,
  Event,
  AttachMoney,
  People,
  Warning,
  CheckCircle,
  Info
} from '@mui/icons-material'
import { bookingsAPI, eventsAPI, reviewsAPI } from '../../services/api'
import { useNavigate } from 'react-router-dom'
import logo from '../../assets/logo.png'

const AdminDashboard = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)

  // Estado para el filtro de mes
  const currentDate = new Date()
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth())
  const [selectedYear, setSelectedYear] = useState(currentDate.getFullYear())

  const [stats, setStats] = useState({
    newBookings: 0,
    monthlyEvents: 0,
    monthlyIncome: 0,
    monthlyProfit: 0
  })
  const [todayBookings, setTodayBookings] = useState([])
  const [alerts, setAlerts] = useState({
    pendingReviews: 0,
    confirmedEvents: 0,
    completedEventsWithoutCost: 0
  })

  useEffect(() => {
    loadDashboardData()
  }, [selectedMonth, selectedYear])

  const loadDashboardData = async () => {
    try {
      setLoading(true)

      // Load bookings and calculate stats
      const [bookingsResponse, eventsResponse, reviewsResponse] = await Promise.all([
        bookingsAPI.getAll(),
        eventsAPI.getAll(),
        reviewsAPI.getAll()
      ])

      const bookings = bookingsResponse.data || []
      const events = eventsResponse.data || []
      const reviews = reviewsResponse.data || []

      // Debug: log first booking and event to see data structure
      console.log('🔍 DEBUG - Sample booking:', bookings[0])
      console.log('🔍 DEBUG - Sample event:', events[0])
      console.log('🔍 DEBUG - Total bookings:', bookings.length)
      console.log('🔍 DEBUG - Total events:', events.length)

      // Calculate today's bookings
      const today = new Date()
      const todayStr = today.toISOString().split('T')[0]
      const todayBookingsData = bookings.filter(booking => {
        const createdDate = booking.created_at ? new Date(booking.created_at).toISOString().split('T')[0] : null
        return createdDate === todayStr
      })

      // Calculate monthly stats using selected month/year
      // Count events from bookings (confirmed/completed) for the selected month
      const monthlyEvents = bookings.filter(booking => {
        if (booking.status !== 'confirmed' && booking.status !== 'completed') return false
        const eventDate = booking.event_date ? new Date(booking.event_date) : null
        return eventDate && eventDate.getMonth() === selectedMonth && eventDate.getFullYear() === selectedYear
      })

      // Calculate monthly income from confirmed bookings for selected month
      const confirmedBookings = bookings.filter(booking => {
        if (booking.status !== 'confirmed' && booking.status !== 'completed') return false
        const eventDate = booking.event_date ? new Date(booking.event_date) : null

        // For revenue calculation, include selected month events
        let includeInRevenue = false
        if (eventDate) {
          includeInRevenue = eventDate.getMonth() === selectedMonth && eventDate.getFullYear() === selectedYear
        }

        // Debug each booking
        console.log(`📊 Booking ${booking.id}: status=${booking.status}, date=${booking.event_date}, parsed=${eventDate}, includeInRevenue=${includeInRevenue}, price=${booking.estimated_price}`)

        return includeInRevenue
      })

      console.log(`💰 Confirmed bookings this month:`, confirmedBookings.length)

      const monthlyIncome = confirmedBookings.reduce((total, booking) => {
        const price = booking.estimated_price || 0
        console.log(`💰 Adding price: ${price} (total so far: ${total + price})`)
        return total + price
      }, 0)

      const monthlyProfit = monthlyEvents.reduce((total, booking) => {
        const profit = booking.profit || 0
        console.log(`💸 Booking profit: ${profit} (total so far: ${total + profit})`)
        return total + profit
      }, 0)

      console.log(`💰 Final monthly income: ${monthlyIncome}`)
      console.log(`💸 Final monthly profit: ${monthlyProfit}`)

      // Calculate alerts
      const pendingReviews = reviews.filter(review => !review.approved).length
      const confirmedEvents = bookings.filter(booking => booking.status === 'confirmed').length
      const completedEventsWithoutCost = bookings.filter(booking =>
        booking.status === 'completed' && (booking.event_cost === undefined || booking.event_cost === null)
      ).length

      setStats({
        newBookings: todayBookingsData.length,
        monthlyEvents: monthlyEvents.length,
        monthlyIncome: Math.round(monthlyIncome),
        monthlyProfit: Math.round(monthlyProfit)
      })

      setTodayBookings(todayBookingsData)
      setAlerts({
        pendingReviews,
        confirmedEvents,
        completedEventsWithoutCost
      })

    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Funciones para el manejo del filtro de mes
  const monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ]

  const handleMonthChange = (event) => {
    setSelectedMonth(event.target.value)
  }

  const handleYearChange = (event) => {
    setSelectedYear(event.target.value)
  }

  // Generar años disponibles (3 años atrás hasta 1 año adelante)
  const generateYearOptions = () => {
    const currentYear = new Date().getFullYear()
    const years = []
    for (let i = currentYear - 3; i <= currentYear + 1; i++) {
      years.push(i)
    }
    return years
  }

  const StatCard = ({ title, value, icon, color = 'primary' }) => (
    <Card>
      <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
        <Box sx={{ 
          backgroundColor: `${color}.main`,
          color: 'white',
          p: 2,
          borderRadius: 2,
          mr: 2
        }}>
          {icon}
        </Box>
        <Box>
          <Typography variant="h4" color={`${color}.main`}>
            {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            component="img"
            src={logo}
            alt="Pablo's Pizza Logo"
            sx={{
              width: 60,
              height: 60,
              borderRadius: '50%',
              objectFit: 'cover'
            }}
          />
          <Box>
            <Typography variant="h3" gutterBottom>
              Dashboard - Pablo's Pizza
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Resumen general del negocio y métricas importantes
            </Typography>
          </Box>
        </Box>
        <Button
          variant="outlined"
          onClick={() => loadDashboardData()}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          {loading ? 'Actualizando...' : 'Actualizar'}
        </Button>
      </Box>

      {/* Filtro de Mes */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        mb: 3,
        p: 2,
        borderRadius: 2,
        bgcolor: 'background.paper',
        boxShadow: 1
      }}>
        <Typography variant="h6" sx={{ mr: 2 }}>
          Período:
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Mes</InputLabel>
          <Select
            value={selectedMonth}
            label="Mes"
            onChange={handleMonthChange}
          >
            {monthNames.map((month, index) => (
              <MenuItem key={index} value={index}>
                {month}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>Año</InputLabel>
          <Select
            value={selectedYear}
            label="Año"
            onChange={handleYearChange}
          >
            {generateYearOptions().map((year) => (
              <MenuItem key={year} value={year}>
                {year}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
          Mostrando datos de {monthNames[selectedMonth]} {selectedYear}
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Agendamientos Hoy"
                value={stats.newBookings}
                icon={<Event />}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={`Eventos - ${monthNames[selectedMonth]}`}
                value={stats.monthlyEvents}
                icon={<People />}
                color="secondary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={`Ingresos - ${monthNames[selectedMonth]}`}
                value={`$${stats.monthlyIncome.toLocaleString('es-CL')}`}
                icon={<AttachMoney />}
                color="success"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title={`Utilidad - ${monthNames[selectedMonth]}`}
                value={`$${stats.monthlyProfit.toLocaleString('es-CL')}`}
                icon={<TrendingUp />}
                color="warning"
              />
            </Grid>
          </Grid>
        </>
      )}

      {!loading && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Acciones Rápidas
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Button
                    variant="contained"
                    fullWidth
                    onClick={() => navigate('/admin/agendamientos')}
                    startIcon={<Event />}
                  >
                    Ver Agendamientos ({stats.newBookings} hoy)
                  </Button>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => navigate('/admin/eventos')}
                    startIcon={<People />}
                  >
                    Gestionar Galería de Eventos
                  </Button>
                  {alerts.pendingReviews > 0 && (
                    <Button
                      variant="outlined"
                      fullWidth
                      color="warning"
                      startIcon={<Warning />}
                    >
                      Revisar Reseñas ({alerts.pendingReviews} pendientes)
                    </Button>
                  )}
                  {alerts.confirmedEvents > 0 && (
                    <Button
                      variant="outlined"
                      fullWidth
                      color="success"
                      onClick={() => navigate('/admin/agendamientos')}
                      startIcon={<CheckCircle />}
                    >
                      Completar Eventos ({alerts.confirmedEvents} confirmados)
                    </Button>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Alertas del Sistema
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {alerts.confirmedEvents > 0 && (
                    <Alert severity="success" icon={<CheckCircle />}>
                      {alerts.confirmedEvents} evento{alerts.confirmedEvents > 1 ? 's' : ''} confirmado{alerts.confirmedEvents > 1 ? 's' : ''} listo{alerts.confirmedEvents > 1 ? 's' : ''} para completar
                    </Alert>
                  )}

                  {alerts.pendingReviews > 0 && (
                    <Alert severity="warning" icon={<Warning />}>
                      {alerts.pendingReviews} reseña{alerts.pendingReviews > 1 ? 's' : ''} pendiente{alerts.pendingReviews > 1 ? 's' : ''} de aprobación
                    </Alert>
                  )}

                  {alerts.completedEventsWithoutCost > 0 && (
                    <Alert severity="info" icon={<Info />}>
                      {alerts.completedEventsWithoutCost} evento{alerts.completedEventsWithoutCost > 1 ? 's' : ''} completado{alerts.completedEventsWithoutCost > 1 ? 's' : ''} sin datos de costo
                    </Alert>
                  )}

                  {todayBookings.length > 0 && (
                    <Alert severity="info" icon={<Event />}>
                      {todayBookings.length} nuevo{todayBookings.length > 1 ? 's' : ''} agendamiento{todayBookings.length > 1 ? 's' : ''} hoy
                    </Alert>
                  )}

                  {alerts.confirmedEvents === 0 && alerts.pendingReviews === 0 && alerts.completedEventsWithoutCost === 0 && todayBookings.length === 0 && (
                    <Alert severity="success" icon={<CheckCircle />}>
                      ¡Todo está al día! No hay alertas pendientes.
                    </Alert>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Container>
  )
}

export default AdminDashboard