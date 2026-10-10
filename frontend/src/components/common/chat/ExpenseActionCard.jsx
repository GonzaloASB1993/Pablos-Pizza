import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography
} from '@mui/material'
import {
  CheckCircle as ConfirmedIcon,
  Cancel as CancelledIcon,
  ReceiptLong as ReceiptIcon,
  WarningAmber as WarningIcon
} from '@mui/icons-material'
import { cancelPending, confirmPending, describeError, fetchPending } from './chatApi'

const CATEGORIES = [
  ['general', 'General'],
  ['servicios', 'Servicios'],
  ['arriendo', 'Arriendo'],
  ['sueldos', 'Sueldos'],
  ['marketing', 'Marketing'],
  ['otros', 'Otros']
]
const DOCUMENT_TYPES = [['boleta', 'Boleta'], ['factura', 'Factura'], ['otro', 'Otro']]
const KINDS = [['variable', 'Puntual'], ['fixed', 'Fijo mensual']]

const clp = (n) => `$${Math.round(Number(n) || 0).toLocaleString('es-CL')}`

const STATUS_LABEL = {
  confirmed: { label: 'Confirmada', color: 'success', Icon: ConfirmedIcon },
  cancelled: { label: 'Cancelada', color: 'default', Icon: CancelledIcon },
  expired: { label: 'Expirada', color: 'warning', Icon: WarningIcon },
  processing: { label: 'Procesando…', color: 'info', Icon: null }
}

