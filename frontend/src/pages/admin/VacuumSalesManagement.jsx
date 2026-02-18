import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
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
  Alert,
  LinearProgress,
  IconButton,
  Tooltip,
  Autocomplete,
  Divider,
  List,
  ListItem,
  ListItemText,
  InputAdornment,
  Stack,
  Avatar
} from '@mui/material'
import {
  Add,
  Edit,
  Delete,
  Visibility,
  LocalPizza,
  AttachMoney,
  TrendingUp,
  People,
  ShoppingCart,
  Payment,
  Search,
  FilterList,
  Refresh
} from '@mui/icons-material'
import { vacuumSalesAPI, customersAPI, inventoryAPI } from '../../services/api'
import { formatCurrency } from '../../utils/formatters'
import toast from 'react-hot-toast'

const VacuumSalesManagement = () => {
  // State
  const [sales, setSales] = useState([])
  const [customers, setCustomers] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)

  // Dialogs
  const [saleDialog, setSaleDialog] = useState(false)
  const [detailDialog, setDetailDialog] = useState(false)
  const [paymentDialog, setPaymentDialog] = useState(false)
  const [selectedSale, setSelectedSale] = useState(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [paymentFilter, setPaymentFilter] = useState('all')
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${String(now.getMonth() + 1).padStart(2, '0')}-${now.getFullYear()}`
  })

  // Form data
  const [formData, setFormData] = useState({
    customer_id: '',
    customer_name: '',
    items: [],
    discount: 0,
    discountType: 'amount', // 'amount' or 'percent'
    notes: '',
    sale_date: new Date().toISOString().split('T')[0]
  })

  const [newItem, setNewItem] = useState({
    product_id: '',
    product_name: '',
    quantity: '',
    unit_price: ''
  })

  const [paymentData, setPaymentData] = useState({
    amount: '',
    method: 'transferencia',
    date: new Date().toISOString().split('T')[0],
    notes: ''
  })

  // Load data
  useEffect(() => {
    loadData()
  }, [selectedMonth])

  const loadData = async () => {
    try {
      setLoading(true)
      const [year, month] = selectedMonth.split('-').reverse()

      const [salesRes, customersRes, inventoryRes, summaryRes] = await Promise.all([
        vacuumSalesAPI.getAll({ year, month }),
        customersAPI.getAll({ limit: 500 }),
        inventoryAPI.getAll({ limit: 500 }),
        vacuumSalesAPI.getSummary(year, month)
      ])

      setSales(salesRes.data.items || salesRes.data || [])
      setCustomers(customersRes.data.items || customersRes.data || [])

      // Filter only finished products with stock > 0
      const allProducts = inventoryRes.data.items || inventoryRes.data || []
      setProducts(allProducts.filter(p =>
        (p.product_type === 'finished_good' || p.category === 'finished') &&
        (p.current_stock > 0)
      ))

      setSummary(summaryRes.data)
    } catch (error) {
      console.error('Error loading data:', error)
      toast.error('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  // Filtered sales
  const filteredSales = useMemo(() => {
    let filtered = [...sales]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(sale =>
        sale.customer_name?.toLowerCase().includes(query) ||
        sale.id?.toLowerCase().includes(query)
      )
    }

    if (paymentFilter !== 'all') {
      filtered = filtered.filter(sale => sale.payment_status === paymentFilter)
    }

    return filtered
  }, [sales, searchQuery, paymentFilter])

  // Calculate totals for items
  const calculateTotals = useCallback((items, discount = 0, discountType = 'amount') => {
    const subtotal = items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0)
    const totalCost = items.reduce((sum, item) => sum + (item.quantity * (item.cost_per_unit || 0)), 0)

    // Calculate discount amount based on type
    const discountAmount = discountType === 'percent'
      ? (subtotal * (discount / 100))
      : discount

    const total = subtotal - discountAmount
    const profit = total - totalCost

    return { subtotal, total, totalCost, profit, discountAmount }
  }, [])

  // Handle new sale
  const handleOpenSaleDialog = () => {
    setFormData({
      customer_id: '',
      customer_name: '',
      items: [],
      discount: 0,
      discountType: 'amount',
      notes: '',
      sale_date: new Date().toISOString().split('T')[0]
    })
    setNewItem({ product_id: '', product_name: '', quantity: '', unit_price: '' })
    setSaleDialog(true)
  }

  const handleAddItem = () => {
    if (!newItem.product_id || !newItem.quantity || !newItem.unit_price) {
      toast.error('Completa todos los campos del item')
      return
    }

    const product = products.find(p => p.id === newItem.product_id)
    const item = {
      product_id: newItem.product_id,
      product_name: newItem.product_name || product?.name || '',
      quantity: parseFloat(newItem.quantity),
      unit_price: parseFloat(newItem.unit_price),
      cost_per_unit: product?.weighted_average_cost || product?.cost_per_unit || 0
    }

    setFormData(prev => ({
      ...prev,
      items: [...prev.items, item]
    }))

    setNewItem({ product_id: '', product_name: '', quantity: '', unit_price: '' })
  }

  const handleRemoveItem = (index) => {
    setFormData(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index)
    }))
  }

  const handleSubmitSale = async () => {
    if (!formData.customer_id) {
      toast.error('Selecciona un cliente')
      return
    }
    if (formData.items.length === 0) {
      toast.error('Agrega al menos un producto')
      return
    }

    try {
      // Calculate final discount amount
      const totals = calculateTotals(formData.items, formData.discount, formData.discountType)

      // Send with discount as amount (calculated)
      const saleData = {
        ...formData,
        discount: totals.discountAmount // Always send as amount
      }
      delete saleData.discountType // Remove discountType before sending

      await vacuumSalesAPI.create(saleData)
      toast.success('Venta registrada exitosamente')
      setSaleDialog(false)
      loadData()
    } catch (error) {
      console.error('Error creating sale:', error)
      toast.error('Error al registrar venta')
    }
  }

  // Handle view details
  const handleViewDetails = (sale) => {
    setSelectedSale(sale)
    setDetailDialog(true)
  }

  // Handle delete
  const handleDelete = async (saleId) => {
    if (!window.confirm('¿Estás seguro de eliminar esta venta? Se restaurará el inventario.')) return

    try {
      await vacuumSalesAPI.delete(saleId)
      toast.success('Venta eliminada')
      loadData()
    } catch (error) {
      console.error('Error deleting sale:', error)
      toast.error('Error al eliminar venta')
    }
  }

  // Handle payment
  const handleOpenPaymentDialog = (sale) => {
    setSelectedSale(sale)
    setPaymentData({
      amount: '',
      method: 'transferencia',
      date: new Date().toISOString().split('T')[0],
      notes: ''
    })
    setPaymentDialog(true)
  }

  const handleSubmitPayment = async () => {
    if (!paymentData.amount || parseFloat(paymentData.amount) <= 0) {
      toast.error('Ingresa un monto válido')
      return
    }

    try {
      await vacuumSalesAPI.addPayment(selectedSale.id, paymentData)
      toast.success('Pago registrado')
      setPaymentDialog(false)
      loadData()
    } catch (error) {
      console.error('Error adding payment:', error)
      toast.error(error.response?.data?.error || 'Error al registrar pago')
    }
  }

  const handleDeletePayment = async (saleId, paymentId) => {
    if (!window.confirm('¿Eliminar este pago?')) return

    try {
      await vacuumSalesAPI.deletePayment(saleId, paymentId)
      toast.success('Pago eliminado')
      loadData()
      // Refresh selected sale
      const updated = await vacuumSalesAPI.getById(saleId)
      setSelectedSale(updated.data)
    } catch (error) {
      console.error('Error deleting payment:', error)
      toast.error('Error al eliminar pago')
    }
  }

  // Get status color
  const getPaymentStatusColor = (status) => {
    switch (status) {
      case 'paid': return 'success'
      case 'partial': return 'warning'
      case 'unpaid': return 'error'
      default: return 'default'
    }
  }

  const getPaymentStatusLabel = (status) => {
    switch (status) {
      case 'paid': return 'Pagado'
      case 'partial': return 'Parcial'
      case 'unpaid': return 'Pendiente'
      default: return status
    }
  }

  // Generate month options
  const monthOptions = useMemo(() => {
    const options = []
    const now = new Date()
    for (let i = 0; i < 12; i++) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const value = `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`
      const label = date.toLocaleDateString('es-CL', { month: 'long', year: 'numeric' })
      options.push({ value, label: label.charAt(0).toUpperCase() + label.slice(1) })
    }
    return options
  }, [])

  const formTotals = calculateTotals(formData.items, formData.discount, formData.discountType)

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>
        Ventas de Pizzas al Vacío
      </Typography>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* KPI Cards - Diseño consistente con Inventario */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              height: '100%',
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 4
              }
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box
                  sx={{
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.3)',
                    color: 'inherit',
                    p: 1.2,
                    borderRadius: 2,
                    mr: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <ShoppingCart fontSize="medium" />
                </Box>
                <Typography variant="subtitle2" fontWeight="600">
                  Ventas del Mes
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
                {summary?.total_sales || 0}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                Transacciones realizadas
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              height: '100%',
              bgcolor: 'success.main',
              color: 'success.contrastText',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 4
              }
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box
                  sx={{
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.3)',
                    color: 'inherit',
                    p: 1.2,
                    borderRadius: 2,
                    mr: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <AttachMoney fontSize="medium" />
                </Box>
                <Typography variant="subtitle2" fontWeight="600">
                  Ingresos
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
                {formatCurrency(summary?.total_income || 0)}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                Total facturado
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              height: '100%',
              bgcolor: 'info.main',
              color: 'info.contrastText',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 4
              }
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box
                  sx={{
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.3)',
                    color: 'inherit',
                    p: 1.2,
                    borderRadius: 2,
                    mr: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <TrendingUp fontSize="medium" />
                </Box>
                <Typography variant="subtitle2" fontWeight="600">
                  Ganancia
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
                {formatCurrency(summary?.total_profit || 0)}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                {summary?.profit_margin || 0}% margen
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              height: '100%',
              bgcolor: 'warning.main',
              color: 'warning.contrastText',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 4
              }
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box
                  sx={{
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.1)',
                    color: 'inherit',
                    p: 1.2,
                    borderRadius: 2,
                    mr: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Payment fontSize="medium" />
                </Box>
                <Typography variant="subtitle2" fontWeight="600">
                  Por Cobrar
                </Typography>
              </Box>
              <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
                {formatCurrency(summary?.total_pending || 0)}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                Pendiente de pago
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters and Actions */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Mes</InputLabel>
                <Select
                  value={selectedMonth}
                  label="Mes"
                  onChange={(e) => setSelectedMonth(e.target.value)}
                >
                  {monthOptions.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                size="small"
                placeholder="Buscar cliente..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: <Search sx={{ color: 'text.secondary', mr: 1 }} />
                }}
              />
            </Grid>

            <Grid item xs={12} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Estado Pago</InputLabel>
                <Select
                  value={paymentFilter}
                  label="Estado Pago"
                  onChange={(e) => setPaymentFilter(e.target.value)}
                >
                  <MenuItem value="all">Todos</MenuItem>
                  <MenuItem value="unpaid">Pendiente</MenuItem>
                  <MenuItem value="partial">Parcial</MenuItem>
                  <MenuItem value="paid">Pagado</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4} sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Button
                startIcon={<Refresh />}
                onClick={loadData}
                disabled={loading}
              >
                Actualizar
              </Button>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={handleOpenSaleDialog}
                sx={{ bgcolor: '#FFD700', color: '#000', '&:hover': { bgcolor: '#FFC000' } }}
              >
                Nueva Venta
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Sales Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: 'action.hover' }}>
              <TableCell>Fecha</TableCell>
              <TableCell>Cliente</TableCell>
              <TableCell align="center">Items</TableCell>
              <TableCell align="right">Total</TableCell>
              <TableCell align="right">Ganancia</TableCell>
              <TableCell align="center">Estado Pago</TableCell>
              <TableCell align="center">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSales.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <LocalPizza sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography color="text.secondary">
                    No hay ventas registradas
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredSales.map((sale) => (
                <TableRow key={sale.id} hover>
                  <TableCell>
                    {new Date(sale.sale_date).toLocaleDateString('es-CL')}
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight="medium">{sale.customer_name}</Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={`${sale.items?.length || 0} items`}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold">
                      {formatCurrency(sale.total)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography color="success.main" fontWeight="medium">
                      {formatCurrency(sale.profit)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={getPaymentStatusLabel(sale.payment_status)}
                      color={getPaymentStatusColor(sale.payment_status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Ver detalles">
                      <IconButton size="small" onClick={() => handleViewDetails(sale)}>
                        <Visibility />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Registrar pago">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenPaymentDialog(sale)}
                        disabled={sale.payment_status === 'paid'}
                      >
                        <Payment />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Eliminar">
                      <IconButton size="small" color="error" onClick={() => handleDelete(sale.id)}>
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* New Sale Dialog */}
      <Dialog open={saleDialog} onClose={() => setSaleDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ bgcolor: '#000', color: '#FFD700', pb: 2 }}>
          Nueva Venta de Pizzas al Vacío
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 0.5 }}>
            {/* Customer Selection */}
            <Grid item xs={12} md={6}>
              <Autocomplete
                options={customers}
                getOptionLabel={(option) => option.name || ''}
                value={customers.find(c => c.id === formData.customer_id) || null}
                onChange={(_, newValue) => {
                  setFormData(prev => ({
                    ...prev,
                    customer_id: newValue?.id || '',
                    customer_name: newValue?.name || ''
                  }))
                }}
                renderInput={(params) => (
                  <TextField {...params} label="Cliente" required />
                )}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="date"
                label="Fecha de Venta"
                value={formData.sale_date}
                onChange={(e) => setFormData(prev => ({ ...prev, sale_date: e.target.value }))}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            {/* Add Product */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 2 }}>
                Agregar Productos
              </Typography>
              {products.length === 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  No hay productos terminados con stock disponible. Registra producción en la sección de Producción.
                </Alert>
              )}
              <Grid container spacing={2} alignItems="flex-end">
                <Grid item xs={12} md={4}>
                  <Autocomplete
                    options={products}
                    getOptionLabel={(option) => {
                      const stock = Math.round((option.current_stock || 0) * 100) / 100
                      return `${option.name} (Stock: ${stock < 0.01 ? 0 : stock.toFixed(2)} ${option.unit || 'unidades'})`
                    }}
                    value={products.find(p => p.id === newItem.product_id) || null}
                    onChange={(_, newValue) => {
                      setNewItem(prev => ({
                        ...prev,
                        product_id: newValue?.id || '',
                        product_name: newValue?.name || ''
                      }))
                    }}
                    renderInput={(params) => (
                      <TextField {...params} label="Producto" size="small" />
                    )}
                    disabled={products.length === 0}
                  />
                </Grid>
                <Grid item xs={6} md={2}>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label="Cantidad"
                    value={newItem.quantity}
                    onChange={(e) => setNewItem(prev => ({ ...prev, quantity: e.target.value }))}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label="Precio Unitario"
                    value={newItem.unit_price}
                    onChange={(e) => setNewItem(prev => ({ ...prev, unit_price: e.target.value }))}
                    InputProps={{
                      startAdornment: <InputAdornment position="start">$</InputAdornment>
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<Add />}
                    onClick={handleAddItem}
                  >
                    Agregar
                  </Button>
                </Grid>
              </Grid>
            </Grid>

            {/* Items List */}
            {formData.items.length > 0 && (
              <Grid item xs={12}>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Producto</TableCell>
                        <TableCell align="center">Cantidad</TableCell>
                        <TableCell align="right">Precio Unit.</TableCell>
                        <TableCell align="right">Total</TableCell>
                        <TableCell align="center" width={50}></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {formData.items.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>{item.product_name}</TableCell>
                          <TableCell align="center">{item.quantity}</TableCell>
                          <TableCell align="right">{formatCurrency(item.unit_price)}</TableCell>
                          <TableCell align="right">{formatCurrency(item.quantity * item.unit_price)}</TableCell>
                          <TableCell align="center">
                            <IconButton size="small" color="error" onClick={() => handleRemoveItem(index)}>
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>
            )}

            {/* Discount and Notes */}
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <FormControl size="small" sx={{ minWidth: 80 }}>
                  <Select
                    value={formData.discountType}
                    onChange={(e) => setFormData(prev => ({ ...prev, discountType: e.target.value }))}
                  >
                    <MenuItem value="amount">$</MenuItem>
                    <MenuItem value="percent">%</MenuItem>
                  </Select>
                </FormControl>
                <TextField
                  fullWidth
                  type="number"
                  label="Descuento"
                  value={formData.discount}
                  onChange={(e) => setFormData(prev => ({ ...prev, discount: parseFloat(e.target.value) || 0 }))}
                  InputProps={{
                    endAdornment: formData.discountType === 'percent' ? (
                      <InputAdornment position="end">%</InputAdornment>
                    ) : null
                  }}
                  helperText={formData.discountType === 'percent' && formData.items.length > 0
                    ? `= ${formatCurrency(formTotals.discountAmount)}`
                    : ''
                  }
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Notas"
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              />
            </Grid>

            {/* Totals */}
            {formData.items.length > 0 && (
              <Grid item xs={12}>
                <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" color="text.secondary">Subtotal</Typography>
                      <Typography variant="h6">{formatCurrency(formTotals.subtotal)}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Descuento {formData.discountType === 'percent' ? `(${formData.discount}%)` : ''}
                      </Typography>
                      <Typography variant="h6" color="error.main">-{formatCurrency(formTotals.discountAmount)}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" color="text.secondary">Total</Typography>
                      <Typography variant="h6" fontWeight="bold">{formatCurrency(formTotals.total)}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" color="text.secondary">Ganancia Est.</Typography>
                      <Typography variant="h6" color="success.main">{formatCurrency(formTotals.profit)}</Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSaleDialog(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleSubmitSale}
            disabled={!formData.customer_id || formData.items.length === 0}
            sx={{ bgcolor: '#FFD700', color: '#000', '&:hover': { bgcolor: '#FFC000' } }}
          >
            Registrar Venta
          </Button>
        </DialogActions>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailDialog} onClose={() => setDetailDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ bgcolor: '#000', color: '#FFD700' }}>
          Detalle de Venta
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          {selectedSale && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Cliente</Typography>
                <Typography variant="h6">{selectedSale.customer_name}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">Fecha</Typography>
                <Typography variant="h6">
                  {new Date(selectedSale.sale_date).toLocaleDateString('es-CL')}
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 2 }}>
                  Productos
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Producto</TableCell>
                        <TableCell align="center">Cantidad</TableCell>
                        <TableCell align="right">Precio</TableCell>
                        <TableCell align="right">Costo</TableCell>
                        <TableCell align="right">Total</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedSale.items?.map((item, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{item.product_name}</TableCell>
                          <TableCell align="center">{item.quantity}</TableCell>
                          <TableCell align="right">{formatCurrency(item.unit_price)}</TableCell>
                          <TableCell align="right">{formatCurrency(item.cost_per_unit)}</TableCell>
                          <TableCell align="right">{formatCurrency(item.total_price)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>

              <Grid item xs={12}>
                <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Total</Typography>
                      <Typography variant="h5" fontWeight="bold">{formatCurrency(selectedSale.total)}</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Costo</Typography>
                      <Typography variant="h5" color="error.main">{formatCurrency(selectedSale.total_cost)}</Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Ganancia</Typography>
                      <Typography variant="h5" color="success.main">{formatCurrency(selectedSale.profit)}</Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>

              {/* Payments */}
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    Pagos
                  </Typography>
                  <Chip
                    label={getPaymentStatusLabel(selectedSale.payment_status)}
                    color={getPaymentStatusColor(selectedSale.payment_status)}
                    size="small"
                  />
                </Box>

                {selectedSale.payments?.length > 0 ? (
                  <List dense>
                    {selectedSale.payments.map((payment, idx) => (
                      <ListItem
                        key={idx}
                        secondaryAction={
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleDeletePayment(selectedSale.id, payment.id)}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        }
                      >
                        <ListItemText
                          primary={formatCurrency(payment.amount)}
                          secondary={`${payment.method} - ${new Date(payment.date).toLocaleDateString('es-CL')}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    Sin pagos registrados
                  </Typography>
                )}

                <Box sx={{ mt: 2, p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                  <Typography variant="body2">
                    <strong>Pagado:</strong> {formatCurrency(selectedSale.payment_summary?.total_paid || 0)}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Por cobrar:</strong> {formatCurrency(selectedSale.payment_summary?.balance_due || 0)}
                  </Typography>
                </Box>
              </Grid>

              {selectedSale.notes && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">Notas</Typography>
                  <Typography>{selectedSale.notes}</Typography>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog(false)}>Cerrar</Button>
          {selectedSale?.payment_status !== 'paid' && (
            <Button
              variant="contained"
              startIcon={<Payment />}
              onClick={() => {
                setDetailDialog(false)
                handleOpenPaymentDialog(selectedSale)
              }}
            >
              Registrar Pago
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Payment Dialog */}
      <Dialog open={paymentDialog} onClose={() => setPaymentDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Registrar Pago</DialogTitle>
        <DialogContent>
          {selectedSale && (
            <Box sx={{ mt: 2 }}>
              <Alert severity="info" sx={{ mb: 2 }}>
                Total: {formatCurrency(selectedSale.total)} |
                Pagado: {formatCurrency(selectedSale.payment_summary?.total_paid || 0)} |
                Pendiente: {formatCurrency(selectedSale.payment_summary?.balance_due || 0)}
              </Alert>

              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Monto"
                    value={paymentData.amount}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, amount: e.target.value }))}
                    InputProps={{
                      startAdornment: <InputAdornment position="start">$</InputAdornment>
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>Método</InputLabel>
                    <Select
                      value={paymentData.method}
                      label="Método"
                      onChange={(e) => setPaymentData(prev => ({ ...prev, method: e.target.value }))}
                    >
                      <MenuItem value="efectivo">Efectivo</MenuItem>
                      <MenuItem value="transferencia">Transferencia</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="date"
                    label="Fecha"
                    value={paymentData.date}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, date: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Notas"
                    value={paymentData.notes}
                    onChange={(e) => setPaymentData(prev => ({ ...prev, notes: e.target.value }))}
                  />
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPaymentDialog(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleSubmitPayment}>
            Registrar Pago
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default VacuumSalesManagement
