# 🍕 Pablo's Pizza - Sistema Completo de Gestión

Sistema web completo para la gestión de talleres de pizza para niños y eventos de pizza parties, incluyendo panel administrativo, sistema de agendamientos, notificaciones WhatsApp, chat en vivo y aplicación móvil.

## 📋 Características Principales

### 🌐 Frontend Cliente (React)
- **Landing Page** con presentación de servicios
- **Sistema de Agendamiento** online con formularios intuitivos
- **Galería de Eventos** con imágenes destacadas
- **Sistema de Reseñas** para testimonios de clientes
- **Chat en Vivo** para consultas inmediatas
- **Diseño Responsive** optimizado para móviles
- **Colores de Marca** - Negro y amarillo dorado

### 🛠️ Panel Administrativo (React)
- **Dashboard Principal** con métricas y estadísticas
- **Gestión de Agendamientos** con calendario visual
- **Registro de Eventos** con información financiera (ingresos/egresos)
- **Estado de Resultados Mensual** para análisis de utilidades
- **Gestión de Galería** para subir y administrar fotos
- **Sistema de Aprobación de Reseñas**
- **Gestión de Inventario** con alertas de stock bajo
- **Reportes Avanzados** (clientes frecuentes, servicios populares)
- **Chat de Soporte** para atender consultas
- **Sistema de Notificaciones** masivas

### 🔧 Backend (Python + FastAPI + Firebase)
- **API RESTful** completa con documentación automática
- **Base de Datos** Firebase Firestore
- **Autenticación** Firebase Authentication
- **Almacenamiento** Firebase Storage para imágenes
- **Notificaciones WhatsApp** via Twilio
- **WebSockets** para chat en tiempo real
- **Generación de Reportes** en Excel/PDF

### 📱 App Móvil (React Native + Expo)
- **Dashboard Móvil** para administradores
- **Gestión de Agendamientos** desde cualquier lugar
- **Notificaciones Push** para nuevos agendamientos
- **Cámara Integrada** para subir fotos de eventos
- **Acceso Offline** a información básica

## 🏗️ Arquitectura del Sistema

```
Pablo's Pizza/
├── 🖥️ frontend/          # React App - Cliente público
│   ├── src/
│   │   ├── components/    # Componentes reutilizables
│   │   ├── pages/         # Páginas públicas y admin
│   │   ├── contexts/      # Context API (Auth, Chat)
│   │   ├── services/      # APIs y servicios
│   │   └── utils/         # Utilidades y tema
│   └── public/
├── ⚡ backend/           # Python FastAPI + Firebase
│   ├── routers/          # Endpoints organizados por módulo
│   ├── models/           # Schemas de Pydantic
│   ├── services/         # Lógica de negocio
│   └── utils/            # Utilidades generales
├── 📱 mobile/            # React Native App - Admin móvil
│   ├── src/
│   │   ├── screens/      # Pantallas de la app
│   │   ├── components/   # Componentes móviles
│   │   └── services/     # APIs móviles
│   └── assets/
└── 📚 docs/              # Documentación completa
```

## 🚀 Instalación y Configuración

### 📋 Prerequisitos
- Python 3.9+
- Node.js 18+
- Firebase Account
- Twilio Account (para WhatsApp)

### 🔥 Configuración de Firebase

1. **Crear Proyecto Firebase**
   ```bash
   # Instalar Firebase CLI
   npm install -g firebase-tools
   
   # Login y configurar proyecto
   firebase login
   firebase init
   ```

2. **Configurar Servicios**
   - ✅ Authentication (Email/Password)
   - ✅ Firestore Database
   - ✅ Cloud Storage
   - ✅ Hosting
   - ✅ Cloud Functions

### ⚙️ Backend Setup

1. **Instalar Dependencias**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Configurar Variables de Entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

3. **Configurar Firebase Service Account**
   - Descargar `firebase-service-account.json` desde Firebase Console
   - Colocar en directorio `backend/`

4. **Ejecutar Backend**
   ```bash
   python main.py
   # API disponible en http://localhost:8000
   ```

### 🌐 Frontend Setup

1. **Instalar Dependencias**
   ```bash
   cd frontend
   npm install
   ```

2. **Configurar Variables de Entorno**
   ```bash
   cp .env.example .env.local
   # Configurar Firebase y API URL
   ```

3. **Ejecutar Frontend**
   ```bash
   npm run dev
   # App disponible en http://localhost:3000
   ```

### 📱 Mobile App Setup

1. **Instalar Expo CLI**
   ```bash
   npm install -g @expo/cli
   ```

2. **Configurar App Móvil**
   ```bash
   cd mobile
   npm install
   expo start
   ```

## 📧 Configuración de Notificaciones WhatsApp

### 🔧 Twilio Setup

