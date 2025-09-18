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
    MarkEmailRead,
    MarkEmailUnread,
    Reply,
    Close,
    WhatsApp,
    Phone,
    Email,
    CheckCircle,
    AccessTime,
    Send
} from '@mui/icons-material'
import toast from 'react-hot-toast'
import { CONTACT_INFO } from '../../config/constants'
import { chatAPI } from '../../services/api'

const ChatManagement = () => {
    const [chats, setChats] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedChat, setSelectedChat] = useState(null)
    const [replyDialog, setReplyDialog] = useState(false)
    const [response, setResponse] = useState('')
    const [messages, setMessages] = useState([])

    const mockChats = [
        {
            id: 1,
            customer_name: 'María González',
            customer_email: 'maria@example.com',
            customer_phone: '+56912345678',
            subject: 'Consulta sobre Pizza Party',
            message: 'Hola, quisiera saber los precios para una pizza party de 15 niños. ¿Qué incluye el servicio?',
            status: 'pending',
            created_at: new Date(Date.now() - 2 * 60 * 60 * 1000),
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
            created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
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
            created_at: new Date(Date.now() - 30 * 60 * 1000),
            responded_at: null
        }
    ]

    useEffect(() => {
        loadChatRooms()
    }, [])

    const loadChatRooms = async () => {
        try {
            setLoading(true)
            console.log('🔄 Cargando salas de chat...')
            
            const response = await chatAPI.getRooms()
            console.log('📥 Respuesta del API:', response.data)
            
            if (!response.data || response.data.length === 0) {
                console.log('⚠️ No hay salas de chat disponibles')
                setChats([])
                return
            }
            
            // Transformar los datos de las salas a formato compatible con el componente
            const transformedChats = response.data.map(room => {
                console.log('🔄 Transformando sala:', room)
                
                // Manejar diferentes formatos de fecha de Firestore
                let timestamp
                if (room.created_at && room.created_at._seconds) {
                    timestamp = new Date(room.created_at._seconds * 1000)
                } else if (room.created_at) {
                    timestamp = new Date(room.created_at)
                } else {
                    timestamp = new Date()
                }
                
                return {
                    id: room.id,
                    customer_name: room.client_name,
                    customer_email: room.client_email,
                    customer_phone: room.client_phone || null,
                    message: 'Ver conversación completa',
                    timestamp: timestamp,
                    status: room.status === 'open' ? 'pending' : 'resolved',
                    subject: 'Consulta desde formulario web',
                    messages_count: room.messages_count || 0
                }
            })
            
            console.log('✅ Salas transformadas:', transformedChats)
            setChats(transformedChats)
            
        } catch (error) {
            console.error('❌ Error loading chat rooms:', error)
            toast.error('Error al cargar las conversaciones: ' + error.message)
            
            // NO usar datos mock como fallback - mejor mostrar error real
            setChats([])
        } finally {
            setLoading(false)
        }
    }

    const loadChatMessages = async (roomId) => {
        try {
            const response = await chatAPI.getMessages(roomId)
            setMessages(response.data)
        } catch (error) {
            console.error('Error loading messages:', error)
            toast.error('Error al cargar los mensajes')
        }
    }

    useEffect(() => {
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

    const handleViewChat = async (chat) => {
        setSelectedChat(chat)
        await loadChatMessages(chat.id)
    }

    const handleReplyClick = async (chat) => {
        setSelectedChat(chat)
        await loadChatMessages(chat.id)
        setReplyDialog(true)
    }

    const handleSendReply = async () => {
        if (!response.trim() || !selectedChat) return

        try {
            await chatAPI.sendMessage(selectedChat.id, {
                message: response,
                sender_name: 'Administrador - Pablo\'s Pizza',
                is_admin: true
            })

            toast.success('Respuesta enviada exitosamente')
            setResponse('')
            setReplyDialog(false)
            
            // Recargar mensajes y actualizar el estado de la conversación
            await loadChatMessages(selectedChat.id)
            await loadChatRooms()
            
        } catch (error) {
            console.error('Error sending reply:', error)
            toast.error('Error al enviar la respuesta')
        }
    }

    const handleMarkResolved = async (chatId) => {
        try {
            await chatAPI.closeRoom(chatId)
            toast.success('Conversación marcada como resuelta')
            await loadChatRooms()
        } catch (error) {
            console.error('Error marking as resolved:', error)
            toast.error('Error al marcar como resuelto')
        }
    }

    const handleMarkResolved_old = (chatId) => {
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
                        Gestiona las consultas de clientes desde el formulario de contacto
                    </Typography>
                </Box>
                <Button
                    variant="outlined"
                    startIcon={<Chat />}
                    onClick={loadChatRooms}
                    disabled={loading}
                >
                    {loading ? 'Cargando...' : 'Recargar Chats'}
                </Button>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Card sx={{ p: 2, textAlign: 'center', minWidth: 100 }}>
                    <Typography variant="h6" color="warning.main">{pendingChats.length}</Typography>
                    <Typography variant="caption">Pendientes</Typography>
                </Card>
                <Card sx={{ p: 2, textAlign: 'center', minWidth: 100 }}>
                    <Typography variant="h6" color="success.main">{respondedChats.length}</Typography>
                    <Typography variant="caption">Respondidos</Typography>
                </Card>
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

            <Dialog open={!!selectedChat && !replyDialog} onClose={() => setSelectedChat(null)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Conversación con {selectedChat?.customer_name}
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
                                        {selectedChat.customer_phone && (
                                            <>
                                                <strong>Teléfono:</strong> {selectedChat.customer_phone}<br />
                                            </>
                                        )}
                                        <strong>Fecha de inicio:</strong> {selectedChat.timestamp.toLocaleString('es-CL')}<br />
                                        <strong>Mensajes:</strong> {selectedChat.messages_count}
                                    </Typography>
                                </Alert>
                            </Grid>
                            <Grid item xs={12}>
                                <Typography variant="h6" gutterBottom>Historial de conversación:</Typography>
                                <Box sx={{ 
                                    maxHeight: '400px', 
                                    overflow: 'auto', 
                                    border: '1px solid #e0e0e0', 
                                    borderRadius: 1, 
                                    p: 2,
                                    bgcolor: 'grey.50'
                                }}>
                                    {messages.length > 0 ? (
                                        messages.map((message, index) => (
                                            <Card 
                                                key={message.id || index} 
                                                sx={{ 
                                                    mb: 2, 
                                                    bgcolor: message.is_admin ? 'primary.light' : 'white',
                                                    color: message.is_admin ? 'white' : 'inherit'
                                                }}
                                            >
                                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                                                        {message.sender_name} {message.is_admin ? '(Admin)' : '(Cliente)'}
                                                        <Typography component="span" variant="caption" sx={{ ml: 1, opacity: 0.7 }}>
                                                            {new Date(message.created_at._seconds * 1000 || message.created_at).toLocaleString('es-CL')}
                                                        </Typography>
                                                    </Typography>
                                                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                                                        {message.message}
                                                    </Typography>
                                                </CardContent>
                                            </Card>
                                        ))
                                    ) : (
                                        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                                            No hay mensajes en esta conversación
                                        </Typography>
                                    )}
                                </Box>
                            </Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setSelectedChat(null)}>Cerrar</Button>
                    <Button
                        onClick={() => handleReplyClick(selectedChat)}
                        variant="contained"
                        startIcon={<Reply />}
                    >
                        Responder
                    </Button>
                    {selectedChat?.status === 'pending' && (
                        <Button
                            onClick={() => handleMarkResolved(selectedChat.id)}
                            variant="outlined"
                            startIcon={<CheckCircle />}
                            color="success"
                        >
                            Marcar como Resuelto
                        </Button>
                    )}
                </DialogActions>
            </Dialog>

            <Dialog open={replyDialog} onClose={() => setReplyDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Responder a {selectedChat?.customer_name}</DialogTitle>
                <DialogContent>
                    {selectedChat && (
                        <Grid container spacing={2} sx={{ mt: 1 }}>
                            <Grid item xs={12}>
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    <Typography variant="body2">
                                        Envía una respuesta directa a través del sistema de chat. 
                                        El cliente recibirá una notificación por email.
                                    </Typography>
                                </Alert>
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    label="Tu respuesta"
                                    multiline
                                    rows={4}
                                    value={response}
                                    onChange={(e) => setResponse(e.target.value)}
                                    placeholder="Escribe tu respuesta aquí..."
                                    required
                                />
                            </Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setReplyDialog(false)}>Cancelar</Button>
                    <Button
                        onClick={() => window.open(`https://wa.me/${selectedChat?.customer_phone?.replace(/\D/g, '')}?text=${encodeURIComponent(`Hola ${selectedChat?.customer_name}, ${response || 'gracias por contactarnos desde Pablo\'s Pizza'}`)}`)}
                        startIcon={<WhatsApp />}
                        sx={{ bgcolor: '#25D366', color: 'white', '&:hover': { bgcolor: '#1DA851' } }}
                        disabled={!selectedChat?.customer_phone}
                    >
                        WhatsApp
                    </Button>
                    <Button
                        onClick={handleSendReply}
                        variant="contained"
                        startIcon={<Send />}
                        disabled={!response.trim()}
                    >
                        Enviar Respuesta
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default ChatManagement