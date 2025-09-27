# Planning.md - Pablo's Pizza Project

## 🎯 Visión del Proyecto

### Objetivo Principal
Sistema completo de gestión para el negocio de Pablo's Pizza que incluye una **página web pública** para captación de clientes y un **panel administrativo** robusto para gestión integral del negocio (reservas, eventos, galería, contactos, inventario y reportes financieros).

### Propuesta de Valor
- **Captación automatizada**: Sistema de reservas online con confirmación automática
- **Gestión completa**: Panel admin unificado para todas las operaciones
- **Comunicación directa**: Integración WhatsApp para contacto inmediato
- **Tracking financiero**: Seguimiento de costos, ganancias y rentabilidad
- **Experiencia visual**: Galería de eventos para mostrar el trabajo realizado

### Audiencia Objetivo
- **Primaria**: Familias y particulares organizando fiestas de cumpleaños
- **Secundaria**: Empresas buscando actividades corporativas y team building
- **Terciaria**: Colegios y organizaciones educativas para eventos escolares

### Métricas de Éxito Actuales
- **Sistema funcionando**: ✅ Web pública + Admin panel operativo
- **Reservas activas**: Sistema de booking con confirmación
- **Gestión de eventos**: Workflow completo de evento → financiero
- **Comunicación**: Sistema de contacto con WhatsApp integrado
- **Galería operativa**: Upload y publicación de fotos de eventos

## 🏗️ Arquitectura del Sistema

### Arquitectura General Actual
```
Frontend (React + Vite) ↔ Backend API (Python Flask) ↔ Database (Firebase)
        ↓                       ↓                          ↓
   Firebase Hosting          Cloud Run               Firestore + Storage
```

### Componentes Principales

#### Frontend Architecture
- **Public Site**: Landing, booking, contact, gallery, reviews
- **Admin Panel**: Dashboard, bookings, events, contacts, gallery, reports
- **Authentication**: Firebase Auth con protección de rutas
- **State Management**: React Context + local state
- **UI Framework**: Material-UI con tema personalizado

#### Backend Architecture
- **API Layer**: Flask con CORS y validación Pydantic
- **Business Logic**: Servicios especializados por feature
- **Data Access**: Firebase Firestore con queries optimizadas
- **File Management**: Firebase Storage para galería
- **External APIs**: WhatsApp Business integration

#### Database Schema (Firestore)
- **bookings**: Sistema de reservas con estados y costos
- **events**: Eventos completados con tracking financiero
- **contacts**: Sistema de contacto con prioridades y respuestas
- **gallery**: Gestión de fotos con estado de publicación
- **reviews**: Testimonios de clientes con aprobación
- **inventory**: Control de stock (en desarrollo)

## 💻 Technology Stack Actual

### Frontend Stack
```javascript
// Core Framework
- React 18 (Hooks + Context)
- Vite (Build tool)
- Material-UI 5 (Component library)
- React Router DOM 6 (Navigation)

// Data & Forms
- Axios (HTTP client)
- React Hot Toast (Notifications)
- date-fns (Date utilities)
- Custom form validation

// Firebase Integration
- Firebase 10 (Auth + Hosting)
- Firebase Auth (Authentication)
- Firebase Storage (File uploads)
```

### Backend Stack
```python
# Framework & Runtime
- Python 3.9+
- Flask 2.3+ (Web framework)
- Flask-CORS (Cross-origin support)
- Gunicorn (Production server)

# Database & Validation
- Firebase Admin SDK
- Firebase Firestore (Database)
- Pydantic 2.1+ (Data validation)
- python-dotenv (Environment management)

# External Services
- WhatsApp Business API integration
- Firebase Storage (File management)
- Email service integration
```

### DevOps & Deployment
```yaml
# Hosting & Infrastructure
Frontend: Firebase Hosting
Backend: Google Cloud Run
Database: Firebase Firestore
Storage: Firebase Storage
CDN: Firebase CDN

# Development
Version Control: Git
Code Quality: ESLint + Python formatting
Environment: Development + Production configs
```

## 🛠️ Herramientas y Servicios Actuales

### Desarrollo Local
```bash
# Frontend Tools
- Node.js 18+ LTS
- npm/yarn package manager
- Vite development server
- Firebase CLI

# Backend Tools
- Python 3.9+ virtual environment
- Flask development server
- Firebase Admin SDK
- Python debugging tools
```

### Servicios Externos Integrados
```javascript
// Firebase Services
- Authentication (user management)
- Firestore (database)
- Storage (file management)
- Hosting (frontend deployment)

// Communication
- WhatsApp Business API (customer contact)
- Email service (confirmations)
- SMS integration (pending)

// Monitoring & Analytics
- Firebase Analytics (basic)
- Cloud Run monitoring
- Error logging (basic)
```

