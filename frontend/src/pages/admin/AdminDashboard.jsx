import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Button
} from '@mui/material'
import {
  TrendingUp,
  Event,
  AttachMoney,
  People
} from '@mui/icons-material'

const AdminDashboard = () => {
  // Mock data
  const stats = {
    newBookings: 3,
    monthlyEvents: 12,
    monthlyIncome: 3600,
    monthlyProfit: 2400
  }

  const StatCard = ({ title, value, icon, color = 'primary' }) => (
    <Card>
      <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
        <Box sx={{ 
          backgroundColor: `${color}.main`,
          color: 'white',
          p: 2,
          borderRadius: 2,
          mr: 2
        }}>
          {icon}
        </Box>
        <Box>
          <Typography variant="h4" color={`${color}.main`}>
            {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom>
        Dashboard - Pablo's Pizza
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Resumen general del negocio y métricas importantes
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Agendamientos Hoy"
            value={stats.newBookings}
            icon={<Event />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Eventos del Mes"
            value={stats.monthlyEvents}
            icon={<People />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Ingresos del Mes"
            value={`$${stats.monthlyIncome}`}
            icon={<AttachMoney />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Utilidad del Mes"
            value={`$${stats.monthlyProfit}`}
            icon={<TrendingUp />}
            color="warning"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Acciones Rápidas
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button variant="contained" fullWidth>
                  Ver Agendamientos del Día
                </Button>
                <Button variant="outlined" fullWidth>
                  Registrar Nuevo Evento
                </Button>
                <Button variant="outlined" fullWidth>
                  Gestionar Inventario
                </Button>
                <Button variant="outlined" fullWidth>
                  Enviar Notificaciones
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Alertas del Sistema
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                  <Typography variant="body2">
                    3 productos con stock bajo
                  </Typography>
                </Box>
                <Box sx={{ p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                  <Typography variant="body2">
                    5 reseñas pendientes de aprobación
                  </Typography>
                </Box>
                <Box sx={{ p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                  <Typography variant="body2">
                    2 chats activos esperando respuesta
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  )
}

export default AdminDashboard