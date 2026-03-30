import React from 'react'
import { Box, Typography, Container } from '@mui/material'

export default function GalleryPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 2 }}>
          Galería
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Próximamente encontrarás aquí las fotos de nuestros eventos.
        </Typography>
      </Box>
    </Container>
  )
}
