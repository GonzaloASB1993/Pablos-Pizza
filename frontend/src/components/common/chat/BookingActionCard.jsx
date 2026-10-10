import { useState } from 'react'
import { Box, Checkbox, FormControlLabel, FormGroup, MenuItem, TextField, Typography } from '@mui/material'
import { EventAvailable as BookingIcon } from '@mui/icons-material'
import ActionCardFrame from './ActionCardFrame'
import { clp, num, useActionCard } from './useActionCard'

const SERVICES = [['pizzeros', 'Pizzeros en Acción'], ['party', 'Pizza Party']]
const EVENT_TYPES = [['birthday', 'Cumpleaños'], ['school', 'Colegio'], ['corporate', 'Empresa'], ['private', 'Privado']]

// A NEW booking proposed by the assistant. It is always created as PENDING; confirming it in the
// admin panel (which notifies the customer) is a separate, manual step.
const BookingActionCard = ({ action, getAuthToken, onChange }) => {
  const [draft, setDraft] = useState(action.payload)
  const { busy, error, confirm, cancel, editable } = useActionCard(action, getAuthToken, onChange)
  const set = (field) => (e) => setDraft((d) => ({ ...d, [field]: e.target.value }))
  const toggleService = (service) => setDraft((d) => ({
    ...d,
    services: d.services.includes(service) ? d.services.filter((s) => s !== service) : [...d.services, service]
  }))

  const hasPizzeros = draft.services.includes('pizzeros')
  const hasParty = draft.services.includes('party')
  const issues = []
  if (!draft.client_name?.trim()) issues.push('nombre')
  if (draft.services.length === 0) issues.push('servicio')
  if (hasPizzeros && !(num(draft.pizzeros_participants) >= 1)) issues.push('niños')
  if (hasParty && !(num(draft.pizza_quantity) >= 1)) issues.push('pizzas')
  if (!draft.event_date) issues.push('fecha')
  if (!draft.location?.trim()) issues.push('lugar')

  const priceChanged = JSON.stringify([draft.services, draft.pizzeros_participants, draft.pizza_quantity, draft.comuna])
    !== JSON.stringify([action.payload.services, action.payload.pizzeros_participants, action.payload.pizza_quantity, action.payload.comuna])

  const handleConfirm = () => confirm({
    ...draft,
    client_name: draft.client_name.trim(),
    client_email: draft.client_email?.trim() || null,
    client_phone: draft.client_phone?.trim() || null,
    comuna: draft.comuna?.trim() || null,
    location: draft.location.trim(),
    pizzeros_participants: hasPizzeros ? num(draft.pizzeros_participants) || 0 : 0,
    pizza_quantity: hasParty ? num(draft.pizza_quantity) || 0 : 0,
    participants: num(draft.participants) || 0
  })

  return (
    <ActionCardFrame
      title="Reserva nueva (quedará pendiente)"
      icon={<BookingIcon color="primary" fontSize="small" />}
      action={action}
      editable={editable}
      busy={busy}
      error={error}
      canConfirm={editable && issues.length === 0}
      confirmLabel="Crear reserva"
      onConfirm={handleConfirm}
      onCancel={cancel}
    >
      <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: '1fr 1fr', mt: 0.5 }}>
        <TextField
          label="Cliente" size="small" required value={draft.client_name || ''} onChange={set('client_name')}
          disabled={!editable} sx={{ gridColumn: '1 / -1' }}
        />
        <TextField label="Teléfono" size="small" value={draft.client_phone || ''} onChange={set('client_phone')} disabled={!editable} />
        <TextField label="Correo" size="small" type="email" value={draft.client_email || ''} onChange={set('client_email')} disabled={!editable} />

        <FormGroup row sx={{ gridColumn: '1 / -1' }} aria-label="Servicios">
          {SERVICES.map(([value, label]) => (
            <FormControlLabel
              key={value} label={label} disabled={!editable}
              control={<Checkbox size="small" checked={draft.services.includes(value)} onChange={() => toggleService(value)} />}
            />
          ))}
        </FormGroup>

        <TextField
          label="Fecha" type="date" size="small" required value={draft.event_date || ''} onChange={set('event_date')}
          disabled={!editable} InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Hora" type="time" size="small" value={draft.event_time || ''} onChange={set('event_time')}
          disabled={!editable} InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Lugar" size="small" required value={draft.location || ''} onChange={set('location')}
          disabled={!editable} sx={{ gridColumn: '1 / -1' }}
        />
        <TextField label="Comuna" size="small" value={draft.comuna || ''} onChange={set('comuna')} disabled={!editable} />
        <TextField select label="Tipo de evento" size="small" value={draft.event_type || 'birthday'} onChange={set('event_type')} disabled={!editable}>
          {EVENT_TYPES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
        </TextField>
        {hasPizzeros && (
          <TextField
            label="Niños (Pizzeros)" type="number" size="small" value={draft.pizzeros_participants ?? ''}
            onChange={set('pizzeros_participants')} disabled={!editable} inputProps={{ min: 1, step: 1, inputMode: 'numeric' }}
          />
        )}
        {hasParty && (
          <TextField
            label="Pizzas (Party)" type="number" size="small" value={draft.pizza_quantity ?? ''}
            onChange={set('pizza_quantity')} disabled={!editable} inputProps={{ min: 1, step: 1, inputMode: 'numeric' }}
          />
        )}
        <TextField
          label="Observaciones / alergias" size="small" multiline maxRows={3} value={draft.special_requests || ''}
          onChange={set('special_requests')} disabled={!editable} sx={{ gridColumn: '1 / -1' }}
        />
      </Box>

      <Typography variant="body2" fontWeight={600} textAlign="right" mt={1.25}>
        Precio estimado: {clp(action.context?.estimated_price)}
      </Typography>
      {editable && priceChanged && (
        <Typography variant="caption" color="text.secondary" display="block" textAlign="right">
          Cambiaste servicios, cantidades o comuna: el precio se recalcula al crear la reserva.
        </Typography>
      )}
      {editable && issues.length > 0 && (
        <Typography variant="caption" color="warning.main" display="block" mt={0.5}>Falta: {issues.join(', ')}</Typography>
      )}

      {action.status === 'confirmed' && action.result && (
        <Typography variant="caption" color="success.main" display="block" mt={1}>
          Reserva creada como PENDIENTE ({clp(action.result.estimated_price)}). Confírmala en el panel de reservas cuando corresponda:
          ahí se avisa al cliente.
        </Typography>
      )}
    </ActionCardFrame>
  )
}

export default BookingActionCard
