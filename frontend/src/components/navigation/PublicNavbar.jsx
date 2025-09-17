import { useState } from 'react'
import {
    AppBar,
    Toolbar,
    Typography,
    Button,
    IconButton,
    Box,
    Drawer,
    List,
    ListItem,
    ListItemText,
    useTheme,
    useMediaQuery,
    Container
} from '@mui/material'
import {
    Menu as MenuIcon,
    Close as CloseIcon,
    Restaurant,
    Phone,
    WhatsApp,
    Instagram
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import logo from '../../assets/logo.png'
import { CONTACT_INFO } from '../../config/constants'

const PublicNavbar = () => {
    const [mobileOpen, setMobileOpen] = useState(false)
    const theme = useTheme()
    const isMobile = useMediaQuery(theme.breakpoints.down('md'))
    const navigate = useNavigate()
    const location = useLocation()

    const navItems = [
        { label: 'Inicio', path: '/' },
        { label: 'Servicios', path: '/servicios' },
        { label: 'Galería', path: '/galeria' },
        { label: 'Testimonios', path: '/testimonios' },
        { label: 'Contacto', path: '/contacto' },
    ]

    const handleDrawerToggle = () => {
        setMobileOpen(!mobileOpen)
    }

    const handleNavigation = (path) => {
        navigate(path)
        if (mobileOpen) {
            setMobileOpen(false)
        }
    }

    const isActiveRoute = (path) => {
        return location.pathname === path
    }

    const drawer = (
        <Box sx={{ width: 250 }}>
            <Box sx={{
                p: 2,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: `1px solid ${theme.palette.divider}`
            }}>
                <Typography variant="h6" sx={{ color: theme.palette.primary.main, fontWeight: 600 }}>
                    Pablo's Pizza
                </Typography>
                <IconButton onClick={handleDrawerToggle}>
                    <CloseIcon />
                </IconButton>
            </Box>
            <List>
                {navItems.map((item) => (
                    <ListItem
                        button
                        key={item.path}
                        onClick={() => handleNavigation(item.path)}
                        sx={{
                            backgroundColor: isActiveRoute(item.path) ?
                                theme.palette.primary.main + '20' : 'transparent',
                            '&:hover': {
                                backgroundColor: theme.palette.primary.main + '10'
                            }
                        }}
                    >
                        <ListItemText
                            primary={item.label}
                            sx={{
                                color: isActiveRoute(item.path) ?
                                    theme.palette.primary.main : theme.palette.text.primary
                            }}
                        />
                    </ListItem>
                ))}
                <ListItem sx={{ mt: 2, borderTop: `1px solid ${theme.palette.divider}`, pt: 2 }}>
                    <Box sx={{ width: '100%' }}>
                        <Button
                            fullWidth
                            variant="contained"
                            onClick={() => handleNavigation('/agendar')}
                            sx={{ mb: 2 }}
                            startIcon={<Restaurant />}
                        >
                            Agendar Evento
                        </Button>
                        <Button
                            fullWidth
                            variant="outlined"
                            href={CONTACT_INFO.WHATSAPP_URL}
                            target="_blank"
                            startIcon={<WhatsApp />}
                        >
                            WhatsApp
                        </Button>
                        <Button
                            fullWidth
                            variant="outlined"
                            href="https://instagram.com/pablospizza.cl"
                            target="_blank"
                            startIcon={<Instagram />}
                            sx={{ mt: 1 }}
                        >
                            Instagram
                        </Button>
                    </Box>
                </ListItem>
            </List>
        </Box>
    )

    return (
        <>
            <AppBar position="sticky" elevation={2}>
                <Container maxWidth="lg">
                    <Toolbar sx={{ px: { xs: 0, sm: 2 } }}>
                        {/* Logo and Brand */}
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                flexGrow: 1,
                                cursor: 'pointer'
                            }}
                            onClick={() => navigate('/')}
                        >
                            <Box
                                component="img"
                                src={logo}
                                alt="Pablo's Pizza Logo"
                                sx={{
                                    width: 40,
                                    height: 40,
                                    mr: 2,
                                    borderRadius: '50%',
                                    objectFit: 'cover'
                                }}
                            />
                            <Typography
                                variant="h5"
                                sx={{
                                    fontWeight: 700,
                                    color: theme.palette.primary.main,
                                    display: { xs: 'none', sm: 'block' }
                                }}
                            >
                                Pablo's Pizza
                            </Typography>
                        </Box>

                        {/* Desktop Navigation */}
                        {!isMobile && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {navItems.map((item) => (
                                    <Button
                                        key={item.path}
                                        onClick={() => handleNavigation(item.path)}
                                        sx={{
                                            color: isActiveRoute(item.path) ?
                                                theme.palette.primary.main : 'white',
                                            fontWeight: isActiveRoute(item.path) ? 600 : 400,
                                            '&:hover': {
                                                color: theme.palette.primary.main,
                                                backgroundColor: 'rgba(255, 215, 0, 0.1)'
                                            }
                                        }}
                                    >
                                        {item.label}
                                    </Button>
                                ))}

                                <Button
                                    variant="contained"
                                    onClick={() => handleNavigation('/agendar')}
                                    sx={{
                                        ml: 2,
                                        px: 2.5,
                                        py: 1,
                                        borderRadius: 12,
                                        boxShadow: 'none',
                                        backgroundColor: theme.palette.primary.main,
                                        color: theme.palette.secondary.main,
                                        border: '1px solid transparent',
                                        '&:hover': {
                                            backgroundColor: theme.palette.primary.dark,
                                            boxShadow: 'none',
                                        }
                                    }}
                                    startIcon={<Restaurant />}
                                >
                                    Agendar
                                </Button>

                                <IconButton
                                    href={CONTACT_INFO.WHATSAPP_URL}
                                    target="_blank"
                                    sx={{
                                        ml: 1,
                                        color: theme.palette.primary.main
                                    }}
                                >
                                    <WhatsApp />
                                </IconButton>
                                <IconButton
                                    href="https://instagram.com/pablospizza.cl"
                                    target="_blank"
                                    sx={{
                                        ml: 1,
                                        color: theme.palette.primary.main,
                                        '&:hover': { color: theme.palette.primary.light }
                                    }}
                                    aria-label="Instagram"
                                >
                                    <Instagram />
                                </IconButton>
                            </Box>
                        )}

                        {/* Mobile Menu Button */}
                        {isMobile && (
                            <IconButton
                                color="inherit"
                                aria-label="open drawer"
                                edge="end"
                                onClick={handleDrawerToggle}
                            >
                                <MenuIcon />
                            </IconButton>
                        )}
                    </Toolbar>
                </Container>
            </AppBar>

            {/* Mobile Drawer */}
            <Drawer
                variant="temporary"
                anchor="right"
                open={mobileOpen}
                onClose={handleDrawerToggle}
                ModalProps={{
                    keepMounted: true,
                }}
            >
                {drawer}
            </Drawer>
        </>
    )
}

export default PublicNavbar