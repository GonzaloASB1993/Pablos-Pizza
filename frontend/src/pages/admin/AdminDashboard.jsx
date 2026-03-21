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
  MenuItem,
  Skeleton,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  List,
  ListItem,
  ListItemText,
  IconButton,
  LinearProgress
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  Event,
  AttachMoney,
  People,
  Warning,
  CheckCircle,
  Info,
  Assessment,
  Inventory,
  ShowChart,
  Refresh,
  Kitchen,
  CalendarToday,
  EventNote,
  PointOfSale,
  Store,
  PhotoLibrary,
  Receipt
} from '@mui/icons-material'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip as ChartTooltip,
  Legend
} from 'chart.js'
import { Line, Pie } from 'react-chartjs-2'
import { bookingsAPI, reviewsAPI, reportsAPI, inventoryAPI } from '../../services/api'
import { formatCurrency, formatPercentage } from '../../utils/formatters'
import { useNavigate } from 'react-router-dom'
import logo from '../../assets/logo.png'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend
)

const monthNames = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

// --- Inline Components ---

const StatCard = ({ title, value, icon, color = '#FFD700', trend, subtitle }) => (
  <Card
    sx={{
      height: '100%',
      position: 'relative',
      borderLeft: `4px solid ${color}`,
      transition: 'transform 0.2s, box-shadow 0.2s',
      '&:hover': {
        transform: 'translateY(-3px)',
        boxShadow: 4
      }
    }}
  >
    <CardContent sx={{ p: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" color="text.secondary" fontWeight={500} sx={{ mb: 0.5 }}>
            {title}
          </Typography>
          <Typography variant="h5" fontWeight="bold" color="text.primary">
            {value}
          </Typography>
          {trend !== undefined && trend !== null && (
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
              {trend >= 0 ? (
                <TrendingUp sx={{ fontSize: 16, color: 'success.main', mr: 0.5 }} />
              ) : (
                <TrendingDown sx={{ fontSize: 16, color: 'error.main', mr: 0.5 }} />
              )}
              <Typography
                variant="caption"
                fontWeight={600}
                sx={{ color: trend >= 0 ? 'success.main' : 'error.main' }}
              >
                {trend >= 0 ? '+' : ''}{trend.toFixed(1)}% vs mes ant.
              </Typography>
            </Box>
          )}
          {subtitle && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            bgcolor: color + '22',
            color: color,
            p: 1,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
)

const SectionCard = ({ title, icon, children, action, minHeight }) => (
  <Card sx={{ height: '100%', minHeight: minHeight || 'auto' }}>
    <CardContent sx={{ p: 2.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {icon}
          <Typography variant="h6" fontWeight={600}>{title}</Typography>
        </Box>
        {action}
      </Box>
      {children}
    </CardContent>
  </Card>
)

const SkeletonCard = () => (
  <Card sx={{ height: '100%' }}>
    <CardContent sx={{ p: 2.5 }}>
      <Skeleton variant="text" width="60%" height={20} />
      <Skeleton variant="text" width="40%" height={36} sx={{ mt: 1 }} />
      <Skeleton variant="text" width="50%" height={16} sx={{ mt: 0.5 }} />
    </CardContent>
  </Card>
)

// --- Main Component ---

const AdminDashboard = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)

  const currentDate = new Date()
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1)
  const [selectedYear, setSelectedYear] = useState(currentDate.getFullYear())

  // Data states
  const [monthlyReport, setMonthlyReport] = useState(null)
  const [annualReport, setAnnualReport] = useState(null)
  const [dashboardData, setDashboardData] = useState(null)
  const [topClients, setTopClients] = useState([])
  const [inventoryAlerts, setInventoryAlerts] = useState([])
  const [upcomingEvents, setUpcomingEvents] = useState([])
  const [alerts, setAlerts] = useState({
    pendingReviews: 0,
    confirmedEvents: 0,
    completedEventsWithoutCost: 0
  })
  const [trends, setTrends] = useState({})

  useEffect(() => {
    loadDashboardData()
  }, [selectedMonth, selectedYear])

  const loadDashboardData = async () => {
    try {
      setLoading(true)

      const results = await Promise.allSettled([
        reportsAPI.getMonthly(selectedYear, selectedMonth),
        reportsAPI.getAnnual(selectedYear),
        reportsAPI.getDashboard(),
        reportsAPI.getTopClients({ limit: 5 }),
        inventoryAPI.getAlerts(),
        bookingsAPI.getAll(),
        reviewsAPI.getAll()
      ])

      // Monthly report
      if (results[0].status === 'fulfilled') {
        setMonthlyReport(results[0].value.data)
      }

      // Annual report + trend calculation
      if (results[1].status === 'fulfilled') {
        const annual = results[1].value.data
        setAnnualReport(annual)
        calculateTrends(annual, selectedMonth)
      }

      // Dashboard stats
      if (results[2].status === 'fulfilled') {
        setDashboardData(results[2].value.data)
      }

      // Top clients
      if (results[3].status === 'fulfilled') {
        const clientsData = results[3].value.data
        setTopClients(Array.isArray(clientsData) ? clientsData : clientsData.clients || [])
      }

      // Inventory alerts
      if (results[4].status === 'fulfilled') {
        const alertsData = results[4].value.data
        setInventoryAlerts(Array.isArray(alertsData) ? alertsData : alertsData.alerts || [])
      }

      // Bookings -> upcoming events + alerts
      if (results[5].status === 'fulfilled') {
        const bookingsData = results[5].value.data
        const bookings = bookingsData.items || bookingsData || []

        // Upcoming confirmed events (next 7 days)
        const now = new Date()
        const in7Days = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
        // Parse date as local (not UTC) to avoid timezone offset
        const parseLocalDate = (dateStr) => {
          if (!dateStr) return new Date(0)
          const [y, m, d] = dateStr.split('-').map(Number)
          return new Date(y, m - 1, d)
        }
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())

        const upcoming = bookings
          .filter(b => {
            if (b.status !== 'confirmed') return false
            const eventDate = parseLocalDate(b.event_date)
            return eventDate >= todayStart && eventDate <= in7Days
          })
          .sort((a, b) => parseLocalDate(a.event_date) - parseLocalDate(b.event_date))
          .slice(0, 5)
        setUpcomingEvents(upcoming)

        // Alerts
        const confirmedEvents = bookings.filter(b => b.status === 'confirmed').length
        const completedEventsWithoutCost = bookings.filter(b =>
          b.status === 'completed' && (b.event_cost === undefined || b.event_cost === null)
        ).length

        // Reviews
        let pendingReviews = 0
        if (results[6].status === 'fulfilled') {
          const reviewsData = results[6].value.data
          const reviews = reviewsData.items || reviewsData || []
          pendingReviews = reviews.filter(r => !r.approved).length
        }

        setAlerts({ pendingReviews, confirmedEvents, completedEventsWithoutCost })
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const calculateTrends = (annual, month) => {
    if (!annual?.monthly_reports) return
    const reports = annual.monthly_reports
    const currentIdx = reports.findIndex(r => r.month === month)
    if (currentIdx < 1) {
      setTrends({})
      return
    }
    const curr = reports[currentIdx]
    const prev = reports[currentIdx - 1]
    const calcTrend = (c, p) => (p && p !== 0) ? ((c - p) / Math.abs(p)) * 100 : null

    setTrends({
      events: calcTrend(curr.total_events || 0, prev.total_events || 0),
      income: calcTrend(curr.total_income || 0, prev.total_income || 0),
      profit: calcTrend(curr.total_profit || 0, prev.total_profit || 0),
      participants: calcTrend(curr.avg_participants || 0, prev.avg_participants || 0)
    })
  }

  const generateYearOptions = () => {
    const cy = new Date().getFullYear()
    return Array.from({ length: 5 }, (_, i) => cy - 3 + i)
  }

  // Chart data: Annual Revenue Trend
  const revenueTrendData = () => {
    if (!annualReport?.monthly_reports) return null
    const reports = annualReport.monthly_reports
    const labels = reports.map(r => monthNames[r.month - 1]?.substring(0, 3) || `M${r.month}`)
    return {
      labels,
      datasets: [
        {
          label: 'Ingresos',
          data: reports.map(r => r.total_income || 0),
          borderColor: '#FFD700',
          backgroundColor: 'rgba(255, 215, 0, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6
        },
        {
          label: 'Gastos',
          data: reports.map(r => r.total_cost || 0),
          borderColor: '#F44336',
          backgroundColor: 'rgba(244, 67, 54, 0.05)',
          fill: false,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5
        },
        {
          label: 'Utilidad',
          data: reports.map(r => r.total_profit || 0),
          borderColor: '#4CAF50',
          backgroundColor: 'rgba(76, 175, 80, 0.05)',
          borderDash: [5, 5],
          fill: false,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
    }
  }

  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true, padding: 16 } },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`
        }
      }
    },
    scales: {
      y: {
        ticks: {
          callback: (v) => formatCurrency(v)
        }
      }
    }
  }

  // Chart data: Service Pie
  const servicePieData = () => {
    if (!monthlyReport?.events_by_service) return null
    const breakdown = monthlyReport.events_by_service
    const entries = Object.entries(breakdown).filter(([, v]) => v.count > 0)
    if (entries.length === 0) return null
    const colors = ['#FFD700', '#FF6A00', '#4CAF50', '#2196F3', '#9C27B0', '#F44336']
    return {
      labels: entries.map(([k]) => k),
      datasets: [{
        data: entries.map(([, v]) => v.count),
        backgroundColor: entries.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor: '#fff'
      }]
    }
  }

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { usePointStyle: true, padding: 12, font: { size: 11 } } }
    }
  }

  // Payment status from monthly report
  const paymentStats = () => {
    if (!monthlyReport?.payment_metrics) return null
    const pm = monthlyReport.payment_metrics
    return {
      paid: pm.paid_count || 0,
      partial: pm.partial_count || 0,
      pending: pm.unpaid_count || 0,
      total_paid: pm.total_paid || 0,
      total_pending: pm.total_pending || 0
    }
  }

  // Margin calculation
  const margin = () => {
    if (!monthlyReport) return 0
    const income = monthlyReport.total_income || 0
    if (income === 0) return 0
    return ((monthlyReport.total_profit || 0) / income) * 100
  }

  // --- Render ---
  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: { xs: 'flex-start', sm: 'center' },
        flexDirection: { xs: 'column', sm: 'row' },
        gap: 2,
        mb: 3
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            component="img"
            src={logo}
            alt="Pablo's Pizza Logo"
            sx={{ width: 50, height: 50, borderRadius: '50%', objectFit: 'cover' }}
          />
          <Box>
            <Typography variant="h4" fontWeight={700}>Dashboard</Typography>
            <Typography variant="body2" color="text.secondary">
              Resumen ejecutivo del negocio
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <FormControl size="small" sx={{ minWidth: 110 }}>
            <InputLabel>Mes</InputLabel>
            <Select value={selectedMonth} label="Mes" onChange={e => setSelectedMonth(e.target.value)}>
              {monthNames.map((m, i) => (
                <MenuItem key={i} value={i + 1}>{m}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 90 }}>
            <InputLabel>Año</InputLabel>
            <Select value={selectedYear} label="Año" onChange={e => setSelectedYear(e.target.value)}>
              {generateYearOptions().map(y => (
                <MenuItem key={y} value={y}>{y}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <IconButton onClick={() => loadDashboardData()} disabled={loading} color="primary" size="small">
            {loading ? <CircularProgress size={20} /> : <Refresh />}
          </IconButton>
        </Box>
      </Box>

      {/* Stat Cards Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <Grid item xs={6} sm={4} md key={i}><SkeletonCard /></Grid>
          ))
        ) : (
          <>
            <Grid item xs={6} sm={4} md>
              <StatCard
                title="Eventos"
                value={monthlyReport?.total_events || 0}
                icon={<Event />}
                color="#2196F3"
                trend={trends.events}
              />
            </Grid>
            <Grid item xs={6} sm={4} md>
              <StatCard
                title="Ingresos"
                value={formatCurrency(monthlyReport?.total_income || 0)}
                icon={<AttachMoney />}
                color="#FFD700"
                trend={trends.income}
              />
            </Grid>
            <Grid item xs={6} sm={4} md>
              <StatCard
                title="Utilidad"
                value={formatCurrency(monthlyReport?.total_profit || 0)}
                icon={<TrendingUp />}
                color="#4CAF50"
                trend={trends.profit}
              />
            </Grid>
            <Grid item xs={6} sm={4} md>
              <StatCard
                title="Margen"
                value={formatPercentage(margin())}
                icon={<ShowChart />}
                color="#9C27B0"
              />
            </Grid>
            <Grid item xs={6} sm={4} md>
              <StatCard
                title="Prom. Participantes"
                value={Math.round(monthlyReport?.avg_participants || 0)}
                icon={<People />}
                color="#FF6A00"
                trend={trends.participants}
              />
            </Grid>
          </>
        )}
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <SectionCard
            title={`Tendencia ${selectedYear}`}
            icon={<Assessment sx={{ color: 'text.secondary' }} />}
            minHeight={360}
          >
            {loading ? (
              <Skeleton variant="rectangular" height={280} sx={{ borderRadius: 1 }} />
            ) : revenueTrendData() ? (
              <Box sx={{ height: 280 }}>
                <Line data={revenueTrendData()} options={lineChartOptions} />
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 280 }}>
                <Typography color="text.secondary">Sin datos anuales disponibles</Typography>
              </Box>
            )}
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <SectionCard
            title="Servicios"
            icon={<Kitchen sx={{ color: 'text.secondary' }} />}
            minHeight={360}
          >
            {loading ? (
              <Skeleton variant="circular" width={200} height={200} sx={{ mx: 'auto', mt: 4 }} />
            ) : servicePieData() ? (
              <Box sx={{ height: 280 }}>
                <Pie data={servicePieData()} options={pieChartOptions} />
              </Box>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 280 }}>
                <Typography color="text.secondary">Sin eventos este mes</Typography>
              </Box>
            )}
          </SectionCard>
        </Grid>
      </Grid>

      {/* Middle Row: Payment Status, Upcoming Events, Alerts */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* Payment Status */}
        <Grid item xs={12} md={4}>
          <SectionCard
            title="Estado de Pagos"
            icon={<PointOfSale sx={{ color: 'text.secondary' }} />}
            minHeight={240}
          >
            {loading ? (
              <Box><Skeleton height={30} /><Skeleton height={30} /><Skeleton height={30} /></Box>
            ) : paymentStats() ? (
              <Box>
                {(() => {
                  const ps = paymentStats()
                  const total = (ps.paid || 0) + (ps.partial || 0) + (ps.pending || 0)
                  if (total === 0) return <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>Sin eventos</Typography>
                  const paidPct = ((ps.paid || 0) / total) * 100
                  const partialPct = ((ps.partial || 0) / total) * 100
                  const pendingPct = ((ps.pending || 0) / total) * 100
                  return (
                    <>
                      {/* Segmented bar */}
                      <Box sx={{ display: 'flex', borderRadius: 1, overflow: 'hidden', height: 12, mb: 2 }}>
                        {paidPct > 0 && <Box sx={{ width: `${paidPct}%`, bgcolor: '#4CAF50' }} />}
                        {partialPct > 0 && <Box sx={{ width: `${partialPct}%`, bgcolor: '#FF9800' }} />}
                        {pendingPct > 0 && <Box sx={{ width: `${pendingPct}%`, bgcolor: '#F44336' }} />}
                      </Box>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#4CAF50' }} />
                            <Typography variant="body2">Pagado</Typography>
                          </Box>
                          <Typography variant="body2" fontWeight={600}>{ps.paid || 0}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#FF9800' }} />
                            <Typography variant="body2">Parcial</Typography>
                          </Box>
                          <Typography variant="body2" fontWeight={600}>{ps.partial || 0}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#F44336' }} />
                            <Typography variant="body2">Pendiente</Typography>
                          </Box>
                          <Typography variant="body2" fontWeight={600}>{ps.pending || 0}</Typography>
                        </Box>
                      </Box>
                      <Divider sx={{ my: 1.5 }} />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">Cobrado</Typography>
                        <Typography variant="body2" fontWeight={600} color="success.main">
                          {formatCurrency(ps.total_paid || 0)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">Por cobrar</Typography>
                        <Typography variant="body2" fontWeight={600} color="error.main">
                          {formatCurrency(ps.total_pending || 0)}
                        </Typography>
                      </Box>
                    </>
                  )
                })()}
              </Box>
            ) : (
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>Sin datos de pago</Typography>
            )}
          </SectionCard>
        </Grid>

        {/* Upcoming Events */}
        <Grid item xs={12} md={4}>
          <SectionCard
            title="Próximos Eventos"
            icon={<EventNote sx={{ color: 'text.secondary' }} />}
            minHeight={240}
            action={
              <Chip
                label="7 días"
                size="small"
                variant="outlined"
                sx={{ fontSize: 11 }}
              />
            }
          >
            {loading ? (
              <Box>{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={50} />)}</Box>
            ) : upcomingEvents.length > 0 ? (
              <List dense disablePadding>
                {upcomingEvents.map((event, i) => (
                  <ListItem
                    key={event.id || i}
                    disablePadding
                    sx={{
                      py: 0.8,
                      borderBottom: i < upcomingEvents.length - 1 ? '1px solid' : 'none',
                      borderColor: 'divider'
                    }}
                  >
                    <ListItemText
                      primary={
                        <Typography variant="body2" fontWeight={600} noWrap>
                          {event.client_name || event.name || 'Cliente'}
                        </Typography>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.3 }}>
                          <Typography variant="caption" color="text.secondary">
                            {(() => {
                              if (!event.event_date) return 'N/A'
                              const [y, m, d] = event.event_date.split('-').map(Number)
                              return new Date(y, m - 1, d).toLocaleDateString('es-CL')
                            })()}
                          </Typography>
                          {event.service_type && (
                            <Chip label={event.service_type} size="small" sx={{ fontSize: 10, height: 18 }} />
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
                <Typography color="text.secondary" variant="body2">Sin eventos próximos</Typography>
              </Box>
            )}
          </SectionCard>
        </Grid>

        {/* Alerts */}
        <Grid item xs={12} md={4}>
          <SectionCard
            title="Alertas"
            icon={<Warning sx={{ color: 'text.secondary' }} />}
            minHeight={240}
          >
            {loading ? (
              <Box>{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={40} />)}</Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {inventoryAlerts.length > 0 && (
                  <Alert severity="warning" sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">
                      {inventoryAlerts.length} producto{inventoryAlerts.length > 1 ? 's' : ''} con stock bajo
                    </Typography>
                  </Alert>
                )}
                {alerts.completedEventsWithoutCost > 0 && (
                  <Alert severity="info" sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">
                      {alerts.completedEventsWithoutCost} evento{alerts.completedEventsWithoutCost > 1 ? 's' : ''} sin costo registrado
                    </Typography>
                  </Alert>
                )}
                {alerts.pendingReviews > 0 && (
                  <Alert severity="warning" sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">
                      {alerts.pendingReviews} reseña{alerts.pendingReviews > 1 ? 's' : ''} por aprobar
                    </Typography>
                  </Alert>
                )}
                {alerts.confirmedEvents > 0 && (
                  <Alert severity="success" sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">
                      {alerts.confirmedEvents} evento{alerts.confirmedEvents > 1 ? 's' : ''} confirmado{alerts.confirmedEvents > 1 ? 's' : ''}
                    </Typography>
                  </Alert>
                )}
                {monthlyReport?.waste_summary?.total_waste_cost > 0 && (
                  <Alert severity="error" sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">
                      Mermas del mes: {formatCurrency(monthlyReport.waste_summary.total_waste_cost)}
                    </Typography>
                  </Alert>
                )}
                {inventoryAlerts.length === 0 &&
                  alerts.completedEventsWithoutCost === 0 &&
                  alerts.pendingReviews === 0 &&
                  alerts.confirmedEvents === 0 &&
                  !(monthlyReport?.waste_summary?.total_waste_cost > 0) && (
                  <Alert severity="success" icon={<CheckCircle />} sx={{ py: 0, '& .MuiAlert-message': { py: 0.8 } }}>
                    <Typography variant="body2">Todo al día - sin alertas</Typography>
                  </Alert>
                )}
              </Box>
            )}
          </SectionCard>
        </Grid>
      </Grid>

      {/* Bottom Row: Top Clients + Quick Actions */}
      <Grid container spacing={2}>
        {/* Top Clients */}
        <Grid item xs={12} md={6}>
          <SectionCard
            title="Top Clientes"
            icon={<People sx={{ color: 'text.secondary' }} />}
          >
            {loading ? (
              <Box>{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={40} />)}</Box>
            ) : topClients.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, fontSize: 12 }}>Cliente</TableCell>
                      <TableCell align="center" sx={{ fontWeight: 600, fontSize: 12 }}>Eventos</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600, fontSize: 12 }}>Total</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {topClients.slice(0, 5).map((client, i) => (
                      <TableRow key={i} sx={{ '&:last-child td': { border: 0 } }}>
                        <TableCell>
                          <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>
                            {client.name || client.client_name || 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip label={client.total_bookings || 0} size="small" sx={{ height: 22, fontSize: 12 }} />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" fontWeight={600}>
                            {formatCurrency(client.total_spent || 0)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography color="text.secondary" variant="body2">Sin datos de clientes</Typography>
              </Box>
            )}
          </SectionCard>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <SectionCard
            title="Acciones Rápidas"
            icon={<Assessment sx={{ color: 'text.secondary' }} />}
          >
            <Grid container spacing={1.5}>
              {[
                { label: 'Agendamientos', icon: <Event />, path: '/admin/agendamientos', color: '#2196F3' },
                { label: 'Reportes', icon: <ShowChart />, path: '/admin/reportes', color: '#FFD700' },
                { label: 'Inventario', icon: <Inventory />, path: '/admin/inventario', color: '#4CAF50' },
                { label: 'Galería', icon: <PhotoLibrary />, path: '/admin/eventos', color: '#9C27B0' },
                { label: 'Producción', icon: <Kitchen />, path: '/admin/produccion', color: '#FF6A00' },
                { label: 'Gastos', icon: <Receipt />, path: '/admin/gastos', color: '#F44336' }
              ].map((action) => (
                <Grid item xs={6} sm={4} key={action.label}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => navigate(action.path)}
                    sx={{
                      py: 1.8,
                      flexDirection: 'column',
                      gap: 0.5,
                      borderColor: 'divider',
                      color: 'text.primary',
                      '&:hover': {
                        borderColor: action.color,
                        bgcolor: action.color + '0A'
                      }
                    }}
                  >
                    <Box sx={{ color: action.color }}>{action.icon}</Box>
                    <Typography variant="caption" fontWeight={600}>{action.label}</Typography>
                  </Button>
                </Grid>
              ))}
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>
    </Container>
  )
}

export default AdminDashboard
