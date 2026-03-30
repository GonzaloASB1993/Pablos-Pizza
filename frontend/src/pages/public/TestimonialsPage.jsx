import React from 'react'
import { Box, Typography, Container } from '@mui/material'

export default function TestimonialsPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 2 }}>
          Testimonios
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Lo que dicen nuestros clientes.
        </Typography>
      </Box>
    </Container>
  )
}
