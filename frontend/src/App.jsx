import { Routes, Route } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

// Public pages
import HomePage from './pages/public/HomePage'
import ServicesPage from './pages/public/ServicesPage'
import GalleryPage from './pages/public/GalleryPage'
import ReviewsPage from './pages/public/ReviewsPage'
import BookingPage from './pages/public/BookingPage'
import ContactPage from './pages/public/ContactPage'

// Admin pages
import AdminDashboard from './pages/admin/AdminDashboard'
import BookingsManagement from './pages/admin/BookingsManagement'
import EventsManagement from './pages/admin/EventsManagement'
import GalleryManagement from './pages/admin/GalleryManagement'
import ReviewsManagement from './pages/admin/ReviewsManagement'
import InventoryManagement from './pages/admin/InventoryManagement'
import ReportsPage from './pages/admin/ReportsPage'
import ChatManagement from './pages/admin/ChatManagement'
import AdminLogin from './pages/admin/AdminLogin'

// Layouts
import PublicLayout from './components/layouts/PublicLayout'
import AdminLayout from './components/layouts/AdminLayout'
import ProtectedRoute from './components/common/ProtectedRoute'

// Components
import LoadingSpinner from './components/common/LoadingSpinner'
import ChatWidget from './components/chat/ChatWidget'

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
          <Route path="testimonios" element={<ReviewsPage />} />
          <Route path="agendar" element={<BookingPage />} />
          <Route path="contacto" element={<ContactPage />} />
        </Route>

        {/* Admin Login */}
        <Route path="/admin/login" element={<AdminLogin />} />

        {/* Protected Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<AdminDashboard />} />
          <Route path="agendamientos" element={<BookingsManagement />} />
          <Route path="eventos" element={<EventsManagement />} />
          <Route path="galeria" element={<GalleryManagement />} />
          <Route path="testimonios" element={<ReviewsManagement />} />
          <Route path="inventario" element={<InventoryManagement />} />
          <Route path="reportes" element={<ReportsPage />} />
          <Route path="chat" element={<ChatManagement />} />
        </Route>
      </Routes>

      {/* Chat Widget - Solo en páginas públicas */}
      <Routes>
        <Route path="/admin/*" element={null} />
        <Route path="*" element={<ChatWidget />} />
      </Routes>
    </div>
  )
}

export default App