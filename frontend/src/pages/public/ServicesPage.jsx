import React from 'react'
import { Box, Typography, Container } from '@mui/material'

export default function ServicesPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 2 }}>
          Servicios
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Conoce todos los servicios que Pablo's Pizza tiene para ti.
        </Typography>
      </Box>
    </Container>
  )
}
