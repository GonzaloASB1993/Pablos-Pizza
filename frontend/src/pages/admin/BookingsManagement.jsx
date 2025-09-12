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
  Chip,
  Paper
} from '@mui/material'
import { Add, Edit, Delete } from '@mui/icons-material'

const BookingsManagement = () => {
  const demoBookings = [
    {
      id: 1,
      client_name: 'María García',
      service_type: 'workshop',
      event_date: '2024-01-20',
      participants: 10,
      status: 'confirmed',
      estimated_price: 250
    },
    {
      id: 2,
      client_name: 'Carlos Rodríguez',
      service_type: 'pizza_party',
      event_date: '2024-01-22',
      participants: 15,
      status: 'pending',
      estimated_price: 300
    }
  ]

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      confirmed: 'success',
      completed: 'info',
      cancelled: 'error'
    }
    return colors[status] || 'default'
  }

  const getServiceLabel = (type) => {
    return type === 'workshop' ? 'Taller' : 'Pizza Party'
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Gestión de Agendamientos</Typography>
        <Button variant="contained" startIcon={<Add />}>
          Nuevo Agendamiento
        </Button>
      </Box>

      <Card>
        <CardContent>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Cliente</TableCell>
                  <TableCell>Servicio</TableCell>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Participantes</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Precio</TableCell>
                  <TableCell>Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {demoBookings.map((booking) => (
                  <TableRow key={booking.id}>
                    <TableCell>{booking.client_name}</TableCell>
                    <TableCell>{getServiceLabel(booking.service_type)}</TableCell>
                    <TableCell>{booking.event_date}</TableCell>
                    <TableCell>{booking.participants}</TableCell>
                    <TableCell>
                      <Chip 
                        label={booking.status}
                        color={getStatusColor(booking.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>${booking.estimated_price}</TableCell>
                    <TableCell>
                      <Button size="small" startIcon={<Edit />}>
                        Editar
                      </Button>
                      <Button size="small" color="error" startIcon={<Delete />}>
                        Cancelar
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  )
}

export default BookingsManagement