import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Alert,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material'
import {
  Message,
  WhatsApp,
  Email,
  Phone,
  Reply,
  CheckCircle,
  PendingActions,
  PriorityHigh,
  FilterList,
  Refresh
} from '@mui/icons-material'
import { contactAPI } from '../../services/api'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

const priorityColors = {
  low: { color: '#4caf50', label: 'Baja' },
  normal: { color: '#2196f3', label: 'Normal' },
  high: { color: '#ff9800', label: 'Alta' },
  urgent: { color: '#f44336', label: 'Urgente' }
}

const statusColors = {
  pending: { color: '#ff9800', label: 'Pendiente' },
  in_progress: { color: '#2196f3', label: 'En Progreso' },
  resolved: { color: '#4caf50', label: 'Resuelto' }
}

export default function ContactManagement() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedContact, setSelectedContact] = useState(null)
  const [responseDialog, setResponseDialog] = useState(false)
  const [detailDialog, setDetailDialog] = useState(false)
  const [responseData, setResponseData] = useState({
    response_message: '',
    response_method: 'whatsapp',
    notes: ''
  })
  const [filter, setFilter] = useState('all')
  const [tabValue, setTabValue] = useState(0)

  useEffect(() => {
    loadContacts()
  }, [filter])

  const loadContacts = async () => {
    try {
      setLoading(true)
      const params = {}
      if (filter !== 'all') {
        params.status = filter
      }
      const response = await contactAPI.getAll(params)
      setContacts(response.data)
    } catch (error) {
      console.error('Error loading contacts:', error)
      toast.error('Error al cargar los contactos')
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (contactId, newStatus) => {
    try {
      await contactAPI.update(contactId, { status: newStatus })
      toast.success('Estado actualizado')
      loadContacts()
    } catch (error) {
      console.error('Error updating status:', error)
      toast.error('Error al actualizar el estado')
    }
  }

  const handleResponse = async () => {
    try {
      await contactAPI.respond(selectedContact.id, responseData)
      toast.success(`Respuesta enviada por ${responseData.response_method}`)
      setResponseDialog(false)
      setResponseData({ response_message: '', response_method: 'whatsapp', notes: '' })
      loadContacts()
    } catch (error) {
      console.error('Error sending response:', error)
      toast.error('Error al enviar la respuesta')
    }
  }

  const openResponseDialog = (contact) => {
    setSelectedContact(contact)
    setResponseDialog(true)
  }

  const openDetailDialog = (contact) => {
    setSelectedContact(contact)
    setDetailDialog(true)
  }

  const getContactsByStatus = (status) => {
    return contacts.filter(contact => contact.status === status)
  }

  const ContactCard = ({ contact }) => (
    <Card sx={{ mb: 2, borderLeft: `4px solid ${priorityColors[contact.priority]?.color}` }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {contact.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {contact.email}
            </Typography>
            {contact.phone && (
              <Typography variant="body2" color="text.secondary">
                📞 {contact.phone}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
            <Chip
              label={priorityColors[contact.priority]?.label}
              sx={{ backgroundColor: priorityColors[contact.priority]?.color, color: 'white' }}
              size="small"
            />
            <Chip
              label={statusColors[contact.status]?.label}
              sx={{ backgroundColor: statusColors[contact.status]?.color, color: 'white' }}
              size="small"
            />
          </Box>
        </Box>

        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
          {contact.subject}
        </Typography>

        <Typography variant="body2" sx={{ mb: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {contact.message}
        </Typography>

        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
          {format(new Date(contact.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" variant="outlined" onClick={() => openDetailDialog(contact)}>
            Ver Detalle
          </Button>
          {contact.status !== 'resolved' && (
            <>
              <Button
                size="small"
                variant="contained"
                startIcon={<Reply />}
                onClick={() => openResponseDialog(contact)}
              >
                Responder
              </Button>
              {contact.status === 'pending' && (
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => handleStatusChange(contact.id, 'in_progress')}
                >
                  Tomar Caso
                </Button>
              )}
            </>
          )}
        </Box>
      </CardContent>
    </Card>
  )

  const pendingContacts = getContactsByStatus('pending')
  const inProgressContacts = getContactsByStatus('in_progress')
  const resolvedContacts = getContactsByStatus('resolved')

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Gestión de Contactos
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={loadContacts}
          disabled={loading}
        >
          Actualizar
        </Button>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#fff3e0' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <PendingActions sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                {pendingContacts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pendientes
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#e3f2fd' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <PriorityHigh sx={{ fontSize: 40, color: '#2196f3', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#2196f3' }}>
                {inProgressContacts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                En Progreso
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#e8f5e8' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <CheckCircle sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                {resolvedContacts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Resueltos
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#fce4ec' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Message sx={{ fontSize: 40, color: '#e91e63', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#e91e63' }}>
                {contacts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for different statuses */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label={`Pendientes (${pendingContacts.length})`} />
          <Tab label={`En Progreso (${inProgressContacts.length})`} />
          <Tab label={`Resueltos (${resolvedContacts.length})`} />
        </Tabs>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Box>
          {tabValue === 0 && (
            <Box>
              {pendingContacts.length === 0 ? (
                <Alert severity="info">No hay contactos pendientes</Alert>
              ) : (
                pendingContacts.map(contact => (
                  <ContactCard key={contact.id} contact={contact} />
                ))
              )}
            </Box>
          )}

          {tabValue === 1 && (
            <Box>
              {inProgressContacts.length === 0 ? (
                <Alert severity="info">No hay contactos en progreso</Alert>
              ) : (
                inProgressContacts.map(contact => (
                  <ContactCard key={contact.id} contact={contact} />
                ))
              )}
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              {resolvedContacts.length === 0 ? (
                <Alert severity="info">No hay contactos resueltos</Alert>
              ) : (
                resolvedContacts.map(contact => (
                  <ContactCard key={contact.id} contact={contact} />
                ))
              )}
            </Box>
          )}
        </Box>
      )}

      {/* Response Dialog */}
      <Dialog open={responseDialog} onClose={() => setResponseDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Responder a {selectedContact?.name}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Método de Respuesta</InputLabel>
                <Select
                  value={responseData.response_method}
                  onChange={(e) => setResponseData({...responseData, response_method: e.target.value})}
                  label="Método de Respuesta"
                >
                  <MenuItem value="whatsapp">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <WhatsApp /> WhatsApp
                    </Box>
                  </MenuItem>
                  <MenuItem value="email">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Email /> Email
                    </Box>
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Mensaje de Respuesta"
                multiline
                rows={4}
                fullWidth
                value={responseData.response_message}
                onChange={(e) => setResponseData({...responseData, response_message: e.target.value})}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notas Internas (Opcional)"
                multiline
                rows={2}
                fullWidth
                value={responseData.notes}
                onChange={(e) => setResponseData({...responseData, notes: e.target.value})}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResponseDialog(false)}>Cancelar</Button>
          <Button onClick={handleResponse} variant="contained" disabled={!responseData.response_message}>
            Enviar Respuesta
          </Button>
        </DialogActions>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailDialog} onClose={() => setDetailDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Detalle del Contacto
        </DialogTitle>
        <DialogContent>
          {selectedContact && (
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Información del Cliente</Typography>
                <Typography variant="body2"><strong>Nombre:</strong> {selectedContact.name}</Typography>
                <Typography variant="body2"><strong>Email:</strong> {selectedContact.email}</Typography>
                {selectedContact.phone && (
                  <Typography variant="body2"><strong>Teléfono:</strong> {selectedContact.phone}</Typography>
                )}
                <Typography variant="body2">
                  <strong>Fecha:</strong> {format(new Date(selectedContact.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Estado del Caso</Typography>
                <Chip
                  label={priorityColors[selectedContact.priority]?.label}
                  sx={{ backgroundColor: priorityColors[selectedContact.priority]?.color, color: 'white', mr: 1, mb: 1 }}
                />
                <Chip
                  label={statusColors[selectedContact.status]?.label}
                  sx={{ backgroundColor: statusColors[selectedContact.status]?.color, color: 'white', mb: 1 }}
                />
                {selectedContact.response_sent && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    <strong>Respuesta enviada por:</strong> {selectedContact.response_method}
                  </Typography>
                )}
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Asunto</Typography>
                <Typography variant="body1">{selectedContact.subject}</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Mensaje</Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {selectedContact.message}
                </Typography>
              </Grid>
              {selectedContact.notes && (
                <Grid item xs={12}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Notas Internas</Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedContact.notes}
                  </Typography>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog(false)}>Cerrar</Button>
          {selectedContact?.status !== 'resolved' && (
            <Button
              onClick={() => {
                setDetailDialog(false)
                openResponseDialog(selectedContact)
              }}
              variant="contained"
            >
              Responder
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}