const ExpenseActionCard = ({ action, getAuthToken, onChange }) => {
  const [draft, setDraft] = useState(action.payload)
  const [busy, setBusy] = useState(null) // 'confirm' | 'cancel' | null
  const [error, setError] = useState(null)

  const editable = action.status === 'pending' || action.status === 'failed'
  const set = (field) => (e) => setDraft((d) => ({ ...d, [field]: e.target.value }))

  // The card may have been resolved elsewhere (other device) or expired since it was stored
  useEffect(() => {
    if (action.status !== 'pending') return undefined
    let alive = true
    fetchPending(getAuthToken, action.id)
      .then((fresh) => {
        if (alive && fresh.status !== action.status) onChange(fresh)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action.id])

  const linesTotal = useMemo(
    () => (draft.lines || []).reduce((sum, l) => sum + (Number(l.amount) || 0), 0),
    [draft.lines]
  )
  const linesMismatch = draft.lines?.length > 0 && Math.abs(linesTotal - Number(draft.total)) > 1
  const totalNumber = Number(draft.total)
  const canConfirm = editable && draft.supplier?.trim() && draft.date && totalNumber > 0

  const run = async (kind, fn) => {
    setBusy(kind)
    setError(null)
    try {
      onChange(await fn())
    } catch (err) {
      setError(describeError(err).message)
    } finally {
      setBusy(null)
    }
  }

  const handleConfirm = () =>
    run('confirm', () => confirmPending(getAuthToken, action.id, {
      ...draft,
      total: totalNumber,
      folio: draft.folio?.trim() || null
    }))

  const handleCancel = () => run('cancel', () => cancelPending(getAuthToken, action.id))

  const status = STATUS_LABEL[action.status]
  const isFixed = draft.kind === 'fixed'

  return (
    <Paper
      variant="outlined"
      component="section"
      aria-label="Propuesta de gasto"
      sx={{ p: 2, mt: 1, borderRadius: 2, borderColor: editable ? 'primary.main' : 'divider' }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1} gap={1}>
        <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
          <ReceiptIcon color="primary" fontSize="small" />
          <Typography variant="subtitle2" fontWeight={700} noWrap>
            Propuesta de gasto
          </Typography>
        </Stack>
        {status && (
          <Chip
            size="small"
            color={status.color}
            label={status.label}
            icon={status.Icon ? <status.Icon /> : undefined}
          />
        )}
      </Stack>

      {action.status === 'pending' && (
        <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
          Todavía no se guardó nada. Revisa los datos y confirma.
        </Typography>
      )}

      {editable && action.warnings?.map((w) => (
        <Alert key={w} severity="warning" icon={<WarningIcon fontSize="inherit" />} sx={{ mb: 1, py: 0 }}>
          {w}
        </Alert>
      ))}
      {editable && linesMismatch && (
        <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
          El total ({clp(totalNumber)}) no coincide con la suma de las líneas ({clp(linesTotal)}).
        </Alert>
      )}

      <Box
        sx={{
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: '1fr 1fr',
          mt: 1
        }}
      >
        <TextField
          label="Proveedor" size="small" value={draft.supplier || ''}
          onChange={set('supplier')} disabled={!editable} required
          sx={{ gridColumn: '1 / -1' }}
        />
        <TextField
          label="Fecha" type="date" size="small" value={draft.date || ''}
          onChange={set('date')} disabled={!editable} required
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Total (CLP)" type="number" size="small" value={draft.total ?? ''}
          onChange={set('total')} disabled={!editable} required
          inputProps={{ min: 1, step: 1, inputMode: 'numeric' }}
        />
        <TextField
          select label="Tipo de gasto" size="small" value={draft.kind || 'variable'}
          onChange={set('kind')} disabled={!editable}
        >
          {KINDS.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <TextField
          select label="Categoría" size="small" value={draft.category || 'general'}
          onChange={set('category')} disabled={!editable}
        >
          {CATEGORIES.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <TextField
          select label="Documento" size="small" value={draft.document_type || 'boleta'}
          onChange={set('document_type')} disabled={!editable}
        >
          {DOCUMENT_TYPES.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <TextField
          label="Folio" size="small" value={draft.folio || ''}
          onChange={set('folio')} disabled={!editable}
        />
        <TextField
          label="Notas" size="small" value={draft.notes || ''} multiline maxRows={3}
          onChange={set('notes')} disabled={!editable}
          sx={{ gridColumn: '1 / -1' }}
        />
      </Box>

      {isFixed && editable && (
        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          Un gasto fijo se cuenta todos los meses desde {draft.date?.slice(0, 7)}.
        </Typography>
      )}

      {draft.lines?.length > 0 && (
        <Box component="details" sx={{ mt: 1.5 }}>
          <Typography component="summary" variant="caption" color="text.secondary" sx={{ cursor: 'pointer' }}>
            {draft.lines.length} línea{draft.lines.length === 1 ? '' : 's'} leída{draft.lines.length === 1 ? '' : 's'}
          </Typography>
          <Box component="table" sx={{ width: '100%', fontSize: '0.8rem', mt: 0.5, borderCollapse: 'collapse' }}>
            <tbody>
              {draft.lines.map((line, i) => (
                <tr key={`${line.description}-${i}`}>
                  <td>{line.description || '—'}</td>
                  <Box component="td" sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{clp(line.amount)}</Box>
                </tr>
              ))}
            </tbody>
          </Box>
        </Box>
      )}

      {action.attachments?.length > 0 && (
        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          📎 {action.attachments.length} foto{action.attachments.length === 1 ? '' : 's'} guardada{action.attachments.length === 1 ? '' : 's'} como respaldo
        </Typography>
      )}

      {action.status === 'failed' && (
        <Alert severity="error" sx={{ mt: 1.5 }}>
          No se pudo guardar. Puedes reintentar.
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert>}

      {editable && (
        <Stack direction="row" gap={1} justifyContent="flex-end" mt={2}>
          <Button onClick={handleCancel} disabled={!!busy} color="inherit">
            {busy === 'cancel' ? <CircularProgress size={18} /> : 'Cancelar'}
          </Button>
          <Button variant="contained" onClick={handleConfirm} disabled={!canConfirm || !!busy}>
            {busy === 'confirm' ? <CircularProgress size={18} color="inherit" /> : 'Confirmar gasto'}
          </Button>
        </Stack>
      )}

      {action.status === 'confirmed' && (
        <Typography variant="caption" color="success.main" display="block" mt={1.5}>
          {action.already_confirmed ? 'Ya estaba registrado.' : 'Gasto registrado.'} {clp(action.payload.total)} · {action.payload.supplier}
        </Typography>
      )}
    </Paper>
  )
}

export default ExpenseActionCard
