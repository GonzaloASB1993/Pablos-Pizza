import { Outlet } from 'react-router-dom'
import { Box } from '@mui/material'
import PublicNavbar from '../navigation/PublicNavbar'
import Footer from '../common/Footer'

const PublicLayout = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <PublicNavbar />
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Outlet />
      </Box>
      <Footer />
    </Box>
  )
}

export default PublicLayout