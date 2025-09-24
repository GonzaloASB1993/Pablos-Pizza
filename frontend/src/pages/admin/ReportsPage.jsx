import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Paper,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  AccountBalanceWallet,
  People,
  Star,
  Event,
  Assessment,
  FileDownload,
  Refresh,
  DateRange,
  AttachMoney,
  Inventory,
  ThumbUp,
  CalendarToday,
  ShowChart,
  PieChart,
  BarChart
} from '@mui/icons-material'
import { reportsAPI } from '../../services/api'
import toast from 'react-hot-toast'
import { format, startOfMonth, endOfMonth, subMonths } from 'date-fns'
import { es } from 'date-fns/locale'

export default function ReportsPage() {
  const [loading, setLoading] = useState(true)
  const [tabValue, setTabValue] = useState(0)
  const [selectedPeriod, setSelectedPeriod] = useState('current_month')
  const [dashboardData, setDashboardData] = useState({
    today: {
      new_bookings: 0,
      date: new Date().toISOString().split('T')[0]
    },
    current_month: {
      month_name: format(new Date(), 'MMMM', { locale: es }),
      events: 0,
      income: 0,
      profit: 0,
      avg_rating: 0,
      total_participants: 0
    },
    upcoming_events: 0,
    alerts: {
      low_stock_items: 0,
      pending_reviews: 0,
      overdue_payments: 0
    },
    growth: {
      revenue_growth: 0,
      event_growth: 0,
      customer_growth: 0
    }
  })

  const [monthlyData, setMonthlyData] = useState({
    total_events: 0,
    total_income: 0,
    total_expenses: 0,
    total_profit: 0,
    avg_participants: 0,
    most_popular_service: '',
    client_retention_rate: 0,
    revenue_by_service: {},
    profit_margin: 0
  })

  useEffect(() => {
    loadDashboardData()
    loadMonthlyData()
  }, [selectedPeriod])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const response = await reportsAPI.getDashboard()
      setDashboardData(response.data)
    } catch (error) {
      console.error('Error loading dashboard data:', error)
      toast.error('Error al cargar datos del dashboard')
    } finally {
      setLoading(false)
    }
  }

  const loadMonthlyData = async () => {
    try {
      const now = new Date()
      const year = now.getFullYear()
      const month = now.getMonth() + 1
      const response = await reportsAPI.getMonthly(year, month)
      setMonthlyData(response.data)
    } catch (error) {
      console.error('Error loading monthly data:', error)
    }
  }

  const KPICard = ({ title, value, subtitle, icon, color, trend, trendValue }) => (
    <Card sx={{
      height: '100%',
      background: `linear-gradient(135deg, ${color}15, ${color}05)`,
      border: `1px solid ${color}30`,
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: `0 8px 25px ${color}20`
      },
      transition: 'all 0.3s ease'
    }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{
            bgcolor: color,
            borderRadius: '12px',
            p: 1.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {React.cloneElement(icon, { sx: { fontSize: 28, color: 'white' } })}
          </Box>
          {trend && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {trend === 'up' ?
                <TrendingUp sx={{ fontSize: 20, color: '#4caf50' }} /> :
                <TrendingDown sx={{ fontSize: 20, color: '#f44336' }} />
              }
              <Typography variant="caption" sx={{
                color: trend === 'up' ? '#4caf50' : '#f44336',
                fontWeight: 600
              }}>
                {trendValue}%
              </Typography>
            </Box>
          )}
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 700, color: color, mb: 0.5 }}>
          {value}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      </CardContent>
    </Card>
  )

  const MetricCard = ({ title, value, change, changeLabel, icon, color }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{
            bgcolor: `${color}20`,
            borderRadius: 2,
            p: 1,
            display: 'flex',
            alignItems: 'center'
          }}>
            {React.cloneElement(icon, { sx: { fontSize: 24, color } })}
          </Box>
          <Chip
            label={`${change > 0 ? '+' : ''}${change}%`}
            size="small"
            sx={{
              bgcolor: change >= 0 ? '#e8f5e8' : '#ffebee',
              color: change >= 0 ? '#4caf50' : '#f44336',
              fontWeight: 600
            }}
          />
        </Box>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          {value}
        </Typography>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
          {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {changeLabel}
        </Typography>
      </CardContent>
    </Card>
  )

  const ProgressCard = ({ title, current, target, unit, color }) => {
    const percentage = (current / target) * 100
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            {title}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color }}>
              {current.toLocaleString()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              / {target.toLocaleString()} {unit}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.min(percentage, 100)}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: `${color}20`,
              '& .MuiLinearProgress-bar': {
                bgcolor: color,
                borderRadius: 4
              }
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {percentage.toFixed(1)}% del objetivo mensual
          </Typography>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress size={60} />
      </Box>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          📊 Reportes y Analytics
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Período</InputLabel>
            <Select
              value={selectedPeriod}
              label="Período"
              onChange={(e) => setSelectedPeriod(e.target.value)}
            >
              <MenuItem value="current_month">Mes Actual</MenuItem>
              <MenuItem value="last_month">Mes Anterior</MenuItem>
              <MenuItem value="quarter">Trimestre</MenuItem>
              <MenuItem value="year">Año</MenuItem>
            </Select>
          </FormControl>
          <Tooltip title="Actualizar datos">
            <IconButton onClick={loadDashboardData}>
              <Refresh />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<FileDownload />}
            sx={{ bgcolor: '#FFD700', color: '#000', '&:hover': { bgcolor: '#E6C200' } }}
          >
            Exportar
          </Button>
        </Box>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Ingresos del Mes"
            value={`$${dashboardData.current_month.income.toLocaleString()}`}
            subtitle={`${dashboardData.current_month.month_name} ${new Date().getFullYear()}`}
            icon={<AttachMoney />}
            color="#4caf50"
            trend="up"
            trendValue={dashboardData.growth.revenue_growth}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Eventos Realizados"
            value={dashboardData.current_month.events}
            subtitle={`${dashboardData.upcoming_events} próximos eventos`}
            icon={<Event />}
            color="#2196f3"
            trend="up"
            trendValue={dashboardData.growth.event_growth}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Satisfacción Cliente"
            value={`${dashboardData.current_month.avg_rating.toFixed(1)}/5`}
            subtitle="Promedio de calificaciones"
            icon={<Star />}
            color="#ff9800"
            trend="up"
            trendValue="2.5"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Participantes Total"
            value={dashboardData.current_month.total_participants}
            subtitle="En eventos del mes"
            icon={<People />}
            color="#9c27b0"
            trend="up"
            trendValue={dashboardData.growth.customer_growth}
          />
        </Grid>
      </Grid>

      {/* Alerts Section */}
      {(dashboardData.alerts.low_stock_items > 0 || dashboardData.alerts.pending_reviews > 0) && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            Atención requerida:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {dashboardData.alerts.low_stock_items > 0 && (
              <Chip
                label={`${dashboardData.alerts.low_stock_items} items con stock bajo`}
                color="warning"
                size="small"
              />
            )}
            {dashboardData.alerts.pending_reviews > 0 && (
              <Chip
                label={`${dashboardData.alerts.pending_reviews} reseñas pendientes`}
                color="info"
                size="small"
              />
            )}
          </Box>
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label="Resumen Ejecutivo" icon={<Assessment />} />
          <Tab label="Análisis Financiero" icon={<ShowChart />} />
          <Tab label="Clientes y Satisfacción" icon={<People />} />
          <Tab label="Operaciones" icon={<BarChart />} />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* Progress Cards */}
          <Grid item xs={12} md={4}>
            <ProgressCard
              title="Meta de Ingresos"
              current={dashboardData.current_month.income}
              target={50000}
              unit="pesos"
              color="#4caf50"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <ProgressCard
              title="Meta de Eventos"
              current={dashboardData.current_month.events}
              target={25}
              unit="eventos"
              color="#2196f3"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <ProgressCard
              title="Meta de Participantes"
              current={dashboardData.current_month.total_participants}
              target={300}
              unit="personas"
              color="#9c27b0"
            />
          </Grid>

          {/* Quick Metrics */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Métricas Rápidas
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                        ${monthlyData.profit_margin?.toFixed(1) || '0'}%
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Margen de Ganancia
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: '#2196f3' }}>
                        {monthlyData.avg_participants?.toFixed(1) || '0'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Promedio por Evento
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                        {monthlyData.client_retention_rate?.toFixed(1) || '0'}%
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Retención de Clientes
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: '#9c27b0' }}>
                        {monthlyData.most_popular_service === 'workshop' ? 'Talleres' : 'Fiestas'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Servicio Más Popular
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Tendencias del Negocio
                </Typography>
                <Box sx={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    📈 Gráfico de tendencias de ingresos
                    <br />
                    (Implementar con Chart.js)
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Análisis de Ingresos vs Gastos
                </Typography>
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    📊 Gráfico de barras comparativo
                    <br />
                    Ingresos: ${monthlyData.total_income?.toLocaleString() || '0'}
                    <br />
                    Gastos: ${monthlyData.total_expenses?.toLocaleString() || '0'}
                    <br />
                    Ganancia: ${monthlyData.total_profit?.toLocaleString() || '0'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Distribución de Ingresos
                </Typography>
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    🥧 Gráfico circular
                    <br />
                    Por tipo de servicio
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <MetricCard
              title="Clientes Nuevos"
              value="23"
              change={15}
              changeLabel="vs mes anterior"
              icon={<People />}
              color="#2196f3"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <MetricCard
              title="Clientes Recurrentes"
              value="18"
              change={8}
              changeLabel="vs mes anterior"
              icon={<ThumbUp />}
              color="#4caf50"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <MetricCard
              title="Satisfacción Promedio"
              value={`${dashboardData.current_month.avg_rating.toFixed(1)}/5`}
              change={5}
              changeLabel="vs mes anterior"
              icon={<Star />}
              color="#ff9800"
            />
          </Grid>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Análisis de Satisfacción del Cliente
                </Typography>
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    ⭐ Distribución de calificaciones y comentarios destacados
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Eficiencia Operacional
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, bgcolor: '#f5f5f5', borderRadius: 2, mb: 2 }}>
                      <Typography variant="body1">Tasa de Conversión</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#4caf50' }}>
                        85%
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, bgcolor: '#f5f5f5', borderRadius: 2, mb: 2 }}>
                      <Typography variant="body1">Tiempo de Respuesta Promedio</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#2196f3' }}>
                        2.3h
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
                      <Typography variant="body1">Tasa de Cancelación</Typography>
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#ff9800' }}>
                        8%
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Calendario de Eventos
                </Typography>
                <Box sx={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    📅 Vista de calendario con eventos próximos
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}