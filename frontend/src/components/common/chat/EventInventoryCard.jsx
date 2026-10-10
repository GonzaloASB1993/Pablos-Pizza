import { useMemo, useState } from 'react'
import { Box, IconButton, Paper, Stack, TextField, Typography } from '@mui/material'
import { Close as RemoveIcon, Event as EventIcon } from '@mui/icons-material'
import ActionCardFrame from './ActionCardFrame'
import { clp, num, useActionCard } from './useActionCard'

const isReturnMode = (item) => item.quantity_returned !== null && item.quantity_returned !== undefined

// Insumos (estimate, does not move stock) and consumo (real, deducts stock) of ONE event.
const EventInventoryCard = ({ action, getAuthToken, onChange }) => {
  const isConsumption = action.type === 'event_consumption'
  const [draft, setDraft] = useState(action.payload)
  const { busy, error, confirm, cancel, editable } = useActionCard(action, getAuthToken, onChange)
  const ctx = action.context || {}
  const booking = ctx.booking || {}
  const rows = useMemo(() => Object.fromEntries((ctx.rows || []).map((r) => [r.item_id, r])), [ctx.rows])

  const setItem = (index, patch) => setDraft((d) => ({
    ...d, items: d.items.map((it, i) => (i === index ? { ...it, ...patch } : it))
  }))
  const removeItem = (index) => setDraft((d) => ({ ...d, items: d.items.filter((_, i) => i !== index) }))

  // what each line would consume / cost with the current numbers
  const lines = draft.items.map((item) => {
    const info = rows[item.item_id] || {}
    const cost = info.cost_per_unit || 0
    if (!isConsumption) {
      const qty = num(item.estimated_quantity)
      return { item, info, qty, cost: (qty || 0) * cost, problem: !(qty > 0) ? 'cantidad' : (qty > info.current_stock ? `stock insuficiente (${info.current_stock} ${info.unit})` : null) }
    }
    if (isReturnMode(item)) {
      const returned = num(item.quantity_returned)
      const estimated = info.estimated_quantity || 0
      const consumed = Math.max(0, estimated - (returned || 0))
      return { item, info, qty: consumed, cost: consumed * cost, problem: Number.isNaN(returned) || returned < 0 ? 'cantidad' : (returned > estimated ? `volvió más de lo llevado (${estimated})` : null) }
    }
    const consumed = num(item.actual_quantity_consumed)
    return { item, info, qty: consumed, cost: (consumed || 0) * cost, problem: Number.isNaN(consumed) || consumed < 0 ? 'cantidad' : null }
  })

  const supplyCost = lines.reduce((sum, l) => sum + l.cost, 0)
  const other = num(draft.total_other_expenses) || 0
  const hasProblem = lines.some((l) => l.problem) || draft.items.length === 0 || (isConsumption && other < 0)

  const handleConfirm = () => confirm({
    ...draft,
    ...(isConsumption ? { total_other_expenses: Math.round(other) } : {}),
    notes: draft.notes?.trim() || null,
    items: draft.items.map((it) => (isConsumption
      ? (isReturnMode(it)
        ? { item_id: it.item_id, quantity_returned: num(it.quantity_returned) }
        : { item_id: it.item_id, actual_quantity_consumed: num(it.actual_quantity_consumed) })
      : { item_id: it.item_id, estimated_quantity: num(it.estimated_quantity), notes: it.notes || null }))
  })

  return (
    <ActionCardFrame
      title={isConsumption ? 'Consumo real del evento' : 'Insumos del evento (estimación)'}
      icon={<EventIcon color="primary" fontSize="small" />}
      action={action}
      editable={editable}
      busy={busy}
      error={error}
      canConfirm={editable && !hasProblem}
      confirmLabel={isConsumption ? 'Confirmar consumo' : 'Confirmar insumos'}
      onConfirm={handleConfirm}
      onCancel={cancel}
    >
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        {booking.client_name} · {booking.event_date}{booking.participants ? ` · ${booking.participants} participantes` : ''}
        {isConsumption ? ' · descuenta stock al confirmar' : ' · no mueve stock'}
      </Typography>

      <Stack gap={1}>
        {lines.map(({ item, info, qty, cost, problem }, index) => (
          <Paper key={item.item_id} variant="outlined" sx={{ p: 1.25, borderRadius: 1.5, borderColor: editable && problem ? 'warning.main' : 'divider' }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
              <Typography variant="body2" fontWeight={600} noWrap>{info.item_name || item.item_id}</Typography>
              {editable && draft.items.length > 1 && (
                <IconButton size="small" aria-label={`Quitar ${info.item_name || 'insumo'}`} onClick={() => removeItem(index)}>
                  <RemoveIcon fontSize="small" />
                </IconButton>
              )}
            </Stack>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 1, alignItems: 'center', mt: 0.75 }}>
              <TextField
                size="small" type="number" disabled={!editable}
                label={!isConsumption ? `Cantidad a llevar (${info.unit || ''})` : (isReturnMode(item) ? `Volvió (${info.unit || ''})` : `Consumido (${info.unit || ''})`)}
                value={(!isConsumption ? item.estimated_quantity : (isReturnMode(item) ? item.quantity_returned : item.actual_quantity_consumed)) ?? ''}
                onChange={(e) => setItem(index, !isConsumption ? { estimated_quantity: e.target.value }
                  : (isReturnMode(item) ? { quantity_returned: e.target.value } : { actual_quantity_consumed: e.target.value }))}
                inputProps={{ min: 0, step: 'any', inputMode: 'decimal' }}
              />
              <Typography variant="caption" color="text.secondary" textAlign="right">
                {isConsumption && <>consumo {Number.isFinite(qty) ? qty : 0} {info.unit}<br /></>}
                {clp(cost)}
              </Typography>
            </Box>
            {isConsumption && isReturnMode(item) && info.estimated_quantity > 0 && (
              <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                Se llevó {info.estimated_quantity} {info.unit}
              </Typography>
            )}
            {editable && problem && (
              <Typography variant="caption" color="warning.main" display="block" mt={0.5}>Revisa: {problem}</Typography>
            )}
            {isConsumption && info.stock_before !== undefined && (
              <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                Stock {info.stock_before} → {Math.round((info.stock_before - (Number.isFinite(qty) ? qty : 0)) * 100) / 100} {info.unit}
              </Typography>
            )}
          </Paper>
        ))}
      </Stack>

      {isConsumption && (
        <TextField
          label="Otros gastos del evento (CLP)" type="number" size="small" fullWidth sx={{ mt: 1.5 }}
          value={draft.total_other_expenses ?? 0} disabled={!editable}
          onChange={(e) => setDraft((d) => ({ ...d, total_other_expenses: e.target.value }))}
          inputProps={{ min: 0, step: 1, inputMode: 'numeric' }}
        />
      )}
      <TextField
        label="Notas" size="small" fullWidth multiline maxRows={3} sx={{ mt: 1.5 }}
        value={draft.notes || ''} disabled={!editable} onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
      />

      <Typography variant="body2" fontWeight={600} textAlign="right" mt={1.25}>
        {isConsumption
          ? `Insumos ${clp(supplyCost)} + otros ${clp(other)} = ${clp(supplyCost + other)}`
          : `Costo estimado: ${clp(supplyCost)}`}
      </Typography>

      {action.status === 'confirmed' && action.result && (
        <Typography variant="caption" color="success.main" display="block" mt={1}>
          {isConsumption
            ? `Consumo registrado: ${clp(action.result.total_cost)} en total. El stock ya se descontó.`
            : `Estimación registrada: ${clp(action.result.estimated_total_cost)}.`}
        </Typography>
      )}
    </ActionCardFrame>
  )
}

export default EventInventoryCard
