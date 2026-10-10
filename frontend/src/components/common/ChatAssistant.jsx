import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  Divider,
  IconButton,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme
} from '@mui/material'
import {
  AddPhotoAlternate as GalleryIcon,
  CameraAlt as CameraIcon,
  Close as CloseIcon,
  DeleteSweep as NewChatIcon,
  Send as SendIcon,
  SmartToy as BotIcon
} from '@mui/icons-material'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import ChatMarkdown from './chat/ChatMarkdown'
import ExpenseActionCard from './chat/ExpenseActionCard'
import ReceiptActionCard from './chat/ReceiptActionCard'
import SimpleActionCard from './chat/SimpleActionCard'
import EventInventoryCard from './chat/EventInventoryCard'
import { describeError, sendChat } from './chat/chatApi'
import { compressImage, MAX_IMAGES } from './chat/imageUtils'

const STORAGE_PREFIX = 'pablos-ai-chat-v1:'
const MAX_STORED_MESSAGES = 40
const IMAGE_PLACEHOLDER = '[imagen enviada]'

const TOOL_LABELS = {
  get_bookings: 'reservas',
  get_events: 'eventos',
  get_inventory_status: 'inventario',
  get_contacts: 'contactos',
  get_financial_summary: 'finanzas',
  get_expenses_summary: 'gastos',
  search_inventory: 'búsqueda en inventario',
  propose_expense: 'propuesta de gasto',
  propose_receipt: 'propuesta de compra',
  propose_inventory_item: 'propuesta de insumo',
  propose_inventory_purchase: 'propuesta de compra',
  propose_inventory_update: 'propuesta de cambios',
  propose_stock_adjustment: 'propuesta de ajuste',
  search_bookings: 'reservas',
  propose_event_supplies: 'propuesta de insumos del evento',
  propose_event_consumption: 'propuesta de consumo del evento'
}

// action.type -> card component (unknown types fall back to a plain confirm/cancel card)
const ACTION_CARDS = {
  expense: ExpenseActionCard,
  inventory_receipt: ReceiptActionCard,
  inventory_update: SimpleActionCard,
  stock_adjustment: SimpleActionCard,
  event_supplies: EventInventoryCard,
  event_consumption: EventInventoryCard
}

const SUGGESTIONS = [
  { label: 'Subir boleta', action: 'upload' },
  { label: '¿Qué tengo esta semana?', text: '¿Qué eventos y reservas tengo esta semana?' },
  { label: 'Estado del inventario', text: '¿Cómo está el inventario? ¿Qué debo reponer?' },
  { label: 'Hacer un conteo', text: 'Quiero registrar un conteo de stock de un insumo' },
  { label: 'Gastos del mes', text: '¿Cuánto he gastado este mes, por categoría?' }
]

let idCounter = 0
const newId = () => `${Date.now()}-${idCounter++}`

