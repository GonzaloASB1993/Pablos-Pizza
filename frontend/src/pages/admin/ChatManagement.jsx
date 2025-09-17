import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Alert,
  IconButton
} from '@mui/material'
import {
  Chat,
  Mark​EmailRead,
  MarkEmailUnread,
  Reply,
  Close,
  WhatsApp,
  Phone,
  Email,
  CheckCircle,
  AccessTime
} from '@mui/icons-material'
import toast from 'react-hot-toast'
import { CONTACT_INFO } from '../../config/constants'

const ChatManagement = () => {
  const [chats, setChats] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedChat, setSelectedChat] = useState(null)
  const [replyDialog, setReplyDialog] = useState(false)
  const [response, setResponse] = useState('')

  // Datos de ejemplo para demostración
  const mockChats = [
    {
      id: 1,
      customer_name: 'María González',
      customer_email: 'maria@example.com',
      customer_phone: '+56912345678',
      subject: 'Consulta sobre Pizza Party',
      message: 'Hola, quisiera saber los precios para una pizza party de 15 niños. ¿Qué incluye el servicio?',
      status: 'pending',
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 horas atrás
      responded_at: null
    },
    {
      id: 2,
      customer_name: 'Carlos Rodríguez',
      customer_email: 'carlos@example.com',
      customer_phone: '+56987654321',
      subject: 'Disponibilidad fin de semana',
      message: 'Buenos días, necesito saber si tienen disponibilidad para el próximo sábado 20 de enero para un cumpleaños.',
      status: 'responded',
      created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 día atrás
      responded_at: new Date(Date.now() - 22 * 60 * 60 * 1000)
    },
    {
      id: 3,
      customer_name: 'Ana Martínez',
      customer_email: 'ana@example.com',
      customer_phone: '+56911111111',
      subject: 'Cambio de fecha',
      message: 'Hola, tengo una reserva para el 15 de enero pero necesito cambiarla al 22. ¿Es posible?',
      status: 'pending',
      created_at: new Date(Date.now() - 30 * 60 * 1000), // 30 minutos atrás
      responded_at: null
    }
  ]

  useEffect(() => {
    // Simular carga de datos
    setTimeout(() => {
      setChats(mockChats)
      setLoading(false)
    }, 1000)
  }, [])

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      responded: 'success',
      resolved: 'info'
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pendiente',
      responded: 'Respondido',
      resolved: 'Resuelto'
    }
    return labels[status] || status
  }

  const formatTimeAgo = (date) => {
    const now = new Date()
    const diffInMinutes = Math.floor((now - date) / (1000 * 60))

    if (diffInMinutes < 60) {
      return `${diffInMinutes} min`
    } else if (diffInMinutes < 1440) {
      return `${Math.floor(diffInMinutes / 60)} h`
    } else {
      return `${Math.floor(diffInMinutes / 1440)} d`
    }
  }

  const handleViewChat = (chat) => {
    setSelectedChat(chat)
  }

  const handleReplyClick = (chat) => {
    setSelectedChat(chat)
    setReplyDialog(true)
  }

  const handleMarkResolved = (chatId) => {
    setChats(prev => prev.map(chat =>
      chat.id === chatId
        ? { ...chat, status: 'resolved', responded_at: new Date() }
        : chat
    ))
    toast.success('Consulta marcada como resuelta')
  }

  const handleWhatsAppReply = (chat) => {
    const message = `Hola ${chat.customer_name}, gracias por contactarnos.

Recibimos tu consulta: "${chat.subject}"

${response || 'Te vamos a ayudar con tu solicitud. ¿Podrías darnos más detalles?'}

Saludos,
Equipo Pablo's Pizza`

    const whatsappUrl = `https://wa.me/${chat.customer_phone.replace(/[^0-9]/g, '')}?text=${encodeURIComponent(message)}`
    window.open(whatsappUrl, '_blank')

    // Marcar como respondido
    setChats(prev => prev.map(c =>
      c.id === chat.id
        ? { ...c, status: 'responded', responded_at: new Date() }
        : c
    ))

    setReplyDialog(false)
    setResponse('')
    toast.success('Respuesta enviada por WhatsApp')
  }

  const pendingChats = chats.filter(chat => chat.status === 'pending')
  const respondedChats = chats.filter(chat => chat.status === 'responded')

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Portal de Chats</Typography>
          <Typography variant="body2" color="text.secondary">
            Gestiona las consultas de los clientes desde el formulario web
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Card sx={{ p: 2, textAlign: 'center', minWidth: 100 }}>
            <Typography variant="h6" color="warning.main">{pendingChats.length}</Typography>
            <Typography variant="caption">Pendientes</Typography>
          </Card>
          <Card sx={{ p: 2, textAlign: 'center', minWidth: 100 }}>
            <Typography variant="h6" color="success.main">{respondedChats.length}</Typography>
            <Typography variant="caption">Respondidos</Typography>
          </Card>
        </Box>
      </Box>

      {pendingChats.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Tienes {pendingChats.length} consulta(s) pendiente(s) de respuesta.
        </Alert>
      )}

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando consultas...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Asunto</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Tiempo</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {chats.map((chat) => (
                    <TableRow key={chat.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {chat.customer_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {chat.customer_phone}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                          {chat.subject}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusLabel(chat.status)}
                          color={getStatusColor(chat.status)}
                          size="small"
                          icon={chat.status === 'pending' ? <AccessTime /> : <CheckCircle />}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {formatTimeAgo(chat.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          <Button
                            size="small"
                            startIcon={<Chat />}
                            onClick={() => handleViewChat(chat)}
                          >
                            Ver
                          </Button>
                          {chat.status === 'pending' && (
                            <Button
                              size="small"
                              color="success"
                              startIcon={<WhatsApp />}
                              onClick={() => handleReplyClick(chat)}
                            >
                              Responder
                            </Button>
                          )}
                          {chat.status === 'responded' && (
                            <Button
                              size="small"
                              color="info"
                              startIcon={<CheckCircle />}
                              onClick={() => handleMarkResolved(chat.id)}
                            >
                              Marcar Resuelto
                            </Button>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                  {chats.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography color="text.secondary">
                          No hay consultas disponibles
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Dialog para ver detalles del chat */}
      <Dialog open={!!selectedChat && !replyDialog} onClose={() => setSelectedChat(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          Consulta de {selectedChat?.customer_name}
          <IconButton
            onClick={() => setSelectedChat(null)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedChat && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Email:</strong> {selectedChat.customer_email}<br />
                    <strong>Teléfono:</strong> {selectedChat.customer_phone}<br />
                    <strong>Asunto:</strong> {selectedChat.subject}<br />
                    <strong>Fecha:</strong> {selectedChat.created_at.toLocaleString('es-CL')}
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>Mensaje del cliente:</Typography>
                <Card sx={{ bgcolor: 'grey.50', p: 2 }}>
                  <Typography variant="body1">
                    {selectedChat.message}
                  </Typography>
                </Card>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedChat(null)}>Cerrar</Button>
          {selectedChat?.status === 'pending' && (
            <Button
              onClick={() => handleReplyClick(selectedChat)}
              variant="contained"
              startIcon={<WhatsApp />}
            >
              Responder por WhatsApp
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Dialog para responder */}
      <Dialog open={replyDialog} onClose={() => setReplyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Responder por WhatsApp</DialogTitle>
        <DialogContent>
          {selectedChat && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    Se abrirá WhatsApp con una respuesta pre-redactada para {selectedChat.customer_name}
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Mensaje adicional (opcional)"
                  multiline
                  rows={4}
                  value={response}
                  onChange={(e) => setResponse(e.target.value)}
                  placeholder="Agrega información específica para esta consulta..."
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReplyDialog(false)}>Cancelar</Button>
          <Button
            onClick={() => handleWhatsAppReply(selectedChat)}
            variant="contained"
            startIcon={<WhatsApp />}
            sx={{ bgcolor: '#25D366', '&:hover': { bgcolor: '#1DA851' } }}
          >
            Enviar por WhatsApp
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ChatManagement