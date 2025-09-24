# 🎨 Frontend Documentation - Pablo's Pizza

## 📁 Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── common/           # Shared components
│   │   ├── layouts/          # Layout components
│   │   └── forms/            # Form components
│   ├── pages/
│   │   ├── public/           # Public pages
│   │   └── admin/            # Admin panel pages
│   ├── services/             # API services
│   ├── contexts/             # React contexts
│   ├── utils/                # Utility functions
│   └── config/               # Configuration files
├── public/                   # Static assets
└── package.json              # Dependencies
```

## 🧩 Key Components

### 📱 Public Pages
- **HomePage.jsx** - Main landing page with hero, features, testimonials
- **BookingPage.jsx** - Public booking form for events
- **ContactPage.jsx** - Contact form with priority selection + WhatsApp integration
- **GalleryPage.jsx** - Public gallery displaying event photos
- **ReviewsPage.jsx** - Customer testimonials and reviews

### 🔧 Admin Pages
- **AdminDashboard.jsx** - Overview stats and quick actions
- **BookingsManagement.jsx** - Booking list/calendar with cost editing workflow
- **EventsManagement.jsx** - Completed events tracking
- **ContactManagement.jsx** - NEW: Contact messages with WhatsApp response system
- **GalleryManagement.jsx** - Photo uploads and publication management
- **InventoryManagement.jsx** - Stock tracking and alerts
- **ReportsPage.jsx** - Financial reports and analytics

### 🎯 Layout Components
- **PublicLayout.jsx** - Navigation, header, footer for public pages
- **AdminLayout.jsx** - Sidebar navigation with menu categories
- **ProtectedRoute.jsx** - Authentication wrapper for admin routes

## 🔄 Routing Structure
```jsx
// App.jsx route structure
<Routes>
  {/* Public Routes */}
  <Route path="/" element={<PublicLayout />}>
    <Route index element={<HomePage />} />
    <Route path="agendar" element={<BookingPage />} />
    <Route path="contacto" element={<ContactPage />} />
    <Route path="galeria" element={<GalleryPage />} />
    <Route path="testimonios" element={<ReviewsPage />} />
  </Route>

  {/* Admin Routes */}
  <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
    <Route index element={<AdminDashboard />} />
    <Route path="agendamientos" element={<BookingsManagement />} />
    <Route path="eventos" element={<EventsManagement />} />
    <Route path="contactos" element={<ContactManagement />} />
    <Route path="galeria" element={<GalleryManagement />} />
    <Route path="testimonios" element={<ReviewsManagement />} />
    <Route path="inventario" element={<InventoryManagement />} />
    <Route path="reportes" element={<ReportsPage />} />
  </Route>
</Routes>
```

## 📡 API Services
```javascript
// services/api.js - Main API configuration
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://main-4kqeqojbsq-uc.a.run.app'
  : 'https://main-4kqeqojbsq-uc.a.run.app'

// API modules
export const bookingsAPI = { create, getAll, update, delete, getCalendar }
export const eventsAPI = { create, getAll, update, requestReview }
export const galleryAPI = { upload, getAll, update, delete }
export const reviewsAPI = { create, getAll, approve, delete }
export const inventoryAPI = { create, getAll, updateStock, getAlerts }
export const reportsAPI = { getMonthly, getAnnual, getDashboard }
export const notificationsAPI = { send, getAll, sendBulk }
export const contactAPI = { create, getAll, update, respond } // NEW
```

## 🎨 UI/UX Patterns

### 🎭 Material-UI Theme
- Primary color: **#1976d2** (blue)
- Secondary color: **#FFD700** (gold)
- Custom theme in `utils/theme.js`

### 📋 Common Dialog Patterns
```jsx
// Standard dialog structure used throughout admin
<Dialog open={dialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
  <DialogTitle>Title</DialogTitle>
  <DialogContent>
    <Grid container spacing={3}>
      {/* Form fields */}
    </Grid>
  </DialogContent>
  <DialogActions>
    <Button onClick={handleClose}>Cancelar</Button>
    <Button variant="contained" onClick={handleSubmit}>Confirmar</Button>
  </DialogActions>
</Dialog>
```

### 📊 Data Display Patterns
- **Cards** for dashboards and overview displays
- **Tables** for detailed data management
- **Calendars** for booking/event scheduling
- **Chips** for status indicators and tags

## 🔒 Authentication Flow
```javascript
// contexts/AuthContext.jsx
const useAuth = () => {
  const { user, loading, login, logout } = useContext(AuthContext)
  return { user, loading, login, logout }
}

// Protected routes check authentication
<ProtectedRoute>
  {user ? <AdminLayout /> : <Navigate to="/admin/login" />}
</ProtectedRoute>
```

## 📱 Responsive Design
- **Mobile-first approach** with Material-UI breakpoints
- **Grid system** for layout flexibility
- **useMediaQuery** for conditional rendering
- **Drawer navigation** on mobile, sidebar on desktop

## 🚀 Performance Optimizations
- **React.lazy** for code splitting admin pages
- **Memo** for expensive calculations
- **Image optimization** with proper loading states
- **API caching** with React Query (where implemented)

## 🎯 Current Development Priorities
1. **Contact System Integration** - New ContactManagement component
2. **Booking Workflow Enhancement** - Cost dialog before completion
3. **Gallery Photo Display** - Fixed real photos vs logo issue
4. **Mobile Responsiveness** - Ongoing improvements
5. **Performance** - Loading states and error handling

## 🔧 Development Commands
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## 📦 Key Dependencies
```json
{
  "@mui/material": "^5.x",
  "@mui/icons-material": "^5.x",
  "react": "^18.x",
  "react-router-dom": "^6.x",
  "axios": "^1.x",
  "react-hot-toast": "^2.x",
  "date-fns": "^2.x",
  "firebase": "^10.x"
}
```