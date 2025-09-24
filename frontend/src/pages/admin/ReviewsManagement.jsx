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
  Grid,
  Tabs,
  Tab,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton
} from '@mui/material'
import {
  CheckCircle,
  Cancel,
  Visibility,
  Delete,
  PendingActions,
  Star,
  ThumbDown,
  Refresh,
  ViewList,
  Assignment
} from '@mui/icons-material'
import { listenTestimonials, updateReview, deleteReview } from '../../services/testimonialsService'
import toast from 'react-hot-toast'

const ReviewsManagement = () => {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewDialog, setViewDialog] = useState(false)
  const [selectedReview, setSelectedReview] = useState(null)
  const [tabValue, setTabValue] = useState(0)
  const [view, setView] = useState('cards')

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

  const getReviewsByStatus = (status) => {
    if (status === 'pending') return pendingReviews
    if (status === 'approved') return approvedReviews
    if (status === 'rejected') return rejectedReviews
    return reviews
  }

  const calculateAverageRating = () => {
    if (approvedReviews.length === 0) return 0
    const sum = approvedReviews.reduce((acc, review) => acc + (review.rating || 0), 0)
    return (sum / approvedReviews.length).toFixed(1)
  }

  const ReviewCard = ({ review }) => (
    <Card sx={{ mb: 2, borderLeft: `4px solid ${getStatusColor(review.approved) === 'warning' ? '#ff9800' : getStatusColor(review.approved) === 'success' ? '#4caf50' : '#f44336'}` }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {review.name || 'Cliente Anónimo'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              📧 {review.email || 'No proporcionado'}
            </Typography>
            <Rating value={review.rating || 0} readOnly size="small" sx={{ mt: 1 }} />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
            <Chip
              label={getStatusLabel(review.approved)}
              color={getStatusColor(review.approved)}
              size="small"
            />
            <Typography variant="caption" color="text.secondary">
              {review.rating || 0} ⭐
            </Typography>
          </Box>
        </Box>

        <Typography variant="body1" sx={{
          mb: 2,
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          fontStyle: 'italic'
        }}>
          "{review.comment || 'Sin comentario'}"
        </Typography>

        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
          {review.createdAt?.toDate
            ? review.createdAt.toDate().toLocaleDateString('es-CL')
            : (review.created_at ? new Date(review.created_at).toLocaleDateString('es-CL') : 'N/A')
          }
        </Typography>

        {Array.isArray(review.photos) && review.photos.length > 0 && (
          <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {review.photos.slice(0, 3).map((url, index) => (
              <Box
                key={index}
                component="img"
                src={url}
                alt="foto reseña"
                sx={{
                  width: 60,
                  height: 60,
                  objectFit: 'cover',
                  borderRadius: 1,
                  border: '1px solid #eee'
                }}
              />
            ))}
            {review.photos.length > 3 && (
              <Box sx={{
                width: 60,
                height: 60,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'grey.100',
                borderRadius: 1,
                border: '1px solid #eee'
              }}>
                <Typography variant="caption">+{review.photos.length - 3}</Typography>
              </Box>
            )}
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" variant="outlined" startIcon={<Visibility />} onClick={() => handleViewClick(review)}>
            Ver Detalle
          </Button>
          {review.approved !== true && (
            <Button
              size="small"
              variant="contained"
              color="success"
              startIcon={<CheckCircle />}
              onClick={() => handleApprove(review.id)}
            >
              Aprobar
            </Button>
          )}
          {review.approved !== false && (
            <Button
              size="small"
              variant="outlined"
              color="warning"
              startIcon={<Cancel />}
              onClick={() => handleReject(review.id)}
            >
              Rechazar
            </Button>
          )}
          <Button
            size="small"
            variant="outlined"
            color="error"
            startIcon={<Delete />}
            onClick={() => handleDelete(review.id)}
          >
            Eliminar
          </Button>
        </Box>
      </CardContent>
    </Card>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Gestión de Reseñas
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => window.location.reload()}
            disabled={loading}
          >
            Actualizar
          </Button>
          <ToggleButtonGroup
            value={view}
            exclusive
            onChange={(e, newView) => newView && setView(newView)}
            size="small"
          >
            <ToggleButton value="cards">
              <ViewList />
            </ToggleButton>
            <ToggleButton value="table">
              <Assignment />
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#fff3e0' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <PendingActions sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#ff9800' }}>
                {pendingReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pendientes
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#e8f5e8' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <CheckCircle sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                {approvedReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Aprobadas
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#ffebee' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <ThumbDown sx={{ fontSize: 40, color: '#f44336', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#f44336' }}>
                {rejectedReviews.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Rechazadas
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: '#e3f2fd' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Star sx={{ fontSize: 40, color: '#2196f3', mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#2196f3' }}>
                {calculateAverageRating()}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Promedio ⭐
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for different statuses - only show in cards view */}
      {view === 'cards' && (
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
            <Tab label={`Pendientes (${pendingReviews.length})`} />
            <Tab label={`Aprobadas (${approvedReviews.length})`} />
            <Tab label={`Rechazadas (${rejectedReviews.length})`} />
          </Tabs>
        </Paper>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : view === 'cards' ? (
        <Box>
          {tabValue === 0 && (
            <Box>
              {pendingReviews.length === 0 ? (
                <Alert severity="info">No hay reseñas pendientes de aprobación</Alert>
              ) : (
                pendingReviews.map(review => (
                  <ReviewCard key={review.id} review={review} />
                ))
              )}
            </Box>
          )}

          {tabValue === 1 && (
            <Box>
              {approvedReviews.length === 0 ? (
                <Alert severity="info">No hay reseñas aprobadas</Alert>
              ) : (
                approvedReviews.map(review => (
                  <ReviewCard key={review.id} review={review} />
                ))
              )}
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              {rejectedReviews.length === 0 ? (
                <Alert severity="info">No hay reseñas rechazadas</Alert>
              ) : (
                rejectedReviews.map(review => (
                  <ReviewCard key={review.id} review={review} />
                ))
              )}
            </Box>
          )}
        </Box>
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