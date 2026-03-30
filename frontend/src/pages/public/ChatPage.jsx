import React from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button
} from '@mui/material'
import { WhatsApp, Instagram } from '@mui/icons-material'

export default function ChatPage() {
  return (
    <Box sx={{ py: { xs: 6, md: 8 } }}>
      <Container maxWidth="sm">
        <Card>
          <CardContent>
            <Typography variant="h2" gutterBottom>
              Chat en Vivo
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              ¿Tienes dudas sobre disponibilidad, precios o servicios? Escríbenos y te
              responderemos a la brevedad.
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<WhatsApp />}
                href="https://wa.me/56989424566"
                target="_blank"
              >
                WhatsApp
              </Button>
              <Button
                variant="outlined"
                startIcon={<Instagram />}
                href="https://instagram.com/pablospizza.cl"
                target="_blank"
              >
                Instagram
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  )
}
