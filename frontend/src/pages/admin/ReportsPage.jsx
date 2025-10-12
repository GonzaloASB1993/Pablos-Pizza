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
  Divider,
  IconButton,
  Tooltip,
  Stack
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
  AttachMoney,
  Inventory,
  CalendarToday,
  ShowChart,
  Warning,
  Brightness4,
  Brightness7
} from '@mui/icons-material'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement
} from 'chart.js'
import { Line, Bar, Pie } from 'react-chartjs-2'
import { reportsAPI, inventoryAPI } from '../../services/api'
import toast from 'react-hot-toast'
import { useThemeMode } from '../../contexts/ThemeContext'
import { useTheme } from '@mui/material/styles'

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

// Enhanced KPI Card Component
const KPICard = ({ title, value, subtitle, icon: Icon, trend, color = 'primary' }) => (
  <Card sx={{ height: '100%', position: 'relative', overflow: 'visible' }}>
    <CardContent>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4" component="div" color={color + '.main'}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="textSecondary">
              {subtitle}
            </Typography>
          )}
          {trend && (
            <Box display="flex" alignItems="center" mt={1}>
              {trend > 0 ? (
                <TrendingUp color="success" fontSize="small" />
              ) : (
                <TrendingDown color="error" fontSize="small" />
              )}
              <Typography
                variant="body2"
                color={trend > 0 ? 'success.main' : 'error.main'}
                ml={0.5}
              >
                {Math.abs(trend)}%
              </Typography>
            </Box>
          )}
        </Box>
        <Box
          sx={{
            backgroundColor: color + '.main',
            borderRadius: '50%',
            p: 1,
            color: 'white'
          }}
        >
          <Icon />
        </Box>
      </Box>
    </CardContent>
  </Card>
)

// Alert Card Component
const AlertCard = ({ title, count, severity = 'warning', icon: Icon, onClick }) => (
  <Card
    sx={{
      cursor: onClick ? 'pointer' : 'default',
      '&:hover': onClick ? { elevation: 4 } : {}
    }}
    onClick={onClick}
  >
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box display="flex" alignItems="center">
          <Icon color={severity} sx={{ mr: 1 }} />
          <Box>
            <Typography variant="body2" color="textSecondary">
              {title}
            </Typography>
            <Typography variant="h6" color={severity + '.main'}>
              {count}
            </Typography>
          </Box>
        </Box>
        <Chip
          label={count}
          color={severity}
          size="small"
        />
      </Box>
    </CardContent>
  </Card>
)

