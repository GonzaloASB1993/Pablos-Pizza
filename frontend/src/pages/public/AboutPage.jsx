import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Avatar,
  Paper,
  Chip,
  Button,
  Fade,
  useMediaQuery,
  Stack
} from '@mui/material'
import {
  Restaurant,
  WhatsApp,
  ArrowForward,
  Star,
  Favorite,
  EmojiEvents,
  LocalPizza,
  Groups,
  AccessTime,
  HealthAndSafety
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import { STATS } from '../../data/stats'

// Team Member Card Component
const TeamMemberCard = ({ name, role, story, initials, delay = 0 }) => {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay)
    return () => clearTimeout(timer)
  }, [delay])

  return (
    <Fade in={isVisible} timeout={1000}>
      <Card
        sx={{
          height: '100%',
          borderRadius: 4,
          overflow: 'hidden',
          background: '#1a1714',
          border: '1px solid rgba(232,182,58,0.12)',
          transition: 'all 0.4s ease',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 12px 32px rgba(232,182,58,0.15)',
            transition: 'transform 0.2s ease, box-shadow 0.2s ease',
          }
        }}
      >
        {/* Avatar con iniciales del miembro del equipo */}
        <Box
          sx={{
            pt: 4,
            pb: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: 'linear-gradient(180deg, rgba(232,182,58,0.06) 0%, transparent 100%)',
            borderBottom: '1px solid rgba(232,182,58,0.1)'
          }}
        >
          <Avatar
            sx={{
              width: 120,
              height: 120,
              bgcolor: '#1a1714',
              color: '#e8b63a',
              fontSize: '2rem',
              fontFamily: '"Fraunces", serif',
              fontWeight: 700,
              border: '3px solid #e8b63a',
              mx: 'auto',
              mb: 2,
            }}
          >
            {initials}
          </Avatar>
          <Typography variant="h4" component="h3" sx={{ color: '#e8b63a', fontWeight: 800, mb: 0.5, textAlign: 'center' }}>
            {name}
          </Typography>
          <Typography variant="h6" sx={{ color: '#FFF', fontWeight: 500, textAlign: 'center' }}>
            {role}
          </Typography>
        </Box>

        {/* Historia del miembro */}
        <CardContent sx={{ p: 3 }}>
          <Typography
            variant="body1"
            sx={{
              lineHeight: 1.8,
              color: 'rgba(255,255,255,0.65)'
            }}
          >
            {story}
          </Typography>
        </CardContent>
      </Card>
    </Fade>
  )
}

// Stat Component
const StatBox = ({ icon, number, label }) => (
  <Box sx={{ textAlign: 'center' }}>
    <Box sx={{ mb: 1 }}>
      {React.cloneElement(icon, {
        sx: { fontSize: 48, color: '#e8b63a' }
      })}
    </Box>
    <Typography variant="h3" component="p" sx={{ fontWeight: 800, color: '#e8b63a', mb: 0.5 }}>
      {number}
    </Typography>
    <Typography variant="body1" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.65)' }}>
      {label}
    </Typography>
  </Box>
)

