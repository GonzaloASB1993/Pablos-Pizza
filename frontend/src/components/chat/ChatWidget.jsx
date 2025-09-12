import React, { useState, useEffect, useRef } from 'react'
import {
  Box,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  IconButton,
  Paper,
  Badge,
  Slide,
  Divider,
  Chip
} from '@mui/material'
import {
  Chat as ChatIcon,
  Close as CloseIcon,
  Send as SendIcon,
  SupportAgent
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { useChat } from '../../contexts/ChatContext'
import toast from 'react-hot-toast'

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />
})

const ChatWidget = () => {
  const theme = useTheme()
  const { 
    chatRoom, 
    messages, 
    isConnected, 
    isOpen, 
    unreadCount,
    initializeChatRoom,
    sendMessage,
    openChat,
    closeChat
  } = useChat()

  const [showDialog, setShowDialog] = useState(false)
  const [clientName, setClientName] = useState('')
  const [clientEmail, setClientEmail] = useState('')
  const [newMessage, setNewMessage] = useState('')
  const [isInitializing, setIsInitializing] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages])

  const handleOpenChat = () => {
    if (!chatRoom) {
      setShowDialog(true)
    } else {
      openChat()
    }
  }

  const handleStartChat = async () => {
    if (!clientName.trim() || !clientEmail.trim()) {
      toast.error('Por favor, completa todos los campos')
      return
    }

    setIsInitializing(true)
    try {
      await initializeChatRoom(clientName.trim(), clientEmail.trim())
      setShowDialog(false)
      openChat()
      toast.success('¡Chat iniciado! Un agente te atenderá pronto.')
    } catch (error) {
      console.error('Error starting chat:', error)
      toast.error('Error al iniciar el chat. Intenta nuevamente.')
    } finally {
      setIsInitializing(false)
    }
  }

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !chatRoom) return

    try {
      await sendMessage(newMessage.trim(), clientName)
      setNewMessage('')
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Error al enviar el mensaje')
    }
  }

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSendMessage()
    }
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <>
      {/* Floating Action Button */}
      <Fab
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          zIndex: 1000,
          backgroundColor: theme.palette.primary.main,
          color: theme.palette.secondary.main,
          '&:hover': {
            backgroundColor: theme.palette.primary.dark,
          }
        }}
        onClick={handleOpenChat}
      >
        <Badge badgeContent={unreadCount} color="error">
          <ChatIcon />
        </Badge>
      </Fab>

      {/* Chat Dialog */}
      <Dialog
        open={isOpen && !!chatRoom}
        onClose={closeChat}
        maxWidth="sm"
        fullWidth
        TransitionComponent={Transition}
        PaperProps={{
          sx: {
            position: 'fixed',
            bottom: 20,
            right: 20,
            top: 'auto',
            left: 'auto',
            m: 0,
            height: '500px',
            width: '400px',
            maxWidth: '90vw',
            maxHeight: '80vh'
          }
        }}
      >
        <DialogTitle sx={{ 
          backgroundColor: theme.palette.secondary.main,
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          py: 1
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SupportAgent />
            <Typography variant="h6">
              Chat - Pablo's Pizza
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip 
              label={isConnected ? 'Conectado' : 'Desconectado'}
              size="small"
              color={isConnected ? 'success' : 'default'}
              variant="outlined"
              sx={{ 
                color: 'white',
                borderColor: 'white'
              }}
            />
            <IconButton onClick={closeChat} size="small" sx={{ color: 'white' }}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Messages Area */}
          <Box sx={{ 
            flexGrow: 1,
            p: 2,
            overflowY: 'auto',
            backgroundColor: '#f5f5f5'
          }}>
            {messages.length === 0 && (
              <Paper sx={{ p: 2, textAlign: 'center', mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  ¡Hola {clientName}! 👋 ¿En qué podemos ayudarte hoy?
                </Typography>
              </Paper>
            )}

            {messages.map((message) => (
              <Box
                key={message.id}
                sx={{
                  display: 'flex',
                  justifyContent: message.is_admin ? 'flex-start' : 'flex-end',
                  mb: 1
                }}
              >
                <Paper
                  sx={{
                    p: 1.5,
                    maxWidth: '80%',
                    backgroundColor: message.is_admin 
                      ? 'white' 
                      : theme.palette.primary.main,
                    color: message.is_admin 
                      ? 'text.primary' 
                      : theme.palette.secondary.main,
                  }}
                >
                  {message.is_admin && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      {message.sender_name}
                    </Typography>
                  )}
                  <Typography variant="body2">
                    {message.message}
                  </Typography>
                  <Typography variant="caption" sx={{ 
                    display: 'block', 
                    textAlign: 'right',
                    mt: 0.5,
                    opacity: 0.7
                  }}>
                    {formatTime(message.timestamp)}
                  </Typography>
                </Paper>
              </Box>
            ))}
            <div ref={messagesEndRef} />
          </Box>

          <Divider />

          {/* Message Input */}
          <Box sx={{ p: 2, backgroundColor: 'white' }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Escribe tu mensaje..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                multiline
                maxRows={3}
                disabled={!isConnected}
              />
              <IconButton
                onClick={handleSendMessage}
                disabled={!newMessage.trim() || !isConnected}
                sx={{ 
                  color: theme.palette.primary.main,
                  '&:hover': {
                    backgroundColor: theme.palette.primary.main + '10'
                  }
                }}
              >
                <SendIcon />
              </IconButton>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Initial Contact Dialog */}
      <Dialog open={showDialog} onClose={() => setShowDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Iniciar Chat con Pablo's Pizza
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            ¡Hola! Para brindarte la mejor atención, necesitamos algunos datos básicos.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Tu nombre"
            fullWidth
            variant="outlined"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Tu email"
            type="email"
            fullWidth
            variant="outlined"
            value={clientEmail}
            onChange={(e) => setClientEmail(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDialog(false)}>
            Cancelar
          </Button>
          <Button 
            onClick={handleStartChat}
            variant="contained"
            disabled={isInitializing || !clientName.trim() || !clientEmail.trim()}
          >
            {isInitializing ? 'Iniciando...' : 'Iniciar Chat'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default ChatWidget