import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  Rating,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Alert,
  Grid
} from '@mui/material'
import { CheckCircle, Cancel, Visibility, Delete } from '@mui/icons-material'
import { listenTestimonials, updateReview, deleteReview } from '../../services/testimonialsService'
import toast from 'react-hot-toast'

const ReviewsManagement = () => {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewDialog, setViewDialog] = useState(false)
  const [selectedReview, setSelectedReview] = useState(null)

  useEffect(() => {
    setLoading(true)
    const unsub = listenTestimonials((list) => {
      setReviews(list)
      setLoading(false)
    })
    return () => unsub && unsub()
  }, [])

  const handleApprove = async (reviewId) => {
    try {
      await updateReview(reviewId, { approved: true })
      toast.success('Reseña aprobada')
    } catch (error) {
      console.error('Error approving review:', error)
      toast.error('Error al aprobar reseña')
    }
  }

  const handleReject = async (reviewId) => {
    try {
      await updateReview(reviewId, { approved: false })
      toast.success('Reseña rechazada')
    } catch (error) {
      console.error('Error rejecting review:', error)
      toast.error('Error al rechazar reseña')
    }
  }

  const handleDelete = async (reviewId) => {
    try {
      await deleteReview(reviewId)
      toast.success('Reseña eliminada')
    } catch (error) {
      console.error('Error deleting review:', error)
      toast.error('Error al eliminar reseña')
    }
  }

  const handleViewClick = (review) => {
    setSelectedReview(review)
    setViewDialog(true)
  }

  const getStatusColor = (approved) => {
    if (approved === true) return 'success'
    if (approved === false) return 'error'
    return 'warning'
  }

  const getStatusLabel = (approved) => {
    if (approved === true) return 'Aprobada'
    if (approved === false) return 'Rechazada'
    return 'Pendiente'
  }

  const pendingReviews = reviews.filter(review => review.approved === undefined || review.approved === null)
  const approvedReviews = reviews.filter(review => review.approved === true)
  const rejectedReviews = reviews.filter(review => review.approved === false)

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Gestión de Reseñas
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Modera y aprueba las reseñas de clientes
      </Typography>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="warning.main" variant="h4">
                {pendingReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pendientes de aprobación
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="success.main" variant="h4">
                {approvedReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Aprobadas
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="error.main" variant="h4">
                {rejectedReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Rechazadas
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {loading ? (
        <Card>
          <CardContent>
            <Typography>Cargando reseñas...</Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Rating</TableCell>
                    <TableCell>Comentario</TableCell>
                    <TableCell>Fecha</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reviews.map((review) => (
                    <TableRow key={review.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {review.name || 'Anónimo'}
                          </Typography>
                          {review.email && (
                            <Typography variant="caption" color="text.secondary">
                              {review.email}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Rating value={review.rating || 0} readOnly size="small" />
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {review.comment || 'Sin comentario'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {review.createdAt?.toDate ? review.createdAt.toDate().toLocaleDateString('es-CL') : (review.created_at ? new Date(review.created_at).toLocaleDateString('es-CL') : 'N/A')}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusLabel(review.approved)}
                          color={getStatusColor(review.approved)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleViewClick(review)}
                          >
                            <Visibility />
                          </IconButton>
                          {review.approved !== true && (
                            <IconButton
                              size="small"
                              color="success"
                              onClick={() => handleApprove(review.id)}
                            >
                              <CheckCircle />
                            </IconButton>
                          )}
                          {review.approved !== false && (
                            <IconButton
                              size="small"
                              color="warning"
                              onClick={() => handleReject(review.id)}
                            >
                              <Cancel />
                            </IconButton>
                          )}
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDelete(review.id)}
                          >
                            <Delete />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                  {reviews.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography color="text.secondary">
                          No hay reseñas disponibles
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* View Review Dialog */}
      <Dialog open={viewDialog} onClose={() => setViewDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Detalle de Reseña</DialogTitle>
        <DialogContent>
          {selectedReview && (
            <Box sx={{ py: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Cliente:</Typography>
                  <Typography variant="body1">{selectedReview.name || 'Anónimo'}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Email:</Typography>
                  <Typography variant="body1">{selectedReview.email || 'No proporcionado'}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Rating:</Typography>
                  <Rating value={selectedReview.rating || 0} readOnly />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Fecha:</Typography>
                  <Typography variant="body1">
                    {selectedReview.createdAt?.toDate ? selectedReview.createdAt.toDate().toLocaleDateString('es-CL') : (selectedReview.created_at ? new Date(selectedReview.created_at).toLocaleDateString('es-CL') : 'N/A')}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="text.secondary">Comentario:</Typography>
                  <Typography variant="body1" sx={{ mt: 1, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                    {selectedReview.comment || 'Sin comentario'}
                  </Typography>
                </Grid>
                {Array.isArray(selectedReview.photos) && selectedReview.photos.length > 0 && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" color="text.secondary">Fotos:</Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {selectedReview.photos.map((url) => (
                        <Box key={url} component="img" src={url} alt="foto reseña" sx={{ width: 96, height: 96, objectFit: 'cover', borderRadius: 1, border: '1px solid #eee' }} />
                      ))}
                    </Box>
                  </Grid>
                )}
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="text.secondary">Estado:</Typography>
                  <Chip
                    label={getStatusLabel(selectedReview.approved)}
                    color={getStatusColor(selectedReview.approved)}
                    sx={{ mt: 1 }}
                  />
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialog(false)}>Cerrar</Button>
          {selectedReview && selectedReview.approved !== true && (
            <Button
              onClick={() => {
                handleApprove(selectedReview.id)
                setViewDialog(false)
              }}
              variant="contained"
              color="success"
              startIcon={<CheckCircle />}
            >
              Aprobar
            </Button>
          )}
          {selectedReview && selectedReview.approved !== false && (
            <Button
              onClick={() => {
                handleReject(selectedReview.id)
                setViewDialog(false)
              }}
              variant="outlined"
              color="warning"
              startIcon={<Cancel />}
            >
              Rechazar
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ReviewsManagement