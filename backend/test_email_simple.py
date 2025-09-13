#!/usr/bin/env python3
"""
Script de prueba simplificado para verificar que el email funciona con Gmail
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# Configuración de email
EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=os.getenv('EMAIL_USERNAME', 'gonzalo.asb@gmail.com'),
    MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD', 'izct tpac jcbw mlhb'),
    MAIL_FROM=os.getenv('EMAIL_FROM', 'noreply@pablospizza.cl'),
    MAIL_PORT=int(os.getenv('EMAIL_PORT', 587)),
    MAIL_SERVER=os.getenv('EMAIL_SERVER', 'smtp.gmail.com'),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

print("Configuracion de email:")
print(f"   Usuario: {EMAIL_CONFIG.MAIL_USERNAME}")
print(f"   Servidor: {EMAIL_CONFIG.MAIL_SERVER}:{EMAIL_CONFIG.MAIL_PORT}")
print(f"   De: {EMAIL_CONFIG.MAIL_FROM}")

fastmail = FastMail(EMAIL_CONFIG)

async def send_test_email():
    """Enviar email de prueba"""

    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Prueba de Email - Pablo's Pizza</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #ff6b35; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .logo {{ font-size: 24px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">Pablo's Pizza</div>
            <h1>Email de Prueba!</h1>
        </div>

        <div class="content">
            <h2>Hola Gonzalo!</h2>

            <p>Esta es una prueba del sistema de notificaciones de Pablo's Pizza.</p>

            <p><strong>Fecha de prueba:</strong> {fecha_actual}</p>

            <h3>Si recibes este email:</h3>
            <ul>
                <li>Gmail SMTP funciona correctamente</li>
                <li>Las credenciales estan bien configuradas</li>
                <li>FastAPI Mail esta funcionando</li>
                <li>El sistema esta listo para enviar notificaciones reales</li>
            </ul>

            <p><strong>El sistema de notificaciones esta funcionando!</strong></p>
        </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Prueba de Email - Pablo's Pizza",
        recipients=["gonzalo.asb@gmail.com"],
        body=html_content,
        subtype="html"
    )

    try:
        print("Enviando email de prueba...")
        await fastmail.send_message(message)
        print("Email enviado exitosamente!")
        print("Revisa tu bandeja de entrada (y carpeta de spam)")
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        return False

async def main():
    print("Iniciando prueba de email...")
    print("=" * 50)

    success = await send_test_email()

    print("=" * 50)
    if success:
        print("Prueba exitosa! El sistema de email esta funcionando.")
        print("Puedes empezar a usar las notificaciones en el sistema.")
    else:
        print("La prueba fallo. Revisa la configuracion.")

    print("Prueba finalizada")

if __name__ == "__main__":
    asyncio.run(main())