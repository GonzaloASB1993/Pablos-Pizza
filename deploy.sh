#!/bin/bash
# ============================================
# SCRIPT DE DEPLOYMENT PARA PABLO'S PIZZA
# ============================================

set -e  # Exit on any error

echo "🍕 Iniciando deployment de Pablo's Pizza..."

# 1. Verificar que estamos en el directorio correcto
if [ ! -f "firebase.json" ]; then
    echo "❌ Error: No se encontró firebase.json. Ejecuta desde la raíz del proyecto."
    exit 1
fi

# 2. Verificar variables de entorno críticas
echo "📋 Verificando configuración..."
if [ ! -f "backend/.env.production" ]; then
    echo "❌ Error: Falta archivo backend/.env.production"
    echo "   Por favor configura las variables de entorno de producción."
    exit 1
fi

# 3. Build del frontend
echo "🔨 Construyendo frontend..."
cd frontend
npm install
npm run build
cd ..

# 4. Limpiar logs de debug del backend
echo "🧹 Limpiando logs de debug del backend..."
find backend -name "*.log" -delete 2>/dev/null || true

# 5. Deploy a Firebase
echo "🚀 Desplegando a Firebase..."
firebase deploy --only hosting,functions

# 6. Verificar deployment
echo "✅ Deployment completado!"
echo ""
echo "🌐 URLs de tu aplicación:"
echo "   Frontend: https://pablospizza.web.app"
echo "   API: https://pablospizza.web.app/api"
echo ""
echo "📊 Verifica que todo funcione:"
echo "   1. Abre https://pablospizza.web.app"
echo "   2. Crea una reserva de prueba"
echo "   3. Verifica que lleguen las notificaciones"
echo ""
echo "🎉 Pablo's Pizza está en producción!"