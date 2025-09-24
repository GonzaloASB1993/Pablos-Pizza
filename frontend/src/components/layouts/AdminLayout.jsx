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
  ListSubheader,
  Collapse
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
  ContactMail,
  Logout,
  Person,
  Settings,
  ExpandLess,
  ExpandMore,
  Business,
  Analytics,
  MenuOpen
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import logo from '../../assets/logo.png'

const DRAWER_WIDTH = 280
const DRAWER_WIDTH_COLLAPSED = 70

const AdminLayout = () => {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileMenu, setProfileMenu] = useState(null)
  const [businessOpen, setBusinessOpen] = useState(true)
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [drawerCollapsed, setDrawerCollapsed] = useState(true) // Compact by default
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const currentDrawerWidth = drawerCollapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH

  const menuItems = [
    { label: 'Dashboard', path: '/admin', icon: <Dashboard />, category: 'main' },
    { label: 'Agendamientos', path: '/admin/agendamientos', icon: <Event />, category: 'business' },
    { label: 'Eventos', path: '/admin/eventos', icon: <Restaurant />, category: 'business' },
    { label: 'Contactos', path: '/admin/contactos', icon: <ContactMail />, category: 'business' },
    { label: 'Testimonios', path: '/admin/testimonios', icon: <Star />, category: 'business' },
    { label: 'Inventario', path: '/admin/inventario', icon: <Inventory />, category: 'analytics' },
    { label: 'Reportes', path: '/admin/reportes', icon: <Assessment />, category: 'analytics' },
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

  // Desktop drawer content (respects collapsed state)
  const desktopDrawer = (
    <div>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', width: '100%' }} onClick={() => navigate('/admin')}>
          {drawerCollapsed ? (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
              <Avatar
                src={logo}
                alt="Pablo's Pizza Logo"
                sx={{
                  width: 32,
                  height: 32,
                  border: '2px solid #FFD700'
                }}
              />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar
                src={logo}
                alt="Pablo's Pizza Logo"
                sx={{
                  width: 40,
                  height: 40,
                  mr: 2,
                  border: '2px solid #FFD700'
                }}
              />
              <Box>
                <Typography variant="h6" noWrap sx={{ fontWeight: 'bold', color: '#FFD700' }}>
                  Pablo's Pizza
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Panel Admin
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
        {!drawerCollapsed && (
          <IconButton
            onClick={() => setDrawerCollapsed(true)}
            sx={{ color: '#FFD700', ml: 'auto' }}
          >
            <MenuOpen />
          </IconButton>
        )}
      </Toolbar>

      {drawerCollapsed ? (
        // Compact view - just icons
        <List sx={{ px: 1 }}>
          <ListItem
            button
            onClick={() => setDrawerCollapsed(false)}
            sx={{
              mb: 1,
              borderRadius: 1,
              justifyContent: 'center'
            }}
          >
            <ListItemIcon sx={{ justifyContent: 'center', minWidth: 'auto' }}>
              <MenuIcon />
            </ListItemIcon>
          </ListItem>
          {menuItems.map((item) => (
            <ListItem
              button
              key={item.path}
              onClick={() => navigate(item.path)}
              selected={location.pathname === item.path}
              sx={{
                mb: 1,
                borderRadius: 1,
                justifyContent: 'center',
                '&.Mui-selected': {
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  borderLeft: '4px solid #FFD700'
                }
              }}
            >
              <ListItemIcon sx={{
                color: location.pathname === item.path ? '#FFD700' : 'inherit',
                justifyContent: 'center',
                minWidth: 'auto'
              }}>
                {item.icon}
              </ListItemIcon>
            </ListItem>
          ))}
        </List>
      ) : (
        // Full view - with categories
        <List>
          {/* Main Dashboard */}
          {menuItems.filter(item => item.category === 'main').map((item) => (
            <ListItem
              button
              key={item.path}
              onClick={() => navigate(item.path)}
              selected={location.pathname === item.path}
              sx={{
                mb: 1,
                borderRadius: 1,
                mx: 1,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  borderLeft: '4px solid #FFD700'
                }
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}

          <Divider sx={{ my: 1 }} />

          {/* Business Section */}
          <ListSubheader sx={{ backgroundColor: 'transparent', fontWeight: 'bold' }}>
            <ListItem button onClick={() => setBusinessOpen(!businessOpen)}>
              <ListItemIcon>
                <Business />
              </ListItemIcon>
              <ListItemText primary="Gestión de Negocio" />
              {businessOpen ? <ExpandLess /> : <ExpandMore />}
            </ListItem>
          </ListSubheader>

          <Collapse in={businessOpen} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {menuItems.filter(item => item.category === 'business').map((item) => (
                <ListItem
                  button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  selected={location.pathname === item.path}
                  sx={{
                    pl: 4,
                    borderRadius: 1,
                    mx: 1,
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(255, 215, 0, 0.1)',
                      borderLeft: '4px solid #FFD700'
                    }
                  }}
                >
                  <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.label} />
                </ListItem>
              ))}
            </List>
          </Collapse>

          <Divider sx={{ my: 1 }} />

          {/* Analytics Section */}
          <ListSubheader sx={{ backgroundColor: 'transparent', fontWeight: 'bold' }}>
            <ListItem button onClick={() => setAnalyticsOpen(!analyticsOpen)}>
              <ListItemIcon>
                <Analytics />
              </ListItemIcon>
              <ListItemText primary="Analytics & Reportes" />
              {analyticsOpen ? <ExpandLess /> : <ExpandMore />}
            </ListItem>
          </ListSubheader>

          <Collapse in={analyticsOpen} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {menuItems.filter(item => item.category === 'analytics').map((item) => (
                <ListItem
                  button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  selected={location.pathname === item.path}
                  sx={{
                    pl: 4,
                    borderRadius: 1,
                    mx: 1,
                    '&.Mui-selected': {
                      backgroundColor: 'rgba(255, 215, 0, 0.1)',
                      borderLeft: '4px solid #FFD700'
                    }
                  }}
                >
                  <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.label} />
                </ListItem>
              ))}
            </List>
          </Collapse>
        </List>
      )}

      <Box sx={{ position: 'absolute', bottom: 16, left: 16, right: 16 }}>
        {drawerCollapsed ? (
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
        ) : (
          <Button
            fullWidth
            variant="outlined"
            startIcon={<Logout />}
            onClick={handleLogout}
          >
            Cerrar Sesión
          </Button>
        )}
      </Box>
    </div>
  )

  // Mobile drawer content (always expanded with visible text)
  const mobileDrawer = (
    <div>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', width: '100%' }} onClick={() => navigate('/admin')}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Avatar
              src={logo}
              alt="Pablo's Pizza Logo"
              sx={{
                width: 40,
                height: 40,
                mr: 2,
                border: '2px solid #FFD700'
              }}
            />
            <Box>
              <Typography variant="h6" noWrap sx={{ fontWeight: 'bold', color: '#FFD700' }}>
                Pablo's Pizza
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                Panel Admin
              </Typography>
            </Box>
          </Box>
          <IconButton
            onClick={handleDrawerToggle}
            sx={{ color: '#FFD700', ml: 'auto' }}
          >
            <MenuOpen />
          </IconButton>
        </Box>
      </Toolbar>

      {/* Always show full view in mobile with all navigation options */}
      <List>
        {/* Main Dashboard */}
        {menuItems.filter(item => item.category === 'main').map((item) => (
          <ListItem
            button
            key={item.path}
            onClick={() => {
              navigate(item.path)
              setMobileOpen(false) // Close drawer after navigation
            }}
            selected={location.pathname === item.path}
            sx={{
              mb: 1,
              borderRadius: 1,
              mx: 1,
              '&.Mui-selected': {
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                borderLeft: '4px solid #FFD700'
              }
            }}
          >
            <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItem>
        ))}

        <Divider sx={{ my: 1 }} />

        {/* Business Section - Always expanded on mobile */}
        <ListSubheader sx={{ backgroundColor: 'transparent', fontWeight: 'bold', color: '#FFD700' }}>
          Gestión de Negocio
        </ListSubheader>

        <List component="div" disablePadding>
          {menuItems.filter(item => item.category === 'business').map((item) => (
            <ListItem
              button
              key={item.path}
              onClick={() => {
                navigate(item.path)
                setMobileOpen(false) // Close drawer after navigation
              }}
              selected={location.pathname === item.path}
              sx={{
                pl: 4,
                borderRadius: 1,
                mx: 1,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  borderLeft: '4px solid #FFD700'
                }
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>

        <Divider sx={{ my: 1 }} />

        {/* Analytics Section - Always expanded on mobile */}
        <ListSubheader sx={{ backgroundColor: 'transparent', fontWeight: 'bold', color: '#FFD700' }}>
          Analytics & Reportes
        </ListSubheader>

        <List component="div" disablePadding>
          {menuItems.filter(item => item.category === 'analytics').map((item) => (
            <ListItem
              button
              key={item.path}
              onClick={() => {
                navigate(item.path)
                setMobileOpen(false) // Close drawer after navigation
              }}
              selected={location.pathname === item.path}
              sx={{
                pl: 4,
                borderRadius: 1,
                mx: 1,
                '&.Mui-selected': {
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  borderLeft: '4px solid #FFD700'
                }
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#FFD700' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>
      </List>

      <Box sx={{ position: 'absolute', bottom: 16, left: 16, right: 16 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<Logout />}
          onClick={handleLogout}
          color="error"
        >
          Cerrar Sesión
        </Button>
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
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
        >
          {mobileDrawer}
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
          {desktopDrawer}
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