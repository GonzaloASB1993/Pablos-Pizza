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
  List,
  ListItem,
  ListItemText,
  Divider,
  Tooltip,
  IconButton
} from '@mui/material'
import {
  Add,
  PlayArrow,
  CheckCircle,
  Cancel,
  Visibility,
  Factory,
  Schedule,
  AttachMoney,
  Label,
  Print,
  Download
} from '@mui/icons-material'
import { productionBatchesAPI, recipesAPI, inventoryAPI } from '../../services/api'
import toast from 'react-hot-toast'

const ProductionManagement = () => {
  const [batches, setBatches] = useState([])
  const [recipes, setRecipes] = useState([])
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(false)
  const [detailDialog, setDetailDialog] = useState(false)
  const [selectedBatch, setSelectedBatch] = useState(null)
  const [formData, setFormData] = useState({
    recipe_id: '',
    quantity_to_produce: '',
    notes: ''
  })
  const [labelDialog, setLabelDialog] = useState(false)
  const [labelData, setLabelData] = useState(null)
  const [loadingLabel, setLoadingLabel] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [batchesRes, recipesRes, inventoryRes] = await Promise.all([
        productionBatchesAPI.getAll(),
        recipesAPI.getAll(),
        inventoryAPI.getAll()
      ])

      // Handle paginated response format: {items: [], pagination: {}}
      setBatches(batchesRes.data.items || batchesRes.data || [])
      setRecipes(recipesRes.data.items || recipesRes.data || [])
      setInventory(inventoryRes.data.items || inventoryRes.data || [])
    } catch (error) {
      console.error('Error loading data:', error)
      toast.error('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      const batchData = {
        ...formData,
        quantity_to_produce: parseFloat(formData.quantity_to_produce)
      }

      await productionBatchesAPI.create(batchData)
      toast.success('Lote de producción creado')

      handleCloseDialog()
      loadData()
    } catch (error) {
      console.error('Error creating batch:', error)
      toast.error('Error al crear lote de producción')
    }
  }

  const handleStartBatch = async (batchId) => {
    try {
      await productionBatchesAPI.updateStatus(batchId, 'in_progress')
      toast.success('Lote iniciado')
      loadData()
    } catch (error) {
      console.error('Error starting batch:', error)
      toast.error('Error al iniciar lote')
    }
  }

  const handleCompleteBatch = async (batchId) => {
    try {
      await productionBatchesAPI.updateStatus(batchId, 'completed')
      toast.success('Lote completado - Inventario actualizado automáticamente')
      loadData()
    } catch (error) {
      console.error('Error completing batch:', error)
      toast.error('Error al completar lote')
    }
  }

  const handleCancelBatch = async (batchId) => {
    if (window.confirm('¿Estás seguro de que deseas cancelar este lote?')) {
      try {
        await productionBatchesAPI.updateStatus(batchId, 'cancelled')
        toast.success('Lote cancelado')
        loadData()
      } catch (error) {
        console.error('Error cancelling batch:', error)
        toast.error('Error al cancelar lote')
      }
    }
  }

  const handleViewDetails = (batch) => {
    setSelectedBatch(batch)
    setDetailDialog(true)
  }

  const handleCloseDialog = () => {
    setDialog(false)
    setFormData({
      recipe_id: '',
      quantity_to_produce: '',
      notes: ''
    })
  }

  const handleCloseDetailDialog = () => {
    setDetailDialog(false)
    setSelectedBatch(null)
  }

  const handleGenerateLabel = async (batch) => {
    try {
      setLoadingLabel(true)
      setLabelDialog(true)
      const response = await productionBatchesAPI.getLabel(batch.id)
      setLabelData(response.data)
    } catch (error) {
      console.error('Error generating label:', error)
      toast.error('Error al generar etiqueta')
      setLabelDialog(false)
    } finally {
      setLoadingLabel(false)
    }
  }

  const handleCloseLabelDialog = () => {
    setLabelDialog(false)
    setLabelData(null)
  }

  const handlePrintLabel = () => {
    const printWindow = window.open('', '_blank')
    const labelContent = document.getElementById('label-content')
    if (labelContent && printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Etiqueta - ${labelData?.product_name || 'Producto'}</title>
          <style>
            @page { size: 10cm 15cm; margin: 5mm; }
            body {
              font-family: Arial, sans-serif;
              margin: 0;
              padding: 10px;
              font-size: 11px;
            }
            .label-container {
              border: 2px solid #333;
              padding: 10px;
              max-width: 9cm;
            }
            .product-name {
              font-size: 16px;
              font-weight: bold;
              text-align: center;
              margin-bottom: 8px;
              border-bottom: 1px solid #333;
              padding-bottom: 5px;
            }
            .company-name {
              font-size: 14px;
              font-weight: bold;
              text-align: center;
              margin-bottom: 10px;
            }
            .nutrition-table {
              width: 100%;
              border-collapse: collapse;
              margin: 10px 0;
              font-size: 10px;
            }
            .nutrition-table th, .nutrition-table td {
              border: 1px solid #333;
              padding: 3px 5px;
              text-align: left;
            }
            .nutrition-table th {
              background: #f0f0f0;
            }
            .info-row {
              display: flex;
              justify-content: space-between;
              margin: 3px 0;
              font-size: 10px;
            }
            .barcode {
              text-align: center;
              margin: 10px 0;
              font-family: 'Libre Barcode 128', monospace;
              font-size: 40px;
            }
            .barcode-number {
              text-align: center;
              font-size: 10px;
              margin-top: -5px;
            }
            .batch-info {
              background: #f5f5f5;
              padding: 5px;
              margin: 5px 0;
              font-size: 10px;
            }
          </style>
        </head>
        <body>
          ${labelContent.innerHTML}
        </body>
        </html>
      `)
      printWindow.document.close()
      printWindow.focus()
      setTimeout(() => {
        printWindow.print()
        printWindow.close()
      }, 250)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'default'
      case 'in_progress': return 'primary'
      case 'completed': return 'success'
      case 'cancelled': return 'error'
      default: return 'default'
    }
  }

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending': return 'Pendiente'
      case 'in_progress': return 'En Proceso'
      case 'completed': return 'Completado'
      case 'cancelled': return 'Cancelado'
      default: return status
    }
  }

  const getSelectedRecipe = () => {
    return recipes.find(r => r.id === formData.recipe_id)
  }

  const calculateBatchCost = () => {
    const recipe = getSelectedRecipe()
    if (!recipe || !formData.quantity_to_produce) return 0
    return recipe.cost_per_batch * parseFloat(formData.quantity_to_produce)
  }

  const calculateOutputQuantity = () => {
    const recipe = getSelectedRecipe()
    if (!recipe || !formData.quantity_to_produce) return 0
    return recipe.output_quantity * parseFloat(formData.quantity_to_produce)
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Gestión de Producción
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Controla los lotes de producción y conversión de materias primas
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setDialog(true)}
          disabled={recipes.length === 0}
        >
          Nuevo Lote
        </Button>
      </Box>

      {recipes.length === 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          No hay recetas disponibles. Necesitas crear recetas antes de poder programar lotes de producción.
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando lotes de producción...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Lote</TableCell>
                    <TableCell>Receta</TableCell>
                    <TableCell>Cantidad</TableCell>
                    <TableCell>Produce</TableCell>
                    <TableCell>Costo Total</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Creado</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {batches.map((batch) => (
                    <TableRow key={batch.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          #{batch.id.slice(-8)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {batch.recipe_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {batch.quantity_to_produce} lotes
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {batch.output_quantity} {batch.output_unit}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          ${batch.total_cost?.toLocaleString('es-CL') || '0'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusLabel(batch.status)}
                          color={getStatusColor(batch.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(batch.created_at).toLocaleDateString('es-CL')}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Tooltip title="Ver detalles">
                            <IconButton
                              size="small"
                              onClick={() => handleViewDetails(batch)}
                            >
                              <Visibility fontSize="small" />
                            </IconButton>
                          </Tooltip>

                          {batch.status === 'pending' && (
                            <Tooltip title="Iniciar producción">
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={() => handleStartBatch(batch.id)}
                              >
                                <PlayArrow fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}

                          {batch.status === 'in_progress' && (
                            <Tooltip title="Completar lote">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleCompleteBatch(batch.id)}
                              >
                                <CheckCircle fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}

                          {batch.status === 'completed' && (
                            <Tooltip title="Generar Etiqueta">
                              <IconButton
                                size="small"
                                color="secondary"
                                onClick={() => handleGenerateLabel(batch)}
                              >
                                <Label fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}

                          {(batch.status === 'pending' || batch.status === 'in_progress') && (
                            <Tooltip title="Cancelar lote">
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleCancelBatch(batch.id)}
                              >
                                <Cancel fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                  {batches.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">
                          No hay lotes de producción programados
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

      {/* Add Batch Dialog */}
      <Dialog open={dialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          Crear Nuevo Lote de Producción
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Receta</InputLabel>
                <Select
                  value={formData.recipe_id}
                  onChange={(e) => setFormData({...formData, recipe_id: e.target.value})}
                  label="Receta"
                  required
                >
                  {recipes.map((recipe) => (
                    <MenuItem key={recipe.id} value={recipe.id}>
                      {recipe.name} - Produce {recipe.output_quantity} {recipe.output_unit}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Cantidad de Lotes"
                type="number"
                value={formData.quantity_to_produce}
                onChange={(e) => setFormData({...formData, quantity_to_produce: e.target.value})}
                required
                inputProps={{ min: 1, step: 1 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Costo Total Estimado"
                value={`$${calculateBatchCost().toLocaleString('es-CL')}`}
                InputProps={{ readOnly: true }}
                helperText="Calculado automáticamente"
              />
            </Grid>

            {getSelectedRecipe() && formData.quantity_to_produce && (
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Producirá:</strong> {calculateOutputQuantity()} {getSelectedRecipe().output_unit}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Tipo:</strong> {getSelectedRecipe().output_category}
                  </Typography>
                </Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notas"
                multiline
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Notas adicionales sobre la producción..."
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={!formData.recipe_id || !formData.quantity_to_produce}
          >
            Crear Lote
          </Button>
        </DialogActions>
      </Dialog>

      {/* Batch Detail Dialog */}
      <Dialog open={detailDialog} onClose={handleCloseDetailDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          Detalles del Lote #{selectedBatch?.id?.slice(-8)}
        </DialogTitle>
        <DialogContent>
          {selectedBatch && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={6}>
                <Typography variant="h6" gutterBottom>
                  Información General
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Receta"
                      secondary={selectedBatch.recipe_name}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Estado"
                      secondary={
                        <Chip
                          label={getStatusLabel(selectedBatch.status)}
                          color={getStatusColor(selectedBatch.status)}
                          size="small"
                        />
                      }
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Cantidad a Producir"
                      secondary={`${selectedBatch.quantity_to_produce} lotes`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Producirá"
                      secondary={`${selectedBatch.output_quantity} ${selectedBatch.output_unit}`}
                    />
                  </ListItem>
                </List>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Typography variant="h6" gutterBottom>
                  Información Financiera
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Costo Total"
                      secondary={`$${selectedBatch.total_cost?.toLocaleString('es-CL') || '0'}`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Creado"
                      secondary={new Date(selectedBatch.created_at).toLocaleString('es-CL')}
                    />
                  </ListItem>
                  {selectedBatch.completed_at && (
                    <ListItem>
                      <ListItemText
                        primary="Completado"
                        secondary={new Date(selectedBatch.completed_at).toLocaleString('es-CL')}
                      />
                    </ListItem>
                  )}
                </List>
              </Grid>

              {selectedBatch.notes && (
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    Notas
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedBatch.notes}
                  </Typography>
                </Grid>
              )}

              {selectedBatch.ingredients_consumed && selectedBatch.ingredients_consumed.length > 0 && (
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    Ingredientes Consumidos
                  </Typography>
                  <List dense>
                    {selectedBatch.ingredients_consumed.map((ingredient, index) => (
                      <ListItem key={index}>
                        <ListItemText
                          primary={ingredient.item_name}
                          secondary={`${ingredient.quantity} ${ingredient.unit} - $${ingredient.cost_per_unit?.toLocaleString('es-CL')}/unidad`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetailDialog}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* Label Generation Dialog */}
      <Dialog open={labelDialog} onClose={handleCloseLabelDialog} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Label />
            Etiqueta de Producto
          </Box>
          {labelData && (
            <Box>
              <Tooltip title="Imprimir Etiqueta">
                <IconButton onClick={handlePrintLabel} color="primary">
                  <Print />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </DialogTitle>
        <DialogContent>
          {loadingLabel ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
              <LinearProgress sx={{ width: '100%' }} />
            </Box>
          ) : labelData ? (
            <Box id="label-content" sx={{ p: 2 }}>
              {/* Label Preview Container */}
              <Paper
                elevation={3}
                sx={{
                  p: 2,
                  border: '2px solid #333',
                  maxWidth: 350,
                  mx: 'auto',
                  bgcolor: '#fff'
                }}
              >
                {/* Company Name */}
                <Typography
                  variant="h6"
                  align="center"
                  sx={{ fontWeight: 'bold', mb: 1 }}
                >
                  {labelData.company_info?.name || "Pablo's Pizza"}
                </Typography>

                {/* Product Name */}
                <Typography
                  variant="h5"
                  align="center"
                  sx={{
                    fontWeight: 'bold',
                    borderBottom: '2px solid #333',
                    borderTop: '2px solid #333',
                    py: 1,
                    mb: 2
                  }}
                >
                  {labelData.product_name}
                </Typography>

                {/* Batch Info */}
                <Paper variant="outlined" sx={{ p: 1, mb: 2, bgcolor: '#f5f5f5' }}>
                  <Grid container spacing={1}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        N° Lote:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {labelData.batch_number}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Cantidad:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {labelData.quantity_produced} {labelData.output_unit}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Fecha Producción:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {labelData.production_date}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Fecha Vencimiento:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold" color="error.main">
                        {labelData.expiration_date}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>

                {/* Nutritional Information Table */}
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  INFORMACIÓN NUTRICIONAL
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', mb: 1 }}>
                  Porción: 100g
                </Typography>

                <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Energía (kcal)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.calories || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Proteínas (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.proteins || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Carbohidratos (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.carbohydrates || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ pl: 2, py: 0.5 }}>- Azúcares (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.sugars || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Grasas Totales (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.fats || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ pl: 2, py: 0.5 }}>- Saturadas (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.saturated_fats || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Fibra (g)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.fiber || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', py: 0.5 }}>Sodio (mg)</TableCell>
                        <TableCell align="right" sx={{ py: 0.5 }}>
                          {labelData.nutrition_per_100g?.sodium || 0}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>

                {/* Ingredients List */}
                {labelData.ingredients_list && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                      INGREDIENTES:
                    </Typography>
                    <Typography variant="caption" sx={{ display: 'block' }}>
                      {labelData.ingredients_list}
                    </Typography>
                  </Box>
                )}

                {/* Barcode */}
                <Box sx={{ textAlign: 'center', mt: 2 }}>
                  <Box
                    sx={{
                      fontFamily: "'Libre Barcode 128', 'Courier New', monospace",
                      fontSize: 48,
                      letterSpacing: 2
                    }}
                  >
                    *{labelData.barcode}*
                  </Box>
                  <Typography variant="caption" sx={{ letterSpacing: 3 }}>
                    {labelData.barcode}
                  </Typography>
                </Box>

                {/* Company Contact */}
                <Divider sx={{ my: 1 }} />
                <Typography variant="caption" align="center" sx={{ display: 'block' }}>
                  {labelData.company_info?.contact || 'pablospizza.cl'}
                </Typography>
              </Paper>
            </Box>
          ) : (
            <Alert severity="error">
              No se pudo cargar la información de la etiqueta
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseLabelDialog}>Cerrar</Button>
          {labelData && (
            <Button
              variant="contained"
              startIcon={<Print />}
              onClick={handlePrintLabel}
            >
              Imprimir
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ProductionManagement