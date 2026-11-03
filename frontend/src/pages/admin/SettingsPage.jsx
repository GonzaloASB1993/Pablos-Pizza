import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Chip,
  Button,
  TextField,
  Grid,
  Alert,
  CircularProgress,
  Autocomplete,
  InputAdornment,
  Divider,
  Card,
  CardContent
} from '@mui/material'
import {
  Settings,
  LocalShipping,
  Save,
  AttachMoney,
  NightsStay
} from '@mui/icons-material'
import { alpha } from '@mui/material/styles'
import { settingsAPI } from '../../services/api'
import { DEFAULT_RECARGO_NOCTURNO_PCT } from '../../data/pricing'
import { santiagoComunas } from '../../data/chileanRegions'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const [comunasLejanas, setComunasLejanas] = useState([])
  const [cargo, setCargo] = useState(20000)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [originalData, setOriginalData] = useState({ comunas: [], cargo: 20000 })

  // Recargo nocturno: estado y guardado propios (el porcentaje se edita como texto para poder borrar el campo)
  const [recargoPct, setRecargoPct] = useState(String(DEFAULT_RECARGO_NOCTURNO_PCT))
  const [recargoOriginal, setRecargoOriginal] = useState(DEFAULT_RECARGO_NOCTURNO_PCT)
  const [recargoSaving, setRecargoSaving] = useState(false)

  useEffect(() => {
    loadSettings()
    loadRecargoNocturno()
  }, [])

  const loadRecargoNocturno = async () => {
    try {
      const response = await settingsAPI.getRecargoNocturno()
      const pct = response.data?.porcentaje ?? DEFAULT_RECARGO_NOCTURNO_PCT
      setRecargoPct(String(pct))
      setRecargoOriginal(pct)
    } catch (error) {
      console.error('Error loading recargo nocturno:', error)
    }
  }

  const recargoValue = recargoPct === '' ? NaN : Number(recargoPct)
  const recargoValid = Number.isInteger(recargoValue) && recargoValue >= 0 && recargoValue <= 100
  const recargoChanged = recargoValid && recargoValue !== recargoOriginal

  const handleSaveRecargo = async () => {
    if (!recargoValid) {
      toast.error('El porcentaje debe ser un entero entre 0 y 100')
      return
    }
    try {
      setRecargoSaving(true)
      await settingsAPI.updateRecargoNocturno({ porcentaje: recargoValue })
      setRecargoOriginal(recargoValue)
      toast.success('Recargo nocturno guardado correctamente')
    } catch (error) {
      console.error('Error saving recargo nocturno:', error)
      toast.error('Error al guardar el recargo nocturno')
    } finally {
      setRecargoSaving(false)
    }
  }

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await settingsAPI.getComunasLejanas()
      const data = response.data
      setComunasLejanas(data.comunas || [])
      setCargo(data.cargo || 20000)
      setOriginalData({ comunas: data.comunas || [], cargo: data.cargo || 20000 })
      setHasChanges(false)
    } catch (error) {
      console.error('Error loading settings:', error)
      setComunasLejanas(['Quilicura', 'Lampa', 'Colina', 'Huechuraba'])
      setCargo(20000)
      setOriginalData({ comunas: ['Quilicura', 'Lampa', 'Colina', 'Huechuraba'], cargo: 20000 })
    } finally {
      setLoading(false)
    }
  }

  const handleComunasChange = (_, newValue) => {
    setComunasLejanas(newValue)
    setHasChanges(true)
  }

  const handleCargoChange = (e) => {
    const value = parseInt(e.target.value) || 0
    setCargo(value)
    setHasChanges(true)
  }

  const handleSave = async () => {
    if (comunasLejanas.length === 0) {
      toast.error('Debes seleccionar al menos una comuna')
      return
    }
    if (cargo <= 0) {
      toast.error('El cargo debe ser mayor a 0')
      return
    }

    try {
      setSaving(true)
      await settingsAPI.updateComunasLejanas({
        comunas: comunasLejanas,
        cargo: cargo
      })
      setOriginalData({ comunas: [...comunasLejanas], cargo })
      setHasChanges(false)
      toast.success('Configuración guardada correctamente')
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error('Error al guardar la configuración')
    } finally {
      setSaving(false)
    }
  }

  const handleDiscard = () => {
    setComunasLejanas([...originalData.comunas])
    setCargo(originalData.cargo)
    setHasChanges(false)
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress sx={{ color: '#FFD700' }} />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Settings sx={{ fontSize: 32, color: '#FFD700' }} />
          <Box>
            <Typography variant="h5" fontWeight="bold">
              Configuración
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ajustes generales del sistema
            </Typography>
          </Box>
        </Box>
      </Box>

      <Paper sx={{ p: 3, borderRadius: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
          <LocalShipping sx={{ color: '#FFD700', fontSize: 28 }} />
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Comunas con Traslado Especial
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Selecciona las comunas que tienen un cargo adicional por traslado. Este cargo se aplica automáticamente en el formulario de agendamiento.
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Autocomplete
              multiple
              options={santiagoComunas}
              value={comunasLejanas}
              onChange={handleComunasChange}
              disableCloseOnSelect
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Comunas con cargo adicional"
                  placeholder="Buscar y agregar comunas..."
                  helperText={`${comunasLejanas.length} comuna${comunasLejanas.length !== 1 ? 's' : ''} seleccionada${comunasLejanas.length !== 1 ? 's' : ''}`}
                />
              )}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => {
                  const { key, ...tagProps } = getTagProps({ index })
                  return (
                    <Chip
                      key={key}
                      label={option}
                      {...tagProps}
                      sx={{
                        backgroundColor: (theme) => alpha(theme.palette.warning.main, 0.15),
                        color: 'warning.dark',
                        fontWeight: 500,
                        '& .MuiChip-deleteIcon': {
                          color: 'warning.main',
                          '&:hover': { color: 'error.main' }
                        }
                      }}
                    />
                  )
                })
              }
              renderOption={(props, option) => {
                const { key, ...optionProps } = props
                const isSelected = comunasLejanas.includes(option)
                return (
                  <li
                    key={key}
                    {...optionProps}
                    style={{
                      ...optionProps.style,
                      fontWeight: isSelected ? 600 : 400,
                      backgroundColor: isSelected ? 'rgba(255, 215, 0, 0.08)' : undefined
                    }}
                  >
                    {option}
                    {isSelected && (
                      <Chip
                        label="Seleccionada"
                        size="small"
                        sx={{ ml: 'auto', height: 20, fontSize: '0.7rem', bgcolor: 'warning.main', color: '#000' }}
                      />
                    )}
                  </li>
                )
              }}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Cargo por traslado"
              type="number"
              value={cargo}
              onChange={handleCargoChange}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>,
              }}
              helperText="Monto adicional cobrado en comunas lejanas"
            />
          </Grid>
        </Grid>

        {comunasLejanas.length > 0 && (
          <Card sx={{ mt: 3, bgcolor: (theme) => alpha(theme.palette.info.main, 0.05), border: '1px solid', borderColor: 'divider' }}>
            <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AttachMoney sx={{ color: 'warning.main', fontSize: 20 }} />
                <Typography variant="subtitle2" fontWeight="bold">
                  Resumen de configuración
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                A los clientes que agenden en{' '}
                <strong>{comunasLejanas.join(', ')}</strong>{' '}
                se les aplicará un cargo adicional de{' '}
                <strong>${cargo.toLocaleString('es-CL')}</strong>{' '}
                por concepto de traslado.
              </Typography>
            </CardContent>
          </Card>
        )}

        {hasChanges && (
          <Alert severity="warning" sx={{ mt: 3 }}>
            Tienes cambios sin guardar. Presiona "Guardar" para aplicar los cambios.
          </Alert>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
          {hasChanges && (
            <Button
              variant="outlined"
              onClick={handleDiscard}
              disabled={saving}
            >
              Descartar
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} color="inherit" /> : <Save />}
            onClick={handleSave}
            disabled={!hasChanges || saving}
            sx={{
              bgcolor: '#FFD700',
              color: '#000',
              fontWeight: 'bold',
              '&:hover': { bgcolor: '#FFC107' },
              '&.Mui-disabled': { bgcolor: 'action.disabledBackground' }
            }}
          >
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3, borderRadius: 3, mt: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
          <NightsStay sx={{ color: '#FFD700', fontSize: 28 }} />
          <Box>
            <Typography variant="h6" fontWeight="bold">
              Recargo nocturno
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Porcentaje que se suma al subtotal de servicios (Pizzeros y Pizza Party) cuando el evento empieza desde las 22:00.
              No afecta el cargo de comuna lejana. Las reservas ya creadas no cambian. Usa 0 para desactivarlo.
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Recargo nocturno"
              type="number"
              value={recargoPct}
              onChange={(e) => setRecargoPct(e.target.value)}
              error={recargoPct !== '' && !recargoValid}
              inputProps={{ min: 0, max: 100, step: 1 }}
              InputProps={{
                endAdornment: <InputAdornment position="end">%</InputAdornment>,
              }}
              helperText={
                recargoPct !== '' && !recargoValid
                  ? 'Ingresa un entero entre 0 y 100'
                  : 'Aplica a eventos que parten a las 22:00 o después'
              }
            />
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
          <Button
            variant="contained"
            startIcon={recargoSaving ? <CircularProgress size={20} color="inherit" /> : <Save />}
            onClick={handleSaveRecargo}
            disabled={!recargoChanged || recargoSaving}
            sx={{
              bgcolor: '#FFD700',
              color: '#000',
              fontWeight: 'bold',
              '&:hover': { bgcolor: '#FFC107' },
              '&.Mui-disabled': { bgcolor: 'action.disabledBackground' }
            }}
          >
            {recargoSaving ? 'Guardando...' : 'Guardar recargo'}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
