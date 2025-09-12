# 🚀 Guía de Instalación Completa - Pablo's Pizza

Esta guía te llevará paso a paso para configurar completamente el sistema de Pablo's Pizza en tu entorno.

## 📋 Antes de Empezar

### 💻 Requisitos del Sistema
- **Sistema Operativo:** Windows 10+, macOS 10.15+, o Ubuntu 18.04+
- **Python:** Versión 3.9 o superior
- **Node.js:** Versión 18 o superior
- **Git:** Para control de versiones
- **Editor de Código:** VS Code (recomendado)

### 📱 Cuentas Necesarias
- **Firebase:** Para base de datos y hosting
- **Twilio:** Para notificaciones WhatsApp
- **Google Cloud:** Para funciones en la nube (opcional)

## 🔥 Paso 1: Configuración de Firebase

### 1.1 Crear Proyecto Firebase

1. Ve a [Firebase Console](https://console.firebase.google.com)
2. Haz clic en "Crear proyecto"
3. Nombre del proyecto: `pablos-pizza-app`
4. Habilita Google Analytics (recomendado)
5. Selecciona tu cuenta de Analytics

### 1.2 Configurar Authentication

1. En el panel izquierdo, ve a **Authentication**
2. En la pestaña **Sign-in method**, habilita:
   - **Email/Contraseña**
3. En **Users**, agrega tu usuario administrador:
   ```
   Email: admin@pablospizza.com
   Contraseña: [tu contraseña segura]
   ```

### 1.3 Configurar Firestore Database

1. Ve a **Firestore Database**
2. Haz clic en **Crear base de datos**
3. Selecciona **Empezar en modo de prueba**
4. Elige la ubicación más cercana (ej: `us-central1`)

### 1.4 Configurar Storage

1. Ve a **Storage**
2. Haz clic en **Comenzar**
3. Acepta las reglas de seguridad por defecto

### 1.5 Configurar Hosting

1. Ve a **Hosting**
2. Haz clic en **Comenzar**
3. Instala Firebase CLI:
   ```bash
   npm install -g firebase-tools
   ```
4. Inicia sesión:
   ```bash
   firebase login
   ```

### 1.6 Obtener Credenciales

1. Ve a **Configuración del proyecto** (ícono de engranaje)
2. En **General > Tus aplicaciones**, haz clic en **Web**
3. Registra la app como "Pablo's Pizza Web"
4. **¡IMPORTANTE!** Guarda estos valores para después:
   ```javascript
   const firebaseConfig = {
     apiKey: "tu-api-key",
     authDomain: "pablos-pizza-app.firebaseapp.com",
     projectId: "pablos-pizza-app",
     storageBucket: "pablos-pizza-app.appspot.com",
     messagingSenderId: "123456789",
     appId: "1:123456789:web:abcdef123456"
   };
   ```

### 1.7 Service Account para Backend

1. Ve a **Configuración del proyecto > Cuentas de servicio**
2. Haz clic en **Generar nueva clave privada**
3. Se descargará un archivo JSON
4. Renómbralo a `firebase-service-account.json`

## 📞 Paso 2: Configuración de Twilio WhatsApp

### 2.1 Crear Cuenta Twilio

1. Ve a [twilio.com](https://www.twilio.com)
2. Regístrate para una cuenta gratuita
3. Verifica tu número de teléfono

### 2.2 Configurar WhatsApp Sandbox

1. En el Dashboard de Twilio, ve a **Messaging > Try it out**
2. Selecciona **Send a WhatsApp message**
3. Sigue las instrucciones para conectar tu WhatsApp:
   - Envía "join [codigo-sandbox]" al número de Twilio
   - Ejemplo: Envía "join apple-dog" a +1 415 523 8886

### 2.3 Obtener Credenciales

En el Dashboard de Twilio, anota estos valores:
```
Account SID: ACxxxxxxxxxxxxxxxxxxxxx
Auth Token: xxxxxxxxxxxxxxxxxxxxxxxx
WhatsApp Number: whatsapp:+14155238886
```

## 💻 Paso 3: Configuración del Backend

### 3.1 Preparar Entorno

```bash
# Clonar o navegar al proyecto
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3.2 Configurar Variables de Entorno

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```

2. Edita `.env` con tus credenciales:
   ```env
   # Firebase
   FIREBASE_PROJECT_ID=pablos-pizza-app
   
   # Twilio WhatsApp
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   
   # Admin Configuration
   ADMIN_WHATSAPP_NUMBER=+521234567890
   ADMIN_EMAIL=admin@pablospizza.com
   
   # Environment
   ENVIRONMENT=development
   DEBUG=true
   ```

### 3.3 Configurar Firebase Service Account

1. Coloca el archivo `firebase-service-account.json` en la carpeta `backend/`
2. Verifica que el archivo esté en `.gitignore`

### 3.4 Probar Backend

```bash
# Ejecutar servidor
python main.py

# El servidor debe iniciar en http://localhost:8000
# Visita http://localhost:8000/docs para ver la documentación API
```

## 🌐 Paso 4: Configuración del Frontend

### 4.1 Preparar Entorno

```bash
# Navegar al frontend
cd frontend

# Instalar dependencias
npm install
```

### 4.2 Configurar Variables de Entorno

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env.local
   ```

2. Edita `.env.local` con las credenciales de Firebase:
   ```env
   # Firebase Configuration
   VITE_FIREBASE_API_KEY=tu-api-key
   VITE_FIREBASE_AUTH_DOMAIN=pablos-pizza-app.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=pablos-pizza-app
   VITE_FIREBASE_STORAGE_BUCKET=pablos-pizza-app.appspot.com
   VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
   VITE_FIREBASE_APP_ID=1:123456789:web:abcdef123456
   
   # API Configuration
   VITE_API_URL=http://localhost:8000/api
   
   # Environment
   VITE_ENVIRONMENT=development
   ```

### 4.3 Probar Frontend

```bash
# Ejecutar aplicación
npm run dev

# La aplicación debe abrir en http://localhost:3000
```

## 📱 Paso 5: Configuración de App Móvil (Opcional)

### 5.1 Instalar Expo CLI

```bash
npm install -g @expo/cli
```

### 5.2 Preparar App Móvil

```bash
# Navegar a mobile
cd mobile

# Instalar dependencias
npm install

# Iniciar desarrollo
expo start
```

### 5.3 Probar en Dispositivo

1. Descarga **Expo Go** en tu móvil
2. Escanea el código QR que aparece en la terminal
3. La app debe cargar en tu dispositivo

## 🔧 Paso 6: Configuración de Firebase (Reglas y Deploy)

### 6.1 Inicializar Firebase en el Proyecto

```bash
# En la raíz del proyecto
firebase init

# Selecciona:
# - Firestore
# - Functions
# - Hosting
# - Storage

# Configuraciones:
# - Firestore rules: firestore.rules
# - Firestore indexes: firestore.indexes.json
# - Functions source: backend
# - Hosting public directory: frontend/dist
# - Single page app: Yes
```

### 6.2 Desplegar Reglas de Firestore

```bash
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes
firebase deploy --only storage
```

## ✅ Paso 7: Verificación de Instalación

### 7.1 Probar Backend

1. Ve a http://localhost:8000/docs
2. Prueba el endpoint `/health`
3. Debe responder `{"status": "healthy"}`

### 7.2 Probar Frontend

1. Ve a http://localhost:3000
2. La página debe cargar con el logo y colores correctos
3. Intenta navegar a diferentes secciones

### 7.3 Probar Integración

1. En el frontend, ve a "Agendar Evento"
2. Completa el formulario
3. Revisa en Firebase Console > Firestore que se creó el documento
4. Verifica que llegó notificación WhatsApp (si configuraste tu número)

### 7.4 Probar Panel Admin

1. Ve a http://localhost:3000/admin/login
2. Inicia sesión con las credenciales de Firebase
3. Debe redirigir al dashboard administrativo

## 🎉 ¡Configuración Completa!

Si llegaste aquí sin errores, ¡felicitaciones! Tu sistema de Pablo's Pizza está completamente configurado.

### 🔄 Próximos Pasos

1. **Personalización:** Modifica colores, textos y logo según tu marca
2. **Contenido:** Agrega imágenes a la galería y información de servicios
3. **Pruebas:** Haz pruebas completas de todos los flujos
4. **Producción:** Sigue la guía de deploy para poner en vivo

### 📞 ¿Necesitas Ayuda?

Si encuentras problemas:
1. Revisa la sección **Troubleshooting** en el README
2. Verifica que todos los servicios estén corriendo
3. Consulta los logs de consola para errores específicos

¡Tu sistema de gestión gastronómica está listo para crear experiencias increíbles! 🍕✨