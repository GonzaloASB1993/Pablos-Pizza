import { Box, Typography } from '@mui/material'
import { Inventory2 as InventoryIcon } from '@mui/icons-material'
import ActionCardFrame from './ActionCardFrame'
import { useActionCard } from './useActionCard'

const FIELD_LABELS = {
  name: 'Nombre', category: 'Categoría', unit: 'Unidad', supplier: 'Proveedor', notes: 'Notas',
  min_stock: 'Stock mínimo', max_stock: 'Stock máximo'
}
const TITLES = { inventory_update: 'Corregir insumo', stock_adjustment: 'Ajuste de stock' }
const CONFIRM = { inventory_update: 'Confirmar cambios', stock_adjustment: 'Confirmar ajuste' }

// Cards whose proposal is not edited in the chat (the server confirms exactly what it proposed):
// inventory_update shows before -> after; stock_adjustment shows the stock change.
const SimpleActionCard = ({ action, getAuthToken, onChange }) => {
  const { busy, error, confirm, cancel, editable } = useActionCard(action, getAuthToken, onChange)
  const { payload, context = {} } = action

  return (
    <ActionCardFrame
      title={TITLES[action.type] || 'Propuesta'}
      icon={<InventoryIcon color="primary" fontSize="small" />}
      action={action}
      editable={editable}
      busy={busy}
      error={error}
      canConfirm={editable}
      confirmLabel={CONFIRM[action.type] || 'Confirmar'}
      onConfirm={() => confirm()}
      onCancel={cancel}
    >
      {action.type === 'inventory_update' && (
        <Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 1.5, rowGap: 0.5 }}>
          {Object.entries(payload.changes || {}).filter(([, v]) => v !== null).map(([field, value]) => (
            <Box key={field} sx={{ display: 'contents' }}>
              <Typography component="dt" variant="caption" color="text.secondary">{FIELD_LABELS[field] || field}</Typography>
              <Typography component="dd" variant="body2" sx={{ m: 0 }}>
                {String(context.before?.[field] ?? '—')} → <strong>{String(value)}</strong>
              </Typography>
            </Box>
          ))}
        </Box>
      )}
      {action.type === 'stock_adjustment' && action.status === 'confirmed' && action.result?.stock_after !== undefined && (
        <Typography variant="caption" color="success.main" display="block">
          Stock actual: {action.result.stock_after}
        </Typography>
      )}
    </ActionCardFrame>
  )
}

export default SimpleActionCard
