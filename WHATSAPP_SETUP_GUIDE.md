# Configuración de WhatsApp para Pablo's Pizza

## Opción 1: Twilio WhatsApp Business API (Recomendado)

### 1. Crear cuenta en Twilio
1. Ve a https://www.twilio.com/
2. Registrate con tu email
3. Verifica tu número de teléfono
4. Obtén $15 USD de crédito gratis

### 2. Configurar WhatsApp Sandbox (Para pruebas)
1. En el panel de Twilio, ve a "Messaging" → "Try it out" → "Send a WhatsApp message"
2. Sigue las instrucciones para unir tu número personal al sandbox
3. Envía "join [código]" al número de Twilio desde tu WhatsApp

### 3. Variables de entorno (.env en backend)
```env
TWILIO_ACCOUNT_SID=tu_account_sid_de_twilio
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### 4. Para WhatsApp Business oficial
Para usar tu propio número (+56 9 8942 4566):
1. Solicitar WhatsApp Business API en Twilio
2. Proceso de verificación (puede tomar días/semanas)
3. Costo: ~$0.005 USD por mensaje

## Opción 2: WhatsApp Business App (Manual)

### Para empezar rápidamente sin API:
1. Usar WhatsApp Business en el teléfono del negocio
2. Configurar respuestas automáticas
3. Mensajes manuales por ahora

## Opción 3: Integración con Facebook/Meta

### Si tienes Facebook Business:
1. Configurar WhatsApp Business Platform
2. Conectar con Facebook Business Manager
3. API gratuita hasta cierto volumen

## Para testing inmediato:

1. Usa la Opción 1 (Twilio Sandbox)
2. Agrega estos números al sandbox para pruebas
3. Costo mínimo para pruebas

## Integración con el sistema actual:

El código ya está listo en `whatsapp_service.py`. Solo necesitas:

1. Configurar las credenciales de Twilio
2. Activar en el backend cuando confirmes eventos
3. Los mensajes se enviarán automáticamente

¿Quieres que configure el Twilio Sandbox para pruebas inmediatas?