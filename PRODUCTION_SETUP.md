# 🍕 CONFIGURACIÓN DE PRODUCCIÓN - PABLO'S PIZZA

## ✅ CHECKLIST COMPLETO PARA PRODUCCIÓN

### **PASO 1: Configurar Twilio (WhatsApp)**
1. **Crear cuenta Twilio**: https://console.twilio.com/
2. **Obtener credenciales**:
   - Account SID
   - Auth Token
3. **Configurar WhatsApp Sandbox**: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
4. **Actualizar `.env.production`**:
   ```bash
   TWILIO_ACCOUNT_SID=tu_account_sid_aqui
   TWILIO_AUTH_TOKEN=tu_auth_token_aqui
   ADMIN_WHATSAPP_NUMBER=+56912345678  # Tu número para recibir notificaciones
   ```

### **PASO 2: Configurar Email (Gmail)**
1. **Habilitar 2FA en Gmail**: https://myaccount.google.com/security
2. **Crear App Password**: https://support.google.com/accounts/answer/185833
3. **Actualizar `.env.production`**:
   ```bash
   EMAIL_USERNAME=tu_email@gmail.com
   EMAIL_PASSWORD=tu_app_password_de_16_caracteres
   EMAIL_FROM=tu_email@gmail.com
   ```

### **PASO 3: Configurar Firebase**
1. **Verificar proyecto Firebase**: `pablospizza-d84bf`
2. **Verificar dominios autorizados**:
   - `pablospizza.web.app`
   - `pablospizza.firebaseapp.com`

### **PASO 4: Variables de Entorno Críticas**

#### **Backend (`backend/.env.production`)**
```bash
# ✅ OBLIGATORIAS para producción
TWILIO_ACCOUNT_SID=tu_twilio_sid
TWILIO_AUTH_TOKEN=tu_twilio_token
ADMIN_WHATSAPP_NUMBER=+56912345678

EMAIL_USERNAME=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password
EMAIL_FROM=tu_email@gmail.com

ENVIRONMENT=production
DEBUG=false
```

#### **Frontend (`frontend/.env`)**
```bash
# ✅ Ya configurado correctamente
VITE_API_URL=https://pablospizza.web.app/api
VITE_ENVIRONMENT=production
```

### **PASO 5: Deployment**

#### **Opción A: Script Automático**
```bash
chmod +x deploy.sh
./deploy.sh
```

#### **Opción B: Manual**
```bash
# 1. Build frontend
cd frontend
npm install
npm run build
cd ..

# 2. Deploy a Firebase
firebase deploy
```

### **PASO 6: Verificación Post-Deployment**

1. **✅ Frontend**: https://pablospizza.web.app
2. **✅ API Health**: https://pablospizza.web.app/api/health
3. **✅ Test Booking**: Crear una reserva de prueba
4. **✅ Notificaciones**: Verificar WhatsApp y Email

### **PASO 7: Monitoreo**

#### **Firebase Console**
- Functions: https://console.firebase.google.com/project/pablospizza-d84bf/functions
- Firestore: https://console.firebase.google.com/project/pablospizza-d84bf/firestore
- Hosting: https://console.firebase.google.com/project/pablospizza-d84bf/hosting

#### **Logs de Errores**
```bash
firebase functions:log
```

## 🚨 TROUBLESHOOTING

### **Problema: Functions no se despliegan**
```bash
# Verificar requirements.txt
cd backend
pip install -r requirements.txt

# Verificar Firebase CLI
firebase --version
firebase login
```

### **Problema: CORS Errors**
- Verificar dominios en `main.py` allow_origins
- Verificar URL en frontend `.env`

### **Problema: WhatsApp no funciona**
1. Verificar Account SID y Auth Token
2. Verificar formato de números: `+56912345678`
3. Probar WhatsApp Sandbox primero

### **Problema: Email no funciona**
1. Verificar App Password (no contraseña normal)
2. Verificar 2FA habilitado en Gmail
3. Verificar SMTP settings

## 📊 MÉTRICAS DE NEGOCIO

### **Precios Configurados**
- Workshop (Pizzeros en Acción): $13,500 por niño
- Pizza Party: $11,990 por persona
- Descuentos automáticos por volumen

### **Capacidades**
- Reservas simultáneas: ✅ Ilimitadas
- Almacenamiento: ✅ Firestore escalable
- Notificaciones: ✅ WhatsApp + Email
- Admin Panel: ✅ Completo

## 🎯 PRÓXIMOS PASOS RECOMENDADOS

1. **Dominio Personalizado**: Configurar `www.pablospizza.cl`
2. **WhatsApp Business**: Migrar de Sandbox a cuenta Business
3. **Analytics**: Implementar Google Analytics
4. **SEO**: Optimizar meta tags y sitemap
5. **Backup**: Configurar backup automático de Firestore

---

**🎉 ¡Pablo's Pizza listo para producción!**

Para soporte técnico, contactar al desarrollador.