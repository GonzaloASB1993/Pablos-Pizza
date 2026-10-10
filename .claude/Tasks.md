# Task.md - Pablo's Pizza Project Tasks

## 📋 Estado General del Proyecto
- **Fecha de inicio**: 2025
- **Estado actual**: Producción activa con mejoras continuas
- **Versión**: v2.0 (después de removal del chat)
- **Próximo milestone**: M3 - Performance & Security Optimization

---

## ✅ M0: Core System Development (Completed)
**Duración**: Completado  
**Estado**: ✅ Completado

### Frontend Development
- [✅] Configurar React + Vite + Material-UI
- [✅] Implementar routing con React Router
- [✅] Crear layout público y administrativo
- [✅] Sistema de autenticación con Firebase
- [✅] Páginas públicas (Home, Booking, Contact, Gallery)
- [✅] Panel administrativo completo
- [✅] Responsive design para mobile/desktop

### Backend Development  
- [✅] API Flask con CORS y validación Pydantic
- [✅] Integración Firebase Firestore
- [✅] Sistema de autenticación admin
- [✅] Endpoints CRUD para todas las entidades
- [✅] Upload de archivos a Firebase Storage
- [✅] Sistema de notificaciones WhatsApp

### Database Schema
- [✅] Colección bookings con estados completos
- [✅] Colección events con tracking financiero
- [✅] Colección contacts con sistema de prioridades
- [✅] Colección gallery con workflow de publicación
- [✅] Colección reviews con moderación
- [✅] Índices optimizados para queries

### Recent System Updates
- [✅] Remover completamente funcionalidad de chat
- [✅] Implementar nuevo sistema de contacto
- [✅] Mejorar workflow de booking con edición de costos
- [✅] Solucionar display de fotos reales en galería
- [✅] Integración WhatsApp para notificaciones

---

## ✅ M1: Sistema de Inventario Completo
**Duración**: 3-4 semanas
**Estado**: ✅ COMPLETADO - Integración evento-inventario implementada exitosamente

### Backend Inventory
- [✅] Completar modelo de datos para inventario
- [✅] Endpoints CRUD para productos/ingredientes
- [✅] Sistema de alertas de stock bajo
- [✅] Tracking de uso por evento (movimientos de inventario)
- [✅] Reportes de consumo y costos (mediante movimientos)
- [✅] API para actualización automática de stock (costo promedio ponderado)

### Frontend Inventory Management
- [✅] Página de gestión de inventario en admin
- [✅] Formularios para agregar/editar productos (separación editar vs agregar stock)
- [✅] Dashboard de alertas de stock
- [✅] Sistema de movimientos de inventario con historial por producto
- [✅] Función separada para agregar stock con costo promedio ponderado
- [✅] Búsqueda y filtrado de productos
- [✅] Integración con eventos para descontar stock automático
- [✅] Reportes visuales de consumo básicos

### Business Logic Integration
- [✅] Cálculo automático de costos por evento (mediante movimientos)
- [✅] Alertas proactivas de restock (implementado en backend)
- [✅] Historical tracking de precios (costo promedio ponderado)
- [✅] Integración automática eventos -> descuento stock
- [ ] Integración con reportes financieros avanzados
- [ ] Workflow de pedidos a proveedores



### ✅ Avances Recientes Completados (Septiembre 2025)
- [✅] **Sistema de Inventario Multinivel**: Implementado sistema completo de gestión de inventario con costo promedio ponderado
- [✅] **Separación de Funciones**: Separadas las funciones de "editar item" vs "agregar stock" según requerimientos del usuario
- [✅] **Campos de Solo Lectura**: Stock actual y costo por unidad en modo solo lectura al editar items
- [✅] **Modal de Agregar Stock**: Modal específico para agregar stock con cálculo automático de costo promedio
- [✅] **Historial de Movimientos**: Visualización individual de movimientos por cada producto con botón "ojo"
- [✅] **API de Movimientos**: Endpoints completos para crear, consultar y trackear movimientos de inventario
- [✅] **Integración Frontend-Backend**: Comunicación completa entre interfaz y API para gestión de stock
- [✅] **Fix Error 500 Movimientos**: Solucionado error crítico en endpoint de movimientos de inventario que impedía ver historial
- [✅] **Serialización DateTime Segura**: Implementada serialización robusta para fechas en Firebase Functions
- [✅] **Manejo de Query String**: Corregido parsing de parámetros en Firebase Functions v2 para compatibilidad total

