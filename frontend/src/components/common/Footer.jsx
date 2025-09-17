import {
  Box,
  Container,
  Grid,
  Typography,
  Link,
  IconButton,
  Divider
} from '@mui/material'
import {
  Instagram,
  WhatsApp,
  Phone,
  Email,
  LocationOn
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import logo from '../../assets/logo.png'
import { CONTACT_INFO } from '../../config/constants'

const Footer = () => {
  const theme = useTheme()

  return (
    <Box
      component="footer"
      sx={{
        backgroundColor: theme.palette.secondary.main,
        color: 'white',
        pt: 6,
        pb: 3
      }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={4}>
          {/* Brand Section */}
          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box
                component="img"
                src={logo}
                alt="Pablo's Pizza Logo"
                sx={{
                  width: 50,
                  height: 50,
                  mr: 2
                }}
              />
              <Typography variant="h5" sx={{ 
                fontWeight: 700,
                color: theme.palette.primary.main
              }}>
                Pablo's Pizza
              </Typography>
            </Box>
            <Typography variant="body1" paragraph sx={{ mb: 3 }}>
              Creamos experiencias gastronómicas únicas para niños y familias. 
              Talleres de pizza educativos y eventos memorables.
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <IconButton 
                href="https://instagram.com/pablospizza.cl" 
                target="_blank"
                sx={{ 
                  color: theme.palette.primary.main,
                  '&:hover': { color: theme.palette.primary.dark }
                }}
              >
                <Instagram />
              </IconButton>
              <IconButton 
                href="{CONTACT_INFO.WHATSAPP_URL}" 
                target="_blank"
                sx={{ 
                  color: theme.palette.primary.main,
                  '&:hover': { color: theme.palette.primary.dark }
                }}
              >
                <WhatsApp />
              </IconButton>
            </Box>
          </Grid>

          {/* Services Section */}
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="h6" gutterBottom sx={{ 
              color: theme.palette.primary.main,
              fontWeight: 600
            }}>
              Servicios
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Link href="/servicios" color="inherit" underline="hover">
                Talleres para Niños
              </Link>
              <Link href="/servicios" color="inherit" underline="hover">
                Pizza Parties
              </Link>
              <Link href="/servicios" color="inherit" underline="hover">
                Eventos Corporativos
              </Link>
              <Link href="/servicios" color="inherit" underline="hover">
                Celebraciones Escolares
              </Link>
            </Box>
          </Grid>

          {/* Links Section */}
          <Grid item xs={12} sm={6} md={2}>
            <Typography variant="h6" gutterBottom sx={{ 
              color: theme.palette.primary.main,
              fontWeight: 600
            }}>
              Enlaces
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Link href="/" color="inherit" underline="hover">
                Inicio
              </Link>
              <Link href="/galeria" color="inherit" underline="hover">
                Galería
              </Link>
              <Link href="/testimonios" color="inherit" underline="hover">
                Testimonios
              </Link>
              <Link href="/agendar" color="inherit" underline="hover">
                Agendar Evento
              </Link>
              <Link href="/contacto" color="inherit" underline="hover">
                Contacto
              </Link>
            </Box>
          </Grid>

          {/* Contact Section */}
          <Grid item xs={12} md={3}>
            <Typography variant="h6" gutterBottom sx={{ 
              color: theme.palette.primary.main,
              fontWeight: 600
            }}>
              Contacto
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <WhatsApp fontSize="small" sx={{ color: theme.palette.primary.main }} />
                <Link href="{CONTACT_INFO.WHATSAPP_URL}" color="inherit" underline="hover">
                  {CONTACT_INFO.WHATSAPP_DISPLAY}
                </Link>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Phone fontSize="small" sx={{ color: theme.palette.primary.main }} />
                <Link href="tel:{CONTACT_INFO.WHATSAPP_NUMBER}" color="inherit" underline="hover">
                  {CONTACT_INFO.WHATSAPP_DISPLAY}
                </Link>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Email fontSize="small" sx={{ color: theme.palette.primary.main }} />
                <Link href="mailto:Pablospizza.cl@gmail.com" color="inherit" underline="hover">
                  Pablospizza.cl@gmail.com
                </Link>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                <LocationOn fontSize="small" sx={{ color: theme.palette.primary.main, mt: 0.5 }} />
                <Typography variant="body2">
                  Santiago de Chile<br />
                  Servicio a domicilio disponible
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>

        <Divider sx={{ my: 4, borderColor: 'rgba(255, 255, 255, 0.2)' }} />

        {/* Bottom Section */}
        <Grid container justifyContent="space-between" alignItems="center">
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="rgba(255, 255, 255, 0.7)">
              © {new Date().getFullYear()} Pablo's Pizza. Todos los derechos reservados.
            </Typography>
          </Grid>
          <Grid item xs={12} md={6} sx={{ textAlign: { xs: 'left', md: 'right' } }}>
            <Typography variant="body2" color="rgba(255, 255, 255, 0.7)">
              Horarios: Lunes a Domingo | 9:00 AM - 8:00 PM
            </Typography>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}

export default Footer