export default function AboutPage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [heroLoaded, setHeroLoaded] = useState(false)

  useEffect(() => {
    setHeroLoaded(true)
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1'
            entry.target.style.transform = 'translateY(0)'
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.2 }
    )
    const titles = document.querySelectorAll('#about-page [data-reveal]')
    titles.forEach((el) => {
      el.style.opacity = '0'
      el.style.transform = 'translateY(24px)'
      el.style.transition = 'opacity 0.6s ease, transform 0.6s ease'
      observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  // Datos del equipo
  const teamMembers = [
    {
      name: 'Juan Pablo',
      role: 'Chef Principal',
      story: 'Con más de 10 años de experiencia en gastronomía profesional, Juan Pablo es el corazón de Pablo\'s Pizza. Su pasión por enseñar a los niños técnicas culinarias auténticas, combinada con su energía contagiosa, hace que cada taller sea una experiencia única. Se especializa en adaptar recetas complejas para que los más pequeños las comprendan y disfruten.',
      initials: 'JP',
    },
    {
      name: 'Nicole',
      role: 'Segunda a Bordo',
      story: 'Nicole es la mano derecha de Juan Pablo y experta en logística de eventos. Con su ojo para los detalles y su capacidad para conectar con los niños, se asegura de que cada taller fluya sin contratiempos. Su experiencia en educación infantil la convierte en la persona ideal para mantener a todos los pequeños chefs seguros, motivados y felices durante todo el taller.',
      initials: 'N',
    },
    {
      name: 'Mauro',
      role: 'Ayudante',
      story: 'Mauro es el músculo del equipo, encargándose de todo el montaje y desmontaje del equipamiento. Su actitud positiva y disposición para ayudar en cada detalle hacen que los eventos se desarrollen sin contratiempos. Además, su habilidad para hacer reír a los niños y mantener el ambiente divertido lo convierte en un favorito de todos los pequeños participantes.',
      initials: 'M',
    }
  ]

  return (
    <Box id="about-page" sx={{ background: '#0d0d0d', minHeight: '100vh' }}>
      {/* Hero Section */}
      <Box
        sx={{
          background: '#0d0d0d',
          color: '#FFFFFF',
          py: { xs: 6, md: 10 },
          position: 'relative',
          overflow: 'hidden',
          borderBottom: '1px solid rgba(232,182,58,0.15)',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(circle at 30% 50%, rgba(232,182,58,0.08) 0%, transparent 60%)',
            opacity: 0.8
          }
        }}
      >
        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
          <Fade in={heroLoaded} timeout={800}>
            <Box sx={{ textAlign: 'center' }}>
              <Chip
                label="Conoce al Equipo"
                sx={{
                  bgcolor: 'rgba(232,182,58,0.12)',
                  color: '#e8b63a',
                  fontWeight: 700,
                  mb: 3,
                  fontSize: '1rem',
                  px: 2,
                  border: '1px solid rgba(232,182,58,0.3)'
                }}
              />
              <Typography
                variant="h1"
                sx={{
                  fontWeight: 900,
                  fontSize: { xs: '2.5rem', md: '4rem' },
                  mb: 3,
                  color: '#FFFFFF'
                }}
              >
                Nosotros
              </Typography>
              <Typography
                variant="h5"
                sx={{
                  maxWidth: 800,
                  mx: 'auto',
                  fontWeight: 500,
                  color: 'rgba(255,255,255,0.65)',
                  lineHeight: 1.6
                }}
              >
                Las personas apasionadas que hacen realidad cada experiencia
                gastronómica que los niños recuerdan.
              </Typography>
            </Box>
          </Fade>
        </Container>
      </Box>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        {/* Stats Section */}
        <Paper
          sx={{
            p: 6,
            mb: 10,
            borderRadius: 4,
            background: '#1a1714',
            border: '1px solid rgba(232,182,58,0.15)'
          }}
        >
          <Grid container spacing={4}>
            <Grid item xs={12} md={4}>
              <StatBox
                icon={<Favorite />}
                number={STATS.kidsServed}
                label="Niños Felices"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatBox
                icon={<EmojiEvents />}
                number={STATS.eventsCount}
                label="Eventos Realizados"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <StatBox
                icon={<Star />}
                number="5.0"
                label="Calificación Promedio"
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Team Section */}
        <Box sx={{ mb: 10, background: '#141414', borderRadius: 4, p: { xs: 3, md: 6 } }}>
          <Typography
            variant="h2"
            component="h2"
            align="center"
            sx={{ fontWeight: 800, mb: 2, color: '#FFFFFF' }}
          >
            Nuestro Equipo
          </Typography>
          <Typography
            variant="h6"
            align="center"
            sx={{ mb: 6, maxWidth: 700, mx: 'auto', color: 'rgba(255,255,255,0.65)' }}
          >
            Tres profesionales dedicados que combinan talento culinario,
            experiencia educativa y pasión por hacer felices a los niños
          </Typography>

          <Grid container spacing={4}>
            {teamMembers.map((member, index) => (
              <Grid item xs={12} md={4} key={member.name}>
                <TeamMemberCard
                  {...member}
                  delay={index * 200}
                />
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* Values Section */}
        <Box
          sx={{
            mb: 10,
            p: 6,
            borderRadius: 4,
            background: '#0d0d0d',
            border: '1px solid rgba(232,182,58,0.15)',
            color: '#FFF'
          }}
        >
          <Typography
            variant="h2"
            component="h2"
            align="center"
            sx={{ fontWeight: 800, mb: 2, color: '#e8b63a' }}
          >
            Lo que Nos Define
          </Typography>
          <Typography
            variant="h6"
            align="center"
            sx={{ mb: 6, maxWidth: 600, mx: 'auto', color: 'rgba(255,255,255,0.65)' }}
          >
            Compromisos concretos, no palabras genéricas
          </Typography>

          <Grid container spacing={4}>
            {[
              {
                title: 'Harina 00 Italiana Caputo',
                description: 'Usamos siempre harina 00 Caputo importada. No hay atajos en la masa.',
                icon: <LocalPizza sx={{ fontSize: 28 }} />,
              },
              {
                title: 'Máx. 15 niños por chef',
                description: 'Nunca más de 15 participantes por taller. Cada niño amasa su propia pizza.',
                icon: <Groups sx={{ fontSize: 28 }} />,
              },
              {
                title: 'Llegamos 45 min antes',
                description: 'Montaje completo antes de que lleguen los invitados. Sin estrés para los papás.',
                icon: <AccessTime sx={{ fontSize: 28 }} />,
              },
              {
                title: 'Sin frutos secos ni sésamo',
                description: 'Por defecto, todos los talleres son libres de frutos secos y sésamo.',
                icon: <HealthAndSafety sx={{ fontSize: 28 }} />,
              },
            ].map((value, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Box sx={{ mb: 4 }}>
                  <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                    <Avatar sx={{ bgcolor: 'rgba(232,182,58,0.15)', color: '#e8b63a', width: 56, height: 56, border: '1px solid rgba(232,182,58,0.3)' }}>
                      {value.icon}
                    </Avatar>
                    <Typography variant="h5" sx={{ fontWeight: 700, color: '#FFFFFF' }}>
                      {value.title}
                    </Typography>
                  </Stack>
                  <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.8, pl: 9 }}>
                    {value.description}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* Timeline del proceso de evento */}
        <Box sx={{ background: '#141414', borderRadius: 4, py: { xs: 6, md: 10 }, px: { xs: 3, md: 6 }, mb: 10 }}>
          <Container maxWidth="md">
            <Typography
              variant="h2"
              component="h2"
              data-reveal
              sx={{ color: '#FFFFFF', textAlign: 'center', mb: 6, fontWeight: 700 }}
            >
              Cómo funciona
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {[
                {
                  step: '01',
                  title: 'Reservá online',
                  desc: 'Completás el formulario con fecha, cantidad de niños y tipo de evento. Te confirmamos en menos de 24 hs.',
                },
                {
                  step: '02',
                  title: 'Llegamos 45 min antes',
                  desc: 'El equipo llega con todo el equipamiento, harina 00 italiana y los ingredientes. Vos no preparás nada.',
                },
                {
                  step: '03',
                  title: '90 min de taller',
                  desc: 'Cada niño amasa, estira y arma su propia pizza con técnicas reales de pizzaiolo. Máximo 15 participantes por chef.',
                },
                {
                  step: '04',
                  title: 'Pizza + certificado',
                  desc: 'Los niños comen la pizza que hicieron y reciben su certificado de pizzaiolo. El equipo limpia y se va.',
                },
              ].map((item, index) => (
                <Box
                  key={index}
                  sx={{ display: 'flex', gap: 3, alignItems: 'flex-start', pb: 4 }}
                >
                  <Box
                    sx={{
                      minWidth: 48,
                      height: 48,
                      borderRadius: '50%',
                      border: '2px solid #e8b63a',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#e8b63a',
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      flexShrink: 0,
                    }}
                  >
                    {item.step}
                  </Box>
                  <Box sx={{ pt: 0.5 }}>
                    <Typography variant="h6" component="h3" sx={{ color: '#FFFFFF', fontWeight: 600, mb: 0.5 }}>
                      {item.title}
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                      {item.desc}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Container>
        </Box>

        {/* CTA Section */}
        <Paper
          sx={{
            p: 6,
            borderRadius: 4,
            textAlign: 'center',
            background: '#1a1714',
            border: '1px solid rgba(232,182,58,0.15)'
          }}
        >
          <Typography variant="h3" component="h3" sx={{ fontWeight: 900, mb: 2, color: '#FFFFFF' }}>
            ¿Listo para Conocernos en Persona?
          </Typography>
          <Typography variant="h6" sx={{ mb: 4, color: 'rgba(255,255,255,0.65)', maxWidth: 600, mx: 'auto' }}>
            Agenda tu taller o pizza party y conoce al equipo que hará de tu
            evento un taller de 90 min a domicilio que los niños llevarán puesto.
          </Typography>

          <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/agendar')}
              endIcon={<ArrowForward />}
              sx={{
                bgcolor: '#e8b63a',
                color: '#0d0d0d',
                px: 4,
                py: 2,
                fontSize: '1.1rem',
                fontWeight: 700,
                '&:hover': {
                  bgcolor: '#d4a030',
                  transform: 'translateY(-2px)'
                }
              }}
            >
              Agendar Evento
            </Button>
            <Button
              variant="outlined"
              size="large"
              href="https://wa.me/56989424566?text=Hola! Me gustaría conocer más sobre el equipo de Pablo's Pizza"
              target="_blank"
              startIcon={<WhatsApp />}
              sx={{
                borderColor: 'rgba(232,182,58,0.5)',
                color: '#e8b63a',
                px: 4,
                py: 2,
                fontSize: '1.1rem',
                fontWeight: 700,
                borderWidth: 2,
                '&:hover': {
                  bgcolor: 'rgba(232,182,58,0.08)',
                  borderColor: '#e8b63a',
                  borderWidth: 2,
                  transform: 'translateY(-2px)'
                }
              }}
            >
              Contactar por WhatsApp
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