### Herramientas de Productividad
```bash
# Development Workflow
- VS Code (IDE principal)
- Firebase Console (database management)
- Postman (API testing)
- Git version control

# Business Management
- WhatsApp Business (comunicación)
- Firebase Console (admin operations)
- Cloud Run Console (deployment monitoring)
```

## 📦 Estructura de Archivos Actual

```
Pablos Pizza/
├── frontend/                 # React app con Vite
│   ├── src/
│   │   ├── components/      # Componentes reutilizables
│   │   │   ├── common/      # Componentes compartidos
│   │   │   ├── layouts/     # Layouts de página
│   │   │   └── forms/       # Componentes de formulario
│   │   ├── pages/
│   │   │   ├── public/      # Páginas públicas
│   │   │   └── admin/       # Panel administrativo
│   │   ├── services/        # Servicios de API
│   │   ├── contexts/        # React contexts
│   │   ├── utils/           # Utilidades
│   │   └── config/          # Configuración
│   └── public/              # Assets estáticos
├── backend/                  # API Python Flask
│   ├── main.py              # Aplicación principal
│   ├── models/              # Modelos Pydantic
│   ├── services/            # Lógica de negocio
│   ├── utils/               # Utilidades
│   └── requirements.txt     # Dependencias Python
├── docs/                    # Documentación
│   └── API_DOCUMENTATION.md # Especificación API
└── .claude/                 # Documentación Claude
    ├── CLAUDE.md            # Overview del proyecto
    ├── CLAUDE-FRONTEND.md   # Frontend específico
    └── CLAUDE-BACKEND.md    # Backend específico
```

## 🎯 Features Implementadas vs Pendientes

### ✅ Features Completadas
- **Sistema de reservas público** con formulario completo
- **Panel administrativo** con autenticación
- **Gestión de eventos** con tracking financiero
- **Sistema de contacto** con WhatsApp integration
- **Galería de fotos** con workflow de publicación
- **Dashboard administrativo** con métricas básicas
- **Responsive design** para mobile y desktop
- **Sistema de reviews** con moderación

### 🔄 Features en Desarrollo
- **Sistema de inventario** (estructura creada, pendiente implementación)
- **Reportes financieros avanzados** (básicos implementados)
- **Notificaciones push** (estructura básica)
- **Email automation** (confirmaciones básicas)
- **Analytics avanzados** (métricas básicas)

### 📋 Features Pendientes
- **Sistema de facturación** automatizada
- **Integración calendarios externos** (Google Calendar)
- **App móvil nativa** (futuro)
- **Multi-tenant** para otros negocios (futuro)
- **Advanced analytics** y dashboards
- **Backup automático** y disaster recovery

## 🔧 Configuración del Entorno

### Variables de Entorno Requeridas
```bash
# Frontend (.env)
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_domain
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_API_BASE_URL=your_backend_url

# Backend (.env)
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_SERVICE_ACCOUNT_PATH=path_to_service_account
WHATSAPP_API_TOKEN=your_whatsapp_token
EMAIL_SERVICE_API_KEY=your_email_key
```

### Comandos de Desarrollo
```bash
# Frontend development
cd frontend && npm run dev        # Puerto 3000

# Backend development  
cd backend && python main.py     # Puerto 5000

# Production build
npm run build                     # Frontend build
```

## 📊 Métricas y Monitoreo Actual

### Métricas Técnicas
- **Performance**: Basic loading times monitored
- **Uptime**: Cloud Run automatic scaling
- **Errors**: Basic error logging en Firestore
- **Usage**: Firebase Analytics básico

### Métricas de Negocio
- **Conversión de reservas**: Tracking en admin panel
- **Eventos completados**: Dashboard con stats
- **Contactos generados**: Sistema de contacto con prioridades
- **Reviews recibidas**: Moderación en admin panel

## 🚀 Roadmap de Mejoras

### Prioridad Alta (Próximas 4 semanas)
- Completar sistema de inventario
- Mejorar reportes financieros
- Optimizar performance de galería
- Implementar backup automático

### Prioridad Media (1-3 meses)
- Sistema de facturación
- Integración Google Calendar
- Analytics avanzados
- Mobile app PWA

### Prioridad Baja (3+ meses)
- Multi-tenant architecture
- Advanced automation
- Machine learning insights
- International expansion features

---

**Última actualización**: Septiembre 2025  
**Estado del proyecto**: Producción activa con mejoras continuas  
**Próximo milestone**: Optimización y nuevas features