export default function ReportsPage() {
  const theme = useTheme()
  const { mode, toggleTheme } = useThemeMode()
  const [loading, setLoading] = useState(true)
  const [tabValue, setTabValue] = useState(0)
  const [selectedPeriod, setSelectedPeriod] = useState('current_month')
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1) // 1-12
  const [dashboardData, setDashboardData] = useState(null)
  const [monthlyData, setMonthlyData] = useState(null)
  const [annualData, setAnnualData] = useState(null)
  const [inventoryAlerts, setInventoryAlerts] = useState([])
  const [topClients, setTopClients] = useState([])

  useEffect(() => {
    loadReportsData()
  }, [selectedMonth, selectedYear])

  const loadReportsData = async () => {
    try {
      setLoading(true)

      // Load dashboard stats
      const dashboardResponse = await reportsAPI.getDashboard()
      setDashboardData(dashboardResponse.data)

      // Load SELECTED month data (not current month)
      const monthlyResponse = await reportsAPI.getMonthly(selectedYear, selectedMonth)
      setMonthlyData(monthlyResponse.data)

      // Load annual data
      const annualResponse = await reportsAPI.getAnnual(selectedYear)
      setAnnualData(annualResponse.data)

      // Load inventory alerts
      const inventoryResponse = await inventoryAPI.getAlerts()
      setInventoryAlerts(inventoryResponse.data.alerts || [])

      // Load top clients
      const clientsResponse = await reportsAPI.getTopClients({ limit: 5 })
      setTopClients(clientsResponse.data.clients || [])

    } catch (error) {
      console.error('Error loading reports data:', error)
      toast.error('Error al cargar datos de reportes')
    } finally {
      setLoading(false)
    }
  }

  const handleExportReport = async () => {
    try {
      // Use filtered year and month instead of current date
      const response = await reportsAPI.exportMonthly(
        selectedYear,
        selectedMonth,
        'excel'
      )

      // Create download link
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `reporte_${selectedYear}_${selectedMonth.toString().padStart(2, '0')}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      const monthName = new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })
      toast.success(`Reporte exportado: ${monthName}`)
    } catch (error) {
      console.error('Error exporting report:', error)
      toast.error('Error al exportar reporte')
    }
  }

  // Chart configurations
  const getMonthlyTrendData = () => {
    if (!annualData?.monthly_reports) return null

    const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    return {
      labels: months,
      datasets: [
        {
          label: 'Ingresos',
          data: annualData.monthly_reports.map(report => report.total_income),
          borderColor: mode === 'dark' ? '#FFD700' : '#1976d2',
          backgroundColor: mode === 'dark' ? 'rgba(255, 215, 0, 0.2)' : 'rgba(25, 118, 210, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Gastos',
          data: annualData.monthly_reports.map(report => report.total_expenses),
          borderColor: mode === 'dark' ? '#EF5350' : '#d32f2f',
          backgroundColor: mode === 'dark' ? 'rgba(239, 83, 80, 0.2)' : 'rgba(211, 47, 47, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    }
  }

  const getServiceDistributionData = () => {
    if (!monthlyData) return null

    // Mapear nombres de servicios a español
    const serviceLabels = {
      'workshop': 'Pizzeros en Acción',
      'pizza_party': 'Pizza Party',
      'workshop,pizza_party': 'Ambos Servicios',
      'party': 'Pizza Party' // alias
    }

    // Contar eventos por tipo de servicio desde el mes actual
    const serviceCounts = {}
    const serviceIncomes = {}

    // Si el backend ya envía events_by_service, usarlo; si no, calcularlo desde el frontend
    if (monthlyData.events_by_service) {
      Object.entries(monthlyData.events_by_service).forEach(([serviceKey, data]) => {
        const label = serviceLabels[serviceKey] || serviceKey
        serviceCounts[label] = data.count || 0
        serviceIncomes[label] = data.total_income || 0
      })
    } else {
      // Fallback: si no hay events_by_service en la respuesta, calcularlo desde monthlyData
      // Esto requeriría tener acceso a la lista de eventos individuales
      // Por ahora asumimos que el backend envía events_by_service
      return null
    }

    const labels = Object.keys(serviceCounts).map(key => `${key} (${serviceCounts[key]} eventos)`)
    const incomes = Object.values(serviceIncomes)

    return {
      labels,
      datasets: [{
        label: 'Ingresos',
        data: incomes,
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF'
        ]
      }]
    }
  }

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: theme.palette.text.primary,
        },
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: theme.palette.text.secondary,
          callback: function(value) {
            return new Intl.NumberFormat('es-CL', {
              style: 'currency',
              currency: 'CLP',
              minimumFractionDigits: 0
            }).format(value)
          }
        },
        grid: {
          color: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
      },
      x: {
        ticks: {
          color: theme.palette.text.secondary,
        },
        grid: {
          color: mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
      },
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          📊 Reportes Financieros
        </Typography>
        <Stack direction="row" spacing={2}>
          <Tooltip title="Actualizar datos">
            <IconButton onClick={loadReportsData} aria-label="refresh data">
              <Refresh />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<FileDownload />}
            onClick={handleExportReport}
          >
            Exportar Excel
          </Button>
        </Stack>
      </Box>

      {/* Month/Year Filter */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'center' }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Mes</InputLabel>
          <Select
            value={selectedMonth}
            label="Mes"
            onChange={(e) => setSelectedMonth(e.target.value)}
          >
            <MenuItem value={1}>Enero</MenuItem>
            <MenuItem value={2}>Febrero</MenuItem>
            <MenuItem value={3}>Marzo</MenuItem>
            <MenuItem value={4}>Abril</MenuItem>
            <MenuItem value={5}>Mayo</MenuItem>
            <MenuItem value={6}>Junio</MenuItem>
            <MenuItem value={7}>Julio</MenuItem>
            <MenuItem value={8}>Agosto</MenuItem>
            <MenuItem value={9}>Septiembre</MenuItem>
            <MenuItem value={10}>Octubre</MenuItem>
            <MenuItem value={11}>Noviembre</MenuItem>
            <MenuItem value={12}>Diciembre</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>Año</InputLabel>
          <Select
            value={selectedYear}
            label="Año"
            onChange={(e) => setSelectedYear(e.target.value)}
          >
            {[2024, 2025, 2026].map((year) => (
              <MenuItem key={year} value={year}>
                {year}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary">
          Mostrando datos de {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
        </Typography>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Ingresos del Mes"
            value={new Intl.NumberFormat('es-CL', {
              style: 'currency',
              currency: 'CLP',
              minimumFractionDigits: 0
            }).format(monthlyData?.total_income || 0)}
            subtitle={new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
            icon={AttachMoney}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Eventos Realizados"
            value={monthlyData?.total_events || 0}
            subtitle="Mes seleccionado"
            icon={Event}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Utilidad del Mes"
            value={new Intl.NumberFormat('es-CL', {
              style: 'currency',
              currency: 'CLP',
              minimumFractionDigits: 0
            }).format(monthlyData?.total_profit || 0)}
            subtitle="Ganancia neta"
            icon={TrendingUp}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Próximos Eventos"
            value={dashboardData?.upcoming_events || 0}
            subtitle="Próximos 7 días"
            icon={CalendarToday}
            color="info"
          />
        </Grid>
      </Grid>

      {/* Alerts */}
      {(inventoryAlerts.length > 0 || (dashboardData?.alerts?.pending_reviews > 0)) && (
        <Grid container spacing={2} mb={4}>
          {inventoryAlerts.length > 0 && (
            <Grid item xs={12} sm={6}>
              <AlertCard
                title="Items con Stock Bajo"
                count={inventoryAlerts.length}
                severity="warning"
                icon={Inventory}
              />
            </Grid>
          )}
          {dashboardData?.alerts?.pending_reviews > 0 && (
            <Grid item xs={12} sm={6}>
              <AlertCard
                title="Reseñas Pendientes"
                count={dashboardData.alerts.pending_reviews}
                severity="info"
                icon={Star}
              />
            </Grid>
          )}
        </Grid>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label="Resumen Ejecutivo" icon={<Assessment />} />
          <Tab label="Análisis Financiero" icon={<ShowChart />} />
          <Tab label="Clientes Top" icon={<People />} />
          <Tab label="Operaciones" icon={<Inventory />} />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* Monthly Performance */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Tendencia Mensual - Ingresos vs Gastos
                </Typography>
                {getMonthlyTrendData() && (
                  <Line data={getMonthlyTrendData()} options={chartOptions} />
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Service Distribution */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Distribución de Servicios - Ingresos por Categoría
                </Typography>
                {getServiceDistributionData() && (
                  <Pie
                    data={getServiceDistributionData()}
                    options={{
                      responsive: true,
                      plugins: {
                        legend: {
                          position: 'bottom',
                        },
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              const label = context.label || ''
                              const value = context.parsed || 0
                              return `${label}: ${new Intl.NumberFormat('es-CL', {
                                style: 'currency',
                                currency: 'CLP',
                                minimumFractionDigits: 0
                              }).format(value)}`
                            }
                          }
                        }
                      }
                    }}
                  />
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Monthly Summary */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Resumen del Mes Actual
                </Typography>
                {monthlyData && (
                  <Grid container spacing={2}>
                    <Grid item xs={6} md={2}>
                      <Typography variant="body2" color="textSecondary">
                        Total Eventos
                      </Typography>
                      <Typography variant="h6">
                        {monthlyData.total_events}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={2}>
                      <Typography variant="body2" color="textSecondary">
                        Participantes Promedio
                      </Typography>
                      <Typography variant="h6">
                        {monthlyData.avg_participants}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Servicio Más Popular
                      </Typography>
                      <Typography variant="h6">
                        {monthlyData.most_popular_service}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={2}>
                      <Typography variant="body2" color="textSecondary">
                        Retención de Clientes
                      </Typography>
                      <Typography variant="h6">
                        {monthlyData.client_retention_rate}%
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Margen de Utilidad
                      </Typography>
                      <Typography variant="h6" color={
                        monthlyData.total_income > 0
                          ? (monthlyData.total_profit / monthlyData.total_income * 100) > 20
                            ? 'success.main'
                            : 'warning.main'
                          : 'error.main'
                      }>
                        {monthlyData.total_income > 0
                          ? `${((monthlyData.total_profit / monthlyData.total_income) * 100).toFixed(1)}%`
                          : '0%'
                        }
                      </Typography>
                    </Grid>
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Grid container spacing={3}>
          {/* Annual Financial Summary */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Resumen Financiero Anual
                </Typography>
                {annualData?.annual_totals && (
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Ingresos Totales
                      </Typography>
                      <Typography variant="h5" color="success.main">
                        {new Intl.NumberFormat('es-CL', {
                          style: 'currency',
                          currency: 'CLP',
                          minimumFractionDigits: 0
                        }).format(annualData.annual_totals.total_income)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Gastos Totales
                      </Typography>
                      <Typography variant="h5" color="error.main">
                        {new Intl.NumberFormat('es-CL', {
                          style: 'currency',
                          currency: 'CLP',
                          minimumFractionDigits: 0
                        }).format(annualData.annual_totals.total_expenses)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Utilidad Total
                      </Typography>
                      <Typography variant="h5" color="primary.main">
                        {new Intl.NumberFormat('es-CL', {
                          style: 'currency',
                          currency: 'CLP',
                          minimumFractionDigits: 0
                        }).format(annualData.annual_totals.total_profit)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={3}>
                      <Typography variant="body2" color="textSecondary">
                        Total Eventos
                      </Typography>
                      <Typography variant="h5">
                        {annualData.annual_totals.total_events}
                      </Typography>
                    </Grid>
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Clientes Más Frecuentes
                </Typography>
                {topClients.map((client, index) => (
                  <Box key={client.email} mb={2}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="subtitle1">
                          {client.name}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          {client.email}
                        </Typography>
                      </Box>
                      <Box textAlign="right">
                        <Typography variant="h6">
                          {client.total_bookings} eventos
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          {new Intl.NumberFormat('es-CL', {
                            style: 'currency',
                            currency: 'CLP',
                            minimumFractionDigits: 0
                          }).format(client.total_spent)}
                        </Typography>
                      </Box>
                    </Box>
                    {index < topClients.length - 1 && <Divider sx={{ mt: 2 }} />}
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Alertas de Inventario
                </Typography>
                {inventoryAlerts.length > 0 ? (
                  inventoryAlerts.map((alert, index) => (
                    <Box key={alert.id} mb={2}>
                      <Box display="flex" alignItems="center" justifyContent="space-between">
                        <Box display="flex" alignItems="center">
                          <Warning color="warning" sx={{ mr: 1 }} />
                          <Box>
                            <Typography variant="subtitle1">
                              {alert.name}
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              {alert.category} - {alert.unit}
                            </Typography>
                          </Box>
                        </Box>
                        <Box textAlign="right">
                          <Typography variant="h6" color="warning.main">
                            {alert.current_stock} / {alert.min_stock}
                          </Typography>
                          <Chip
                            label={alert.priority}
                            color={alert.priority === 'high' ? 'error' : 'warning'}
                            size="small"
                          />
                        </Box>
                      </Box>
                      {index < inventoryAlerts.length - 1 && <Divider sx={{ mt: 2 }} />}
                    </Box>
                  ))
                ) : (
                  <Alert severity="success">
                    No hay alertas de inventario pendientes
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}