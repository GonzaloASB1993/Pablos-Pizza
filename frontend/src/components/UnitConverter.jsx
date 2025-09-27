import { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Alert,
  Box,
  Grid,
  Card,
  CardContent,
  Chip
} from '@mui/material'
import { SwapHoriz, Calculate } from '@mui/icons-material'
import {
  convertUnits,
  getCompatibleUnits,
  formatUnitConversion,
  formatStock,
  unitConversions
} from '../utils/formatters'

const UnitConverter = ({ open, onClose }) => {
  const [amount, setAmount] = useState('')
  const [fromUnit, setFromUnit] = useState('')
  const [toUnit, setToUnit] = useState('')
  const [result, setResult] = useState(null)

  // Get all available units grouped by category
  const unitCategories = Object.entries(unitConversions).map(([category, units]) => ({
    category: category,
    categoryName: {
      weight: 'Peso',
      volume: 'Volumen',
      quantity: 'Cantidad'
    }[category],
    units: Object.keys(units)
  }))

  const handleConvert = () => {
    if (!amount || !fromUnit || !toUnit) {
      return
    }

    const converted = convertUnits(parseFloat(amount), fromUnit, toUnit)

    if (converted !== null) {
      setResult({
        original: parseFloat(amount),
        fromUnit,
        converted,
        toUnit,
        formatted: formatUnitConversion(parseFloat(amount), fromUnit, toUnit)
      })
    } else {
      setResult({
        error: `No se puede convertir de ${fromUnit} a ${toUnit}`
      })
    }
  }

  const handleFromUnitChange = (newFromUnit) => {
    setFromUnit(newFromUnit)
    setToUnit('') // Reset target unit when source changes
    setResult(null)
  }

  const handleSwapUnits = () => {
    if (fromUnit && toUnit) {
      const newFromUnit = toUnit
      const newToUnit = fromUnit
      setFromUnit(newFromUnit)
      setToUnit(newToUnit)

      if (result && !result.error) {
        setAmount(formatStock(result.converted, false))
        setResult(null)
      }
    }
  }

  const handleClose = () => {
    setAmount('')
    setFromUnit('')
    setToUnit('')
    setResult(null)
    onClose()
  }

  const compatibleUnits = fromUnit ? getCompatibleUnits(fromUnit) : []

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Calculate />
          Conversor de Unidades para Recetas
        </Box>
      </DialogTitle>

      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Convierte cantidades entre diferentes unidades para usar en tus recetas.
        </Typography>

        <Grid container spacing={3}>
          {/* Input Section */}
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Conversión
                </Typography>

                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={3}>
                    <TextField
                      fullWidth
                      label="Cantidad"
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      inputProps={{ step: "0.001", min: "0" }}
                    />
                  </Grid>

                  <Grid item xs={12} sm={3}>
                    <FormControl fullWidth>
                      <InputLabel>Unidad origen</InputLabel>
                      <Select
                        value={fromUnit}
                        label="Unidad origen"
                        onChange={(e) => handleFromUnitChange(e.target.value)}
                      >
                        {unitCategories.map(({ category, categoryName, units }) => [
                          <MenuItem key={`${category}-header`} disabled>
                            <em>{categoryName}</em>
                          </MenuItem>,
                          ...units.map(unit => (
                            <MenuItem key={unit} value={unit}>
                              {unit}
                            </MenuItem>
                          ))
                        ])}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} sm={1} display="flex" justifyContent="center">
                    <Button
                      onClick={handleSwapUnits}
                      disabled={!fromUnit || !toUnit}
                      size="small"
                      variant="outlined"
                    >
                      <SwapHoriz />
                    </Button>
                  </Grid>

                  <Grid item xs={12} sm={3}>
                    <FormControl fullWidth>
                      <InputLabel>Unidad destino</InputLabel>
                      <Select
                        value={toUnit}
                        label="Unidad destino"
                        onChange={(e) => setToUnit(e.target.value)}
                        disabled={!fromUnit}
                      >
                        {compatibleUnits.map(unit => (
                          <MenuItem key={unit} value={unit}>
                            {unit}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} sm={2}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={handleConvert}
                      disabled={!amount || !fromUnit || !toUnit}
                    >
                      Convertir
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Result Section */}
          {result && (
            <Grid item xs={12}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Resultado
                  </Typography>

                  {result.error ? (
                    <Alert severity="error">
                      {result.error}
                    </Alert>
                  ) : (
                    <Box>
                      <Alert severity="success" sx={{ mb: 2 }}>
                        <Typography variant="body1">
                          <strong>{result.formatted}</strong>
                        </Typography>
                      </Alert>

                      <Typography variant="body2" color="text.secondary">
                        Para usar en tu receta: <strong>{formatStock(result.converted, false)} {result.toUnit}</strong>
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Examples Section */}
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Ejemplos Comunes
                </Typography>

                <Box display="flex" flexWrap="wrap" gap={1}>
                  <Chip
                    label="1 kg = 1.000 g"
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setAmount('1')
                      setFromUnit('kg')
                      setToUnit('g')
                    }}
                  />
                  <Chip
                    label="1 l = 1.000 ml"
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setAmount('1')
                      setFromUnit('l')
                      setToUnit('ml')
                    }}
                  />
                  <Chip
                    label="1 cup = 240 ml"
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setAmount('1')
                      setFromUnit('cup')
                      setToUnit('ml')
                    }}
                  />
                  <Chip
                    label="1 tbsp = 14.79 ml"
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setAmount('1')
                      setFromUnit('tbsp')
                      setToUnit('ml')
                    }}
                  />
                  <Chip
                    label="1 docena = 12 unidades"
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setAmount('1')
                      setFromUnit('docenas')
                      setToUnit('unidades')
                    }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default UnitConverter