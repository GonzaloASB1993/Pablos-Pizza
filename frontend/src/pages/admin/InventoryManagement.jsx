import { useState, useEffect } from 'react'
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
  LinearProgress
} from '@mui/material'
import { Add, Edit, Delete, Warning } from '@mui/icons-material'
import { inventoryAPI } from '../../services/api'
import toast from 'react-hot-toast'

const InventoryManagement = () => {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    category: 'ingredients',
    current_stock: '',
    min_stock: '',
    max_stock: '',
    unit: '',
    supplier: '',
    cost_per_unit: '',
    notes: ''
  })

  useEffect(() => {
    loadInventory()
  }, [])

  const loadInventory = async () => {
    try {
      setLoading(true)
      const response = await inventoryAPI.getAll()
      setInventory(response.data || [])
    } catch (error) {
      console.error('Error loading inventory:', error)
      toast.error('Error al cargar inventario')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      const itemData = {
        ...formData,
        current_stock: parseFloat(formData.current_stock),
        min_stock: parseFloat(formData.min_stock),
        max_stock: parseFloat(formData.max_stock),
        cost_per_unit: parseFloat(formData.cost_per_unit)
      }

      if (editingItem) {
        await inventoryAPI.update(editingItem.id, itemData)
        toast.success('Producto actualizado')
      } else {
        await inventoryAPI.create(itemData)
        toast.success('Producto agregado al inventario')
      }

      handleCloseDialog()
      loadInventory()
    } catch (error) {
      console.error('Error saving inventory item:', error)
      toast.error('Error al guardar producto')
    }
  }

  const handleEdit = (item) => {
    setEditingItem(item)
    setFormData({
      name: item.name || '',
      category: item.category || 'ingredients',
      current_stock: item.current_stock?.toString() || '',
      min_stock: item.min_stock?.toString() || '',
      max_stock: item.max_stock?.toString() || '',
      unit: item.unit || '',
      supplier: item.supplier || '',
      cost_per_unit: item.cost_per_unit?.toString() || '',
      notes: item.notes || ''
    })
    setDialog(true)
  }

  const handleDelete = async (itemId) => {
    if (window.confirm('¿Estás seguro de que deseas eliminar este producto?')) {
      try {
        await inventoryAPI.delete(itemId)
        toast.success('Producto eliminado')
        loadInventory()
      } catch (error) {
        console.error('Error deleting inventory item:', error)
        toast.error('Error al eliminar producto')
      }
    }
  }

  const handleCloseDialog = () => {
    setDialog(false)
    setEditingItem(null)
    setFormData({
      name: '',
      category: 'ingredients',
      current_stock: '',
      min_stock: '',
      max_stock: '',
      unit: '',
      supplier: '',
      cost_per_unit: '',
      notes: ''
    })
  }

  const getStockStatus = (item) => {
    const percentage = (item.current_stock / item.max_stock) * 100
    if (item.current_stock <= item.min_stock) return 'critical'
    if (percentage <= 25) return 'low'
    if (percentage <= 50) return 'medium'
    return 'good'
  }

  const getStockColor = (status) => {
    switch (status) {
      case 'critical': return 'error'
      case 'low': return 'warning'
      case 'medium': return 'info'
      default: return 'success'
    }
  }

  const getStockLabel = (status) => {
    switch (status) {
      case 'critical': return 'Crítico'
      case 'low': return 'Bajo'
      case 'medium': return 'Medio'
      default: return 'Bueno'
    }
  }

  const getCategoryLabel = (category) => {
    switch (category) {
      case 'ingredients': return 'Ingredientes'
      case 'utensils': return 'Utensilios'
      case 'equipment': return 'Equipos'
      default: return category
    }
  }

  const lowStockItems = inventory.filter(item =>
    getStockStatus(item) === 'critical' || getStockStatus(item) === 'low'
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Gestión de Inventario
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Controla ingredientes, utensilios y equipos
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setDialog(true)}
        >
          Agregar Producto
        </Button>
      </Box>

      {/* Low Stock Alert */}
      {lowStockItems.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }} icon={<Warning />}>
          <Typography variant="body2" fontWeight="bold">
            Atención: {lowStockItems.length} producto(s) con stock bajo o crítico
          </Typography>
          <Typography variant="body2">
            {lowStockItems.map(item => item.name).join(', ')}
          </Typography>
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando inventario...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Producto</TableCell>
                    <TableCell>Categoría</TableCell>
                    <TableCell>Stock Actual</TableCell>
                    <TableCell>Stock Mínimo</TableCell>
                    <TableCell>Stock Máximo</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Proveedor</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {inventory.map((item) => {
                    const stockStatus = getStockStatus(item)
                    const stockPercentage = (item.current_stock / item.max_stock) * 100

                    return (
                      <TableRow key={item.id}>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" fontWeight="bold">
                              {item.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {item.unit && `Unidad: ${item.unit}`}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{getCategoryLabel(item.category)}</TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2">
                              {item.current_stock} {item.unit}
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(stockPercentage, 100)}
                              color={getStockColor(stockStatus)}
                              sx={{ width: 80, height: 4, mt: 0.5 }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell>{item.min_stock} {item.unit}</TableCell>
                        <TableCell>{item.max_stock} {item.unit}</TableCell>
                        <TableCell>
                          <Chip
                            label={getStockLabel(stockStatus)}
                            color={getStockColor(stockStatus)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{item.supplier || 'N/A'}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              size="small"
                              startIcon={<Edit />}
                              onClick={() => handleEdit(item)}
                            >
                              Editar
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDelete(item.id)}
                            >
                              Eliminar
                            </Button>
                          </Box>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {inventory.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">
                          No hay productos en inventario
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
      <Dialog open={dialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingItem ? 'Editar Producto' : 'Agregar Nuevo Producto'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Nombre del Producto"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Categoría</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  label="Categoría"
                >
                  <MenuItem value="ingredients">Ingredientes</MenuItem>
                  <MenuItem value="utensils">Utensilios</MenuItem>
                  <MenuItem value="equipment">Equipos</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Stock Actual"
                type="number"
                value={formData.current_stock}
                onChange={(e) => setFormData({...formData, current_stock: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Stock Mínimo"
                type="number"
                value={formData.min_stock}
                onChange={(e) => setFormData({...formData, min_stock: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Stock Máximo"
                type="number"
                value={formData.max_stock}
                onChange={(e) => setFormData({...formData, max_stock: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Unidad"
                value={formData.unit}
                onChange={(e) => setFormData({...formData, unit: e.target.value})}
                placeholder="kg, unidades, litros, etc."
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Costo por Unidad"
                type="number"
                value={formData.cost_per_unit}
                onChange={(e) => setFormData({...formData, cost_per_unit: e.target.value})}
                InputProps={{
                  startAdornment: '$'
                }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Proveedor"
                value={formData.supplier}
                onChange={(e) => setFormData({...formData, supplier: e.target.value})}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notas"
                multiline
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Información adicional, fechas de vencimiento, etc."
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingItem ? 'Actualizar' : 'Agregar'} Producto
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default InventoryManagement