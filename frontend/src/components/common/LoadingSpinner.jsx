import { Box, CircularProgress, Typography } from '@mui/material'
import { useTheme } from '@mui/material/styles'

const LoadingSpinner = ({ message = 'Cargando...' }) => {
  const theme = useTheme()

  return (
    <Box
      display="flex"
      flexDirection="column"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      gap={2}
    >
      <CircularProgress 
        size={60} 
        thickness={4}
        sx={{ 
          color: theme.palette.primary.main 
        }}
      />
      <Typography 
        variant="body1" 
        color="text.secondary"
        sx={{ fontWeight: 500 }}
      >
        {message}
      </Typography>
    </Box>
  )
}

export default LoadingSpinner