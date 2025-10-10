import { Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { useAuth } from './contexts/AuthContext'

// Public pages - eager loading (critical for SEO and initial load)
import HomePage from './pages/public/HomePage'
import GalleryPage from './pages/public/GalleryPage'
import TestimonialsPage from './pages/public/TestimonialsPage'
import BookingPage from './pages/public/BookingPage'
import ServicesPage from './pages/public/ServicesPage'
import ContactPage from './pages/public/ContactPage'

// Admin pages - lazy loading (no afecta SEO, optimiza bundle inicial)
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'))
const BookingsManagement = lazy(() => import('./pages/admin/BookingsManagement'))
const EventsManagement = lazy(() => import('./pages/admin/EventsManagement'))
const GalleryManagement = lazy(() => import('./pages/admin/GalleryManagement'))
const ReviewsManagement = lazy(() => import('./pages/admin/ReviewsManagement'))
const InventoryManagement = lazy(() => import('./pages/admin/InventoryManagement'))
const ProductionManagement = lazy(() => import('./pages/admin/ProductionManagement'))
const ReportsPage = lazy(() => import('./pages/admin/ReportsPage'))
const ContactManagement = lazy(() => import('./pages/admin/ContactManagement'))
const AdminLogin = lazy(() => import('./pages/admin/AdminLogin'))

// Layouts
import PublicLayout from './components/layouts/PublicLayout'
import AdminLayout from './components/layouts/AdminLayout'
import ProtectedRoute from './components/common/ProtectedRoute'

// Components
import LoadingSpinner from './components/common/LoadingSpinner'

function App() {
  const { loading } = useAuth()

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <div className="App">
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="servicios" element={<ServicesPage />} />
          <Route path="galeria" element={<GalleryPage />} />
          <Route path="testimonios" element={<TestimonialsPage />} />
          <Route path="agendar" element={<BookingPage />} />
          <Route path="contacto" element={<ContactPage />} />
        </Route>

        {/* Admin Login */}
        <Route path="/admin/login" element={
          <Suspense fallback={<LoadingSpinner />}>
            <AdminLogin />
          </Suspense>
        } />

        {/* Protected Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={
            <Suspense fallback={<LoadingSpinner />}>
              <AdminDashboard />
            </Suspense>
          } />
          <Route path="agendamientos" element={
            <Suspense fallback={<LoadingSpinner />}>
              <BookingsManagement />
            </Suspense>
          } />
          <Route path="eventos" element={
            <Suspense fallback={<LoadingSpinner />}>
              <EventsManagement />
            </Suspense>
          } />
          <Route path="galeria" element={
            <Suspense fallback={<LoadingSpinner />}>
              <GalleryManagement />
            </Suspense>
          } />
          <Route path="testimonios" element={
            <Suspense fallback={<LoadingSpinner />}>
              <ReviewsManagement />
            </Suspense>
          } />
          <Route path="inventario" element={
            <Suspense fallback={<LoadingSpinner />}>
              <InventoryManagement />
            </Suspense>
          } />
          <Route path="produccion" element={
            <Suspense fallback={<LoadingSpinner />}>
              <ProductionManagement />
            </Suspense>
          } />
          <Route path="reportes" element={
            <Suspense fallback={<LoadingSpinner />}>
              <ReportsPage />
            </Suspense>
          } />
          <Route path="contactos" element={
            <Suspense fallback={<LoadingSpinner />}>
              <ContactManagement />
            </Suspense>
          } />
        </Route>
      </Routes>

    </div>
  )
}

export default App