import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Button,
  Menu,
  MenuItem,
  Avatar,
  Divider,
  Tooltip
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard,
  Event,
  Restaurant,
  Photo,
  Star,
  Inventory,
  Assessment,
  Chat,
  Logout,
  Person,
  Settings,
  MenuOpen
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import logo from '../../assets/logo.png'

const DRAWER_WIDTH = 70 // Compact by default

const AdminLayout = () => {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileMenu, setProfileMenu] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const currentDrawerWidth = expanded ? 240 : DRAWER_WIDTH

  const menuItems = [
    { label: 'Dashboard', path: '/admin', icon: <Dashboard /> },
    { label: 'Agendamientos', path: '/admin/agendamientos', icon: <Event /> },
    { label: 'Eventos', path: '/admin/eventos', icon: <Restaurant /> },
    { label: 'Galería', path: '/admin/galeria', icon: <Photo /> },
    { label: 'Chat', path: '/admin/chat', icon: <Chat /> },
    { label: 'Testimonios', path: '/admin/testimonios', icon: <Star /> },
    { label: 'Inventario', path: '/admin/inventario', icon: <Inventory /> },
    { label: 'Reportes', path: '/admin/reportes', icon: <Assessment /> },
  ]

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleProfileMenu = (event) => {
    setProfileMenu(event.currentTarget)
  }

  const handleCloseProfileMenu = () => {
    setProfileMenu(null)
  }

  const handleLogout = async () => {
    try {
      await logout()
      navigate('/admin/login')
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  const drawer = (
    <div>
      <Toolbar sx={{ minHeight: '64px !important' }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: expanded ? 'space-between' : 'center',
            width: '100%'
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer'
            }}
            onClick={() => navigate('/admin')}
          >
            <Avatar
              src={logo}
              alt="Pablo's Pizza Logo"
              sx={{
                width: expanded ? 32 : 28,
                height: expanded ? 32 : 28,
                mr: expanded ? 1 : 0,
                border: '2px solid #FFD700'
              }}
            />
            {expanded && (
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#FFD700' }}>
                Pablo's
              </Typography>
            )}
          </Box>

          <IconButton
            onClick={() => setExpanded(!expanded)}
            sx={{ color: '#FFD700', p: 0.5 }}
            size="small"
          >
            {expanded ? <MenuOpen /> : <MenuIcon />}
          </IconButton>
        </Box>
      </Toolbar>

      <List sx={{ px: 1 }}>
        {menuItems.map((item) => (
          <Tooltip
            key={item.path}
            title={expanded ? '' : item.label}
            placement="right"
            arrow
          >
            <ListItem
              button
              onClick={() => navigate(item.path)}
              selected={location.pathname === item.path}
              sx={{
                mb: 0.5,
                borderRadius: 2,
                minHeight: 40,
                justifyContent: expanded ? 'flex-start' : 'center',
                px: expanded ? 2 : 1,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(255, 215, 0, 0.15)',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    left: 0,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: 3,
                    height: '60%',
                    backgroundColor: '#FFD700',
                    borderRadius: '0 2px 2px 0'
                  }
                },
                '&:hover': {
                  backgroundColor: 'rgba(255, 215, 0, 0.08)'
                }
              }}
            >
              <ListItemIcon sx={{
                color: location.pathname === item.path ? '#FFD700' : 'inherit',
                minWidth: expanded ? 40 : 'auto',
                justifyContent: 'center'
              }}>
                {item.icon}
              </ListItemIcon>
              {expanded && (
                <ListItemText
                  primary={item.label}
                  sx={{
                    '& .MuiListItemText-primary': {
                      fontSize: '0.875rem',
                      fontWeight: location.pathname === item.path ? 600 : 400
                    }
                  }}
                />
              )}
            </ListItem>
          </Tooltip>
        ))}
      </List>

      <Box sx={{ position: 'absolute', bottom: 16, left: 8, right: 8 }}>
        <Tooltip title={expanded ? '' : 'Cerrar Sesión'} placement="right" arrow>
          <Box>
            {expanded ? (
              <Button
                fullWidth
                variant="outlined"
                startIcon={<Logout />}
                onClick={handleLogout}
                sx={{
                  borderColor: 'error.main',
                  color: 'error.main',
                  fontSize: '0.75rem',
                  py: 1
                }}
              >
                Cerrar Sesión
              </Button>
            ) : (
              <IconButton
                onClick={handleLogout}
                sx={{
                  width: '100%',
                  color: 'error.main',
                  border: '1px solid',
                  borderColor: 'error.main',
                  borderRadius: 2
                }}
              >
                <Logout fontSize="small" />
              </IconButton>
            )}
          </Box>
        </Tooltip>
      </Box>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          ml: { sm: `${currentDrawerWidth}px` },
          zIndex: (theme) => theme.zIndex.drawer + 1
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <Typography variant="h6" noWrap component="div">
              Panel Administrativo - Pablo's Pizza
            </Typography>

            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <IconButton
                color="inherit"
                onClick={handleProfileMenu}
                sx={{ ml: 1 }}
              >
                <Avatar
                  src={logo}
                  sx={{ width: 32, height: 32 }}
                />
              </IconButton>

              <Menu
                anchorEl={profileMenu}
                open={Boolean(profileMenu)}
                onClose={handleCloseProfileMenu}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
              >
                <MenuItem onClick={handleCloseProfileMenu}>
                  <ListItemIcon>
                    <Person fontSize="small" />
                  </ListItemIcon>
                  Perfil
                </MenuItem>
                <MenuItem onClick={handleCloseProfileMenu}>
                  <ListItemIcon>
                    <Settings fontSize="small" />
                  </ListItemIcon>
                  Configuración
                </MenuItem>
                <Divider />
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <Logout fontSize="small" />
                  </ListItemIcon>
                  Cerrar Sesión
                </MenuItem>
              </Menu>
            </Box>
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: currentDrawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="mailbox folders"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: currentDrawerWidth,
              transition: 'width 0.3s ease'
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          transition: 'width 0.3s ease'
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}

export default AdminLayout