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
  DialogContentText,
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
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemText,
  InputAdornment,
  Stack,
  Skeleton,
  useTheme,
  useMediaQuery,
  alpha
} from '@mui/material'
import { Add, Edit, Delete, Warning, Inventory, Kitchen, Build, Timeline, ArrowDownward, ArrowUpward, AddBox, Visibility, SwapHoriz, Search, RemoveCircleOutline, Undo, AutoAwesome } from '@mui/icons-material'
import { inventoryAPI, recipesAPI } from '../../services/api'
import { formatCurrency, formatStock, safeFormatCost, formatDateTime } from '../../utils/formatters'
import UnitConverter from '../../components/UnitConverter'
import toast from 'react-hot-toast'

const InventoryManagement = () => {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [inventory, setInventory] = useState([])
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(false)
  const [recipeDialog, setRecipeDialog] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [editingRecipe, setEditingRecipe] = useState(null)
  const [currentTab, setCurrentTab] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [stockStatusFilter, setStockStatusFilter] = useState('all') // all, critical, low, medium, good
  const [nutritionMatchDialog, setNutritionMatchDialog] = useState(false)
  const [nutritionMatches, setNutritionMatches] = useState([])
  const [searchingNutrition, setSearchingNutrition] = useState(false)
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
    notes: '',
    nutrition_info: {
      calories: '',
      proteins: '',
      carbohydrates: '',
      sugars: '',
      fats: '',
      saturated_fats: '',
      trans_fats: '',
      unsaturated_fats: '',
      fiber: '',
      sodium: '',
      cholesterol: '',
      calcium: '',
      iron: '',
      allergens: ''
    }
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
  const [stockDialog, setStockDialog] = useState(false)
  const [stockItem, setStockItem] = useState(null)
  const [stockFormData, setStockFormData] = useState({
    quantity: '',
    cost_per_unit: '',
    supplier: '',
    notes: ''
  })
  const [movementsDialog, setMovementsDialog] = useState(false)
  const [viewingItem, setViewingItem] = useState(null)
  const [itemMovements, setItemMovements] = useState([])
  const [loadingItemMovements, setLoadingItemMovements] = useState(false)
  const [unitConverterOpen, setUnitConverterOpen] = useState(false)
  const [wasteDialog, setWasteDialog] = useState(false)
  const [wasteItem, setWasteItem] = useState(null)
  const [wasteFormData, setWasteFormData] = useState({
    quantity: '',
    reason: '',
    notes: ''
  })
  const [confirmDialog, setConfirmDialog] = useState({ open: false, title: '', message: '', onConfirm: null, severity: 'warning' })

  useEffect(() => {
    loadInventory()
    loadRecipes()
  }, [])

  const loadInventory = async () => {
    try {
      setLoading(true)
      const response = await inventoryAPI.getAll()
      // Handle paginated response format: {items: [], pagination: {}}
      setInventory(response.data.items || response.data || [])
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
      // Handle paginated response format: {items: [], pagination: {}}
      setRecipes(response.data.items || response.data || [])
    } catch (error) {
      console.error('Error loading recipes:', error)
      toast.error('Error al cargar recetas')
    }
  }

  const loadItemMovements = async (itemId, itemName) => {
    try {
      setLoadingItemMovements(true)
      const response = await inventoryAPI.getMovements({ item_id: itemId, limit: 50 })
      // Handle paginated response format: {items: [], pagination: {}}
      setItemMovements(response.data.items || response.data || [])
      setViewingItem({ id: itemId, name: itemName })
      setMovementsDialog(true)
    } catch (error) {
      console.error('Error loading item movements:', error)
      toast.error('Error al cargar movimientos del producto')
    } finally {
      setLoadingItemMovements(false)
    }
  }

  const handleSubmit = async () => {
    try {
      let itemData

      // Prepare nutrition_info object with numeric values (extended fields)
      const nutritionInfo = {
        calories: parseFloat(formData.nutrition_info.calories) || 0,
        proteins: parseFloat(formData.nutrition_info.proteins) || 0,
        carbohydrates: parseFloat(formData.nutrition_info.carbohydrates) || 0,
        sugars: parseFloat(formData.nutrition_info.sugars) || 0,
        fats: parseFloat(formData.nutrition_info.fats) || 0,
        saturated_fats: parseFloat(formData.nutrition_info.saturated_fats) || 0,
        trans_fats: parseFloat(formData.nutrition_info.trans_fats) || 0,
        unsaturated_fats: parseFloat(formData.nutrition_info.unsaturated_fats) || 0,
        fiber: parseFloat(formData.nutrition_info.fiber) || 0,
        sodium: parseFloat(formData.nutrition_info.sodium) || 0,
        cholesterol: parseFloat(formData.nutrition_info.cholesterol) || 0,
        calcium: parseFloat(formData.nutrition_info.calcium) || 0,
        iron: parseFloat(formData.nutrition_info.iron) || 0,
        allergens: formData.nutrition_info.allergens || ''
      }

      if (editingItem) {
        // Al editar, NO incluir campos de stock ni costo - solo datos fijos
        itemData = {
          name: formData.name,
          product_type: formData.product_type,
          category: formData.category,
          min_stock: parseFloat(formData.min_stock),
          max_stock: parseFloat(formData.max_stock),
          unit: formData.unit,
          supplier: formData.supplier,
          notes: formData.notes,
          batch_size: formData.batch_size ? parseFloat(formData.batch_size) : null,
          shelf_life_days: formData.shelf_life_days ? parseInt(formData.shelf_life_days) : null,
          nutrition_info: nutritionInfo
        }
        await inventoryAPI.update(editingItem.id, itemData)
        toast.success('Datos del producto actualizados')
      } else {
        // Al crear, usar valores del formulario para stock y costo inicial
        itemData = {
          ...formData,
          current_stock: parseFloat(formData.current_stock) || 0,
          min_stock: parseFloat(formData.min_stock),
          max_stock: parseFloat(formData.max_stock),
          cost_per_unit: parseFloat(formData.cost_per_unit) || 0,
          batch_size: formData.batch_size ? parseFloat(formData.batch_size) : null,
          shelf_life_days: formData.shelf_life_days ? parseInt(formData.shelf_life_days) : null,
          nutrition_info: nutritionInfo
        }
        await inventoryAPI.create(itemData)
        toast.success('Ingrediente creado exitosamente')
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
    const nutritionInfo = item.nutrition_info || {}
    setFormData({
      name: item.name || '',
      product_type: item.product_type || 'raw_material',
      category: item.category || 'flour',
      current_stock: item.current_stock?.toString() || '', // Solo lectura en edición
      min_stock: item.min_stock?.toString() || '',
      max_stock: item.max_stock?.toString() || '',
      unit: item.unit || '',
      supplier: item.supplier || '',
      cost_per_unit: item.cost_per_unit?.toString() || '', // Solo lectura en edición
      batch_size: item.batch_size?.toString() || '',
      shelf_life_days: item.shelf_life_days?.toString() || '',
      notes: item.notes || '',
      nutrition_info: {
        calories: nutritionInfo.calories?.toString() || '',
        proteins: nutritionInfo.proteins?.toString() || '',
        carbohydrates: nutritionInfo.carbohydrates?.toString() || '',
        sugars: nutritionInfo.sugars?.toString() || '',
        fats: nutritionInfo.fats?.toString() || '',
        saturated_fats: nutritionInfo.saturated_fats?.toString() || '',
        trans_fats: nutritionInfo.trans_fats?.toString() || '',
        unsaturated_fats: nutritionInfo.unsaturated_fats?.toString() || '',
        fiber: nutritionInfo.fiber?.toString() || '',
        sodium: nutritionInfo.sodium?.toString() || '',
        cholesterol: nutritionInfo.cholesterol?.toString() || '',
        calcium: nutritionInfo.calcium?.toString() || '',
        iron: nutritionInfo.iron?.toString() || '',
        allergens: nutritionInfo.allergens || ''
      }
    })
    setDialog(true)
  }

  const handleAddStock = (item) => {
    setStockItem(item)
    setStockFormData({
      quantity: '',
      cost_per_unit: item.cost_per_unit?.toString() || '',
      supplier: item.supplier || '',
      notes: ''
    })
    setStockDialog(true)
  }

  const handleStockSubmit = async () => {
    try {
      if (!stockFormData.quantity || !stockFormData.cost_per_unit) {
        toast.error('Cantidad y costo son requeridos')
        return
      }

      const movementData = {
        item_id: stockItem.id,
        movement_type: 'purchase',
        quantity: parseFloat(stockFormData.quantity),
        cost_per_unit: parseFloat(stockFormData.cost_per_unit),
        reference_type: 'manual_purchase',
        notes: stockFormData.notes || `Compra manual: ${stockFormData.quantity} ${stockItem.unit}`,
        supplier: stockFormData.supplier || stockItem.supplier
      }

      await inventoryAPI.createMovement(movementData)
      toast.success('Stock agregado exitosamente')

      loadInventory()
      handleCloseStockDialog()
    } catch (error) {
      console.error('Error adding stock:', error)
      toast.error('Error al agregar stock')
    }
  }

  const handleCloseStockDialog = () => {
    setStockDialog(false)
    setStockItem(null)
    setStockFormData({
      quantity: '',
      cost_per_unit: '',
      supplier: '',
      notes: ''
    })
  }

  const handleCloseMovementsDialog = () => {
    setMovementsDialog(false)
    setViewingItem(null)
    setItemMovements([])
  }

  const handleWasteOpen = (item) => {
    setWasteItem(item)
    setWasteFormData({
      quantity: '',
      reason: 'damaged',
      notes: ''
    })
    setWasteDialog(true)
  }

  const handleWasteSubmit = async () => {
    try {
      if (!wasteFormData.quantity || parseFloat(wasteFormData.quantity) <= 0) {
        toast.error('Debe ingresar una cantidad válida')
        return
      }

      const wasteQuantity = parseFloat(wasteFormData.quantity)

      if (wasteQuantity > wasteItem.current_stock) {
        toast.error('La cantidad mermada no puede ser mayor al stock actual')
        return
      }

      const reasonLabels = {
        'damaged': 'Desperfecto en producción',
        'expired': 'Producto vencido',
        'contaminated': 'Contaminación',
        'transport_damage': 'Daño durante transporte',
        'other': 'Otro'
      }

      const movementData = {
        item_id: wasteItem.id,
        movement_type: 'waste',
        quantity: wasteQuantity,
        cost_per_unit: wasteItem.cost_per_unit || 0,
        reference_type: 'waste',
        notes: `Merma por ${reasonLabels[wasteFormData.reason]}: ${wasteFormData.notes || 'Sin detalles adicionales'}`,
        waste_reason: wasteFormData.reason
      }

      await inventoryAPI.createMovement(movementData)
      toast.success('Merma registrada exitosamente')

      // Recargar inventario
      loadInventory()

      // Cerrar modal
      setWasteDialog(false)
      setWasteItem(null)
      setWasteFormData({
        quantity: '',
        reason: 'damaged',
        notes: ''
      })
    } catch (error) {
      console.error('Error registering waste:', error)
      toast.error('Error al registrar merma')
    }
  }

  const handleWasteClose = () => {
    setWasteDialog(false)
    setWasteItem(null)
    setWasteFormData({
      quantity: '',
      reason: 'damaged',
      notes: ''
    })
  }

  const handleAutoFillNutrition = async () => {
    if (!formData.name) {
      toast.error('Primero ingresa el nombre del ingrediente')
      return
    }

    setSearchingNutrition(true)
    try {
      const response = await inventoryAPI.nutritionLookup(formData.name)
      const data = response.data

      if (data.found) {
        // Show matches dialog for user to confirm
        const matches = data.matches || [{
          name: data.matched_name || data.ingredient,
          similarity: data.exact_match ? 1.0 : (data.similarity || 0.9),
          nutrition_info: data.nutrition_info
        }]
        setNutritionMatches(matches)
        setNutritionMatchDialog(true)
      } else {
        toast.error(`No se encontraron coincidencias para "${formData.name}". Ingresa los valores manualmente.`)
      }
    } catch (error) {
      console.error('Error searching nutrition:', error)
      toast.error('Error al buscar información nutricional')
    } finally {
      setSearchingNutrition(false)
    }
  }

  const handleSelectNutritionMatch = (match) => {
    const info = match.nutrition_info
    setFormData({
      ...formData,
      nutrition_info: {
        calories: info.calories?.toString() || '',
        proteins: info.proteins?.toString() || '',
        carbohydrates: info.carbohydrates?.toString() || '',
        sugars: info.sugars?.toString() || '',
        fats: info.fats?.toString() || '',
        saturated_fats: info.saturated_fats?.toString() || '',
        trans_fats: info.trans_fats?.toString() || '',
        unsaturated_fats: info.unsaturated_fats?.toString() || '',
        fiber: info.fiber?.toString() || '',
        sodium: info.sodium?.toString() || '',
        cholesterol: info.cholesterol?.toString() || '',
        calcium: info.calcium?.toString() || '',
        iron: info.iron?.toString() || '',
        allergens: info.allergens || ''
      }
    })
    setNutritionMatchDialog(false)
    setNutritionMatches([])
    toast.success(`Información nutricional aplicada de "${match.name}"`)
  }

  const handleRevertWaste = async (movementId) => {
    if (!window.confirm('¿Estás seguro de que deseas revertir esta merma? Esto devolverá el producto al inventario.')) {
      return
    }

    try {
      await inventoryAPI.revertWaste(movementId)
      toast.success('Merma revertida exitosamente')

      // Recargar inventario y movimientos
      loadInventory()
      if (stockItem) {
        loadItemMovements(stockItem.id, stockItem.name)
      }
    } catch (error) {
      console.error('Error reverting waste:', error)
      const errorMsg = error.response?.data?.error || 'Error al revertir merma'
      toast.error(errorMsg)
    }
  }

  const handleDelete = (itemId) => {
    setConfirmDialog({
      open: true,
      title: 'Eliminar producto',
      message: 'Esta acción es irreversible. ¿Confirmas que deseas eliminar este producto del inventario?',
      severity: 'error',
      onConfirm: async () => {
        try {
          await inventoryAPI.delete(itemId)
          toast.success('Producto eliminado')
          loadInventory()
        } catch (error) {
          console.error('Error deleting inventory item:', error)
          toast.error('Error al eliminar producto')
        }
        setConfirmDialog(d => ({ ...d, open: false }))
      }
    })
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
      notes: '',
      nutrition_info: {
        calories: '',
        proteins: '',
        carbohydrates: '',
        sugars: '',
        fats: '',
        saturated_fats: '',
        trans_fats: '',
        unsaturated_fats: '',
        fiber: '',
        sodium: '',
        cholesterol: '',
        calcium: '',
        iron: '',
        allergens: ''
      }
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

      if (editingRecipe) {
        await recipesAPI.update(editingRecipe.id, recipeData)
        toast.success('Receta actualizada exitosamente')
      } else {
        await recipesAPI.create(recipeData)
        toast.success('Receta creada exitosamente')
      }

      setShowRecipeForm(false)
      setEditingRecipe(null)
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
      console.error('Error saving recipe:', error)
      toast.error(`Error al ${editingRecipe ? 'actualizar' : 'crear'} receta`)
    }
  }

  const calculateRecipeEstimatedCost = () => {
    return selectedIngredients.reduce((total, ing) => {
      const quantity = parseFloat(ing.quantity) || 0
      const cost = parseFloat(ing.cost_per_unit) || 0
      return total + (quantity * cost)
    }, 0)
  }

  const handleEditRecipe = (recipe) => {
    setEditingRecipe(recipe)
    setRecipeFormData({
      name: recipe.name,
      description: recipe.description || '',
      output_product_type: recipe.output_product_type,
      output_category: recipe.output_category,
      output_quantity: recipe.output_quantity.toString(),
      output_unit: recipe.output_unit,
      prep_time_minutes: recipe.prep_time_minutes?.toString() || '',
      instructions: recipe.instructions || '',
      ingredients: []
    })
    setSelectedIngredients(recipe.ingredients.map(ing => ({
      item_id: ing.item_id,
      item_name: ing.item_name || '',
      quantity: ing.quantity.toString(),
      unit: ing.unit,
      cost_per_unit: ing.cost_per_unit || 0
    })))
    setShowRecipeForm(true)
  }

  const handleDeleteRecipe = (recipeId) => {
    setConfirmDialog({
      open: true,
      title: 'Eliminar receta',
      message: 'Esta acción es irreversible. ¿Confirmas que deseas eliminar esta receta?',
      severity: 'error',
      onConfirm: async () => {
        try {
          await recipesAPI.delete(recipeId)
          toast.success('Receta eliminada exitosamente')
          loadRecipes()
        } catch (error) {
          console.error('Error deleting recipe:', error)
          toast.error('Error al eliminar receta')
        }
        setConfirmDialog(d => ({ ...d, open: false }))
      }
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
    let filtered = []

    // Filter by tab (product type)
    switch (currentTab) {
      case 0: filtered = inventory.filter(item => item.product_type === 'raw_material'); break
      case 1: filtered = inventory.filter(item => item.product_type === 'intermediate'); break
      case 2: filtered = inventory.filter(item => ['finished_good', 'utensil', 'equipment'].includes(item.product_type)); break
      default: filtered = inventory
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const search = searchTerm.toLowerCase()
      filtered = filtered.filter(item =>
        item.name?.toLowerCase().includes(search) ||
        item.category?.toLowerCase().includes(search) ||
        getCategoryLabel(item.category)?.toLowerCase().includes(search)
      )
    }

    // Filter by stock status
    if (stockStatusFilter !== 'all') {
      filtered = filtered.filter(item => getStockStatus(item) === stockStatusFilter)
    }

    return filtered
  }

  const lowStockItems = inventory.filter(item =>
    getStockStatus(item) === 'critical' || getStockStatus(item) === 'low'
  )

  const filteredInventory = getFilteredInventory()

  // Calculate inventory statistics
  const getInventoryStats = () => {
    const totalValue = inventory.reduce((sum, item) => {
      return sum + (item.current_stock * (item.cost_per_unit || 0))
    }, 0)

    const stockByStatus = {
      critical: inventory.filter(item => getStockStatus(item) === 'critical').length,
      low: inventory.filter(item => getStockStatus(item) === 'low').length,
      medium: inventory.filter(item => getStockStatus(item) === 'medium').length,
      good: inventory.filter(item => getStockStatus(item) === 'good').length
    }

    return {
      totalValue,
      stockByStatus,
      totalItems: inventory.length
    }
  }

  const inventoryStats = getInventoryStats()

  return (
    <Box>
      {/* ── Page Header ── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom sx={{ letterSpacing: '-0.5px' }}>
            Gestión de Inventario
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Controla materias primas, productos intermedios y equipos
          </Typography>
        </Box>
        {isMobile ? (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Gestionar Recetas">
              <IconButton
                aria-label="Gestionar recetas"
                onClick={() => setRecipeDialog(true)}
                sx={{ border: 1, borderColor: 'divider', borderRadius: 2 }}
              >
                <Kitchen />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setDialog(true)}
              size="small"
              aria-label="Agregar producto"
            >
              Agregar
            </Button>
          </Box>
        ) : (
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
        )}
      </Box>

      {/* ── Stats Cards ── */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          {
            label: 'Valor Total',
            value: formatCurrency(inventoryStats.totalValue),
            sub: `${inventoryStats.totalItems} productos`,
            icon: <Inventory />,
            color: 'primary.main',
            bg: 'primary.main',
          },
          {
            label: 'Stock Crítico',
            value: inventoryStats.stockByStatus.critical,
            sub: 'Requiere atención inmediata',
            icon: <Warning />,
            color: 'error.main',
            bg: 'error.main',
          },
          {
            label: 'Stock Bajo',
            value: inventoryStats.stockByStatus.low,
            sub: 'Reabastecer pronto',
            icon: <ArrowDownward />,
            color: 'warning.main',
            bg: 'warning.main',
          },
          {
            label: 'Stock Medio',
            value: inventoryStats.stockByStatus.medium,
            sub: 'Nivel aceptable',
            icon: <Timeline />,
            color: 'info.main',
            bg: 'info.main',
          },
          {
            label: 'Stock Bueno',
            value: inventoryStats.stockByStatus.good,
            sub: 'Nivel óptimo',
            icon: <ArrowUpward />,
            color: 'success.main',
            bg: 'success.main',
          },
        ].map((stat) => (
          <Grid item xs={6} sm={4} md={2.4} key={stat.label}>
            <Card
              elevation={0}
              sx={{
                height: '100%',
                border: '1px solid',
                borderColor: 'divider',
                borderLeft: '4px solid',
                borderLeftColor: stat.color,
                borderRadius: 2,
                transition: 'transform 0.18s ease, box-shadow 0.18s ease',
                '&:hover': { transform: 'translateY(-3px)', boxShadow: 4 },
              }}
            >
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, gap: 1.5 }}>
                  <Box
                    sx={{
                      bgcolor: stat.bg,
                      color: '#fff',
                      p: 0.9,
                      borderRadius: 1.5,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {stat.icon}
                  </Box>
                  <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ lineHeight: 1.3 }}>
                    {stat.label}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight={700} sx={{ mb: 0.25, fontVariantNumeric: 'tabular-nums' }}>
                  {stat.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {stat.sub}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

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

      {/* ── Tabs ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Tabs
          value={currentTab}
          onChange={(e, newTab) => setCurrentTab(newTab)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': { minHeight: 52, fontWeight: 600 },
          }}
        >
          <Tab icon={getTabIcon(0)} label="Materias Primas" iconPosition="start" />
          <Tab icon={getTabIcon(1)} label="Prod. Intermedios" iconPosition="start" />
          <Tab icon={getTabIcon(2)} label="Prod. Terminados" iconPosition="start" />
        </Tabs>
      </Card>

      {/* ── Search and Filters ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Buscar producto"
                placeholder="Nombre o categoría..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search color="action" />
                    </InputAdornment>
                  ),
                }}
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
                  Filtrar por stock:
                </Typography>
                <Chip
                  label="Todos"
                  onClick={() => setStockStatusFilter('all')}
                  color={stockStatusFilter === 'all' ? 'primary' : 'default'}
                  variant={stockStatusFilter === 'all' ? 'filled' : 'outlined'}
                  size="small"
                />
                <Chip
                  label="Crítico"
                  onClick={() => setStockStatusFilter('critical')}
                  color={stockStatusFilter === 'critical' ? 'error' : 'default'}
                  variant={stockStatusFilter === 'critical' ? 'filled' : 'outlined'}
                  size="small"
                />
                <Chip
                  label="Bajo"
                  onClick={() => setStockStatusFilter('low')}
                  color={stockStatusFilter === 'low' ? 'warning' : 'default'}
                  variant={stockStatusFilter === 'low' ? 'filled' : 'outlined'}
                  size="small"
                />
                <Chip
                  label="Medio"
                  onClick={() => setStockStatusFilter('medium')}
                  color={stockStatusFilter === 'medium' ? 'info' : 'default'}
                  variant={stockStatusFilter === 'medium' ? 'filled' : 'outlined'}
                  size="small"
                />
                <Chip
                  label="Bueno"
                  onClick={() => setStockStatusFilter('good')}
                  color={stockStatusFilter === 'good' ? 'success' : 'default'}
                  variant={stockStatusFilter === 'good' ? 'filled' : 'outlined'}
                  size="small"
                />
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {loading ? (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <CardContent>
            <Stack spacing={1.5}>
              {[...Array(5)].map((_, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Skeleton variant="rounded" width={120} height={20} />
                  <Skeleton variant="rounded" width={80} height={20} />
                  <Skeleton variant="rounded" width={100} height={20} />
                  <Skeleton variant="rounded" width={90} height={20} sx={{ ml: 'auto' }} />
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      ) : (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <CardContent sx={{ pb: '12px !important' }}>
            {/* Card header */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              <Typography variant="h6" fontWeight={600}>
                {currentTab === 0 ? 'Materias Primas' : currentTab === 1 ? 'Productos Intermedios' : 'Productos Terminados'}
              </Typography>
              <Chip label={`${filteredInventory.length}`} size="small" variant="outlined" />
            </Box>

            {isMobile ? (
              /* ── Mobile cards ── */
              <Stack spacing={1.5}>
                {filteredInventory.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 6 }}>
                    <Inventory sx={{ fontSize: 56, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                      Sin productos aquí
                    </Typography>
                    <Typography variant="body2" color="text.disabled" sx={{ mb: 3 }}>
                      Agrega el primer producto a esta categoría
                    </Typography>
                    <Button variant="contained" startIcon={<Add />} onClick={() => setDialog(true)}>
                      Agregar Producto
                    </Button>
                  </Box>
                ) : filteredInventory.map((item) => {
                  const stockStatus = getStockStatus(item)
                  const stockPercentage = (item.current_stock / item.max_stock) * 100
                  return (
                    <Card
                      key={item.id}
                      elevation={0}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        borderLeft: '3px solid',
                        borderLeftColor: `${getStockColor(stockStatus)}.main`,
                        borderRadius: 2,
                      }}
                    >
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Box sx={{ flex: 1, mr: 1 }}>
                            <Typography variant="body2" fontWeight={700}>{item.name}</Typography>
                            <Typography variant="caption" color="text.secondary">{getCategoryLabel(item.category)}</Typography>
                          </Box>
                          <Chip label={getStockLabel(stockStatus)} color={getStockColor(stockStatus)} size="small" />
                        </Box>
                        <Box sx={{ mb: 1.5 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">Stock actual</Typography>
                            <Typography variant="caption" fontWeight={600} sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {formatStock(item.current_stock, false)} {item.unit}
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(stockPercentage, 100)}
                            color={getStockColor(stockStatus)}
                            sx={{ height: 5, borderRadius: 3 }}
                          />
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                            Costo: ${item.cost_per_unit?.toLocaleString('es-CL') || '0'} / {item.unit}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          <Button size="small" startIcon={<Edit />} onClick={() => handleEdit(item)} aria-label={`Editar ${item.name}`}>
                            Editar
                          </Button>
                          <Button size="small" color="success" startIcon={<AddBox />} onClick={() => handleAddStock(item)} aria-label={`Agregar stock a ${item.name}`}>
                            + Stock
                          </Button>
                          <Button size="small" color="warning" startIcon={<RemoveCircleOutline />} onClick={() => handleWasteOpen(item)} aria-label={`Registrar merma de ${item.name}`}>
                            Merma
                          </Button>
                          <Button size="small" color="error" startIcon={<Delete />} onClick={() => handleDelete(item.id)} aria-label={`Eliminar ${item.name}`}>
                            Eliminar
                          </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  )
                })}
              </Stack>
            ) : (
              /* ── Desktop table ── */
              <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& th': { fontWeight: 700, bgcolor: (t) => alpha(t.palette.primary.main, 0.06), py: 1.5 } }}>
                      <TableCell>Producto</TableCell>
                      <TableCell>Categoría</TableCell>
                      <TableCell>Stock Actual</TableCell>
                      <TableCell>Mín.</TableCell>
                      <TableCell>Estado</TableCell>
                      <TableCell align="right">Costo/Unidad</TableCell>
                      <TableCell align="center">Acciones</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredInventory.map((item, idx) => {
                      const stockStatus = getStockStatus(item)
                      const stockPercentage = (item.current_stock / item.max_stock) * 100
                      return (
                        <TableRow
                          key={item.id}
                          sx={{
                            bgcolor: idx % 2 === 0 ? 'transparent' : (t) => alpha(t.palette.action.hover, 0.03),
                            '&:hover': { bgcolor: (t) => alpha(t.palette.primary.main, 0.04) },
                            transition: 'background-color 0.15s ease',
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>{item.name}</Typography>
                            <Typography variant="caption" color="text.secondary">{item.unit}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{getCategoryLabel(item.category)}</Typography>
                          </TableCell>
                          <TableCell>
                            <Box>
                              <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                                {formatStock(item.current_stock, false)} {item.unit}
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={Math.min(stockPercentage, 100)}
                                color={getStockColor(stockStatus)}
                                sx={{ width: 90, height: 4, borderRadius: 2, mt: 0.5 }}
                              />
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {item.min_stock} {item.unit}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={getStockLabel(stockStatus)} color={getStockColor(stockStatus)} size="small" />
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" fontWeight={500} sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              ${item.cost_per_unit?.toLocaleString('es-CL') || '0'}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                              <Tooltip title="Editar datos del producto">
                                <IconButton size="small" onClick={() => handleEdit(item)} aria-label={`Editar ${item.name}`}>
                                  <Edit fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Agregar stock">
                                <IconButton size="small" color="success" onClick={() => handleAddStock(item)} aria-label={`Agregar stock a ${item.name}`}>
                                  <AddBox fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Historial de movimientos">
                                <IconButton size="small" color="info" onClick={() => loadItemMovements(item.id, item.name)} aria-label={`Ver movimientos de ${item.name}`}>
                                  <Visibility fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Registrar merma">
                                <IconButton size="small" color="warning" onClick={() => handleWasteOpen(item)} aria-label={`Registrar merma de ${item.name}`}>
                                  <RemoveCircleOutline fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Eliminar producto">
                                <IconButton size="small" color="error" onClick={() => handleDelete(item.id)} aria-label={`Eliminar ${item.name}`}>
                                  <Delete fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                    {filteredInventory.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                          <Inventory sx={{ fontSize: 48, color: 'text.disabled', mb: 1.5 }} />
                          <Typography variant="body1" color="text.secondary" gutterBottom>
                            Sin productos en esta categoría
                          </Typography>
                          <Button variant="outlined" startIcon={<Add />} onClick={() => setDialog(true)} sx={{ mt: 1 }}>
                            Agregar primer producto
                          </Button>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialog} onClose={handleCloseDialog} maxWidth="md" fullWidth fullScreen={isMobile}>
        <DialogTitle>
          {editingItem ? 'Editar Producto' : 'Agregar Nuevo Producto'}
        </DialogTitle>
        <DialogContent>
          {!editingItem && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>Crear Ingrediente:</strong><br />
              • Complete los datos básicos del ingrediente<br />
              • Opcionalmente ingrese stock inicial y costo<br />
              • Luego use "+ Stock" para agregar más inventario<br />
              • El costo promedio se calculará automáticamente con cada compra
            </Alert>
          )}
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
                label={editingItem ? "Stock Actual" : "Stock Inicial"}
                type="number"
                value={formData.current_stock}
                onChange={editingItem ? undefined : (e) => setFormData({...formData, current_stock: e.target.value})}
                InputProps={{
                  readOnly: editingItem ? true : false
                }}
                helperText={editingItem ? "Use el botón '+ Stock' para agregar inventario" : "Cantidad inicial de inventario"}
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
                label={editingItem ? "Costo por Unidad" : "Costo Inicial por Unidad"}
                type="number"
                value={formData.cost_per_unit}
                onChange={editingItem ? undefined : (e) => setFormData({...formData, cost_per_unit: e.target.value})}
                InputProps={{
                  startAdornment: '$',
                  readOnly: editingItem ? true : false
                }}
                helperText={editingItem ? "El costo se actualiza automáticamente con cada compra" : "Costo unitario del stock inicial"}
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

            {/* Nutritional Information Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  📊 Información Nutricional (por 100g/100ml)
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<AutoAwesome />}
                  onClick={handleAutoFillNutrition}
                  disabled={!formData.name}
                  color="secondary"
                >
                  Auto-completar
                </Button>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Estos valores se utilizan para calcular la información nutricional de los productos terminados.
                Haz clic en "Auto-completar" para llenar automáticamente según el nombre del ingrediente.
              </Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Calorías (kcal)"
                type="number"
                value={formData.nutrition_info.calories}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, calories: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Proteínas (g)"
                type="number"
                value={formData.nutrition_info.proteins}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, proteins: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Carbohidratos (g)"
                type="number"
                value={formData.nutrition_info.carbohydrates}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, carbohydrates: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Azúcares (g)"
                type="number"
                value={formData.nutrition_info.sugars}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, sugars: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Grasas Totales (g)"
                type="number"
                value={formData.nutrition_info.fats}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, fats: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Grasas Saturadas (g)"
                type="number"
                value={formData.nutrition_info.saturated_fats}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, saturated_fats: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Grasas Trans (g)"
                type="number"
                value={formData.nutrition_info.trans_fats}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, trans_fats: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Grasas Insaturadas (g)"
                type="number"
                value={formData.nutrition_info.unsaturated_fats}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, unsaturated_fats: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Fibra (g)"
                type="number"
                value={formData.nutrition_info.fiber}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, fiber: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Sodio (mg)"
                type="number"
                value={formData.nutrition_info.sodium}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, sodium: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Colesterol (mg)"
                type="number"
                value={formData.nutrition_info.cholesterol}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, cholesterol: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Calcio (mg)"
                type="number"
                value={formData.nutrition_info.calcium}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, calcium: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                label="Hierro (mg)"
                type="number"
                value={formData.nutrition_info.iron}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, iron: e.target.value }
                })}
                inputProps={{ min: 0, step: 0.1 }}
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Alérgenos"
                value={formData.nutrition_info.allergens}
                onChange={(e) => setFormData({
                  ...formData,
                  nutrition_info: { ...formData.nutrition_info, allergens: e.target.value }
                })}
                size="small"
                placeholder="ej: gluten, lacteos, frutos secos"
                helperText="Separar por coma o punto y coma"
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
      <Dialog open={recipeDialog} onClose={handleCloseRecipeDialog} maxWidth="lg" fullWidth fullScreen={isMobile}>
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
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Tooltip title="Editar receta">
                                <IconButton
                                  size="small"
                                  color="primary"
                                  onClick={() => handleEditRecipe(recipe)}
                                >
                                  <Edit fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Eliminar receta">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleDeleteRecipe(recipe.id)}
                                >
                                  <Delete fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
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
                  {editingRecipe ? 'Editar Receta' : 'Crear Nueva Receta'}
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

                    <Button
                      variant="outlined"
                      startIcon={<SwapHoriz />}
                      onClick={() => setUnitConverterOpen(true)}
                      color="secondary"
                    >
                      🔄 Convertir Unidades
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
                {editingRecipe ? 'Actualizar Receta' : 'Crear Receta'}
              </Button>
            </>
          ) : (
            <Button onClick={handleCloseRecipeDialog}>Cerrar</Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Modal para Agregar Stock con Historial */}
      <Dialog open={stockDialog} onClose={handleCloseStockDialog} maxWidth="lg" fullWidth fullScreen={isMobile}>
        <DialogTitle>
          Agregar Stock - {stockItem?.name}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Alert severity="info" sx={{ mb: 2 }}>
                Esto creará un movimiento de compra y actualizará el costo promedio ponderado del producto.
              </Alert>
            </Grid>

            <Grid item xs={6}>
              <TextField
                label="Cantidad a Agregar"
                type="number"
                value={stockFormData.quantity}
                onChange={(e) => setStockFormData(prev => ({ ...prev, quantity: e.target.value }))}
                fullWidth
                required
                inputProps={{ min: 0, step: 0.01 }}
                helperText={`Unidad: ${stockItem?.unit || ''}`}
              />
            </Grid>

            <Grid item xs={6}>
              <TextField
                label="Costo por Unidad"
                type="number"
                value={stockFormData.cost_per_unit}
                onChange={(e) => setStockFormData(prev => ({ ...prev, cost_per_unit: e.target.value }))}
                fullWidth
                required
                inputProps={{ min: 0, step: 0.01 }}
                helperText="Precio de compra"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Proveedor"
                value={stockFormData.supplier}
                onChange={(e) => setStockFormData(prev => ({ ...prev, supplier: e.target.value }))}
                fullWidth
                placeholder="Nombre del proveedor"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Notas"
                value={stockFormData.notes}
                onChange={(e) => setStockFormData(prev => ({ ...prev, notes: e.target.value }))}
                fullWidth
                multiline
                rows={2}
                placeholder="Observaciones sobre esta compra..."
              />
            </Grid>

            {stockItem && stockFormData.quantity && stockFormData.cost_per_unit && (
              <Grid item xs={12}>
                {(() => {
                  const newQuantity = parseFloat(stockFormData.quantity)
                  const newCostPerUnit = parseFloat(stockFormData.cost_per_unit)
                  const currentStock = stockItem.current_stock
                  const currentCostPerUnit = stockItem.cost_per_unit || 0
                  const totalCost = newQuantity * newCostPerUnit
                  const newTotalStock = currentStock + newQuantity

                  // Cálculo del costo promedio ponderado
                  const currentInventoryValue = currentStock * currentCostPerUnit
                  const newInventoryValue = currentInventoryValue + totalCost
                  const newWeightedAverageCost = newTotalStock > 0 ? newInventoryValue / newTotalStock : 0

                  return (
                    <Alert severity="success">
                      <Typography variant="body2">
                        <strong>Resumen del Movimiento:</strong><br />
                        • Se agregarán {stockFormData.quantity} {stockItem.unit}<br />
                        • Costo unitario de compra: ${formatCurrency(newCostPerUnit)}<br />
                        • Costo total de compra: ${formatCurrency(totalCost)}<br />
                        • Stock actual: {stockItem.current_stock} {stockItem.unit}<br />
                        • Stock después: {formatStock(newTotalStock)} {stockItem.unit}<br />
                        <br />
                        <strong>Cálculo Costo Promedio Ponderado:</strong><br />
                        • Valor inventario actual: ${formatCurrency(currentInventoryValue)} ({formatStock(currentStock)} × ${formatCurrency(currentCostPerUnit)})<br />
                        • Valor nueva compra: ${formatCurrency(totalCost)} ({formatStock(newQuantity)} × ${formatCurrency(newCostPerUnit)})<br />
                        • Valor total inventario: ${formatCurrency(newInventoryValue)}<br />
                        • <strong>Nuevo costo promedio: ${formatCurrency(newWeightedAverageCost)} por {stockItem.unit}</strong>
                      </Typography>
                    </Alert>
                  )
                })()}
              </Grid>
            )}

          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseStockDialog}>
            Cancelar
          </Button>
          <Button
            onClick={handleStockSubmit}
            variant="contained"
            color="success"
            disabled={!stockFormData.quantity || !stockFormData.cost_per_unit}
          >
            Agregar Stock
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal de Registro de Mermas */}
      <Dialog open={wasteDialog} onClose={handleWasteClose} maxWidth="md" fullWidth fullScreen={isMobile}>
        <DialogTitle>
          Registrar Merma - {wasteItem?.name}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                <strong>Registro de Merma:</strong><br />
                Este movimiento reducirá el stock del producto y registrará el costo de la merma.
              </Alert>
            </Grid>

            <Grid item xs={12}>
              <Alert severity="info" sx={{ mb: 2 }}>
                <strong>Stock Actual:</strong> {wasteItem?.current_stock} {wasteItem?.unit}<br />
                <strong>Costo por Unidad:</strong> ${wasteItem?.cost_per_unit?.toLocaleString('es-CL') || '0'}
              </Alert>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Cantidad Mermada"
                type="number"
                value={wasteFormData.quantity}
                onChange={(e) => setWasteFormData(prev => ({ ...prev, quantity: e.target.value }))}
                fullWidth
                required
                inputProps={{ min: 0, step: 0.01, max: wasteItem?.current_stock }}
                helperText={`Unidad: ${wasteItem?.unit || ''} (Máximo: ${wasteItem?.current_stock || 0})`}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Razón de la Merma</InputLabel>
                <Select
                  value={wasteFormData.reason}
                  onChange={(e) => setWasteFormData(prev => ({ ...prev, reason: e.target.value }))}
                  label="Razón de la Merma"
                >
                  <MenuItem value="damaged">Desperfecto en producción</MenuItem>
                  <MenuItem value="expired">Producto vencido</MenuItem>
                  <MenuItem value="contaminated">Contaminación</MenuItem>
                  <MenuItem value="transport_damage">Daño durante transporte</MenuItem>
                  <MenuItem value="other">Otro</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                label="Notas / Detalles"
                value={wasteFormData.notes}
                onChange={(e) => setWasteFormData(prev => ({ ...prev, notes: e.target.value }))}
                fullWidth
                multiline
                rows={3}
                placeholder="Detalles adicionales sobre la merma..."
              />
            </Grid>

            {wasteItem && wasteFormData.quantity && parseFloat(wasteFormData.quantity) > 0 && (
              <Grid item xs={12}>
                {(() => {
                  const wasteQuantity = parseFloat(wasteFormData.quantity)
                  const wasteCost = wasteQuantity * (wasteItem.cost_per_unit || 0)
                  const newStock = wasteItem.current_stock - wasteQuantity

                  return (
                    <Alert severity="error">
                      <Typography variant="body2">
                        <strong>Resumen de la Merma:</strong><br />
                        • Cantidad a mermar: {wasteFormData.quantity} {wasteItem.unit}<br />
                        • Costo unitario: ${formatCurrency(wasteItem.cost_per_unit || 0)}<br />
                        • <strong>Costo total de la merma: ${formatCurrency(wasteCost)}</strong><br />
                        <br />
                        • Stock actual: {wasteItem.current_stock} {wasteItem.unit}<br />
                        • <strong>Stock después: {formatStock(newStock, false)} {wasteItem.unit}</strong>
                      </Typography>
                    </Alert>
                  )
                })()}
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleWasteClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleWasteSubmit}
            variant="contained"
            color="warning"
            disabled={!wasteFormData.quantity || parseFloat(wasteFormData.quantity) <= 0}
          >
            Registrar Merma
          </Button>
        </DialogActions>
      </Dialog>

      {/* Unit Converter Dialog */}
      <UnitConverter
        open={unitConverterOpen}
        onClose={() => setUnitConverterOpen(false)}
      />

      {/* Nutrition Match Selection Dialog */}
      <Dialog
        open={nutritionMatchDialog}
        onClose={() => {
          setNutritionMatchDialog(false)
          setNutritionMatches([])
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoAwesome color="primary" />
          Coincidencias encontradas para "{formData.name}"
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Selecciona el ingrediente que mejor coincida para aplicar su información nutricional:
          </Typography>
          <List>
            {nutritionMatches.map((match, index) => (
              <ListItem
                key={index}
                sx={{
                  border: '1px solid',
                  borderColor: index === 0 ? 'primary.main' : 'divider',
                  borderRadius: 1,
                  mb: 1,
                  bgcolor: index === 0 ? 'primary.50' : 'transparent',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => handleSelectNutritionMatch(match)}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight={index === 0 ? 600 : 400}>
                        {match.name}
                      </Typography>
                      {index === 0 && (
                        <Chip label="Mejor coincidencia" size="small" color="primary" />
                      )}
                      <Chip
                        label={`${Math.round((match.similarity || 0.9) * 100)}% similar`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" component="div">
                        {match.nutrition_info?.calories || 0} kcal |
                        Prot: {match.nutrition_info?.proteins || 0}g |
                        Grasas: {match.nutrition_info?.fats || 0}g |
                        Carb: {match.nutrition_info?.carbohydrates || 0}g
                      </Typography>
                      {match.nutrition_info?.allergens && (
                        <Typography variant="caption" color="warning.main">
                          Alérgenos: {match.nutrition_info.allergens}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setNutritionMatchDialog(false)
            setNutritionMatches([])
          }}>
            Cancelar
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Movements History Dialog ── */}
      <Dialog
        open={movementsDialog}
        onClose={handleCloseMovementsDialog}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 700 }}>
          Historial de Movimientos — {viewingItem?.name}
        </DialogTitle>
        <DialogContent>
          {loadingItemMovements ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <LinearProgress sx={{ width: '100%' }} />
            </Box>
          ) : itemMovements.length === 0 ? (
            <Alert severity="info">No hay movimientos registrados para este producto.</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell align="right">Cantidad</TableCell>
                    <TableCell align="right">Costo/Unidad</TableCell>
                    <TableCell align="right">Stock Antes</TableCell>
                    <TableCell align="right">Stock Después</TableCell>
                    <TableCell align="right">Costo Promedio</TableCell>
                    <TableCell>Notas</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {itemMovements.map((movement, index) => (
                    <TableRow key={movement.id || index}>
                      <TableCell>
                        {(() => {
                          const [year, month, day] = movement.created_at.split('T')[0].split('-')
                          return `${day}-${month}-${year}`
                        })()}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={movement.movement_type || 'compra'}
                          color={movement.movement_type === 'purchase' ? 'success' : movement.movement_type === 'waste' ? 'error' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" color={movement.quantity > 0 ? 'success.main' : 'error.main'}>
                          {movement.quantity > 0 ? '+' : ''}{movement.quantity} {movement.unit}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{formatCurrency(movement.cost_per_unit)}</TableCell>
                      <TableCell align="right">{movement.stock_before ?? 'N/A'}</TableCell>
                      <TableCell align="right">{movement.stock_after ?? 'N/A'}</TableCell>
                      <TableCell align="right">{formatCurrency(movement.avg_cost_after)}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">{movement.notes || '—'}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseMovementsDialog}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* ── Confirm Dialog ── */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog(d => ({ ...d, open: false }))}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 700 }}>{confirmDialog.title}</DialogTitle>
        <DialogContent>
          <DialogContentText>{confirmDialog.message}</DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setConfirmDialog(d => ({ ...d, open: false }))}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            color={confirmDialog.severity === 'error' ? 'error' : 'warning'}
            onClick={confirmDialog.onConfirm}
            autoFocus
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  )
}

export default InventoryManagement