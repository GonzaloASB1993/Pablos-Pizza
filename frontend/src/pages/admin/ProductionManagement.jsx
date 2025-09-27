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
  AttachMoney
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

      setBatches(batchesRes.data || [])
      setRecipes(recipesRes.data || [])
      setInventory(inventoryRes.data || [])
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
    </Box>
  )
}

export default ProductionManagement