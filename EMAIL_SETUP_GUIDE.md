# Configuración de Email para Pablo's Pizza

## Opción 1: Gmail SMTP (Recomendado para empezar)

### 1. Crear cuenta Gmail para el negocio
- Crea una cuenta: `pablospizzacl@gmail.com`
- Ve a "Gestionar tu cuenta de Google" → Seguridad
- Activa "Verificación en 2 pasos"
- Una vez activada la verificación en 2 pasos, busca "Contraseñas de aplicaciones"
  - Si no aparece, busca en la barra de búsqueda: "App passwords" o "Contraseñas de aplicaciones"
  - O ve directamente a: https://myaccount.google.com/apppasswords
- Selecciona "Aplicación": Correo
- Selecciona "Dispositivo": Windows Computer (o el que uses)
- Google generará una contraseña de 16 caracteres (ej: abcd efgh ijkl mnop)
- **IMPORTANTE**: Usa esta contraseña generada, NO tu contraseña normal de Gmail

### 2. Variables de entorno (.env en backend)
```env
EMAIL_USERNAME=pablospizzacl@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop  # <- La contraseña de 16 caracteres que generó Google
EMAIL_FROM=noreply@pablospizza.cl
EMAIL_SERVER=smtp.gmail.com
EMAIL_PORT=587
EMAIL_STARTTLS=true
EMAIL_SSL_TLS=false
EMAIL_USE_CREDENTIALS=true
EMAIL_VALIDATE_CERTS=true
```

### 3. Pasos adicionales si no encuentras "Contraseñas de aplicaciones":

**Opción A - Método alternativo (2024):**
1. Ve a https://myaccount.google.com/security
2. En "Cómo inicias sesión en Google" → "Contraseñas de aplicaciones"
3. Si no aparece, es porque necesitas:
   - Tener verificación en 2 pasos activada
   - Esperar unos minutos después de activar 2FA

**Opción B - Si sigue sin aparecer:**
1. Prueba cambiar a "Acceso de aplicaciones menos seguras" (no recomendado)
2. Ve a https://myaccount.google.com/lesssecureapps
3. Activa "Permitir aplicaciones menos seguras"

**Opción C - Usar OAuth2 (más complejo):**
1. Crear proyecto en Google Cloud Console
2. Configurar OAuth2 credentials
3. Usar refresh tokens

## Opción 2: Servidor de correo profesional

### 1. Contratar hosting de email
- Hostinger, SiteGround, o similar
- Crear casilla: `noreply@pablospizza.cl`

### 2. Configuración SMTP (ejemplo Hostinger)
```env
EMAIL_USERNAME=noreply@pablospizza.cl
EMAIL_PASSWORD=tu_contraseña
EMAIL_FROM=noreply@pablospizza.cl
EMAIL_SERVER=smtp.hostinger.com
EMAIL_PORT=587
EMAIL_STARTTLS=true
EMAIL_SSL_TLS=false
EMAIL_USE_CREDENTIALS=true
EMAIL_VALIDATE_CERTS=true
```

## Opción 3: SendGrid (Para volumen alto)

### 1. Registrarse en SendGrid
- Verificar dominio pablospizza.cl
- Obtener API Key

### 2. Configuración
```env
EMAIL_USERNAME=apikey
EMAIL_PASSWORD=tu_sendgrid_api_key
EMAIL_FROM=noreply@pablospizza.cl
EMAIL_SERVER=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_STARTTLS=true
EMAIL_SSL_TLS=false
EMAIL_USE_CREDENTIALS=true
EMAIL_VALIDATE_CERTS=true
```

## Para Firebase Functions

Si quieres que funcione sin servidor backend, necesitarás:

1. Migrar el servicio de email a Firebase Functions
2. Usar SendGrid API o servicio similar
3. Configurar variables de entorno en Firebase

¿Cuál opción prefieres implementar primero?