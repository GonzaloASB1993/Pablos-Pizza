import { useState, useRef, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  TextField,
  IconButton,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Divider,
  Fade,
  useTheme
} from '@mui/material'
import {
  Close as CloseIcon,
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Delete as DeleteIcon
} from '@mui/icons-material'
import axios from 'axios'
import toast from 'react-hot-toast'

// API Configuration
const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const BASE_URL = isDevelopment
  ? 'http://localhost:8000/api'
  : 'https://main-4kqeqojbsq-uc.a.run.app/api'

const ChatAssistant = ({ open, onClose }) => {
  const theme = useTheme()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Focus input when dialog opens
  useEffect(() => {
    if (open) {
      setTimeout(() => {
        inputRef.current?.focus()
      }, 100)
    }
  }, [open])

  // Send message to AI
  const handleSendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setError(null)

    // Add user message to chat
    const newMessages = [...messages, { role: 'user', content: userMessage }]
    setMessages(newMessages)
    setLoading(true)

    try {
      // Call AI API
      const response = await axios.post(`${BASE_URL}/ai-chat/`, {
        messages: newMessages
      }, {
        timeout: 120000 // 2 minutes for complex queries
      })

      // Add AI response to chat
      setMessages([
        ...newMessages,
        { role: 'assistant', content: response.data.response }
      ])

      // Log usage for cost tracking
      console.log('AI Usage:', response.data.usage)

    } catch (err) {
      console.error('Error calling AI:', err)

      let errorMessage = 'Error al comunicarse con el asistente AI'
      if (err.response?.data?.error) {
        errorMessage = err.response.data.error
      } else if (err.code === 'ECONNABORTED') {
        errorMessage = 'La consulta tardó demasiado. Por favor intenta de nuevo.'
      } else if (!navigator.onLine) {
        errorMessage = 'No hay conexión a internet'
      }

      setError(errorMessage)
      toast.error(errorMessage)

    } finally {
      setLoading(false)
    }
  }

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Clear conversation
  const handleClearChat = () => {
    if (window.confirm('¿Deseas borrar toda la conversación?')) {
      setMessages([])
      setError(null)
      toast.success('Conversación borrada')
    }
  }

  // Close dialog and reset if needed
  const handleClose = () => {
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          height: '85vh',
          maxHeight: '800px',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 2,
        }
      }}
    >
      {/* Dialog Title/Header */}
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          bgcolor: theme.palette.primary.main,
          color: 'white',
          py: 2
        }}
      >
        <Box display="flex" alignItems="center" gap={1.5}>
          <BotIcon sx={{ fontSize: 32 }} />
          <Box>
            <Typography variant="h6" component="div" fontWeight={600}>
              Asistente IA Pablo's Pizza
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              Powered by Claude Sonnet 4.5
            </Typography>
          </Box>
        </Box>
        <Box>
          {messages.length > 0 && (
            <IconButton
              onClick={handleClearChat}
              sx={{ color: 'white', mr: 1 }}
              title="Borrar conversación"
            >
              <DeleteIcon />
            </IconButton>
          )}
          <IconButton onClick={handleClose} sx={{ color: 'white' }}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      {/* Messages Area */}
      <DialogContent
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Welcome message when empty */}
        {messages.length === 0 && (
          <Fade in timeout={500}>
            <Box
              display="flex"
              flexDirection="column"
              justifyContent="center"
              alignItems="center"
              flex={1}
              gap={3}
            >
              <BotIcon sx={{ fontSize: 80, color: 'primary.main', opacity: 0.5 }} />
              <Typography variant="h5" color="text.secondary" textAlign="center">
                ¡Hola! Soy tu asistente IA
              </Typography>
              <Typography variant="body1" color="text.secondary" textAlign="center" maxWidth={500}>
                Puedo ayudarte con información sobre eventos, reservas, inventario, finanzas y más.
                Pregúntame lo que necesites.
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Ejemplos:
                </Typography>
                <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                  <Typography variant="body2" color="text.secondary">
                    • "¿Qué eventos tengo esta semana?"
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • "¿Cómo está el inventario?"
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • "¿Cuáles son mis números del mes?"
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • "¿Hay algo urgente que deba atender?"
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Fade>
        )}

        {/* Message bubbles */}
        {messages.map((message, index) => (
          <Fade in key={index} timeout={300}>
            <Box
              sx={{
                display: 'flex',
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                mb: 2
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  gap: 1,
                  maxWidth: '80%',
                  flexDirection: message.role === 'user' ? 'row-reverse' : 'row'
                }}
              >
                {/* Avatar */}
                <Box
                  sx={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    bgcolor: message.role === 'user' ? 'secondary.main' : 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  {message.role === 'user' ? (
                    <PersonIcon sx={{ color: 'white', fontSize: 20 }} />
                  ) : (
                    <BotIcon sx={{ color: 'white', fontSize: 20 }} />
                  )}
                </Box>

                {/* Message bubble */}
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: message.role === 'user'
                      ? 'secondary.main'
                      : 'background.paper',
                    color: message.role === 'user'
                      ? 'white'
                      : 'text.primary',
                    borderTopRightRadius: message.role === 'user' ? 0 : 2,
                    borderTopLeftRadius: message.role === 'user' ? 2 : 0,
                  }}
                >
                  <Typography
                    variant="body1"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      '& strong': { fontWeight: 700 }
                    }}
                  >
                    {message.content}
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Fade>
        ))}

        {/* Loading indicator */}
        {loading && (
          <Fade in>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  bgcolor: 'primary.main',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <BotIcon sx={{ color: 'white', fontSize: 20 }} />
              </Box>
              <Paper elevation={1} sx={{ p: 2, borderRadius: 2 }}>
                <Box display="flex" alignItems="center" gap={1}>
                  <CircularProgress size={16} />
                  <Typography variant="body2" color="text.secondary">
                    Pensando...
                  </Typography>
                </Box>
              </Paper>
            </Box>
          </Fade>
        )}

        {/* Error message */}
        {error && (
          <Fade in>
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          </Fade>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </DialogContent>

      <Divider />

      {/* Input Area */}
      <DialogActions sx={{ p: 2, bgcolor: 'background.paper' }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          variant="outlined"
          placeholder="Escribe tu pregunta..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          multiline
          maxRows={3}
          InputProps={{
            endAdornment: (
              <IconButton
                onClick={handleSendMessage}
                disabled={!input.trim() || loading}
                color="primary"
                sx={{
                  ml: 1,
                  bgcolor: input.trim() && !loading ? 'primary.main' : 'transparent',
                  color: input.trim() && !loading ? 'white' : 'inherit',
                  '&:hover': {
                    bgcolor: input.trim() && !loading ? 'primary.dark' : 'transparent'
                  }
                }}
              >
                <SendIcon />
              </IconButton>
            )
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 3,
              pr: 0.5
            }
          }}
        />
      </DialogActions>
    </Dialog>
  )
}

export default ChatAssistant
