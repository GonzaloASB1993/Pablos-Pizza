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
    if (!labelData || !printWindow) return

    // Calculate dates
    const productionDate = new Date(labelData.production_date)
    const refrigeratedExpiry = new Date(productionDate)
    refrigeratedExpiry.setDate(refrigeratedExpiry.getDate() + 7)
    const frozenExpiry = new Date(productionDate)
    frozenExpiry.setMonth(frozenExpiry.getMonth() + 6)

    const formatDate = (date) => {
      const d = new Date(date)
      return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
    }

    // Nutrition calculations (per 100g and per portion ~140g for 420g pizza / 3 portions)
    const portionSize = 140
    const n = labelData.nutrition_per_100g || {}
    const calcPortion = (val) => ((parseFloat(val) || 0) * portionSize / 100).toFixed(1)
    const calcVD = (val, daily) => Math.round(((parseFloat(val) || 0) * portionSize / 100 / daily) * 100)

    const labelHTML = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Etiqueta - ${labelData.product_name}</title>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

          * { margin: 0; padding: 0; box-sizing: border-box; }

          @page {
            size: 90mm 140mm;
            margin: 0;
          }

          body {
            font-family: 'IBM Plex Sans', Arial, sans-serif;
            background: #fff;
            padding: 0;
            margin: 0;
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
          }

          .label {
            width: 90mm;
            background: #fff;
            border: 2.5px solid #000;
          }

          .label-header {
            background: #000;
            color: #fff;
            padding: 8px 10px 6px;
            text-align: center;
          }
          .label-header .brand {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
          }
          .label-header .tagline {
            font-size: 7px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-top: 2px;
            opacity: 0.8;
          }

          .label-product {
            border-bottom: 2px solid #000;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
          }
          .label-product .name {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .label-product .variant {
            font-size: 8px;
            color: #444;
            margin-top: 2px;
          }
          .vacuum-badge {
            display: inline-block;
            border: 1.5px solid #000;
            font-size: 6px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 1px 4px;
            margin-top: 3px;
          }
          .label-product .weight {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 14px;
            font-weight: 700;
            text-align: right;
          }
          .label-product .weight span {
            font-size: 7px;
            font-weight: 400;
            display: block;
          }

          .label-meta {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            border-bottom: 1.5px solid #000;
          }
          .meta-item {
            padding: 4px 6px;
            border-right: 1px solid #000;
          }
          .meta-item:last-child { border-right: none; }
          .meta-item .meta-label {
            font-size: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #555;
            margin-bottom: 1px;
          }
          .meta-item .meta-value {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 8px;
            font-weight: 700;
          }

          .section-title {
            background: #000;
            color: #fff;
            font-size: 7px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 2px 10px;
          }

          .nutrition-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 7px;
          }
          .nutrition-table thead tr { border-bottom: 1px solid #000; }
          .nutrition-table thead th {
            padding: 2px 6px;
            text-align: left;
            font-size: 6px;
            font-weight: 700;
            text-transform: uppercase;
          }
          .nutrition-table thead th:not(:first-child) { text-align: right; }
          .nutrition-table tbody tr { border-bottom: 0.5px solid #ccc; }
          .nutrition-table tbody tr:last-child { border-bottom: none; }
          .nutrition-table tbody td {
            padding: 2px 6px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 7px;
          }
          .nutrition-table tbody td:not(:first-child) { text-align: right; font-size: 6.5px; }
          .nutrition-table .bold td { font-weight: 700; background: #f4f4f4; }
          .nutrition-table .sub td:first-child { padding-left: 12px; color: #444; }

          .nutrition-note {
            font-size: 5.5px;
            color: #555;
            padding: 3px 6px;
            border-bottom: 1px solid #000;
            line-height: 1.3;
          }

          .ingredients {
            padding: 4px 8px;
            border-bottom: 1px solid #000;
            font-size: 6px;
            line-height: 1.4;
          }
          .ingredients strong {
            font-size: 6px;
            text-transform: uppercase;
            display: block;
            margin-bottom: 1px;
          }
          .allergen { text-transform: uppercase; font-weight: 700; text-decoration: underline; }

          .storage {
            display: flex;
            border-bottom: 1px solid #000;
          }
          .storage-item {
            flex: 1;
            padding: 4px 6px;
            border-right: 1px solid #000;
            text-align: center;
          }
          .storage-item:last-child { border-right: none; }
          .storage-item .stor-icon { font-size: 10px; }
          .storage-item .stor-label {
            font-size: 5.5px;
            text-transform: uppercase;
            margin-top: 1px;
            color: #333;
          }
          .storage-item .stor-temp {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 7px;
            font-weight: 700;
          }

          .label-footer {
            padding: 5px 8px;
          }
          .label-footer .company {
            font-size: 6px;
            line-height: 1.5;
            color: #444;
          }
          .label-footer .company strong {
            display: block;
            font-size: 7px;
            font-weight: 700;
            color: #000;
            text-transform: uppercase;
          }
          .barcode-area {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 4px 0 2px;
            border-top: 1px dashed #bbb;
            margin-top: 4px;
          }
          .barcode-label {
            font-size: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #777;
            margin-bottom: 3px;
          }
          .barcode-number {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 7px;
            letter-spacing: 2px;
            margin-top: 2px;
          }

          @media print {
            body { background: none; }
            .label { border: 2px solid #000; }
          }
        </style>
      </head>
      <body>
        <div class="label">
          <div class="label-header">
            <div class="brand">Pablo's Pizza</div>
            <div class="tagline">Producto envasado al vacío · Hecho artesanalmente</div>
          </div>

          <div class="label-product">
            <div>
              <div class="name">${labelData.product_name}</div>
              <div class="variant">Pizza 25 cm · Envasado al vacío</div>
              <div><span class="vacuum-badge">Al vacío</span></div>
            </div>
            <div class="weight">${labelData.total_weight_grams || 420} g<span>Peso neto</span></div>
          </div>

          <div class="label-meta">
            <div class="meta-item">
              <div class="meta-label">Lote</div>
              <div class="meta-value">${labelData.batch_number}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">Elaboración</div>
              <div class="meta-value">${formatDate(labelData.production_date)}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">Consumir antes (ref.)</div>
              <div class="meta-value">${formatDate(refrigeratedExpiry)}</div>
            </div>
          </div>

          <div class="section-title">Información Nutricional</div>
          <table class="nutrition-table">
            <thead>
              <tr>
                <th>Nutrimento</th>
                <th>Por 100 g</th>
                <th>Por porción (${portionSize} g)</th>
                <th>%VD*</th>
              </tr>
            </thead>
            <tbody>
              <tr class="bold">
                <td>Energía</td>
                <td>${n.calories || 0} kcal</td>
                <td>${calcPortion(n.calories)} kcal</td>
                <td>${calcVD(n.calories, 2000)}%</td>
              </tr>
              <tr>
                <td>Proteínas</td>
                <td>${n.proteins || 0} g</td>
                <td>${calcPortion(n.proteins)} g</td>
                <td>${calcVD(n.proteins, 75)}%</td>
              </tr>
              <tr class="bold">
                <td>Grasas totales</td>
                <td>${n.fats || 0} g</td>
                <td>${calcPortion(n.fats)} g</td>
                <td>${calcVD(n.fats, 65)}%</td>
              </tr>
              <tr class="sub">
                <td>Grasas saturadas</td>
                <td>${n.saturated_fats || 0} g</td>
                <td>${calcPortion(n.saturated_fats)} g</td>
                <td>${calcVD(n.saturated_fats, 22)}%</td>
              </tr>
              <tr class="bold">
                <td>Hidratos de carbono</td>
                <td>${n.carbohydrates || 0} g</td>
                <td>${calcPortion(n.carbohydrates)} g</td>
                <td>${calcVD(n.carbohydrates, 275)}%</td>
              </tr>
              <tr class="sub">
                <td>Azúcares totales</td>
                <td>${n.sugars || 0} g</td>
                <td>${calcPortion(n.sugars)} g</td>
                <td>—</td>
              </tr>
              <tr>
                <td>Fibra dietética</td>
                <td>${n.fiber || 0} g</td>
                <td>${calcPortion(n.fiber)} g</td>
                <td>${calcVD(n.fiber, 25)}%</td>
              </tr>
              <tr>
                <td>Sodio</td>
                <td>${n.sodium || 0} mg</td>
                <td>${calcPortion(n.sodium)} mg</td>
                <td>${calcVD(n.sodium, 2300)}%</td>
              </tr>
            </tbody>
          </table>
          <div class="nutrition-note">
            *%VD = Valores diarios con base en una dieta de 2,000 kcal. Porciones por envase: 3.
          </div>

          <div class="section-title">Ingredientes</div>
          <div class="ingredients">
            <strong>Lista de ingredientes:</strong>
            ${labelData.ingredients_list || 'Consultar en punto de venta'}
          </div>

          <div class="section-title">Condiciones de conservación</div>
          <div class="storage">
            <div class="storage-item">
              <div class="stor-icon">❄</div>
              <div class="stor-label">Refrigeración</div>
              <div class="stor-temp">0 – 4 °C (7 días)</div>
            </div>
            <div class="storage-item">
              <div class="stor-icon">▦</div>
              <div class="stor-label">Congelación</div>
              <div class="stor-temp">−18 °C (6 meses)</div>
            </div>
            <div class="storage-item">
              <div class="stor-icon">✕</div>
              <div class="stor-label">No recongelar</div>
              <div class="stor-temp">Una vez abierto</div>
            </div>
          </div>

          <div class="label-footer">
            <div class="company">
              <strong>Pablo's Pizza SpA</strong>
              Los Tijerales 3814, Puente Alto · Santiago, Chile<br>
              Tel: (+56) 9 8942 4566 · pablospizza.cl
            </div>
            <div class="barcode-area">
              <div class="barcode-label">EAN-13</div>
              <svg width="160" height="35" viewBox="0 0 200 50" xmlns="http://www.w3.org/2000/svg">
                <rect x="10" width="2" height="50" fill="#000"/>
                <rect x="14" width="2" height="50" fill="#000"/>
                <rect x="20" width="3" height="44" fill="#000"/>
                <rect x="25" width="1" height="44" fill="#000"/>
                <rect x="29" width="2" height="44" fill="#000"/>
                <rect x="33" width="1" height="44" fill="#000"/>
                <rect x="37" width="3" height="44" fill="#000"/>
                <rect x="42" width="2" height="44" fill="#000"/>
                <rect x="47" width="1" height="44" fill="#000"/>
                <rect x="50" width="2" height="44" fill="#000"/>
                <rect x="54" width="3" height="44" fill="#000"/>
                <rect x="59" width="1" height="44" fill="#000"/>
                <rect x="62" width="2" height="44" fill="#000"/>
                <rect x="67" width="1" height="44" fill="#000"/>
                <rect x="71" width="3" height="44" fill="#000"/>
                <rect x="76" width="2" height="44" fill="#000"/>
                <rect x="83" width="1" height="50" fill="#000"/>
                <rect x="86" width="1" height="50" fill="#000"/>
                <rect x="89" width="1" height="50" fill="#000"/>
                <rect x="94" width="3" height="44" fill="#000"/>
                <rect x="99" width="1" height="44" fill="#000"/>
                <rect x="103" width="2" height="44" fill="#000"/>
                <rect x="107" width="3" height="44" fill="#000"/>
                <rect x="113" width="1" height="44" fill="#000"/>
                <rect x="116" width="2" height="44" fill="#000"/>
                <rect x="120" width="1" height="44" fill="#000"/>
                <rect x="124" width="3" height="44" fill="#000"/>
                <rect x="129" width="2" height="44" fill="#000"/>
                <rect x="133" width="1" height="44" fill="#000"/>
                <rect x="137" width="3" height="44" fill="#000"/>
                <rect x="142" width="1" height="44" fill="#000"/>
                <rect x="146" width="2" height="44" fill="#000"/>
                <rect x="151" width="3" height="44" fill="#000"/>
                <rect x="158" width="2" height="50" fill="#000"/>
                <rect x="162" width="2" height="50" fill="#000"/>
                <rect x="166" width="2" height="50" fill="#000"/>
              </svg>
              <div class="barcode-number">${labelData.barcode}</div>
            </div>
          </div>
        </div>
      </body>
      </html>
    `

    printWindow.document.write(labelHTML)
    printWindow.document.close()
    printWindow.focus()

    // Wait for fonts to load
    setTimeout(() => {
      printWindow.print()
    }, 500)
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
      <Dialog open={labelDialog} onClose={handleCloseLabelDialog} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Label />
            Vista Previa de Etiqueta
          </Box>
          {labelData && (
            <Button
              variant="contained"
              startIcon={<Print />}
              onClick={handlePrintLabel}
            >
              Imprimir Etiqueta
            </Button>
          )}
        </DialogTitle>
        <DialogContent>
          {loadingLabel ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
              <LinearProgress sx={{ width: '100%' }} />
            </Box>
          ) : labelData ? (
            <Box sx={{ p: 2, bgcolor: '#e8e8e8', borderRadius: 2 }}>
              {/* Label Preview Container - Matching print design */}
              <Paper
                elevation={4}
                sx={{
                  width: '340px',
                  mx: 'auto',
                  bgcolor: '#fff',
                  border: '2.5px solid #000',
                  fontFamily: "'IBM Plex Sans', Arial, sans-serif",
                  overflow: 'hidden'
                }}
              >
                {/* Header */}
                <Box sx={{ bgcolor: '#000', color: '#fff', p: '10px 12px 8px', textAlign: 'center' }}>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '20px', fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' }}>
                    Pablo's Pizza
                  </Typography>
                  <Typography sx={{ fontSize: '8px', letterSpacing: 1.5, textTransform: 'uppercase', mt: 0.5, opacity: 0.8 }}>
                    Producto envasado al vacío · Hecho artesanalmente
                  </Typography>
                </Box>

                {/* Product */}
                <Box sx={{ borderBottom: '2px solid #000', p: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <Box>
                    <Typography sx={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      {labelData.product_name}
                    </Typography>
                    <Typography sx={{ fontSize: '9px', color: '#444', mt: 0.5 }}>
                      Pizza 25 cm · Envasado al vacío
                    </Typography>
                    <Chip label="AL VACÍO" size="small" sx={{ mt: 0.5, height: 16, fontSize: '7px', fontWeight: 700, border: '1.5px solid #000', bgcolor: 'transparent' }} />
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography sx={{ fontFamily: 'monospace', fontSize: '18px', fontWeight: 700 }}>
                      {labelData.total_weight_grams || 420} g
                    </Typography>
                    <Typography sx={{ fontSize: '8px' }}>Peso neto</Typography>
                  </Box>
                </Box>

                {/* Meta Info */}
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: '1.5px solid #000' }}>
                  {[
                    { label: 'Lote', value: labelData.batch_number },
                    { label: 'Elaboración', value: new Date(labelData.production_date).toLocaleDateString('es-CL') },
                    { label: 'Consumir antes (ref.)', value: (() => {
                      const d = new Date(labelData.production_date)
                      d.setDate(d.getDate() + 7)
                      return d.toLocaleDateString('es-CL')
                    })() }
                  ].map((item, i) => (
                    <Box key={i} sx={{ p: '6px 8px', borderRight: i < 2 ? '1px solid #000' : 'none' }}>
                      <Typography sx={{ fontSize: '7px', textTransform: 'uppercase', letterSpacing: 0.5, color: '#555', mb: 0.5 }}>
                        {item.label}
                      </Typography>
                      <Typography sx={{ fontFamily: 'monospace', fontSize: '9px', fontWeight: 700 }}>
                        {item.value}
                      </Typography>
                    </Box>
                  ))}
                </Box>

                {/* Nutrition Table */}
                <Box sx={{ bgcolor: '#000', color: '#fff', fontSize: '8px', fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', p: '3px 12px' }}>
                  Información Nutricional
                </Box>
                <TableContainer>
                  <Table size="small" sx={{ '& td, & th': { py: 0.3, px: 1, fontSize: '8px', borderBottom: '0.5px solid #ccc' } }}>
                    <TableHead>
                      <TableRow sx={{ borderBottom: '1.5px solid #000' }}>
                        <TableCell sx={{ fontWeight: 700, fontSize: '7px' }}>Nutrimento</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, fontSize: '7px' }}>Por 100g</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, fontSize: '7px' }}>Por porción (140g)</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {[
                        { name: 'Energía', value: labelData.nutrition_per_100g?.calories || 0, unit: 'kcal', bold: true },
                        { name: 'Proteínas', value: labelData.nutrition_per_100g?.proteins || 0, unit: 'g' },
                        { name: 'Grasas totales', value: labelData.nutrition_per_100g?.fats || 0, unit: 'g', bold: true },
                        { name: '  - Saturadas', value: labelData.nutrition_per_100g?.saturated_fats || 0, unit: 'g', sub: true },
                        { name: 'Carbohidratos', value: labelData.nutrition_per_100g?.carbohydrates || 0, unit: 'g', bold: true },
                        { name: '  - Azúcares', value: labelData.nutrition_per_100g?.sugars || 0, unit: 'g', sub: true },
                        { name: 'Fibra', value: labelData.nutrition_per_100g?.fiber || 0, unit: 'g' },
                        { name: 'Sodio', value: labelData.nutrition_per_100g?.sodium || 0, unit: 'mg' },
                      ].map((row, i) => (
                        <TableRow key={i} sx={{ bgcolor: row.bold ? '#f4f4f4' : 'transparent' }}>
                          <TableCell sx={{ fontWeight: row.bold ? 700 : 400, color: row.sub ? '#666' : 'inherit', fontFamily: 'monospace' }}>
                            {row.name}
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{row.value} {row.unit}</TableCell>
                          <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{(parseFloat(row.value) * 1.4).toFixed(1)} {row.unit}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Typography sx={{ fontSize: '6px', color: '#555', p: '4px 8px', borderBottom: '1px solid #000', lineHeight: 1.3 }}>
                  *%VD = Valores diarios con base en una dieta de 2,000 kcal. Porciones por envase: 3.
                </Typography>

                {/* Ingredients */}
                <Box sx={{ bgcolor: '#000', color: '#fff', fontSize: '8px', fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', p: '3px 12px' }}>
                  Ingredientes
                </Box>
                <Box sx={{ p: '6px 10px', borderBottom: '1px solid #000', fontSize: '7px', lineHeight: 1.5 }}>
                  <Typography sx={{ fontSize: '7px' }}>
                    {labelData.ingredients_list || 'Consultar en punto de venta'}
                  </Typography>
                </Box>

                {/* Storage */}
                <Box sx={{ bgcolor: '#000', color: '#fff', fontSize: '8px', fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', p: '3px 12px' }}>
                  Condiciones de Conservación
                </Box>
                <Box sx={{ display: 'flex', borderBottom: '1.5px solid #000' }}>
                  {[
                    { icon: '❄', label: 'Refrigeración', temp: '0 – 4 °C (7 días)' },
                    { icon: '▦', label: 'Congelación', temp: '−18 °C (6 meses)' },
                    { icon: '✕', label: 'No recongelar', temp: 'Una vez abierto' }
                  ].map((item, i) => (
                    <Box key={i} sx={{ flex: 1, p: '6px', textAlign: 'center', borderRight: i < 2 ? '1px solid #000' : 'none' }}>
                      <Typography sx={{ fontSize: '14px' }}>{item.icon}</Typography>
                      <Typography sx={{ fontSize: '6px', textTransform: 'uppercase', mt: 0.5, color: '#333' }}>{item.label}</Typography>
                      <Typography sx={{ fontFamily: 'monospace', fontSize: '8px', fontWeight: 700, mt: 0.5 }}>{item.temp}</Typography>
                    </Box>
                  ))}
                </Box>

                {/* Footer */}
                <Box sx={{ p: '8px 10px' }}>
                  <Typography sx={{ fontSize: '8px', fontWeight: 700, textTransform: 'uppercase', color: '#000' }}>
                    Pablo's Pizza SpA
                  </Typography>
                  <Typography sx={{ fontSize: '7px', color: '#444', lineHeight: 1.6 }}>
                    Los Tijerales 3814, Puente Alto · Santiago, Chile<br />
                    Tel: (+56) 9 8942 4566 · pablospizza.cl
                  </Typography>
                  <Divider sx={{ my: 1, borderStyle: 'dashed' }} />
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography sx={{ fontSize: '6px', textTransform: 'uppercase', letterSpacing: 1, color: '#777', mb: 0.5 }}>
                      EAN-13
                    </Typography>
                    <Typography sx={{ fontFamily: 'monospace', fontSize: '10px', letterSpacing: 2 }}>
                      {labelData.barcode}
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              {/* Warning about nutrition values */}
              {(!labelData.nutrition_per_100g?.calories || labelData.nutrition_per_100g?.calories === 0) && (
                <Alert severity="warning" sx={{ mt: 2, mx: 'auto', maxWidth: 340 }}>
                  <Typography variant="body2">
                    <strong>Valores nutricionales en 0:</strong> Debes agregar la información nutricional (por 100g) a cada ingrediente en el módulo de Inventario.
                  </Typography>
                </Alert>
              )}
            </Box>
          ) : (
            <Alert severity="error">
              No se pudo cargar la información de la etiqueta
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseLabelDialog}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ProductionManagement