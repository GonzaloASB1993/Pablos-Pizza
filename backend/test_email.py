#!/usr/bin/env python3
"""
Script de prueba para verificar que el servicio de email funciona correctamente
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar servicios
sys.path.append(str(Path(__file__).parent))

from services.email_service import send_confirmation_email, send_welcome_email
from datetime import datetime

async def test_email():
    """Prueba el envío de emails"""
    print("🧪 Iniciando prueba de email...")

    # Datos de prueba para confirmación
    booking_data = {
        'id': 'test_123',
        'client_name': 'Gonzalo',
        'client_email': 'gonzalo.asb@gmail.com',  # Tu email para recibir la prueba
        'client_phone': '+56912345678',
        'service_type': 'workshop',
        'event_date': datetime.now(),
        'event_time': '15:00',
        'participants': 10,
        'location': 'Casa de Gonzalo',
        'estimated_price': 150000
    }

    print(f"📧 Enviando email de confirmación a: {booking_data['client_email']}")

    try:
        # Probar email de confirmación
        result = await send_confirmation_email(booking_data)
        if result:
            print("✅ Email de confirmación enviado exitosamente!")
            print("📱 Revisa tu bandeja de entrada (y spam)")
        else:
            print("❌ Error al enviar email de confirmación")

        # Probar email de bienvenida
        print(f"📧 Enviando email de bienvenida...")
        welcome_result = await send_welcome_email(
            booking_data['client_email'],
            booking_data['client_name']
        )

        if welcome_result:
            print("✅ Email de bienvenida enviado exitosamente!")
        else:
            print("❌ Error al enviar email de bienvenida")

    except Exception as e:
        print(f"❌ Error durante la prueba: {str(e)}")
        print(f"🔍 Tipo de error: {type(e).__name__}")

        # Mostrar más detalles del error
        import traceback
        traceback.print_exc()

    print("🏁 Prueba finalizada")

if __name__ == "__main__":
    # Ejecutar la prueba
    asyncio.run(test_email())