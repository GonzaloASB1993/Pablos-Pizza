import { Alert, Button, Chip, CircularProgress, Paper, Stack, Typography } from '@mui/material'
import {
  Cancel as CancelledIcon,
  CheckCircle as ConfirmedIcon,
  WarningAmber as WarningIcon
} from '@mui/icons-material'

const STATUS = {
  confirmed: { label: 'Confirmada', color: 'success', Icon: ConfirmedIcon },
  cancelled: { label: 'Cancelada', color: 'default', Icon: CancelledIcon },
  expired: { label: 'Expirada', color: 'warning', Icon: WarningIcon },
  processing: { label: 'Procesando…', color: 'info', Icon: null }
}

// Common chrome of an action card: title + status chip, "nothing saved yet" note, warnings,
// error, and the Cancel / Confirm buttons.
const ActionCardFrame = ({
  title, icon, action, editable, busy, error, canConfirm, confirmLabel, onConfirm, onCancel, extraWarnings = [], children
}) => {
  const status = STATUS[action.status]
  return (
    <Paper
      variant="outlined"
      component="section"
      aria-label={title}
      sx={{ p: 2, mt: 1, borderRadius: 2, borderColor: editable ? 'primary.main' : 'divider' }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1} gap={1}>
        <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
          {icon}
          <Typography variant="subtitle2" component="h3" fontWeight={700} noWrap>{title}</Typography>
        </Stack>
        {status && (
          <Chip size="small" color={status.color} label={status.label} icon={status.Icon ? <status.Icon /> : undefined} />
        )}
      </Stack>

      <Typography variant="body2" sx={{ mb: 1 }}>{action.summary}</Typography>

      {action.status === 'pending' && (
        <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
          Todavía no se guardó nada. Revisa los datos y confirma.
        </Typography>
      )}

      {editable && [...(action.warnings || []), ...extraWarnings].map((w) => (
        <Alert key={w} severity="warning" icon={<WarningIcon fontSize="inherit" />} sx={{ mb: 1, py: 0 }}>{w}</Alert>
      ))}

      {children}

      {action.attachments?.length > 0 && (
        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          📎 {action.attachments.length} foto{action.attachments.length === 1 ? '' : 's'} guardada{action.attachments.length === 1 ? '' : 's'} como respaldo
        </Typography>
      )}

      {action.status === 'failed' && (
        <Alert severity="error" sx={{ mt: 1.5 }}>
          No se pudo guardar completo. Lo que ya se aplicó no se repetirá al reintentar.
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert>}

      {editable && (
        <Stack direction="row" gap={1} justifyContent="flex-end" mt={2}>
          <Button onClick={onCancel} disabled={!!busy} color="inherit">
            {busy === 'cancel' ? <CircularProgress size={18} /> : 'Cancelar'}
          </Button>
          <Button variant="contained" onClick={onConfirm} disabled={!canConfirm || !!busy}>
            {busy === 'confirm' ? <CircularProgress size={18} color="inherit" /> : confirmLabel}
          </Button>
        </Stack>
      )}
    </Paper>
  )
}

export default ActionCardFrame