1. **Crear Cuenta Twilio**
   - Registrarse en [twilio.com](https://twilio.com)
   - Obtener Account SID y Auth Token

2. **Configurar WhatsApp Sandbox**
   ```bash
   # En Twilio Console:
   # 1. Ir a Messaging > Try it out > Send a WhatsApp message
   # 2. Seguir instrucciones para configurar sandbox
   # 3. Añadir números de prueba
   ```

3. **Variables de Entorno**
   ```env
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ADMIN_WHATSAPP_NUMBER=+1234567890
   ```

## 🎨 Personalización de Marca

### 🎨 Colores Principales
- **Primario:** `#FFD700` (Amarillo dorado)
- **Secundario:** `#000000` (Negro)
- **Fondo:** `#FAFAFA` (Gris claro)

### 🖼️ Logo y Branding
- Logo ubicado en `frontend/src/assets/logo.png`
- Favicon en `frontend/public/favicon.ico`
- Colores definidos en `frontend/src/utils/theme.js`

## 📊 Funcionalidades Clave

### 🎯 Sistema de Agendamientos
- **Formulario Público** para solicitar eventos
- **Validación Automática** de fechas y horarios
- **Cálculo de Precios** basado en participantes
- **Notificaciones Automáticas** via WhatsApp
- **Estados de Agendamiento:** Pendiente → Confirmado → Completado

### 💰 Gestión Financiera
- **Registro de Ingresos** por evento
- **Control de Gastos** detallado por categorías
- **Cálculo Automático** de utilidades
- **Reportes Mensuales** con gráficos
- **Exportación a Excel** para contabilidad

### 📸 Galería de Eventos
- **Subida Automática** con redimensionado
- **Organización por Evento** 
- **Imágenes Destacadas** para página principal
- **Optimización Web** automática

### ⭐ Sistema de Reseñas
- **Solicitud Automática** post-evento via WhatsApp
- **Moderación Manual** antes de publicar
- **Estadísticas de Satisfacción**
- **Testimonios Destacados** en homepage

### 💬 Chat en Vivo
- **WebSocket Real-time** para respuestas instantáneas
- **Múltiples Conversaciones** simultáneas
- **Historial Persistente** de conversaciones
- **Notificaciones** para nuevos mensajes

### 📦 Control de Inventario
- **Gestión de Ingredientes** y utensilios
- **Alertas de Stock Bajo** automáticas
- **Categorización** por tipo de producto
- **Historial de Movimientos**

## 🚀 Deployment

### 🌐 Frontend (Firebase Hosting)
```bash
cd frontend
npm run build
firebase deploy --only hosting
```

### ⚡ Backend (Firebase Functions)
```bash
cd backend
firebase deploy --only functions
```

### 📱 Mobile App
```bash
cd mobile
eas build --platform all
eas submit --platform all
```

## 📈 Métricas y Análisis

### 📊 Dashboard Administrativo
- **Eventos del Día/Mes/Año**
- **Ingresos y Utilidades** en tiempo real
- **Clientes Frecuentes** y retención
- **Servicios Más Solicitados**
- **Ocupación por Mes** y temporadas altas

### 📱 Reportes Avanzados
- **Estado de Resultados Mensual**
- **Análisis de Clientes** (nuevos vs. recurrentes)
- **Rendimiento por Tipo de Evento**
- **Eficiencia Operativa** (tiempo promedio por evento)

## 🔒 Seguridad y Permisos

### 🛡️ Autenticación
- **Firebase Authentication** para administradores
- **Roles y Permisos** granulares
- **Tokens JWT** para APIs
- **Logout Automático** por inactividad

### 🔐 Firestore Rules
- **Lectura Pública** para galería y reseñas aprobadas
- **Escritura Restringida** solo para administradores
- **Validación de Datos** en el servidor

## 🆘 Troubleshooting

### ❌ Problemas Comunes

**Error de Conexión Firebase**
```bash
# Verificar credenciales
firebase login --reauth
# Verificar proyecto activo
firebase use --add
```

**WhatsApp no funciona**
```bash
# Verificar sandbox Twilio
# Confirmar números en whitelist
# Revisar logs en Twilio Console
```

**Chat desconectado**
```bash
# Verificar WebSocket URL
# Comprobar CORS settings
# Reiniciar servidor backend
```

## 📞 Soporte y Contacto

- **Documentación:** Ver carpeta `/docs` para guías detalladas
- **Issues:** Reportar problemas en GitHub Issues
- **Email:** soporte@pablospizza.com

---

## 🎉 ¡Listo para Empezar!

Tu sistema completo de Pablo's Pizza está configurado y listo para usar. El proyecto incluye:

✅ **Frontend Responsivo** con sistema de agendamientos  
✅ **Panel Admin Completo** con métricas financieras  
✅ **Backend Robusto** con APIs documentadas  
✅ **Notificaciones WhatsApp** automáticas  
✅ **Chat en Vivo** para soporte  
✅ **App Móvil** para administradores  
✅ **Sistema de Inventario** con alertas  
✅ **Reportes Financieros** exportables  

¡Comienza a crear experiencias gastronómicas inolvidables! 🍕✨