// localStorage can throw (private mode, quota, blocked): the chat must work without it
const loadStored = (key) => {
  try {
    const raw = window.localStorage.getItem(key)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const saveStored = (key, messages) => {
  try {
    // Photos are never persisted (size + privacy): keep only that there was one
    const slim = messages.slice(-MAX_STORED_MESSAGES).map(({ images, imagePayloads, ...rest }) => ({
      ...rest,
      imageCount: images?.length || rest.imageCount || 0
    }))
    window.localStorage.setItem(key, JSON.stringify(slim))
  } catch {
    // ignore
  }
}

// What the server receives: text for the history, image blocks only for the message being sent
const toApiMessages = (messages) => {
  const lastIndex = messages.length - 1
  const api = messages
    .map((m, index) => {
      if (m.role === 'assistant') {
        return m.content?.trim() ? { role: 'assistant', content: m.content } : null
      }
      const text = m.content || ''
      if (index === lastIndex && m.images?.length && m.imagePayloads?.length) {
        return {
          role: 'user',
          content: [
            ...(text ? [{ type: 'text', text }] : []),
            ...m.imagePayloads.map((img) => ({
              type: 'image',
              source: { type: 'base64', media_type: img.media_type, data: img.data }
            }))
          ]
        }
      }
      const imageNote = (m.images?.length || m.imageCount) ? ` ${IMAGE_PLACEHOLDER}` : ''
      const content = `${text}${imageNote}`.trim()
      return content ? { role: 'user', content } : null
    })
    .filter(Boolean)

  const trimmed = api.slice(-38)
  while (trimmed.length && trimmed[0].role !== 'user') trimmed.shift()
  return trimmed
}

const Avatar = () => (
  <Box
    aria-hidden="true"
    sx={{
      width: 32, height: 32, borderRadius: '50%', bgcolor: 'primary.main', flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}
  >
    <BotIcon sx={{ color: 'primary.contrastText', fontSize: 18 }} />
  </Box>
)

const ChatAssistant = ({ open, onClose }) => {
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'))
  const { user, getAuthToken } = useAuth()
  const storageKey = `${STORAGE_PREFIX}${user?.uid || 'anon'}`

  const [messages, setMessages] = useState(() => loadStored(storageKey))
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState([]) // {preview, media_type, data}
  const [loading, setLoading] = useState(false)
  const [loadingLong, setLoadingLong] = useState(false)
  const [error, setError] = useState(null) // {message, retryable}
  const [confirmingClear, setConfirmingClear] = useState(false)
  const [model, setModel] = useState(null)

  const endRef = useRef(null)
  const inputRef = useRef(null)
  const cameraRef = useRef(null)
  const galleryRef = useRef(null)

  useEffect(() => {
    saveStored(storageKey, messages)
  }, [messages, storageKey])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading, error])

  useEffect(() => {
    if (!open) return undefined
    const t = setTimeout(() => inputRef.current?.focus(), 150)
    return () => clearTimeout(t)
  }, [open])

  useEffect(() => {
    if (!loading) {
      setLoadingLong(false)
      return undefined
    }
    const t = setTimeout(() => setLoadingLong(true), 8000)
    return () => clearTimeout(t)
  }, [loading])

  const requestReply = useCallback(async (history) => {
    setLoading(true)
    setError(null)
    try {
      const data = await sendChat(getAuthToken, toApiMessages(history))
      setModel(data.model || null)
      setMessages([
        // the raw photo bytes are only needed until the server has answered (retry)
        ...history.map(({ imagePayloads, ...rest }) => rest),
        {
          id: newId(),
          role: 'assistant',
          content: data.response || '',
          tools: [...new Set((data.tools_used || []).map((t) => TOOL_LABELS[t.name]).filter(Boolean))],
          actions: data.pending_actions || [],
          choices: data.choices || []
        }
      ])
    } catch (err) {
      console.error('Error calling AI:', err)
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }, [getAuthToken])

  const send = useCallback(async (textOverride, display) => {
    const text = (textOverride ?? input).trim()
    if ((!text && attachments.length === 0) || loading) return

    const userMessage = {
      id: newId(),
      role: 'user',
      content: text,
      ...(display ? { display } : {}),
      images: attachments.map((a) => a.preview),
      imagePayloads: attachments
    }
    const history = [...messages, userMessage]
    setInput('')
    setAttachments([])
    setMessages(history)
    await requestReply(history)
  }, [input, attachments, loading, messages, requestReply])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  const handleFiles = async (event) => {
    const files = Array.from(event.target.files || [])
    event.target.value = '' // allow choosing the same photo again
    const room = MAX_IMAGES - attachments.length
    if (files.length > room) {
      toast.error(`Máximo ${MAX_IMAGES} fotos por mensaje`)
    }
    for (const file of files.slice(0, Math.max(room, 0))) {
      try {
        const compressed = await compressImage(file)
        setAttachments((prev) => (prev.length < MAX_IMAGES ? [...prev, compressed] : prev))
      } catch (err) {
        toast.error(err.message || 'No se pudo procesar la foto')
      }
    }
  }

  const updateAction = (messageId, updated) => {
    setMessages((prev) => prev.map((m) => (
      m.id === messageId
        ? { ...m, actions: m.actions.map((a) => (a.id === updated.id ? updated : a)) }
        : m
    )))
  }

  const startNewConversation = () => {
    setMessages([])
    setAttachments([])
    setError(null)
    setConfirmingClear(false)
    setInput('')
    inputRef.current?.focus()
  }

  const retry = () => requestReply(messages)

  const canSend = (input.trim() || attachments.length > 0) && !loading
  const atImageLimit = attachments.length >= MAX_IMAGES

  const handleSuggestion = (s) => {
    if (s.action === 'upload') {
      cameraRef.current?.click()
    } else {
      send(s.text)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      fullScreen={fullScreen}
      aria-labelledby="ai-chat-title"
      PaperProps={{
        sx: {
          height: fullScreen ? '100dvh' : '85vh',
          maxHeight: fullScreen ? 'none' : 800,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: fullScreen ? 0 : 2
        }
      }}
    >
      {/* Header */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          bgcolor: 'primary.main', color: 'primary.contrastText', px: 2, py: 1.25,
          pt: fullScreen ? 'max(10px, env(safe-area-inset-top))' : 1.25
        }}
      >
        <Stack direction="row" alignItems="center" gap={1.25} minWidth={0}>
          <BotIcon />
          <Box minWidth={0}>
            <Typography id="ai-chat-title" variant="subtitle1" component="h2" fontWeight={700} color="inherit" noWrap>
              Asistente de Pablo's Pizza
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.85 }} noWrap component="div">
              {model ? `Claude · ${model.replace(/^claude-/, '')}` : 'Claude'}
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" alignItems="center">
          {messages.length > 0 && !confirmingClear && (
            <Tooltip title="Nueva conversación">
              <IconButton onClick={() => setConfirmingClear(true)} sx={{ color: 'inherit' }} aria-label="Nueva conversación">
                <NewChatIcon />
              </IconButton>
            </Tooltip>
          )}
          {confirmingClear && (
            <Stack direction="row" alignItems="center" gap={0.5} mr={0.5}>
              <Typography variant="caption">¿Borrar todo?</Typography>
              <Button size="small" color="inherit" onClick={startNewConversation} sx={{ minWidth: 0 }}>Sí</Button>
              <Button size="small" color="inherit" onClick={() => setConfirmingClear(false)} sx={{ minWidth: 0 }}>No</Button>
            </Stack>
          )}
          <IconButton onClick={onClose} sx={{ color: 'inherit' }} aria-label="Cerrar asistente">
            <CloseIcon />
          </IconButton>
        </Stack>
      </Stack>

      {/* Messages */}
      <Box
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Conversación"
        sx={{
          flex: 1, overflowY: 'auto', p: { xs: 1.5, sm: 2 }, display: 'flex', flexDirection: 'column', gap: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50'
        }}
      >
        {messages.length === 0 && (
          <Stack alignItems="center" justifyContent="center" flex={1} gap={2} textAlign="center" py={3}>
            <BotIcon sx={{ fontSize: 56, color: 'primary.main', opacity: 0.6 }} />
            <Typography variant="h6" component="p">¡Hola! ¿En qué te ayudo?</Typography>
            <Typography variant="body2" color="text.secondary" maxWidth={440}>
              Consulta reservas, inventario y finanzas, o súbeme la foto de una boleta para dejarte lista la propuesta de gasto.
            </Typography>
          </Stack>
        )}

        {messages.map((m, index) => (
          <Box key={m.id} sx={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', gap: 1 }}>
            {m.role === 'assistant' && <Avatar />}
            <Box sx={{ maxWidth: { xs: '92%', sm: '82%' }, minWidth: 0 }}>
              <Paper
                elevation={0}
                sx={{
                  px: 1.75, py: 1.25, borderRadius: 2.5,
                  bgcolor: m.role === 'user' ? 'primary.main' : 'background.paper',
                  color: m.role === 'user' ? 'primary.contrastText' : 'text.primary',
                  border: m.role === 'user' ? 'none' : 1, borderColor: 'divider'
                }}
              >
                {m.images?.length > 0 && (
                  <Stack direction="row" gap={0.75} flexWrap="wrap" mb={m.content ? 1 : 0}>
                    {m.images.map((src, i) => (
                      <Box
                        key={i} component="img" src={src} alt={`Foto adjunta ${i + 1}`}
                        sx={{ width: 96, height: 96, objectFit: 'cover', borderRadius: 1.5 }}
                      />
                    ))}
                  </Stack>
                )}
                {!m.images?.length && m.imageCount > 0 && (
                  <Typography variant="caption" sx={{ opacity: 0.85 }} display="block">
                    📷 {m.imageCount} foto{m.imageCount === 1 ? '' : 's'}
                  </Typography>
                )}
                {m.role === 'assistant'
                  ? (m.content ? <ChatMarkdown>{m.content}</ChatMarkdown> : null)
                  : ((m.display || m.content) && (
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {m.display || m.content}
                    </Typography>
                  ))}
              </Paper>

              {m.choices?.length > 0 && index === messages.length - 1 && !loading && (
                <Stack direction="row" gap={1} flexWrap="wrap" mt={1} role="group" aria-label="Opciones">
                  {m.choices.map((choice) => (
                    <Chip
                      key={choice.id} label={choice.label} color="primary" variant="outlined" clickable
                      onClick={() => send(`${choice.label} [id: ${choice.id}]`, choice.label)}
                      sx={{ height: 'auto', py: 0.75, '& .MuiChip-label': { whiteSpace: 'normal', textAlign: 'left' } }}
                    />
                  ))}
                </Stack>
              )}

              {m.tools?.length > 0 && (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.5} ml={0.5}>
                  Consultó: {m.tools.join(', ')}
                </Typography>
              )}

              {m.actions?.map((action) => {
                const Card = ACTION_CARDS[action.type] || SimpleActionCard
                return (
                  <Card
                    key={action.id}
                    action={action}
                    getAuthToken={getAuthToken}
                    onChange={(updated) => updateAction(m.id, updated)}
                  />
                )
              })}
            </Box>
          </Box>
        ))}

        {loading && (
          <Stack direction="row" alignItems="center" gap={1} aria-busy="true">
            <Avatar />
            <Paper elevation={0} sx={{ px: 1.75, py: 1.25, borderRadius: 2.5, border: 1, borderColor: 'divider' }}>
              <Stack direction="row" alignItems="center" gap={1}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">
                  {messages[messages.length - 1]?.images?.length
                    ? 'Leyendo la foto…'
                    : 'Consultando tus datos…'}
                  {loadingLong && ' Esto puede tardar un poco.'}
                </Typography>
              </Stack>
            </Paper>
          </Stack>
        )}

        {error && (
          <Alert
            severity="error"
            onClose={() => setError(null)}
            action={error.retryable && (
              <Button color="inherit" size="small" onClick={retry} disabled={loading}>
                Reintentar
              </Button>
            )}
          >
            {error.message}
          </Alert>
        )}

        <div ref={endRef} />
      </Box>

      <Divider />

      {/* Composer */}
      <Box
        sx={{
          p: 1.5, pb: fullScreen ? 'max(12px, env(safe-area-inset-bottom))' : 1.5,
          bgcolor: 'background.paper'
        }}
      >
        {messages.length === 0 && (
          <Stack direction="row" gap={1} flexWrap="wrap" mb={1.25}>
            {SUGGESTIONS.map((s) => (
              <Chip
                key={s.label} label={s.label} variant="outlined" color="primary" clickable
                onClick={() => handleSuggestion(s)} disabled={loading}
              />
            ))}
          </Stack>
        )}

        {attachments.length > 0 && (
          <Stack direction="row" gap={1} mb={1.25} aria-label="Fotos para enviar">
            {attachments.map((a, i) => (
              <Box key={i} sx={{ position: 'relative' }}>
                <Box
                  component="img" src={a.preview} alt={`Vista previa ${i + 1}`}
                  sx={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 1.5, display: 'block' }}
                />
                <IconButton
                  size="small"
                  aria-label={`Quitar foto ${i + 1}`}
                  onClick={() => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
                  sx={{
                    position: 'absolute', top: -8, right: -8, bgcolor: 'background.paper',
                    border: 1, borderColor: 'divider', p: 0.25,
                    '&:hover': { bgcolor: 'background.paper' }
                  }}
                >
                  <CloseIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Box>
            ))}
          </Stack>
        )}

        <Stack direction="row" alignItems="flex-end" gap={0.5}>
          <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={handleFiles} />
          <input ref={galleryRef} type="file" accept="image/*" multiple hidden onChange={handleFiles} />
          <Tooltip title="Tomar foto">
            <span>
              <IconButton onClick={() => cameraRef.current?.click()} disabled={loading || atImageLimit} aria-label="Tomar foto" color="primary">
                <CameraIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Elegir de la galería">
            <span>
              <IconButton onClick={() => galleryRef.current?.click()} disabled={loading || atImageLimit} aria-label="Elegir foto de la galería" color="primary">
                <GalleryIcon />
              </IconButton>
            </span>
          </Tooltip>
          <TextField
            inputRef={inputRef}
            fullWidth
            size="small"
            placeholder="Escribe tu pregunta…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            multiline
            maxRows={4}
            inputProps={{ 'aria-label': 'Mensaje', enterKeyHint: 'send' }}
            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 3 } }}
          />
          <IconButton
            onClick={() => send()}
            disabled={!canSend}
            aria-label="Enviar mensaje"
            sx={{
              bgcolor: canSend ? 'primary.main' : 'action.disabledBackground',
              color: canSend ? 'primary.contrastText' : 'action.disabled',
              '&:hover': { bgcolor: canSend ? 'primary.dark' : 'action.disabledBackground' }
            }}
          >
            <SendIcon />
          </IconButton>
        </Stack>
        <Typography variant="caption" color="text.disabled" display="block" mt={0.75} textAlign="center">
          Enter envía · Shift+Enter nueva línea · El asistente propone, tú confirmas
        </Typography>
      </Box>
    </Dialog>
  )
}

export default ChatAssistant
