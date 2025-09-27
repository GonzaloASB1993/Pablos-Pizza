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
  LinearProgress,
  Tabs,
  Tab,
  Tooltip,
  IconButton
} from '@mui/material'
import { Add, Edit, Delete, Warning, Inventory, Kitchen, Build } from '@mui/icons-material'
import { inventoryAPI, recipesAPI } from '../../services/api'
import toast from 'react-hot-toast'

const InventoryManagement = () => {
  const [inventory, setInventory] = useState([])
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(false)
  const [recipeDialog, setRecipeDialog] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [editingRecipe, setEditingRecipe] = useState(null)
  const [currentTab, setCurrentTab] = useState(0)
  const [formData, setFormData] = useState({
    name: '',
    product_type: 'raw_material',
    category: 'flour',
    current_stock: '',
    min_stock: '',
    max_stock: '',
    unit: '',
    supplier: '',
    cost_per_unit: '',
    batch_size: '',
    shelf_life_days: '',
    notes: ''
  })
  const [recipeFormData, setRecipeFormData] = useState({
    name: '',
    description: '',
    output_product_type: 'intermediate',
    output_category: 'dough',
    output_quantity: '',
    output_unit: '',
    prep_time_minutes: '',
    instructions: '',
    ingredients: []
  })
  const [showRecipeForm, setShowRecipeForm] = useState(false)
  const [selectedIngredients, setSelectedIngredients] = useState([])

  useEffect(() => {
    loadInventory()
    loadRecipes()
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

  const loadRecipes = async () => {
    try {
      const response = await recipesAPI.getAll()
      setRecipes(response.data || [])
    } catch (error) {
      console.error('Error loading recipes:', error)
      toast.error('Error al cargar recetas')
    }
  }

  const handleSubmit = async () => {
    try {
      const itemData = {
        ...formData,
        current_stock: parseFloat(formData.current_stock),
        min_stock: parseFloat(formData.min_stock),
        max_stock: parseFloat(formData.max_stock),
        cost_per_unit: parseFloat(formData.cost_per_unit),
        batch_size: formData.batch_size ? parseFloat(formData.batch_size) : null,
        shelf_life_days: formData.shelf_life_days ? parseInt(formData.shelf_life_days) : null
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
      product_type: item.product_type || 'raw_material',
      category: item.category || 'flour',
      current_stock: item.current_stock?.toString() || '',
      min_stock: item.min_stock?.toString() || '',
      max_stock: item.max_stock?.toString() || '',
      unit: item.unit || '',
      supplier: item.supplier || '',
      cost_per_unit: item.cost_per_unit?.toString() || '',
      batch_size: item.batch_size?.toString() || '',
      shelf_life_days: item.shelf_life_days?.toString() || '',
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
      product_type: 'raw_material',
      category: 'flour',
      current_stock: '',
      min_stock: '',
      max_stock: '',
      unit: '',
      supplier: '',
      cost_per_unit: '',
      batch_size: '',
      shelf_life_days: '',
      notes: ''
    })
  }

  const handleCloseRecipeDialog = () => {
    setRecipeDialog(false)
    setEditingRecipe(null)
    setShowRecipeForm(false)
    setSelectedIngredients([])
    setRecipeFormData({
      name: '',
      description: '',
      output_product_type: 'intermediate',
      output_category: 'dough',
      output_quantity: '',
      output_unit: '',
      prep_time_minutes: '',
      instructions: '',
      ingredients: []
    })
  }

  const handleAddIngredient = () => {
    setSelectedIngredients([...selectedIngredients, {
      item_id: '',
      item_name: '',
      quantity: '',
      unit: '',
      cost_per_unit: 0
    }])
  }

  const handleRemoveIngredient = (index) => {
    const newIngredients = selectedIngredients.filter((_, i) => i !== index)
    setSelectedIngredients(newIngredients)
  }

  const handleIngredientChange = (index, field, value) => {
    const newIngredients = [...selectedIngredients]
    newIngredients[index][field] = value

    // If selecting an item, auto-fill name and cost
    if (field === 'item_id' && value) {
      const selectedItem = inventory.find(item => item.id === value)
      if (selectedItem) {
        newIngredients[index].item_name = selectedItem.name
        newIngredients[index].unit = selectedItem.unit
        newIngredients[index].cost_per_unit = selectedItem.cost_per_unit
      }
    }

    setSelectedIngredients(newIngredients)
  }

  const handleSubmitRecipe = async () => {
    try {
      const recipeData = {
        ...recipeFormData,
        output_quantity: parseFloat(recipeFormData.output_quantity),
        prep_time_minutes: parseInt(recipeFormData.prep_time_minutes) || null,
        ingredients: selectedIngredients.map(ing => ({
          item_id: ing.item_id,
          quantity: parseFloat(ing.quantity),
          unit: ing.unit
        }))
      }

      await recipesAPI.create(recipeData)
      toast.success('Receta creada exitosamente')

      setShowRecipeForm(false)
      setSelectedIngredients([])
      setRecipeFormData({
        name: '',
        description: '',
        output_product_type: 'intermediate',
        output_category: 'dough',
        output_quantity: '',
        output_unit: '',
        prep_time_minutes: '',
        instructions: '',
        ingredients: []
      })
      loadRecipes()
    } catch (error) {
      console.error('Error creating recipe:', error)
      toast.error('Error al crear receta')
    }
  }

  const calculateRecipeEstimatedCost = () => {
    return selectedIngredients.reduce((total, ing) => {
      const quantity = parseFloat(ing.quantity) || 0
      const cost = parseFloat(ing.cost_per_unit) || 0
      return total + (quantity * cost)
    }, 0)
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

  const getProductTypeLabel = (type) => {
    switch (type) {
      case 'raw_material': return 'Materia Prima'
      case 'intermediate': return 'Producto Intermedio'
      case 'finished_good': return 'Producto Terminado'
      case 'utensil': return 'Utensilio'
      case 'equipment': return 'Equipo'
      default: return type
    }
  }

  const getCategoryLabel = (category) => {
    const labels = {
      // Raw Materials
      flour: 'Harinas',
      dairy: 'Lácteos',
      proteins: 'Proteínas',
      vegetables: 'Vegetales',
      spices: 'Especias',
      oils: 'Aceites',
      beverages: 'Bebidas',
      packaging: 'Empaques',
      // Intermediate Products
      dough: 'Masas',
      sauces: 'Salsas',
      mixes: 'Mezclas',
      // Finished Goods
      pizzas: 'Pizzas',
      desserts: 'Postres',
      // Utensils & Equipment
      utensils: 'Utensilios',
      equipment: 'Equipos'
    }
    return labels[category] || category
  }

  const getTabIcon = (index) => {
    switch (index) {
      case 0: return <Inventory />
      case 1: return <Kitchen />
      case 2: return <Build />
      default: return <Inventory />
    }
  }

  const getFilteredInventory = () => {
    switch (currentTab) {
      case 0: return inventory.filter(item => item.product_type === 'raw_material')
      case 1: return inventory.filter(item => item.product_type === 'intermediate')
      case 2: return inventory.filter(item => ['finished_good', 'utensil', 'equipment'].includes(item.product_type))
      default: return inventory
    }
  }

  const lowStockItems = inventory.filter(item =>
    getStockStatus(item) === 'critical' || getStockStatus(item) === 'low'
  )

  const filteredInventory = getFilteredInventory()

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Gestión de Inventario
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Controla materias primas, productos intermedios y equipos
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Kitchen />}
            onClick={() => setRecipeDialog(true)}
          >
            Gestionar Recetas
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setDialog(true)}
          >
            Agregar Producto
          </Button>
        </Box>
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

      {/* Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs
          value={currentTab}
          onChange={(e, newTab) => setCurrentTab(newTab)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab
            icon={getTabIcon(0)}
            label="Materias Primas"
            iconPosition="start"
          />
          <Tab
            icon={getTabIcon(1)}
            label="Productos Intermedios"
            iconPosition="start"
          />
          <Tab
            icon={getTabIcon(2)}
            label="Productos Terminados"
            iconPosition="start"
          />
        </Tabs>
      </Card>

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando inventario...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              {currentTab === 0 ? 'Materias Primas' :
               currentTab === 1 ? 'Productos Intermedios' : 'Productos Terminados'}
              <Chip
                label={`${filteredInventory.length} items`}
                size="small"
                sx={{ ml: 2 }}
              />
            </Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Producto</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell>Categoría</TableCell>
                    <TableCell>Stock Actual</TableCell>
                    <TableCell>Stock Mínimo</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Costo/Unidad</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredInventory.map((item) => {
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
                        <TableCell>
                          <Chip
                            label={getProductTypeLabel(item.product_type)}
                            size="small"
                            color={item.product_type === 'raw_material' ? 'primary' :
                                   item.product_type === 'intermediate' ? 'secondary' : 'default'}
                          />
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
                        <TableCell>
                          <Chip
                            label={getStockLabel(stockStatus)}
                            color={getStockColor(stockStatus)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          ${item.cost_per_unit?.toLocaleString('es-CL') || '0'}
                        </TableCell>
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
                  {filteredInventory.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">
                          No hay productos en esta categoría
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
                <InputLabel>Tipo de Producto</InputLabel>
                <Select
                  value={formData.product_type}
                  onChange={(e) => setFormData({...formData, product_type: e.target.value})}
                  label="Tipo de Producto"
                >
                  <MenuItem value="raw_material">Materia Prima</MenuItem>
                  <MenuItem value="intermediate">Producto Intermedio</MenuItem>
                  <MenuItem value="finished_good">Producto Terminado</MenuItem>
                  <MenuItem value="utensil">Utensilio</MenuItem>
                  <MenuItem value="equipment">Equipo</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Categoría</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  label="Categoría"
                >
                  {/* Raw Materials */}
                  <MenuItem value="flour">Harinas</MenuItem>
                  <MenuItem value="dairy">Lácteos</MenuItem>
                  <MenuItem value="proteins">Proteínas</MenuItem>
                  <MenuItem value="vegetables">Vegetales</MenuItem>
                  <MenuItem value="spices">Especias</MenuItem>
                  <MenuItem value="oils">Aceites</MenuItem>
                  <MenuItem value="beverages">Bebidas</MenuItem>
                  <MenuItem value="packaging">Empaques</MenuItem>
                  {/* Intermediate Products */}
                  <MenuItem value="dough">Masas</MenuItem>
                  <MenuItem value="sauces">Salsas</MenuItem>
                  <MenuItem value="mixes">Mezclas</MenuItem>
                  {/* Finished Goods */}
                  <MenuItem value="pizzas">Pizzas</MenuItem>
                  <MenuItem value="desserts">Postres</MenuItem>
                  {/* Utensils & Equipment */}
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
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Proveedor"
                value={formData.supplier}
                onChange={(e) => setFormData({...formData, supplier: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Tamaño de Lote"
                type="number"
                value={formData.batch_size}
                onChange={(e) => setFormData({...formData, batch_size: e.target.value})}
                placeholder="Opcional - para productos que se producen en lotes"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Vida Útil (días)"
                type="number"
                value={formData.shelf_life_days}
                onChange={(e) => setFormData({...formData, shelf_life_days: e.target.value})}
                placeholder="Opcional - para productos perecederos"
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

      {/* Recipe Management Dialog */}
      <Dialog open={recipeDialog} onClose={handleCloseRecipeDialog} maxWidth="lg" fullWidth>
        <DialogTitle>
          Gestión de Recetas
        </DialogTitle>
        <DialogContent>
          {!showRecipeForm ? (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Recetas Existentes
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => setShowRecipeForm(true)}
                  disabled={inventory.length === 0}
                >
                  Nueva Receta
                </Button>
              </Box>

              {inventory.length === 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  Necesitas tener ingredientes en inventario antes de crear recetas.
                </Alert>
              )}

              {recipes.length > 0 ? (
                <TableContainer component={Paper} sx={{ mb: 3 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Nombre</TableCell>
                        <TableCell>Descripción</TableCell>
                        <TableCell>Produce</TableCell>
                        <TableCell>Costo por Lote</TableCell>
                        <TableCell>Costo por Unidad</TableCell>
                        <TableCell>Acciones</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recipes.map((recipe) => (
                        <TableRow key={recipe.id}>
                          <TableCell>
                            <Typography variant="body2" fontWeight="bold">
                              {recipe.name}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {recipe.description || 'Sin descripción'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {recipe.output_quantity} {recipe.output_unit}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {getCategoryLabel(recipe.output_category)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              ${recipe.cost_per_batch?.toLocaleString('es-CL') || '0'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              ${recipe.cost_per_unit?.toLocaleString('es-CL') || '0'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Tooltip title="Ver ingredientes">
                              <IconButton size="small">
                                <Inventory fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info" sx={{ mb: 3 }}>
                  No hay recetas creadas aún. Las recetas permiten convertir materias primas en productos intermedios.
                </Alert>
              )}
            </>
          ) : (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Button
                  startIcon={<Kitchen />}
                  onClick={() => setShowRecipeForm(false)}
                  sx={{ mr: 2 }}
                >
                  Volver a Recetas
                </Button>
                <Typography variant="h6">
                  Crear Nueva Receta
                </Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Nombre de la Receta"
                    value={recipeFormData.name}
                    onChange={(e) => setRecipeFormData({...recipeFormData, name: e.target.value})}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Tiempo de Preparación (minutos)"
                    type="number"
                    value={recipeFormData.prep_time_minutes}
                    onChange={(e) => setRecipeFormData({...recipeFormData, prep_time_minutes: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Descripción"
                    value={recipeFormData.description}
                    onChange={(e) => setRecipeFormData({...recipeFormData, description: e.target.value})}
                    multiline
                    rows={2}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Tipo de Producto</InputLabel>
                    <Select
                      value={recipeFormData.output_product_type}
                      onChange={(e) => setRecipeFormData({...recipeFormData, output_product_type: e.target.value})}
                      label="Tipo de Producto"
                    >
                      <MenuItem value="intermediate">Producto Intermedio</MenuItem>
                      <MenuItem value="finished_good">Producto Terminado</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Categoría</InputLabel>
                    <Select
                      value={recipeFormData.output_category}
                      onChange={(e) => setRecipeFormData({...recipeFormData, output_category: e.target.value})}
                      label="Categoría"
                    >
                      <MenuItem value="dough">Masas</MenuItem>
                      <MenuItem value="sauces">Salsas</MenuItem>
                      <MenuItem value="mixes">Mezclas</MenuItem>
                      <MenuItem value="pizzas">Pizzas</MenuItem>
                      <MenuItem value="desserts">Postres</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Cantidad que Produce"
                    type="number"
                    value={recipeFormData.output_quantity}
                    onChange={(e) => setRecipeFormData({...recipeFormData, output_quantity: e.target.value})}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Unidad de Salida"
                    value={recipeFormData.output_unit}
                    onChange={(e) => setRecipeFormData({...recipeFormData, output_unit: e.target.value})}
                    placeholder="kg, unidades, porciones, etc."
                    required
                  />
                </Grid>

                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      Ingredientes
                    </Typography>
                    <Button
                      variant="outlined"
                      startIcon={<Add />}
                      onClick={handleAddIngredient}
                      disabled={inventory.length === 0}
                    >
                      Agregar Ingrediente
                    </Button>
                  </Box>

                  {selectedIngredients.map((ingredient, index) => (
                    <Card key={index} sx={{ mb: 2, p: 2 }}>
                      <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} sm={4}>
                          <FormControl fullWidth>
                            <InputLabel>Ingrediente</InputLabel>
                            <Select
                              value={ingredient.item_id}
                              onChange={(e) => handleIngredientChange(index, 'item_id', e.target.value)}
                              label="Ingrediente"
                            >
                              {inventory.map((item) => (
                                <MenuItem key={item.id} value={item.id}>
                                  {item.name} ({item.unit})
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={3}>
                          <TextField
                            fullWidth
                            label="Cantidad"
                            type="number"
                            value={ingredient.quantity}
                            onChange={(e) => handleIngredientChange(index, 'quantity', e.target.value)}
                            inputProps={{ step: 0.01 }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={2}>
                          <TextField
                            fullWidth
                            label="Unidad"
                            value={ingredient.unit}
                            InputProps={{ readOnly: true }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={2}>
                          <TextField
                            fullWidth
                            label="Costo/Unidad"
                            value={`$${ingredient.cost_per_unit?.toLocaleString('es-CL') || '0'}`}
                            InputProps={{ readOnly: true }}
                          />
                        </Grid>
                        <Grid item xs={12} sm={1}>
                          <IconButton
                            color="error"
                            onClick={() => handleRemoveIngredient(index)}
                          >
                            <Delete />
                          </IconButton>
                        </Grid>
                      </Grid>
                    </Card>
                  ))}

                  {selectedIngredients.length > 0 && (
                    <Alert severity="success" sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        <strong>Costo Estimado por Lote:</strong> ${calculateRecipeEstimatedCost().toLocaleString('es-CL')}
                      </Typography>
                      {recipeFormData.output_quantity && (
                        <Typography variant="body2">
                          <strong>Costo por Unidad:</strong> ${(calculateRecipeEstimatedCost() / parseFloat(recipeFormData.output_quantity)).toLocaleString('es-CL')}
                        </Typography>
                      )}
                    </Alert>
                  )}
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Instrucciones"
                    value={recipeFormData.instructions}
                    onChange={(e) => setRecipeFormData({...recipeFormData, instructions: e.target.value})}
                    multiline
                    rows={4}
                    placeholder="Describe los pasos para preparar esta receta..."
                  />
                </Grid>
              </Grid>
            </>
          )}
        </DialogContent>
        <DialogActions>
          {showRecipeForm ? (
            <>
              <Button onClick={() => setShowRecipeForm(false)}>Cancelar</Button>
              <Button
                onClick={handleSubmitRecipe}
                variant="contained"
                disabled={!recipeFormData.name || !recipeFormData.output_quantity || selectedIngredients.length === 0}
              >
                Crear Receta
              </Button>
            </>
          ) : (
            <Button onClick={handleCloseRecipeDialog}>Cerrar</Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default InventoryManagement