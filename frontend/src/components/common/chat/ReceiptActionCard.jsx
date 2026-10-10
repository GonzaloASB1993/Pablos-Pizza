import { useMemo, useState } from 'react'
import {
  Autocomplete,
  Box,
  MenuItem,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from '@mui/material'
import { ShoppingCart as CartIcon } from '@mui/icons-material'
import ActionCardFrame from './ActionCardFrame'
import { clp, num, useActionCard } from './useActionCard'

const EXPENSE_CATEGORIES = [
  ['general', 'General'], ['servicios', 'Servicios'], ['arriendo', 'Arriendo'],
  ['sueldos', 'Sueldos'], ['marketing', 'Marketing'], ['otros', 'Otros']
]
const DOCUMENT_TYPES = [['boleta', 'Boleta'], ['factura', 'Factura'], ['otro', 'Otro']]
const CLASSES = [['existing', 'Insumo'], ['new', 'Insumo nuevo'], ['expense', 'Gasto']]

// Mirrors the server rules (ReceiptLine) so the button explains what is missing
const lineIssues = (line) => {
  const issues = []
  const amount = num(line.amount)
  const quantity = num(line.quantity)
  if (line.classification === 'expense') {
    if (!(amount > 0)) issues.push('monto')
  } else if (line.classification === 'existing') {
    if (!line.item_id) issues.push('insumo')
    if (!(quantity > 0)) issues.push('cantidad')
    if (!(amount > 0)) issues.push('monto')
  } else {
    if (!line.name?.trim()) issues.push('nombre')
    if (!line.unit?.trim()) issues.push('unidad')
    if (!line.category?.trim()) issues.push('categoría')
    if (quantity > 0 && !(amount > 0)) issues.push('monto')
    if (num(line.max_stock) > 0 && num(line.max_stock) < num(line.min_stock || 0)) issues.push('máximo menor al mínimo')
  }
  return issues
}

const cleanLine = (line) => {
  const base = { description: line.description, classification: line.classification, amount: num(line.amount) || 0 }
  if (line.classification === 'expense') return { ...base, expense_category: line.expense_category || 'general' }
  if (line.classification === 'existing') {
    return { ...base, item_id: line.item_id, quantity: num(line.quantity), unit: line.unit || null }
  }
  return {
    ...base, name: line.name?.trim(), category: line.category?.trim(), unit: line.unit?.trim(),
    quantity: num(line.quantity) || 0, min_stock: num(line.min_stock) || 0, max_stock: num(line.max_stock) || 0
  }
}

const ReceiptActionCard = ({ action, getAuthToken, onChange }) => {
  const [draft, setDraft] = useState(action.payload)
  const { busy, error, confirm, cancel, editable } = useActionCard(action, getAuthToken, onChange)
  const ctx = action.context || {}

  const setDoc = (field) => (e) => setDraft((d) => ({ ...d, [field]: e.target.value }))
  const setLine = (index, patch) => setDraft((d) => ({
    ...d, lines: d.lines.map((l, i) => (i === index ? { ...l, ...patch } : l))
  }))

  const itemOptions = (index) => {
    const seen = new Map()
    const pool = [...(ctx.candidates?.[String(index)] || []), ...Object.values(ctx.items || {})]
    pool.forEach((it) => { if (!seen.has(it.id)) seen.set(it.id, it) })
    return [...seen.values()]
  }

  const changeClass = (index, line, next) => {
    if (!next || next === line.classification) return
    const patch = { classification: next }
    if (next === 'existing') {
      const first = itemOptions(index)[0]
      patch.item_id = line.item_id || first?.id || ''
      patch.unit = (itemOptions(index).find((o) => o.id === patch.item_id)?.unit) || line.unit || ''
    } else if (next === 'new') {
      patch.name = line.name || line.description
      patch.category = line.category || ctx.known_categories?.[0] || ''
    }
    setLine(index, patch)
  }

  const linesTotal = useMemo(() => draft.lines.reduce((sum, l) => sum + (num(l.amount) || 0), 0), [draft.lines])
  const issues = draft.lines.map(lineIssues)
  const hasIssues = issues.some((list) => list.length > 0)
  const extraWarnings = []
  if (draft.total && Math.abs(linesTotal - num(draft.total)) > 1) {
    extraWarnings.push(`Las líneas suman ${clp(linesTotal)} y el documento dice ${clp(draft.total)}.`)
  }
  const counts = draft.lines.reduce((acc, l) => ({ ...acc, [l.classification]: (acc[l.classification] || 0) + 1 }), {})

  const handleConfirm = () => confirm({
    ...draft,
    supplier: draft.supplier?.trim() || null,
    folio: draft.folio?.trim() || null,
    total: draft.total ? num(draft.total) : null,
    lines: draft.lines.map(cleanLine)
  })

  return (
    <ActionCardFrame
      title="Propuesta de compra"
      icon={<CartIcon color="primary" fontSize="small" />}
      action={action}
      editable={editable}
      busy={busy}
      error={error}
      canConfirm={editable && !hasIssues}
      confirmLabel="Confirmar compra"
      onConfirm={handleConfirm}
      onCancel={cancel}
      extraWarnings={extraWarnings}
    >
      <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: '1fr 1fr', mt: 0.5 }}>
        <TextField
          label="Proveedor" size="small" value={draft.supplier || ''} onChange={setDoc('supplier')}
          disabled={!editable} sx={{ gridColumn: '1 / -1' }}
        />
        <TextField
          label="Fecha" type="date" size="small" value={draft.date || ''} onChange={setDoc('date')}
          disabled={!editable} InputLabelProps={{ shrink: true }}
        />
        <TextField label="Folio" size="small" value={draft.folio || ''} onChange={setDoc('folio')} disabled={!editable} />
        <TextField
          select label="Documento" size="small" value={draft.document_type || 'boleta'}
          onChange={setDoc('document_type')} disabled={!editable} sx={{ gridColumn: '1 / -1' }}
        >
          {DOCUMENT_TYPES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
        </TextField>
      </Box>

      <Typography variant="overline" color="text.secondary" display="block" mt={1.5}>
        Líneas · {counts.existing || 0} insumo · {counts.new || 0} nuevo · {counts.expense || 0} gasto
      </Typography>

      <Stack gap={1.25}>
        {draft.lines.map((line, index) => {
          const options = itemOptions(index)
          const lineProblems = issues[index]
          const unitCost = num(line.quantity) > 0 ? (num(line.amount) || 0) / num(line.quantity) : null
          return (
            <Paper
              key={index} variant="outlined" component="fieldset"
              sx={{ p: 1.5, m: 0, borderRadius: 1.5, borderColor: editable && lineProblems.length ? 'warning.main' : 'divider' }}
            >
              <Typography component="legend" variant="caption" sx={{ px: 0.5 }}>
                Línea {index + 1}: {line.description}
              </Typography>

              <ToggleButtonGroup
                exclusive fullWidth size="small" color="primary" value={line.classification}
                disabled={!editable} onChange={(_, next) => changeClass(index, line, next)}
                aria-label={`Clasificación de la línea ${index + 1}`} sx={{ mb: 1.25 }}
              >
                {CLASSES.map(([value, label]) => (
                  <ToggleButton
                    key={value} value={value}
                    sx={{
                      textTransform: 'none', py: 0.5, lineHeight: 1.2,
                      '&.Mui-selected, &.Mui-selected:hover': {
                        bgcolor: 'primary.main', color: 'primary.contrastText', fontWeight: 700
                      }
                    }}
                  >
                    {label}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>

              <Box sx={{ display: 'grid', gap: 1.25, gridTemplateColumns: '1fr 1fr' }}>
                {line.classification === 'existing' && (
                  <TextField
                    select label="Insumo" size="small" value={line.item_id || ''} disabled={!editable}
                    onChange={(e) => {
                      const picked = options.find((o) => o.id === e.target.value)
                      setLine(index, { item_id: e.target.value, unit: picked?.unit || line.unit })
                    }}
                    sx={{ gridColumn: '1 / -1' }}
                    helperText={options.length === 0 ? 'No hay insumos parecidos: usa "Insumo nuevo".' : undefined}
                  >
                    {options.map((o) => (
                      <MenuItem key={o.id} value={o.id}>{o.name} · stock {o.current_stock} {o.unit}</MenuItem>
                    ))}
                  </TextField>
                )}

                {line.classification === 'new' && (
                  <>
                    <TextField
                      label="Nombre" size="small" value={line.name || ''} disabled={!editable}
                      onChange={(e) => setLine(index, { name: e.target.value })} sx={{ gridColumn: '1 / -1' }}
                    />
                    <Autocomplete
                      freeSolo size="small" options={ctx.known_categories || []} value={line.category || ''}
                      disabled={!editable}
                      onInputChange={(_, v) => setLine(index, { category: v })}
                      renderInput={(params) => <TextField {...params} label="Categoría" />}
                    />
                    <Autocomplete
                      freeSolo size="small" options={ctx.known_units || []} value={line.unit || ''}
                      disabled={!editable}
                      onInputChange={(_, v) => setLine(index, { unit: v })}
                      renderInput={(params) => <TextField {...params} label="Unidad" />}
                    />
                  </>
                )}

                {line.classification === 'expense' && (
                  <TextField
                    select label="Categoría del gasto" size="small" value={line.expense_category || 'general'}
                    disabled={!editable} onChange={(e) => setLine(index, { expense_category: e.target.value })}
                    sx={{ gridColumn: '1 / -1' }}
                  >
                    {EXPENSE_CATEGORIES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
                  </TextField>
                )}

                {line.classification !== 'expense' && (
                  <TextField
                    label={`Cantidad${line.unit ? ` (${line.unit})` : ''}`} type="number" size="small"
                    value={line.quantity ?? ''} disabled={!editable}
                    onChange={(e) => setLine(index, { quantity: e.target.value })}
                    inputProps={{ min: 0, step: 'any', inputMode: 'decimal' }}
                  />
                )}
                <TextField
                  label="Monto (CLP)" type="number" size="small" value={line.amount ?? ''}
                  disabled={!editable} onChange={(e) => setLine(index, { amount: e.target.value })}
                  inputProps={{ min: 0, step: 1, inputMode: 'numeric' }}
                  sx={line.classification === 'expense' ? { gridColumn: '1 / -1' } : undefined}
                />

                {line.classification === 'new' && (
                  <>
                    <TextField
                      label="Stock mínimo" type="number" size="small" value={line.min_stock ?? 0} disabled={!editable}
                      onChange={(e) => setLine(index, { min_stock: e.target.value })} inputProps={{ min: 0, step: 'any' }}
                    />
                    <TextField
                      label="Stock máximo" type="number" size="small" value={line.max_stock ?? 0} disabled={!editable}
                      onChange={(e) => setLine(index, { max_stock: e.target.value })} inputProps={{ min: 0, step: 'any' }}
                    />
                  </>
                )}
              </Box>

              {line.classification !== 'expense' && unitCost !== null && (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.75}>
                  Costo por {line.unit || 'unidad'}: {clp(unitCost)}
                </Typography>
              )}
              {editable && lineProblems.length > 0 && (
                <Typography variant="caption" color="warning.main" display="block" mt={0.5}>
                  Falta: {lineProblems.join(', ')}
                </Typography>
              )}
            </Paper>
          )
        })}
      </Stack>

      <Typography variant="body2" fontWeight={600} textAlign="right" mt={1.25}>
        Total de líneas: {clp(linesTotal)}
      </Typography>

      {action.status === 'confirmed' && action.result && (
        <Typography variant="caption" color="success.main" display="block" mt={1}>
          {action.already_confirmed ? 'Ya estaba registrada. ' : 'Registrada. '}
          {action.result.inventory_lines} línea{action.result.inventory_lines === 1 ? '' : 's'} a inventario
          y {action.result.expense_lines} a gastos.
        </Typography>
      )}
    </ActionCardFrame>
  )
}

export default ReceiptActionCard
