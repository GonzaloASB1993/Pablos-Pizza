import React, { useState, useEffect, useMemo, useCallback } from 'react'
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
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
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
  Brightness7,
  RemoveCircleOutline,
  AccountBalance,
  Add,
  ExpandMore
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
import { reportsAPI, inventoryAPI, expensesAPI } from '../../services/api'
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
  const [initialLoading, setInitialLoading] = useState(true)
  const [tabValue, setTabValue] = useState(0)
  const [selectedPeriod, setSelectedPeriod] = useState('current_month')
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1) // 1-12
  const [dashboardData, setDashboardData] = useState(null)
  const [monthlyData, setMonthlyData] = useState(null)
  const [annualData, setAnnualData] = useState(null)
  const [inventoryAlerts, setInventoryAlerts] = useState([])
  const [topClients, setTopClients] = useState([])
  const [inventoryTotalValue, setInventoryTotalValue] = useState(0)

  // Expense management state
  const [fixedExpenses, setFixedExpenses] = useState([])
  const [variableExpenses, setVariableExpenses] = useState([])
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false)
  const [expenseDialogType, setExpenseDialogType] = useState('fixed') // 'fixed' or 'variable'
  const [editingExpense, setEditingExpense] = useState(null)
  const [expenseFormData, setExpenseFormData] = useState({
    description: '',
    amount: '',
    category: 'general',
    notes: ''
  })
  const [incomeStatementView, setIncomeStatementView] = useState('monthly') // 'monthly' or 'annual'
  const [monthlyTax, setMonthlyTax] = useState(0)
  const [annualTax, setAnnualTax] = useState(0)

  // Define functions BEFORE useEffect to avoid initialization errors
  const loadExpensesData = useCallback(async () => {
    try {
      // Parallel loading of expenses
      const [fixedResponse, variableResponse] = await Promise.all([
        expensesAPI.getFixed(),
        expensesAPI.getVariable({ year: selectedYear, month: selectedMonth })
      ])

      setFixedExpenses(fixedResponse.data || [])
      setVariableExpenses(variableResponse.data || [])
    } catch (error) {
      console.error('Error loading expenses data:', error)
      // Don't show error toast - expenses might not be set up yet
    }
  }, [selectedMonth, selectedYear])

  const loadMonthlyTax = useCallback(async () => {
    try {
      const response = await expensesAPI.getTax({
        year: selectedYear,
        month: selectedMonth
      })
      setMonthlyTax(response.data.amount || 0)
    } catch (error) {
      console.error('Error loading tax:', error)
      setMonthlyTax(0)
    }
  }, [selectedMonth, selectedYear])

  // Load data that doesn't change with filters (only once)
  const loadStaticData = useCallback(async () => {
    try {
      // Parallel loading of static data
      const [dashboardResponse, inventoryAlertsResponse, clientsResponse, inventoryResponse] =
        await Promise.all([
          reportsAPI.getDashboard(),
          inventoryAPI.getAlerts(),
          reportsAPI.getTopClients({ limit: 5 }),
          inventoryAPI.getAll().catch(() => ({ data: { items: [] } }))
        ])

      setDashboardData(dashboardResponse.data)
      setInventoryAlerts(inventoryAlertsResponse.data.alerts || [])
      setTopClients(clientsResponse.data.clients || [])

      const totalValue = inventoryResponse.data.items?.reduce((sum, item) => {
        return sum + (item.total_value || 0)
      }, 0) || 0
      setInventoryTotalValue(totalValue)

    } catch (error) {
      console.error('Error loading static data:', error)
      toast.error('Error al cargar datos estáticos')
    }
  }, [])

  // Load data that changes with filters
  const loadFilteredData = useCallback(async () => {
    try {
      setLoading(true)

      // Parallel loading of filtered data
      const [monthlyResponse, annualResponse] = await Promise.all([
        reportsAPI.getMonthly(selectedYear, selectedMonth),
        reportsAPI.getAnnual(selectedYear)
      ])

      setMonthlyData(monthlyResponse.data)
      setAnnualData(annualResponse.data)

      // Load expenses and tax in parallel
      await Promise.all([
        loadExpensesData(),
        loadMonthlyTax()
      ])

    } catch (error) {
      console.error('Error loading filtered data:', error)
      toast.error('Error al cargar datos de reportes')
    } finally {
      setLoading(false)
    }
  }, [selectedMonth, selectedYear, loadExpensesData, loadMonthlyTax])

  // Load data that doesn't depend on filters only once
  useEffect(() => {
    const init = async () => {
      await loadStaticData()
      await loadFilteredData()
      setInitialLoading(false)
    }
    init()
  }, [loadStaticData, loadFilteredData])

  // Load filtered data when month/year changes (but not on initial load)
  useEffect(() => {
    if (!initialLoading) {
      loadFilteredData()
    }
  }, [selectedMonth, selectedYear, initialLoading, loadFilteredData])

  const saveMonthlyTax = async (amount) => {
    try {
      await expensesAPI.saveTax({
        year: selectedYear,
        month: selectedMonth,
        amount: amount
      })
    } catch (error) {
      console.error('Error saving tax:', error)
      toast.error('Error al guardar impuesto')
    }
  }

  const handleOpenExpenseDialog = (type, expense = null) => {
    setExpenseDialogType(type)
    setEditingExpense(expense)
    if (expense) {
      setExpenseFormData({
        description: expense.description || '',
        amount: expense.amount || '',
        category: expense.category || 'general',
        notes: expense.notes || ''
      })
    } else {
      setExpenseFormData({
        description: '',
        amount: '',
        category: 'general',
        notes: ''
      })
    }
    setExpenseDialogOpen(true)
  }

  const handleCloseExpenseDialog = () => {
    setExpenseDialogOpen(false)
    setEditingExpense(null)
    setExpenseFormData({
      description: '',
      amount: '',
      category: 'general',
      notes: ''
    })
  }

  const handleSaveExpense = async () => {
    try {
      const expenseData = {
        ...expenseFormData,
        amount: parseFloat(expenseFormData.amount)
      }

      // Add year/month for variable expenses
      if (expenseDialogType === 'variable') {
        expenseData.year = selectedYear
        expenseData.month = selectedMonth
      }

      if (editingExpense) {
        // Update existing expense
        if (expenseDialogType === 'fixed') {
          await expensesAPI.updateFixed(editingExpense.id, expenseData)
        } else {
          await expensesAPI.updateVariable(editingExpense.id, expenseData)
        }
        toast.success('Gasto actualizado exitosamente')
      } else {
        // Create new expense
        if (expenseDialogType === 'fixed') {
          await expensesAPI.createFixed(expenseData)
        } else {
          await expensesAPI.createVariable(expenseData)
        }
        toast.success('Gasto creado exitosamente')
      }

      handleCloseExpenseDialog()
      loadExpensesData()
    } catch (error) {
      console.error('Error saving expense:', error)
      toast.error('Error al guardar el gasto')
    }
  }

  const handleDeleteExpense = async (type, expenseId) => {
    if (!window.confirm('¿Estás seguro de eliminar este gasto?')) return

    try {
      if (type === 'fixed') {
        await expensesAPI.deleteFixed(expenseId)
      } else {
        await expensesAPI.deleteVariable(expenseId)
      }
      toast.success('Gasto eliminado exitosamente')
      loadExpensesData()
    } catch (error) {
      console.error('Error deleting expense:', error)
      toast.error('Error al eliminar el gasto')
    }
  }

  // Memoized calculations for better performance
  const totalFixedExpenses = useMemo(() => {
    return fixedExpenses
      .filter(exp => exp.is_active)
      .reduce((sum, exp) => sum + (exp.amount || 0), 0)
  }, [fixedExpenses])

  const totalVariableExpenses = useMemo(() => {
    return variableExpenses.reduce((sum, exp) => sum + (exp.amount || 0), 0)
  }, [variableExpenses])

  const ebitda = useMemo(() => {
    return (
      (monthlyData?.total_income || 0) -
      (monthlyData?.total_expenses || 0) -
      (monthlyData?.waste_cost || 0) -
      totalFixedExpenses -
      totalVariableExpenses
    )
  }, [monthlyData, totalFixedExpenses, totalVariableExpenses])

  const netProfit = useMemo(() => {
    return ebitda - monthlyTax
  }, [ebitda, monthlyTax])

  // Annual calculations (memoized)
  const annualTotalIncome = useMemo(() => {
    return annualData?.annual_totals?.total_income || 0
  }, [annualData])

  const annualTotalExpenses = useMemo(() => {
    return annualData?.annual_totals?.total_expenses || 0
  }, [annualData])

  const annualWasteCost = useMemo(() => {
    if (!annualData?.monthly_reports) return 0
    return annualData.monthly_reports.reduce((sum, month) => sum + (month.waste_cost || 0), 0)
  }, [annualData])

  const annualFixedExpenses = useMemo(() => {
    return totalFixedExpenses * 12
  }, [totalFixedExpenses])

  const annualVariableExpenses = useMemo(() => {
    // Would need to load all variable expenses for the year
    // For now, return 0 - can be enhanced later
    return 0
  }, [])

  const annualEBITDA = useMemo(() => {
    return (
      annualTotalIncome -
      annualTotalExpenses -
      annualWasteCost -
      annualFixedExpenses -
      annualVariableExpenses
    )
  }, [annualTotalIncome, annualTotalExpenses, annualWasteCost, annualFixedExpenses, annualVariableExpenses])

  const annualNetProfit = useMemo(() => {
    return annualEBITDA - annualTax
  }, [annualEBITDA, annualTax])

  // Legacy function getters for compatibility (use memoized values)
  const getTotalFixedExpenses = () => totalFixedExpenses
  const getTotalVariableExpenses = () => totalVariableExpenses
  const getEBITDA = () => ebitda
  const getNetProfit = () => netProfit
  const getAnnualTotalIncome = () => annualTotalIncome
  const getAnnualTotalExpenses = () => annualTotalExpenses
  const getAnnualWasteCost = () => annualWasteCost
  const getAnnualFixedExpenses = () => annualFixedExpenses
  const getAnnualVariableExpenses = () => annualVariableExpenses
  const getAnnualEBITDA = () => annualEBITDA
  const getAnnualNetProfit = () => annualNetProfit

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

  // Memoized chart data for better performance
  const monthlyTrendData = useMemo(() => {
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
  }, [annualData, mode])

  const serviceDistributionData = useMemo(() => {
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
  }, [monthlyData])

  // Legacy getters for compatibility
  const getMonthlyTrendData = () => monthlyTrendData
  const getServiceDistributionData = () => serviceDistributionData

  const chartOptions = useMemo(() => ({
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
  }), [theme.palette.text.primary, theme.palette.text.secondary, mode])

  if (initialLoading) {
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
            <IconButton onClick={() => { loadStaticData(); loadFilteredData(); }} aria-label="refresh data">
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
      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'center', position: 'relative' }}>
        {loading && (
          <CircularProgress
            size={20}
            sx={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)' }}
          />
        )}
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
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
        >
          <Tab label="Resumen Ejecutivo" icon={<Assessment />} />
          <Tab label="Análisis Financiero" icon={<ShowChart />} />
          <Tab label="Clientes Top" icon={<People />} />
          <Tab label="Operaciones" icon={<Inventory />} />
          <Tab label="Resumen de Mermas" icon={<RemoveCircleOutline />} />
          <Tab label="Estado de Resultados" icon={<AccountBalance />} />
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
                {monthlyTrendData && (
                  <Line data={monthlyTrendData} options={chartOptions} />
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
                {serviceDistributionData && (
                  <Pie
                    data={serviceDistributionData}
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

      {tabValue === 4 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={3}>
                  <RemoveCircleOutline sx={{ fontSize: 40, color: 'warning.main', mr: 2 }} />
                  <Box>
                    <Typography variant="h5" gutterBottom>
                      Resumen de Mermas
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Analiza y controla las pérdidas de inventario
                    </Typography>
                  </Box>
                </Box>

                <Alert severity="info" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    <strong>Cómo registrar mermas:</strong><br />
                    1. Ve a Gestión de Inventario<br />
                    2. Selecciona un producto y haz clic en el botón "Merma"<br />
                    3. Registra la cantidad y razón de la merma<br />
                    4. Los datos aparecerán automáticamente en este reporte
                  </Typography>
                </Alert>

                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" gutterBottom variant="body2">
                          Costo Total de Mermas
                        </Typography>
                        <Typography variant="h4" color="error.main">
                          {new Intl.NumberFormat('es-CL', {
                            style: 'currency',
                            currency: 'CLP',
                            minimumFractionDigits: 0
                          }).format(monthlyData?.waste_cost || 0)}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" gutterBottom variant="body2">
                          Items Mermados
                        </Typography>
                        <Typography variant="h4" color="warning.main">
                          {monthlyData?.waste_items_count || 0}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Registros en el período
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" gutterBottom variant="body2">
                          Tasa de Merma
                        </Typography>
                        <Typography variant="h4" color="info.main">
                          {inventoryTotalValue > 0
                            ? `${((monthlyData?.waste_cost || 0) / inventoryTotalValue * 100).toFixed(2)}%`
                            : '0%'
                          }
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Del valor total de inventario
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Detalle de Mermas del Período
                        </Typography>
                        {monthlyData?.waste_details && monthlyData.waste_details.length > 0 ? (
                          <TableContainer sx={{ mt: 2 }}>
                            <Table>
                              <TableHead>
                                <TableRow>
                                  <TableCell>Fecha</TableCell>
                                  <TableCell>Item</TableCell>
                                  <TableCell align="right">Cantidad</TableCell>
                                  <TableCell align="right">Costo Unit.</TableCell>
                                  <TableCell align="right">Costo Total</TableCell>
                                  <TableCell>Notas</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {monthlyData.waste_details.map((waste, index) => (
                                  <TableRow
                                    key={index}
                                    sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                                  >
                                    <TableCell>
                                      {(() => {
                                        const [year, month, day] = waste.created_at.split('T')[0].split('-');
                                        const monthNames = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
                                        return `${day} ${monthNames[parseInt(month) - 1]} ${year}`;
                                      })()}
                                    </TableCell>
                                    <TableCell>{waste.item_name}</TableCell>
                                    <TableCell align="right">
                                      {waste.quantity} {waste.unit}
                                    </TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(waste.cost_per_unit)}
                                    </TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(waste.total_cost)}
                                    </TableCell>
                                    <TableCell sx={{ fontSize: '0.875rem', color: 'text.secondary' }}>
                                      {waste.notes || '-'}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        ) : (
                          <Alert severity="info" sx={{ mt: 2 }}>
                            No hay mermas registradas en este período
                          </Alert>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 5 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card sx={{ borderRadius: 3, overflow: 'hidden' }}>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
                  <Box display="flex" alignItems="center">
                    <AccountBalance sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
                    <Box>
                      <Typography variant="h5" gutterBottom>
                        Estado de Resultados
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Análisis financiero detallado del período seleccionado
                      </Typography>
                    </Box>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button
                      variant={incomeStatementView === 'monthly' ? 'contained' : 'outlined'}
                      onClick={() => setIncomeStatementView('monthly')}
                      size="small"
                    >
                      Mensual
                    </Button>
                    <Button
                      variant={incomeStatementView === 'annual' ? 'contained' : 'outlined'}
                      onClick={() => setIncomeStatementView('annual')}
                      size="small"
                    >
                      Anual
                    </Button>
                  </Stack>
                </Box>

                {incomeStatementView === 'monthly' && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Mostrando datos de {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                  </Alert>
                )}
                {incomeStatementView === 'annual' && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Mostrando datos anuales de {selectedYear}
                  </Alert>
                )}

                <TableContainer>
                  <Table>
                    <TableBody>
                      {/* NIVEL 1: INGRESOS */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Accordion
                            elevation={0}
                            sx={{
                              '&:before': { display: 'none' },
                              bgcolor: mode === 'dark' ? 'rgba(102, 187, 106, 0.15)' : 'rgba(102, 187, 106, 0.1)',
                              borderRadius: '12px !important',
                              overflow: 'hidden',
                              my: 1,
                              mx: 1,
                              borderLeft: '4px solid',
                              borderLeftColor: 'success.main',
                              '&:hover': { bgcolor: mode === 'dark' ? 'rgba(102, 187, 106, 0.2)' : 'rgba(102, 187, 106, 0.15)' }
                            }}
                          >
                            <AccordionSummary
                              expandIcon={<ExpandMore />}
                              sx={{
                                px: 2,
                                '& .MuiAccordionSummary-content': {
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  my: 2
                                }
                              }}
                            >
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                Ingresos
                              </Typography>
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                {new Intl.NumberFormat('es-CL', {
                                  style: 'currency',
                                  currency: 'CLP',
                                  minimumFractionDigits: 0
                                }).format(incomeStatementView === 'monthly' ? (monthlyData?.total_income || 0) : getAnnualTotalIncome())}
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ pt: 0, pb: 2, px: 2, bgcolor: mode === 'dark' ? '#1e1e1e' : '#ffffff' }}>
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell><strong>Servicio</strong></TableCell>
                                    <TableCell align="center"><strong>Cantidad</strong></TableCell>
                                    <TableCell align="right"><strong>Ingreso</strong></TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  <TableRow>
                                    <TableCell>Pizza Party</TableCell>
                                    <TableCell align="center">
                                      {incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.pizza_party?.count || monthlyData?.events_by_service?.party?.count || 0)
                                        : 0}
                                    </TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.pizza_party?.total_income || monthlyData?.events_by_service?.party?.total_income || 0)
                                        : 0)}
                                    </TableCell>
                                  </TableRow>
                                  <TableRow>
                                    <TableCell>Pizzeros en Acción</TableCell>
                                    <TableCell align="center">
                                      {incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.workshop?.count || 0)
                                        : 0}
                                    </TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.workshop?.total_income || 0)
                                        : 0)}
                                    </TableCell>
                                  </TableRow>
                                  <TableRow>
                                    <TableCell>Ambos Servicios</TableCell>
                                    <TableCell align="center">
                                      {incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.['workshop,pizza_party']?.count || 0)
                                        : 0}
                                    </TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(incomeStatementView === 'monthly'
                                        ? (monthlyData?.events_by_service?.['workshop,pizza_party']?.total_income || 0)
                                        : 0)}
                                    </TableCell>
                                  </TableRow>
                                  <TableRow sx={{ bgcolor: 'action.hover' }}>
                                    <TableCell>Venta Pizzas al Vacío</TableCell>
                                    <TableCell align="center">
                                      <Chip label="Próximamente" size="small" color="info" />
                                    </TableCell>
                                    <TableCell align="right">$0</TableCell>
                                  </TableRow>
                                </TableBody>
                              </Table>
                            </AccordionDetails>
                          </Accordion>
                        </TableCell>
                      </TableRow>

                      {/* NIVEL 2: COSTOS DIRECTOS */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Accordion
                            elevation={0}
                            sx={{
                              '&:before': { display: 'none' },
                              bgcolor: mode === 'dark' ? 'rgba(239, 83, 80, 0.15)' : 'rgba(239, 83, 80, 0.1)',
                              borderRadius: '12px !important',
                              overflow: 'hidden',
                              my: 1,
                              mx: 1,
                              borderLeft: '4px solid',
                              borderLeftColor: 'error.main',
                              '&:hover': { bgcolor: mode === 'dark' ? 'rgba(239, 83, 80, 0.2)' : 'rgba(239, 83, 80, 0.15)' }
                            }}
                          >
                            <AccordionSummary
                              expandIcon={<ExpandMore />}
                              sx={{
                                px: 2,
                                '& .MuiAccordionSummary-content': {
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  my: 2
                                }
                              }}
                            >
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                Costos Directos
                              </Typography>
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                -{new Intl.NumberFormat('es-CL', {
                                  style: 'currency',
                                  currency: 'CLP',
                                  minimumFractionDigits: 0
                                }).format(
                                  incomeStatementView === 'monthly'
                                    ? (monthlyData?.total_expenses || 0)
                                    : getAnnualTotalExpenses()
                                )}
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ pt: 0, pb: 2, px: 2, bgcolor: mode === 'dark' ? '#1e1e1e' : '#ffffff' }}>
                              <Table size="small">
                                <TableBody>
                                  <TableRow>
                                    <TableCell>Costo de Eventos</TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(
                                        incomeStatementView === 'monthly'
                                          ? ((monthlyData?.total_expenses || 0) - (monthlyData?.waste_cost || 0))
                                          : (getAnnualTotalExpenses() - getAnnualWasteCost())
                                      )}
                                    </TableCell>
                                  </TableRow>
                                  <TableRow>
                                    <TableCell>Costo de Mermas</TableCell>
                                    <TableCell align="right">
                                      {new Intl.NumberFormat('es-CL', {
                                        style: 'currency',
                                        currency: 'CLP',
                                        minimumFractionDigits: 0
                                      }).format(incomeStatementView === 'monthly' ? (monthlyData?.waste_cost || 0) : getAnnualWasteCost())}
                                    </TableCell>
                                  </TableRow>
                                </TableBody>
                              </Table>
                            </AccordionDetails>
                          </Accordion>
                        </TableCell>
                      </TableRow>

                      {/* NIVEL 3: GASTOS */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Accordion
                            elevation={0}
                            sx={{
                              '&:before': { display: 'none' },
                              bgcolor: mode === 'dark' ? 'rgba(255, 167, 38, 0.15)' : 'rgba(255, 167, 38, 0.1)',
                              borderRadius: '12px !important',
                              overflow: 'hidden',
                              my: 1,
                              mx: 1,
                              borderLeft: '4px solid',
                              borderLeftColor: 'warning.main',
                              '&:hover': { bgcolor: mode === 'dark' ? 'rgba(255, 167, 38, 0.2)' : 'rgba(255, 167, 38, 0.15)' }
                            }}
                          >
                            <AccordionSummary
                              expandIcon={<ExpandMore />}
                              sx={{
                                px: 2,
                                '& .MuiAccordionSummary-content': {
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  my: 2
                                }
                              }}
                            >
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                Gastos
                              </Typography>
                              <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                                -{new Intl.NumberFormat('es-CL', {
                                  style: 'currency',
                                  currency: 'CLP',
                                  minimumFractionDigits: 0
                                }).format(
                                  incomeStatementView === 'monthly'
                                    ? (getTotalFixedExpenses() + getTotalVariableExpenses())
                                    : (getAnnualFixedExpenses() + getAnnualVariableExpenses())
                                )}
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ pt: 0, pb: 2, px: 2, bgcolor: mode === 'dark' ? '#1e1e1e' : '#ffffff' }}>
                              {/* Gastos Fijos - Sub-acordeón */}
                              <Accordion
                                elevation={0}
                                sx={{
                                  '&:before': { display: 'none' },
                                  bgcolor: mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                                  borderRadius: '8px',
                                  mb: 1,
                                  border: `1px solid ${mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}`,
                                  '&:hover': { bgcolor: mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)' }
                                }}
                              >
                                <AccordionSummary
                                  expandIcon={<ExpandMore />}
                                  sx={{
                                    px: 2,
                                    minHeight: '48px',
                                    '& .MuiAccordionSummary-content': {
                                      justifyContent: 'space-between',
                                      alignItems: 'center',
                                      my: 1
                                    }
                                  }}
                                >
                                  <Box display="flex" alignItems="center" gap={1}>
                                    <Typography sx={{ fontWeight: 500 }}>
                                      Gastos Fijos {incomeStatementView === 'annual' && '(x12 meses)'}
                                    </Typography>
                                  </Box>
                                  <Typography sx={{ fontWeight: 500 }}>
                                    {new Intl.NumberFormat('es-CL', {
                                      style: 'currency',
                                      currency: 'CLP',
                                      minimumFractionDigits: 0
                                    }).format(incomeStatementView === 'monthly' ? getTotalFixedExpenses() : getAnnualFixedExpenses())}
                                  </Typography>
                                </AccordionSummary>
                                <AccordionDetails sx={{ pt: 0, px: 2, pb: 2 }}>
                                  <Box>
                                    <Button
                                      variant="outlined"
                                      startIcon={<Add />}
                                      size="small"
                                      sx={{ mb: 2 }}
                                      onClick={() => handleOpenExpenseDialog('fixed')}
                                    >
                                      Agregar Gasto Fijo
                                    </Button>
                                    {fixedExpenses.filter(exp => exp.is_active).length > 0 ? (
                                      <Table size="small">
                                        <TableBody>
                                          {fixedExpenses.filter(exp => exp.is_active).map((expense) => (
                                            <TableRow key={expense.id}>
                                              <TableCell>{expense.description}</TableCell>
                                              <TableCell>{expense.category}</TableCell>
                                              <TableCell align="right">
                                                {new Intl.NumberFormat('es-CL', {
                                                  style: 'currency',
                                                  currency: 'CLP',
                                                  minimumFractionDigits: 0
                                                }).format(expense.amount)}
                                              </TableCell>
                                              <TableCell align="right">
                                                <IconButton
                                                  size="small"
                                                  onClick={() => handleOpenExpenseDialog('fixed', expense)}
                                                >
                                                  <Assessment fontSize="small" />
                                                </IconButton>
                                                <IconButton
                                                  size="small"
                                                  color="error"
                                                  onClick={() => handleDeleteExpense('fixed', expense.id)}
                                                >
                                                  <RemoveCircleOutline fontSize="small" />
                                                </IconButton>
                                              </TableCell>
                                            </TableRow>
                                          ))}
                                        </TableBody>
                                      </Table>
                                    ) : (
                                      <Alert severity="info">
                                        No hay gastos fijos registrados. Haz clic en "Agregar Gasto Fijo" para crear uno.
                                      </Alert>
                                    )}
                                  </Box>
                                </AccordionDetails>
                              </Accordion>

                              {/* Gastos Variables - Sub-acordeón */}
                              <Accordion
                                elevation={0}
                                sx={{
                                  '&:before': { display: 'none' },
                                  bgcolor: mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                                  borderRadius: '8px',
                                  border: `1px solid ${mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}`,
                                  '&:hover': { bgcolor: mode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)' }
                                }}
                              >
                                <AccordionSummary
                                  expandIcon={<ExpandMore />}
                                  sx={{
                                    px: 2,
                                    minHeight: '48px',
                                    '& .MuiAccordionSummary-content': {
                                      justifyContent: 'space-between',
                                      alignItems: 'center',
                                      my: 1
                                    }
                                  }}
                                >
                                  <Box display="flex" alignItems="center" gap={1}>
                                    <Typography sx={{ fontWeight: 500 }}>Gastos Variables</Typography>
                                  </Box>
                                  <Typography sx={{ fontWeight: 500 }}>
                                    {new Intl.NumberFormat('es-CL', {
                                      style: 'currency',
                                      currency: 'CLP',
                                      minimumFractionDigits: 0
                                    }).format(incomeStatementView === 'monthly' ? getTotalVariableExpenses() : getAnnualVariableExpenses())}
                                  </Typography>
                                </AccordionSummary>
                                <AccordionDetails sx={{ pt: 0, px: 2, pb: 2 }}>
                                  <Box>
                                    {incomeStatementView === 'monthly' && (
                                      <Button
                                        variant="outlined"
                                        startIcon={<Add />}
                                        size="small"
                                        sx={{ mb: 2 }}
                                        onClick={() => handleOpenExpenseDialog('variable')}
                                      >
                                        Agregar Gasto Variable
                                      </Button>
                                    )}
                                    {incomeStatementView === 'monthly' && variableExpenses.length > 0 ? (
                                      <Table size="small">
                                        <TableBody>
                                          {variableExpenses.map((expense) => (
                                            <TableRow key={expense.id}>
                                              <TableCell>
                                                {expense.description}
                                                {expense.notes && (
                                                  <Typography variant="caption" display="block" color="text.secondary">
                                                    {expense.notes}
                                                  </Typography>
                                                )}
                                              </TableCell>
                                              <TableCell>{expense.category}</TableCell>
                                              <TableCell align="right">
                                                {new Intl.NumberFormat('es-CL', {
                                                  style: 'currency',
                                                  currency: 'CLP',
                                                  minimumFractionDigits: 0
                                                }).format(expense.amount)}
                                              </TableCell>
                                              <TableCell align="right">
                                                <IconButton
                                                  size="small"
                                                  onClick={() => handleOpenExpenseDialog('variable', expense)}
                                                >
                                                  <Assessment fontSize="small" />
                                                </IconButton>
                                                <IconButton
                                                  size="small"
                                                  color="error"
                                                  onClick={() => handleDeleteExpense('variable', expense.id)}
                                                >
                                                  <RemoveCircleOutline fontSize="small" />
                                                </IconButton>
                                              </TableCell>
                                            </TableRow>
                                          ))}
                                        </TableBody>
                                      </Table>
                                    ) : (
                                      <Alert severity="info">
                                        {incomeStatementView === 'annual'
                                          ? 'En vista anual se muestra el total de gastos variables del año'
                                          : 'No hay gastos variables registrados. Haz clic en "Agregar Gasto Variable" para crear uno.'}
                                      </Alert>
                                    )}
                                  </Box>
                                </AccordionDetails>
                              </Accordion>
                            </AccordionDetails>
                          </Accordion>
                        </TableCell>
                      </TableRow>

                      {/* EBITDA */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Box
                            sx={{
                              bgcolor: mode === 'dark' ? 'rgba(33, 150, 243, 0.15)' : 'rgba(33, 150, 243, 0.1)',
                              borderLeft: '4px solid',
                              borderLeftColor: 'primary.main',
                              borderRadius: '12px',
                              my: 1,
                              mx: 1,
                              px: 2,
                              py: 2.5,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              '&:hover': { bgcolor: mode === 'dark' ? 'rgba(33, 150, 243, 0.2)' : 'rgba(33, 150, 243, 0.15)' }
                            }}
                          >
                            <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                              EBITDA
                            </Typography>
                            <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
                              {new Intl.NumberFormat('es-CL', {
                                style: 'currency',
                                currency: 'CLP',
                                minimumFractionDigits: 0
                              }).format(incomeStatementView === 'monthly' ? getEBITDA() : getAnnualEBITDA())}
                            </Typography>
                          </Box>
                        </TableCell>
                      </TableRow>

                      {/* Impuestos */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Box sx={{ px: 2, py: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography>Impuestos</Typography>
                            <TextField
                              type="number"
                              size="small"
                              value={incomeStatementView === 'monthly' ? monthlyTax : annualTax}
                              onChange={(e) => {
                                const value = parseFloat(e.target.value) || 0
                                if (incomeStatementView === 'monthly') {
                                  setMonthlyTax(value)
                                  // Save to database after a short delay
                                  setTimeout(() => saveMonthlyTax(value), 1000)
                                } else {
                                  setAnnualTax(value)
                                }
                              }}
                              InputProps={{
                                startAdornment: <Typography sx={{ mr: 0.5 }}>-$</Typography>,
                              }}
                              sx={{ width: '200px' }}
                              placeholder="0"
                            />
                          </Box>
                        </TableCell>
                      </TableRow>

                      {/* UTILIDAD NETA */}
                      <TableRow>
                        <TableCell colSpan={2} sx={{ p: 0 }}>
                          <Box
                            sx={{
                              bgcolor: mode === 'dark' ? 'rgba(255, 167, 38, 0.15)' : 'rgba(255, 167, 38, 0.1)',
                              borderLeft: '4px solid',
                              borderLeftColor: 'warning.main',
                              borderRadius: '12px',
                              my: 1,
                              mx: 1,
                              px: 2,
                              py: 3,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              '&:hover': { bgcolor: mode === 'dark' ? 'rgba(255, 167, 38, 0.2)' : 'rgba(255, 167, 38, 0.15)' }
                            }}
                          >
                            <Typography sx={{ fontWeight: 700, fontSize: '1.2rem' }}>
                              UTILIDAD NETA
                            </Typography>
                            <Typography sx={{ fontWeight: 700, fontSize: '1.2rem' }}>
                              {new Intl.NumberFormat('es-CL', {
                                style: 'currency',
                                currency: 'CLP',
                                minimumFractionDigits: 0
                              }).format(incomeStatementView === 'monthly' ? getNetProfit() : getAnnualNetProfit())}
                            </Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Expense Dialog */}
      <Dialog
        open={expenseDialogOpen}
        onClose={handleCloseExpenseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editingExpense ? 'Editar' : 'Agregar'} Gasto {expenseDialogType === 'fixed' ? 'Fijo' : 'Variable'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Descripción"
              fullWidth
              value={expenseFormData.description}
              onChange={(e) => setExpenseFormData({ ...expenseFormData, description: e.target.value })}
              required
            />
            <TextField
              label="Monto"
              type="number"
              fullWidth
              value={expenseFormData.amount}
              onChange={(e) => setExpenseFormData({ ...expenseFormData, amount: e.target.value })}
              required
              InputProps={{
                startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>
              }}
            />
            <FormControl fullWidth>
              <InputLabel>Categoría</InputLabel>
              <Select
                value={expenseFormData.category}
                label="Categoría"
                onChange={(e) => setExpenseFormData({ ...expenseFormData, category: e.target.value })}
              >
                <MenuItem value="general">General</MenuItem>
                <MenuItem value="servicios">Servicios</MenuItem>
                <MenuItem value="arriendo">Arriendo</MenuItem>
                <MenuItem value="sueldos">Sueldos</MenuItem>
                <MenuItem value="marketing">Marketing</MenuItem>
                <MenuItem value="otros">Otros</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Notas (opcional)"
              fullWidth
              multiline
              rows={2}
              value={expenseFormData.notes}
              onChange={(e) => setExpenseFormData({ ...expenseFormData, notes: e.target.value })}
            />
            {expenseDialogType === 'variable' && (
              <Alert severity="info">
                Este gasto se registrará para {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseExpenseDialog}>Cancelar</Button>
          <Button
            onClick={handleSaveExpense}
            variant="contained"
            disabled={!expenseFormData.description || !expenseFormData.amount}
          >
            {editingExpense ? 'Actualizar' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}