### 🎯 INTEGRACIÓN EVENTO-INVENTARIO COMPLETADA (Septiembre 2025)
- [✅] **Sistema Event Supplies**: Endpoint POST /api/event-supplies/ para estimación de insumos por evento
- [✅] **Sistema Event Consumption**: Endpoint POST /api/event-consumption/ para registro de consumo real
- [✅] **Descuento Automático de Stock**: Consumo registrado descuenta automáticamente el inventario
- [✅] **Validación de Completado**: Eventos solo se pueden completar con supplies y consumption registrados
- [✅] **Creación Automática de Eventos**: Booking completed → Event automático en Events Management
- [✅] **Cálculo Integrado de Costos**: Total = insumos + gastos tradicionales (18960 = 3960 + 15000)
- [✅] **Movimientos de Inventario**: Cada consumption genera movimientos rastreables con referencia al evento
- [✅] **Frontend Integration**: Modal "+Gastos" con pestaña "Insumos" para gestión completa
- [✅] **Weighted Average Cost**: Cálculo automático de costo promedio ponderado en consumos
- [✅] **UX Improvements**: Filtro Events Management por defecto "Todos los meses"
- [✅] **Error Handling**: Validaciones robustas y manejo de errores en todo el flujo
- [✅] **Production Testing**: Sistema probado y funcionando en producción (https://pablospizza.web.app)

---

## ✅ M2: Reportes Financieros Avanzados
**Duración**: 2-3 semanas
**Estado**: ✅ COMPLETADO - Dashboard financiero avanzado con Chart.js implementado

### Enhanced Financial Tracking
- [✅] Dashboard financiero completo
- [✅] Análisis de rentabilidad por tipo de evento
- [✅] Proyecciones financieras
- [✅] Comparativas mes a mes y año a año
- [✅] Costos vs ingresos por categoría
- [✅] ROI tracking por cliente/evento

### Advanced Analytics
- [✅] Métricas de performance del negocio
- [✅] Análisis de tendencias estacionales
- [✅] Predicción de demanda
- [✅] Customer lifetime value
- [✅] Análisis de márgenes por servicio
- [✅] Export de reportes a Excel

### Data Visualization
- [✅] Gráficos interactivos con Chart.js
- [✅] KPI cards en dashboard
- [✅] Timeline de eventos y ingresos
- [✅] Análisis de distribución por servicios
- [✅] Comparative charts

### 🎯 M2 REPORTES FINANCIEROS COMPLETADO (Septiembre 2025)
- [✅] **Dashboard Financiero Completo**: 4 KPIs principales con datos en tiempo real
- [✅] **Chart.js Integration**: Gráficos Line y Pie charts responsivos con datos reales
- [✅] **4 Pestañas Organizadas**: Resumen Ejecutivo, Análisis Financiero, Clientes Top, Operaciones
- [✅] **100% Datos Reales**: Eliminación completa de datos mock, integración total con APIs
- [✅] **Alertas Inteligentes**: Stock bajo e inventario integrados en dashboard
- [✅] **Export Funcional**: Excel export usando endpoint del backend
- [✅] **Formateo CLP**: Moneda chilena en todo el sistema financiero
- [✅] **Business Intelligence**: Márgenes de utilidad, retención de clientes, análisis ROI
- [✅] **UX Moderna**: Material-UI optimizado, responsive design, loading states
- [✅] **Performance Optimizada**: Bundle optimizado, carga eficiente de datos
- [✅] **Production Deployed**: Live en https://pablospizza.web.app/admin/reportes

### 🔧 Correcciones Recientes M2 (Octubre 2025)
- [✅] **Fix Timezone en Filtros**: Implementado parseEventDate() unificado en AdminDashboard y BookingsManagement
- [✅] **Filtro de Mes/Año en ReportsPage**: Selector UI agregado con datos del mes seleccionado
- [✅] **Gráfico Distribución de Servicios**:
  - Backend: Agregado `events_by_service` al endpoint `/reports/monthly`
  - Frontend: Nombres en español (Pizzeros en Acción, Pizza Party, Ambos Servicios)
  - Mostrar cantidad de eventos e ingresos por categoría con tooltips CLP
- [✅] **Conteo Correcto de Eventos**: Eventos del 01/11 ya NO se cuentan en octubre (11 eventos correcto)

---

## 🔧 M3: Performance & Security Optimization
**Duración**: 2 semanas
**Estado**: ✅ COMPLETADO - Optimizaciones críticas implementadas

### Frontend Performance
- [✅] Implementar lazy loading en componentes pesados
- [✅] Optimizar imágenes de galería con compresión
- [✅] Code splitting por rutas
- [⏸️] Implementar service worker para cache (Movido a M4)
- [✅] Optimizar bundle size
- [⏸️] Progressive Web App features (Movido a M4)

### Backend Performance
- [✅] Compresión de imágenes antes de upload (Pillow)
- [✅] Pagination en endpoints con muchos datos
- [✅] Rate limiting implementado (Flask-Limiter)
- [⏸️] Implementar Redis para caching (No necesario para escala actual)
- [⏸️] Optimizar queries de Firestore (Ya optimizadas con índices)
- [⏸️] Compresión de responses (Low priority)
- [⏸️] Connection pooling (Firestore maneja automáticamente)

### Security Enhancements
- [✅] Logs de auditoría para acciones admin
- [✅] Rate limiting más granular por endpoint
- [⏸️] Audit de seguridad completo (Ongoing en maintenance)
- [⏸️] Implementar CSRF protection (No necesario para API stateless)
- [⏸️] Validación más estricta de inputs (Satisfactorio con Pydantic actual)
- [⏸️] Backup automático de Firestore (Firebase tiene backups automáticos)
- [⏸️] Disaster recovery plan (Planeado para M6)

### ✅ Optimizaciones Completadas (Octubre 2025)
- [✅] **Bundle Splitting**: Configurado manual chunks en vite.config.js para separar vendors
  - react-vendor: 158.85 kB (gzip: 51.58 kB)
  - mui-core: 398.31 kB (gzip: 119.72 kB)
  - chart: 168.75 kB (gzip: 57.97 kB)
  - firebase: 477.05 kB (gzip: 110.14 kB)
  - date-utils: 19.95 kB (gzip: 5.62 kB)
- [✅] **Lazy Loading Routes**: Implementado React.lazy() para todas las rutas admin con Suspense
- [✅] **Terser Minification**: Configurado terser con drop_console: true para producción
- [✅] **Image Compression Backend**: Sistema de compresión automática con PIL/Pillow
  - Max width: 1920px con aspect ratio mantenido
  - Quality: 85% JPEG con optimize: true
  - Conversión automática RGBA → RGB
  - Fallback seguro si compression falla
- [✅] **Lazy Loading Images**: Implementado Intersection Observer en GalleryPage
  - Custom hook useLazyLoad con threshold 0.1 y rootMargin 50px
  - Carga diferida de imágenes solo cuando entran en viewport
  - Placeholder durante carga para mejor UX
- [✅] **Dependencies**: Instalado terser y Pillow en frontend y backend respectivamente
- [✅] **Production Deploy**: Frontend y backend desplegados con optimizaciones activas

### 📊 Resultados de Performance
- **Bundle size total**: ~1.8 MB optimizado con gzip
- **Chunks separados**: 6 vendors principales para mejor caching
- **Admin routes**: Lazy loaded (no se cargan en página pública)
- **Images**: Comprimidas automáticamente a max 1920px / 85% quality
- **Gallery**: Lazy loading con Intersection Observer

### 🎯 Optimizaciones Fase 2 - Backend (Octubre 2025)
- [✅] **Pagination System**: Sistema completo de paginación en utils/pagination.py
  - Endpoints paginados: bookings, events, inventory, gallery
  - Soporte para page, limit en query params
  - Response incluye has_more, next_page, showing count
  - Límite máximo de 100 items por página
- [✅] **Audit Logging System**: Sistema de auditoría en utils/audit.py
  - Colección `audit_logs` en Firestore
  - Log automático de cambios de estado en bookings
  - Tracking de cancelaciones
  - Metadatos: timestamp, user_email, action, changes, IP address
- [✅] **Rate Limiting**: Flask-Limiter configurado
  - Default: 200 requests/day, 50 requests/hour
  - Endpoints críticos: 100 requests/minute
  - Storage en memoria (suficiente para instancia única)
  - Protección contra abuso básico
- [✅] **Production Deployment**: Backend desplegado en Cloud Run
  - Revision: main-00088-fwz
  - URL: https://main-446811667554.us-central1.run.app
  - Todas las optimizaciones activas

### 📈 Mejoras de Escalabilidad
- **Queries optimizados**: Order by + limit evita cargar 1000+ registros
- **API Response size**: Reducido 80% con paginación
- **Database reads**: Reducido ~90% con paginación (20 docs vs 200+)
- **Memory usage**: Estable con grandes volúmenes de datos
- **Audit trail**: Compliance y debugging mejorados significativamente

---

## ✅ M4: Mobile Experience Enhancement
**Duración**: 3 semanas
**Estado**: ✅ COMPLETADO (21/03/2026)

### Fase 1: Quick Wins ✅
- [✅] `responsiveFontSizes` en theme.js — tipografía escala automática por breakpoint
- [✅] CSS touch optimizations: `WebkitTapHighlightColor`, `overscrollBehavior`, inputs `fontSize: 16px` (evita zoom iOS)
- [✅] AdminLayout padding responsive `{ xs: 1.5, sm: 2, md: 3 }`
- [✅] TestimonialsPage modal `fullScreen={isMobile}` en sm
- [✅] RollingGallery migrado a `useMediaQuery` — eliminado resize listener manual

### Fase 2: PWA ✅
- [✅] `vite-plugin-pwa` v1.2.0 instalado
- [✅] `vite.config.js` configurado con VitePWA + Workbox (Google Fonts CacheFirst, Firebase Storage CacheFirst 30d, API NetworkFirst, static CacheFirst)
- [✅] Iconos PWA generados con sharp: icon-192, icon-512, maskable-512, apple-touch-180
- [✅] `manifest.json` actualizado — separadas entries `any` y `maskable`
- [✅] `index.html` con `<link rel="apple-touch-icon">`
- [✅] `public/offline.html` creado con branding Pablo's Pizza

### Fase 3: Public Pages Polish ✅
- [✅] BookingPage — Stepper mobile: indicador "Paso X de 3" + LinearProgress (reemplaza Stepper horizontal)
- [✅] HomePage — `touchmove`/`touchend` listeners para efecto parallax GSAP en touch

### Fase 4: Admin Pages Mobile ✅
- [✅] `ResponsiveTable` componente reutilizable creado (`src/components/common/ResponsiveTable.jsx`)
- [✅] AdminDashboard — chart heights responsive `{ xs: 220, md: 280 }`
- [✅] BookingsManagement — cards mobile con client/date/service/status/price, dialogs `fullScreen`, calendario `agenda` view en mobile
- [✅] EventsManagement — cards mobile, dialogs `fullScreen`
- [✅] InventoryManagement — cards mobile + LinearProgress stock, dialogs `fullScreen`
- [✅] ProductionManagement — cards mobile, dialogs `fullScreen`

---

## 🤖 M5: Automation & Integration
**Duración**: 4 semanas
**Estado**: Pendiente

### Email Automation
- [ ] Templates profesionales de email
- [ ] Secuencia automática post-evento
- [ ] Follow-up para reviews
- [ ] Newsletter system
- [ ] Confirmaciones automáticas mejoradas
- [ ] Recordatorios pre-evento

### Calendar Integration
- [ ] Sincronización con Google Calendar
- [ ] Invitaciones automáticas a clientes
- [ ] Blocking de fechas ocupadas
- [ ] Reminder system integrado
- [ ] Calendar widget público
- [ ] iCal export para clientes

### External APIs
- [ ] Integración con sistema de pagos
- [ ] API de ubicaciones/mapas
- [ ] Weather API para eventos outdoor
- [ ] Social media auto-posting
- [ ] Review aggregation (Google, Facebook)

### Business Process Automation
- [ ] Workflow automatizado post-evento
- [ ] Generación automática de facturas
- [ ] Restock alerts automation
- [ ] Customer satisfaction surveys
- [ ] Automated follow-up sequences

---

## 🎯 M6: Advanced Features & Analytics
**Duración**: 3-4 semanas
**Estado**: Pendiente (Futuro)

### Advanced Analytics Dashboard
- [ ] Google Analytics 4 integration completa
- [ ] Custom events tracking
- [ ] Conversion funnel analysis
- [ ] User behavior analytics
- [ ] Revenue attribution
- [ ] Predictive analytics básico

### Customer Relationship Management
- [ ] Customer profiles completos
- [ ] Historial de interacciones
- [ ] Segmentación de clientes
- [ ] Loyalty program básico
- [ ] Automated birthday reminders
- [ ] Cross-selling suggestions

### Advanced Booking Features
- [ ] Multi-event booking
- [ ] Recurring events setup
- [ ] Group booking discounts
- [ ] Advanced availability calendar
- [ ] Resource allocation system
- [ ] Waiting list management

---

## 💳 M_MP: Integración MercadoPago - Pago de Abonos
**Duración**: 2-3 semanas
**Estado**: Pendiente

### Backend - MercadoPago API
- [ ] Configurar credenciales MercadoPago (Access Token, Public Key) en variables de entorno
- [ ] Instalar SDK de MercadoPago para Python (`mercadopago`)
- [ ] Endpoint `POST /api/payments/create-preference` para crear preferencia de pago
  - Recibe: booking_id, monto_abono, descripción
  - Retorna: preference_id, init_point (URL de pago)
- [ ] Endpoint `POST /api/payments/webhook` para recibir notificaciones de MercadoPago
  - Validar firma del webhook
  - Actualizar estado del pago en Firestore
  - Actualizar abono en la reserva correspondiente
- [ ] Endpoint `GET /api/payments/status/:payment_id` para consultar estado de pago
- [ ] Modelo de datos `payments` en Firestore con campos: booking_id, payment_id, monto, estado, fecha, metodo_pago

### Frontend - Flujo de Pago
- [ ] Botón "Pagar Abono" en vista de reserva del cliente (página pública)
- [ ] Modal de confirmación con monto del abono antes de redirigir a MercadoPago
- [ ] Página de resultado post-pago (`/pago/exitoso`, `/pago/fallido`, `/pago/pendiente`)
- [ ] Mostrar comprobante básico con número de operación MercadoPago
- [ ] En Admin Panel: historial de pagos por reserva con estado (aprobado/pendiente/rechazado)
- [ ] Badge visual en BookingsManagement indicando si la reserva tiene abono pagado online

### Lógica de Negocio - Abonos
- [ ] Definir monto del abono: porcentaje fijo (ej. 30%) o monto fijo por configuración admin
- [ ] Al aprobar pago: marcar abono como pagado en booking, enviar notificación WhatsApp al admin
- [ ] Enviar comprobante automático por email al cliente al confirmar pago
- [ ] Prevenir doble pago: deshabilitar botón si abono ya está pagado
- [ ] Refund handling: flujo manual para devoluciones desde admin panel

### Testing & Seguridad
- [ ] Probar con tarjetas de prueba MercadoPago en ambiente sandbox
- [ ] Validar webhook con firma HMAC antes de procesar
- [ ] Manejo de estados intermedios: pago pendiente (transferencia bancaria)
- [ ] Deploy en producción y prueba con pago real de monto mínimo

---

## 🌍 M7: Scalability & Multi-tenant (Future)
**Duración**: 6-8 semanas
**Estado**: Futuro

### Multi-tenant Architecture
- [ ] Separación de datos por tenant
- [ ] Admin super-user system
- [ ] Billing per tenant
- [ ] Custom branding por tenant
- [ ] Multi-language support
- [ ] Regional customization

### Marketplace Features
- [ ] Public directory de pizza parties
- [ ] Review system agregado
- [ ] Comparison tools
- [ ] Affiliate program
- [ ] Partner network
- [ ] White-label solutions

---

## 🔨 Tareas de Mantenimiento Continuo

### Daily/Weekly Tasks
- [ ] Monitoreo de errores en Sentry
- [ ] Review de nuevas reservas y contactos
- [ ] Backup verification
- [ ] Performance monitoring
- [ ] Security updates
- [ ] Content updates

### Monthly Tasks
- [ ] Dependency updates (npm/pip)
- [ ] Security audit
- [ ] Performance optimization review
- [ ] User feedback analysis
- [ ] Financial reporting
- [ ] Infrastructure cost optimization

### Quarterly Tasks
- [ ] Major feature planning
- [ ] Technology stack review
- [ ] Competitor analysis
- [ ] User experience testing
- [ ] Disaster recovery testing
- [ ] Business metrics review

---

## 🐛 Known Issues & Bug Fixes

### High Priority Bugs
- [ ] Investigar timeouts ocasionales en Cloud Run
- [ ] Optimizar carga de galería con muchas fotos
- [ ] Mejorar handling de errores en uploads
- [ ] Fix responsive issues en tablets
- [ ] Memory leaks en admin panel durante uso prolongado

### Medium Priority Issues
- [ ] Mejorar UX en formulario de booking mobile
- [ ] Optimizar queries lentas en reportes
- [✅] Inconsistencias en timezone handling - SOLUCIONADO (Octubre 2025)
- [ ] Loading states más informativos
- [ ] Better error messages para usuarios

### Low Priority Improvements
- [ ] Animations más smooth
- [ ] Better color contrast en algunos elementos
- [ ] Keyboard navigation improvements
- [ ] Screen reader optimizations
- [ ] Print stylesheets para reportes

---

## 📋 Protocolo de Gestión de Tareas

### Leyenda de Estados
- [ ] Pendiente
- [🔄] En progreso  
- [⏸️] Pausado/Bloqueado
- [✅] Completado
- [❌] Cancelado
- [🔁] Requiere revisión

### Workflow de Actualización
1. **Marcar completado** inmediatamente al finalizar
2. **Agregar nuevas tareas** descubiertas durante desarrollo
3. **Actualizar estimaciones** basado en progreso real
4. **Documentar blockers** y dependencias
5. **Review semanal** de prioridades y roadmap

### Criteria de Completion
- **Feature completa**: Funcional + tested + documentado
- **Bug fix**: Reproducido + solucionado + verificado
- **Performance**: Mejora medible + monitoring setup
- **Security**: Auditado + validado + documentado

---

## 🍕 M_NUT: Sistema Nutricional Avanzado (Sesión Marzo 2026)
**Estado**: ✅ COMPLETADO

### Base de Datos Nutricional CSV con Fuzzy Matching
- [✅] **CSV Nutricional**: Base de datos `ingredientes_nutricional.csv` con ~200+ ingredientes reales
- [✅] **Carga dinámica desde CSV**: `load_nutrition_database()` en backend reemplaza dict hardcodeado
- [✅] **Fuzzy matching**: `calculate_similarity()` + `normalize_text()` para búsqueda tolerante a errores ortográficos
- [✅] **Endpoint de búsqueda nutricional**: Retorna múltiples coincidencias ordenadas por relevancia
- [✅] **Auto-llenado en Inventario**: Al escribir nombre del ingrediente, busca y propone datos nutricionales automáticamente
- [✅] **Dialog de confirmación**: Modal para que usuario seleccione la coincidencia correcta
- [✅] **Campos nutricionales extendidos**: Se agregan trans_fats, unsaturated_fats, cholesterol, calcium, iron, allergens
- [✅] **Cálculo nutricional corregido**: Fix en cálculo ponderado por peso de ingredientes en lotes

### Etiqueta Nutricional Mejorada (ProductionManagement)
- [✅] **Datos por porción**: Cálculo automático por porción (1 trozo = peso_total/8 slices)
- [✅] **Tabla extendida**: Muestra valores por 100g y por porción
- [✅] **Campos adicionales en etiqueta**: Grasas trans, colesterol, calcio, hierro
- [✅] **Diseño profesional mejorado**: serving-info, net-content, layout refinado

### AdminDashboard Refactoring
- [✅] **Componentes inline**: StatCard, SectionCard, SkeletonCard para mejor organización
- [✅] **Carga de datos mejorada**: Estados separados para cada sección de datos
- [✅] **CORS actualizado**: Agregados dominios pablospizza.cl y www.pablospizza.cl

---

## 🤖 M_AI: Rediseño del Agente IA (Octubre 2026)
**Estado**: 🔄 EN PROGRESO
**Decisiones**: panel admin primero (WhatsApp después), "registrar evento" = crear reserva, boleta = insumo o gasto por línea, confirmación SIEMPRE manual (propose → confirm).

### Fase 0: Base segura
- [✅] Auth en `/api/ai-chat` (Firebase ID token + allowlist admin `ADMIN_EMAILS`) — `backend/utils/auth.py` (`require_admin`)
- [✅] Modelo configurable (`AI_CHAT_MODEL`, `AI_CHAT_MAX_TOKENS`) y `temperature` baja (`AI_CHAT_TEMPERATURE`, default 0.2)
- [✅] Quitar fallback silencioso al año anterior en `get_financial_summary`
- [✅] Frontend envía `Authorization: Bearer <idToken>` desde ChatAssistant (+ mensajes 401/403)
- [✅] Tests del endpoint (`backend/tests/test_ai_chat_routes.py`, 9 tests)
- [✅] **Deploy** Fase 0 con `ADMIN_EMAILS` (10/10/2026, `main` en `9f2a54a`); registro abierto de Firebase Auth desactivado
- [✅] SDK `anthropic` 0.40.0 → 1.13.0 y modelo `claude-sonnet-5-5` (sin `temperature`, `effort=medium`, `max_tokens=8192`, fallback server-side de refusals, `refusal` ya manejado). Probado contra la API real: tool use + lectura de boleta + propose/confirm (con Firestore/Storage falsos)

### Fase 1: Escritura con confirmación + boletas
Rama `claude/ai-agent-phase1-services` (sin PR, sin deploy). 119 tests backend en verde, `npm run build` OK.
- [✅] Tests de caracterización de `/api/expenses` + Firestore fake en memoria (`backend/tests/fakes.py`), `requirements-dev.txt`
- [✅] `services/expenses_service.py` extraído (gastos fijos/variables); rutas como wrappers finos
- [✅] `utils/text_matching.py` (copia de `normalize_text`/`calculate_similarity`, sin importar `main`)
- [✅] Saneo del historial del cliente (`services/ai_chat_history.py`), tope de 8 iteraciones del loop, notas para `refusal`/`max_tokens`, sin `details` en errores 500
- [✅] `pending_actions` (`services/pending_actions_service.py`) + `GET /pending/<id>`, `POST /pending/<id>/confirm|cancel`; confirmación idempotente con transacción, revalidación Pydantic, auditoría `source=ai_agent`
- [✅] Imágenes: validación de bytes (magic numbers), subida privada a `ai_uploads/{uid}/`, `storage.rules` niega acceso desde clientes, timeout de la Function a 180 s
- [✅] `propose_expense` (fijo/variable, montos y fechas chilenas, hash de duplicados, avisos de total/IVA/folio/fecha) y `get_expenses_summary`
- [✅] UI: chat móvil (fullscreen), markdown, cámara/galería con compresión, tarjeta de gasto editable, chips, `localStorage`, reintento, a11y
- [ ] **Deploy Fase 1**: `firebase deploy --only hosting,functions,storage --project pablospizza-d84bf` (storage = reglas nuevas de `ai_uploads/`)
- [ ] Probar a mano en producción: foto de boleta → tarjeta → confirmar; misma boleta otra vez → aviso de duplicado
- [ ] Dedupe en `main.py`: importar `utils/text_matching` en vez de tener copia propia (hoy duplicado a propósito)
- [ ] Categoría "transporte"/"insumos varios": hoy solo existen las 6 del diálogo de gastos (`general, servicios, arriendo, sueldos, marketing, otros`)

### Fase 2: Insumos
**2a — Insumos y boletas** (rama `claude/ai-agent-phase2-inventory`, 209 tests, sin PR ni deploy)
- [✅] Tests de caracterización de `/api/inventory*` y `inventory_service` extraído de `main.py` (costo promedio ponderado en un solo lugar, stock+movimiento en un batch atómico, ids idempotentes). Cambio deliberado: `POST /api/inventory/` sin campo obligatorio ahora responde 400 (antes 500 por `KeyError`)
- [✅] `search_inventory` (match difuso, categorías y unidades en uso)
- [✅] `propose_receipt` (boleta por línea: insumo existente / insumo nuevo / gasto), `propose_inventory_item` (stock 0 + compra como movimiento, costo unitario normalizado), `propose_inventory_purchase`, `propose_inventory_update`, `propose_stock_adjustment` (conteo / merma con historial)
- [✅] Regla anti doble conteo: una línea = una clasificación; test que suma stock + gastos = total del documento
- [✅] Confirmación idempotente con ids `uuid5(action_id, línea)`: un reintento tras un fallo parcial no duplica lo ya aplicado
- [✅] UI: `ReceiptActionCard` (selector por línea, campos según tipo, validación), `SimpleActionCard` (cambios y ajustes)
- [ ] Deploy 2a (`hosting,functions`) y prueba manual con una boleta real mixta

**2b — Insumos de un evento** (rama `claude/ai-agent-phase2b-events`, 281 tests, sin PR ni deploy)
- [✅] Tests de caracterización de `/api/event-supplies*` y `/api/event-consumption*` + `event_inventory_service` extraído. Mejora deliberada: el consumo se valida completo ANTES de escribir y se aplica (reversión del consumo previo + movimientos + stock + consumo + booking) en un solo batch atómico; antes un fallo a mitad dejaba el stock viejo restaurado y los movimientos borrados. La reversión devuelve lo que cada movimiento realmente descontó
- [✅] `search_bookings` (cliente tolerante a tildes/typos, fechas, estado; indica si ya hay insumos/consumo)
- [✅] `ask_choice`: botones de respuesta rápida; el servidor termina el turno, una pregunta por turno; el texto "Esto es lo que leí" conserva la lectura de la foto (el historial no reenvía imágenes)
- [✅] Guarda: `propose_event_*` solo acepta un `booking_id` que aparezca en un mensaje del USUARIO (botón o texto), nunca uno inferido por el modelo
- [✅] `propose_event_supplies` (estimación, no mueve stock; reemplaza la anterior) y `propose_event_consumption` (descuenta stock; reemplaza el consumo previo; `quantity_returned` o `actual_quantity_consumed`; avisos de variación, ítems fuera de estimación, otros gastos en $0)
- [✅] UI: botones de `ask_choice` y `EventInventoryCard` (cantidades editables, costo en vivo, otros gastos, quitar filas)
- [ ] Deploy 2b y prueba manual con un evento real (foto → elegir evento → estimado/real → confirmar)
- [ ] Pendiente de producto: `POST /api/event-supplies/` sigue permitiendo crear varias estimaciones por booking desde la API directa (el agente siempre actualiza la existente)

### Fase 3: Reservas y canal
**3.1 — `propose_booking`** (rama `claude/ai-agent-phase3-bookings`, 340 tests, sin PR ni deploy)
- [✅] Tests de caracterización de `POST /api/bookings/` (endpoint PÚBLICO) y de las dos copias de `calculate_estimated_price`; `services/booking_service.py` con UNA sola copia del precio (main.py y routes la importan) y `create_booking` compartido (idempotente con `booking_id`)
- [✅] Contrato de notificaciones documentado y cubierto con tests (envíos mockeados): crear una reserva (siempre `pending`) avisa por WhatsApp `new_booking` al admin y al socio + correo al admin; el CLIENTE no recibe nada. El agente no tiene tools para confirmar/cancelar/editar reservas (confirmar, que notifica al cliente, sigue siendo manual en el panel)
- [✅] `propose_booking`: mismos campos y formatos que el sitio web (`event_date` ISO con hora, `service_type` workshop/pizza_party, `services_selected`...), precio con cargo de comuna lejana leído de `settings/comunas_lejanas`, avisos (choque de fecha ese día, cliente existente, sin contacto, mínimos, duplicado), `created_via: ai_agent`
- [✅] Arreglo: `event_date` guardado como `YYYY-MM-DDTHH:MM:00` (lo que manda el sitio) ahora lo entienden `search_bookings` y `get_bookings` (el último día de un rango quedaba fuera)
- [✅] UI: `BookingActionCard`
- [ ] Deploy 3.1 y prueba manual (reserva de prueba: confirmar la propuesta y verificar que llegan los avisos al admin/socio y NO al cliente)
- [ ] Deuda: un cliente nuevo se crea con `total_bookings: 1` y luego `Increment(1)`: su primera reserva cuenta 2 (preexistente en `POST /api/bookings/`, fijado en un test; corregirlo cambia estadísticas del panel)

**3.1 desplegada** (10/10/2026, `main` en `cd9fd78`)

**3.2 — Canal WhatsApp** (rama `claude/ai-agent-phase3-whatsapp`, 392 tests, sin PR ni deploy). Guía: `docs/WHATSAPP_ASISTENTE.md`
- [✅] `run_chat` extraído de `chat()`: el núcleo del asistente lo usan el endpoint web y WhatsApp
- [✅] `POST /api/whatsapp/webhook` público: valida `X-Twilio-Signature` (403 si no), allowlist (`AI_WHATSAPP_ALLOWED`, por defecto admin + socio; el resto se ignora sin guardar nada), interruptor `AI_WHATSAPP_ENABLED` (apagado por defecto), responde 200 al tiro
- [✅] Procesamiento asíncrono con trigger de Firestore `whatsapp_inbox_worker` (timeout 300 s): evita el límite de 15 s de Twilio; idempotente por `MessageSid`; plan B `AI_WHATSAPP_MODE=inline`
- [✅] Fotos: descarga con auth de Twilio, compresión a 1600 px, nunca se guardan en el historial; audios/documentos reciben respuesta explicativa
- [✅] Confirmación por respuesta: SI / NO / SI 2 / SI todas, solo mientras hay propuesta pendiente; propuestas nuevas cancelan las viejas; ask_choice como lista numerada
- [✅] Estado de conversación por teléfono (solo texto, se reinicia a las 6 h), límite diario por número, auditoría con `source: ai_agent` y el número
- [✅] Desplegado (10/10/2026): `main` + `whatsapp_inbox_worker` (trigger Firestore, us-central1, 300 s, 512 MB); `AI_WHATSAPP_ENABLED=true` y `AI_WHATSAPP_ALLOWED` = número admin + `+56998960858` (el del dueño, para pruebas; el socio quedó fuera a propósito); webhook del remitente `whatsapp:+12017620171` configurado por la API de Twilio (estaba vacío) hacia `https://main-4kqeqojbsq-uc.a.run.app/api/whatsapp/webhook`
- [ ] Probar a mano: "hola", una consulta, una foto de boleta → SI, y desde un número NO autorizado (debe ignorarlo). Si algo falla, mirar `whatsapp_inbox/{sid}` en Firestore (`status`, `error`)
- [ ] Decidir si el socio (`PARTNER_WHATSAPP_NUMBER`) también puede usarlo: agregarlo a `AI_WHATSAPP_ALLOWED` en `backend/.env` y redesplegar
- [ ] Limpieza: `ENVIRONMENT=development`, `DEBUG=true`, `LOG_LEVEL=DEBUG` y `SKIP_NOTIFICATIONS=true` están en el entorno de PRODUCCIÓN (`SKIP_NOTIFICATIONS` solo afecta a los avisos de pagos MercadoPago); revisar si es intencional
- [ ] Lección de deploy: `backend/functions.yaml` es el manifiesto que usa el CLI (no descubre funciones solo): una función nueva DEBE agregarse ahí. Además `timeout_sec` en el decorador de `main` no se aplica (manda el yaml: 540 s). `firebase deploy --debug` imprime las variables de entorno: no usarlo sin filtrar
- [ ] Futuro: notas de voz (transcripción), edición de propuestas campo a campo, avisos proactivos con plantillas aprobadas (ventana de 24 h)

### UI/UX del asistente (transversal)
- [ ] Rediseño del chat: markdown en respuestas, tarjetas de acción, estados de tool ("consultando inventario…"), adjuntar foto, sugerencias rápidas, layout móvil (fullscreen), historial persistente, accesibilidad

### Deuda detectada
- [ ] Al importar `main.py` se imprime `Error loading nutrition database: could not convert string to float: 'Vegetales'`: `load_nutrition_database()` falla leyendo el CSV, así que `/api/inventory/nutrition-lookup` queda con base vacía (preexistente, sin tocar)
- [ ] `POST /api/inventory/` sin validación (KeyError → 500) ni chequeo de duplicados
- [ ] `isAdmin()` del frontend es "usuario con email"; backend sin verificación de token en el resto de rutas (aplicar `@require_admin` ruta por ruta, cuidando las rutas públicas: reservas, contacto)

---

**Última actualización**: Marzo 2026
**Total tareas activas**: 55+ items
**Estado del proyecto**: M0 ✅, M1 ✅, M2 ✅, M3 ✅, M4 ✅, M_NUT ✅ COMPLETADO
**Próximo milestone**: M_MP - Integración MercadoPago Abonos
**Último cambio**: M4 Mobile Experience Enhancement completo — PWA funcional, admin pages responsive, touch optimizations (21/03/2026)