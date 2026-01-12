"""Email Service - Send confirmation and notification emails"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from services.calendar_service import generate_calendar_invite
from utils.formatters import format_service_name
from database import get_db

def send_confirmation_email(booking_data: dict) -> bool:
    """Send professional HTML confirmation email to client"""
    try:
        print(f"Enviando email de confirmación a: {booking_data.get('client_email')}")

        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            print("Error: Configuración de email incompleta")
            return False

        # Determine service name
        service_types = booking_data.get('service_type', '')
        services = [s.strip() for s in service_types.split(',') if s.strip()]
        if len(services) > 1:
            service_name = 'Pizza Party + Pizzeros en Acción'
        elif 'workshop' in services or 'pizzeros' in services:
            service_name = 'Pizzeros en Acción'
        else:
            service_name = 'Pizza Party'

        # Format participants info
        participants_display = ""
        if booking_data.get('service_type') == 'workshop':
            participants_display = f"{booking_data.get('pizzeros_participants', 0)} niños"
        elif booking_data.get('service_type') == 'pizza_party':
            participants_display = f"{booking_data.get('party_guests', 0)} personas"
        else:
            # Combo
            participants_display = f"{booking_data.get('pizzeros_participants', 0)} niños + {booking_data.get('party_guests', 0)} personas"

        # Pizza quantity display (only for pizza party)
        pizza_row = ""
        if 'pizza_party' in booking_data.get('service_type', ''):
            pizza_row = f'''
                        <div class="detail-row">
                            <span class="detail-icon">🍕</span>
                            <span class="detail-label">Pizzas incluidas:</span>
                            <span class="detail-value">{booking_data.get('pizza_quantity', 10)} pizzas artesanales</span>
                        </div>'''

        # Create professional branded HTML email with modern design
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Evento Confirmado - Pablo's Pizza</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background-color: #f8f9fa;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    padding: 40px 30px;
                    text-align: center;
                    position: relative;
                }}
                .logo-image {{
                    width: 180px;
                    height: 180px;
                    border-radius: 50%;
                    box-shadow: 0 8px 24px rgba(255, 193, 7, 0.4);
                    margin-bottom: 20px;
                    border: 3px solid #FFC107;
                }}
                .header h1 {{
                    color: #ffffff;
                    font-size: 28px;
                    font-weight: 700;
                    margin: 0;
                }}
                .status-badge {{
                    display: inline-block;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-weight: 700;
                    font-size: 14px;
                    margin-top: 15px;
                }}
                .content {{
                    padding: 40px 30px;
                    background-color: #ffffff;
                }}
                .greeting {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #000000;
                    margin-bottom: 15px;
                }}
                .intro-text {{
                    font-size: 16px;
                    color: #4a4a4a;
                    margin-bottom: 30px;
                    line-height: 1.7;
                }}
                .event-details {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border: 2px solid #FFC107;
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                }}
                .event-details h3 {{
                    color: #000000;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 20px;
                }}
                .detail-row {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 12px;
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }}
                .detail-row:last-child {{ border-bottom: none; margin-bottom: 0; }}
                .detail-icon {{ width: 24px; font-size: 18px; margin-right: 12px; }}
                .detail-label {{ font-weight: 600; color: #2c2c2c; min-width: 100px; }}
                .detail-value {{ color: #4a4a4a; flex: 1; }}
                .price-highlight {{
                    color: #FFC107 !important;
                    font-weight: 700;
                    font-size: 18px;
                }}
                .expectations {{
                    margin: 30px 0;
                }}
                .expectations h3 {{
                    color: #000000;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 20px;
                }}
                .expectations ul {{
                    list-style: none;
                    padding: 0;
                }}
                .expectations li {{
                    padding: 12px 0;
                    border-bottom: 1px solid #f0f0f0;
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                }}
                .expectations li:last-child {{ border-bottom: none; }}
                .check-icon {{
                    color: #FFC107;
                    font-weight: bold;
                    font-size: 16px;
                    margin-top: 2px;
                }}
                .contact-section {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    text-align: center;
                }}
                .contact-section h3 {{
                    color: #FFC107;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 15px;
                }}
                .contact-section p {{
                    color: #cccccc;
                    margin-bottom: 20px;
                }}
                .contact-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 600;
                    margin: 5px;
                }}
                .calendar-section {{
                    background-color: #f8f9fa;
                    padding: 25px 20px;
                    margin: 25px 0;
                    border-radius: 8px;
                    border: 2px dashed #FFC107;
                }}
                .calendar-section h3 {{
                    color: #000000;
                    font-size: 20px;
                    margin-bottom: 15px;
                    text-align: center;
                }}
                .cta-section {{
                    text-align: center;
                    margin: 30px 0;
                    padding: 25px;
                    background: linear-gradient(135deg, #FFF3C4 0%, #FFECB3 100%);
                    border-radius: 16px;
                    border: 1px solid #FFC107;
                }}
                .cta-text {{
                    font-size: 18px;
                    font-weight: 700;
                    color: #000000;
                    margin: 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
                .footer-brand {{
                    color: #000000;
                    font-weight: 700;
                    font-size: 16px;
                    margin-bottom: 8px;
                }}
                .footer-tagline {{
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 15px;
                }}
                .footer-disclaimer {{
                    color: #adb5bd;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                @media only screen and (max-width: 600px) {{
                    .email-container {{ margin: 10px; }}
                    .header {{ padding: 30px 20px; }}
                    .content {{ padding: 25px 20px; }}
                    .header h1 {{ font-size: 24px; }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <img src="https://pablospizza.web.app/assets/logo-nqn6pSjR.png" alt="Pablo's Pizza" class="logo-image">
                    <h1>¡Tu evento ha sido confirmado!</h1>
                    <div class="status-badge">✅ CONFIRMADO</div>
                </div>
                <div class="content">
                    <div class="greeting">¡Hola {booking_data.get('client_name', 'Cliente')}!</div>
                    <p class="intro-text">
                        ¡Excelente noticia! Tu evento ha sido <strong>confirmado oficialmente</strong> y estamos emocionados de ser parte de tu celebración especial. Nuestro equipo está preparado para brindarte una experiencia inolvidable.
                    </p>
                    <div class="event-details">
                        <h3>📋 Detalles de tu evento</h3>
                        <div class="detail-row">
                            <span class="detail-icon">🍕</span>
                            <span class="detail-label">Servicio:</span>
                            <span class="detail-value"><strong>{service_name}</strong></span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-icon">📅</span>
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{booking_data.get('event_date', 'No especificada')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-icon">⏰</span>
                            <span class="detail-label">Hora:</span>
                            <span class="detail-value">{booking_data.get('event_time', 'No especificada')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-icon">👥</span>
                            <span class="detail-label">Participantes:</span>
                            <span class="detail-value">{participants_display}</span>
                        </div>
                        {pizza_row}
                        <div class="detail-row">
                            <span class="detail-icon">📍</span>
                            <span class="detail-label">Ubicación:</span>
                            <span class="detail-value">{booking_data.get('location', 'No especificada')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-icon">💰</span>
                            <span class="detail-label">Precio:</span>
                            <span class="detail-value price-highlight">${booking_data.get('estimated_price', 0):,.0f} CLP</span>
                        </div>
                    </div>
                    <div class="expectations">
                        <h3>🔥 ¿Qué puedes esperar de nosotros?</h3>
                        <ul>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Nuestro equipo profesional llegará puntualmente con todo el equipamiento necesario</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Ingredientes frescos y de primera calidad, incluyendo opciones especiales</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Una experiencia interactiva, divertida y educativa para todas las edades</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Pizzas artesanales deliciosas hechas por los propios participantes</span>
                            </li>
                            <li>
                                <span class="check-icon">✓</span>
                                <span>Recuerdos fotográficos y momentos únicos que durarán para siempre</span>
                            </li>
                        </ul>
                    </div>
                    <div class="contact-section">
                        <h3>📞 ¿Tienes alguna pregunta?</h3>
                        <p>Nuestro equipo está disponible para ayudarte con cualquier consulta o cambio de último momento.</p>
                        <div>
                            <a href="https://wa.me/56989424566" class="contact-btn">
                                📱 WhatsApp: +56 9 8942 4566
                            </a>
                            <a href="mailto:pablospizza.cl@gmail.com" class="contact-btn">
                                ✉️ pablospizza.cl@gmail.com
                            </a>
                        </div>
                    </div>
                    <div class="calendar-section">
                        <h3>📅 Agregar a mi Calendario</h3>
                        <p style="text-align: center; margin-bottom: 15px;">Hemos incluido una invitación de calendario con este email. <strong>Revisa los archivos adjuntos</strong> y ábrelo para agregar automáticamente el evento a tu calendario personal.</p>
                        <div style="background-color: #FFF3CD; border-left: 4px solid #FFC107; padding: 12px; margin: 15px 0; border-radius: 4px;">
                            <p style="margin: 0; font-size: 14px; color: #856404;">
                                💡 <strong>Tip:</strong> El archivo "evento_pablos_pizza.ics" se puede abrir con Google Calendar, Outlook, Apple Calendar y la mayoría de aplicaciones de calendario.
                            </p>
                        </div>
                    </div>
                    <div class="cta-section">
                        <p class="cta-text">¡Nos vemos pronto para una experiencia gastronómica increíble! 🎉🍕</p>
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-brand">Pablo's Pizza</div>
                    <div class="footer-tagline">Creando momentos deliciosos y memorables desde siempre</div>
                    <div class="footer-disclaimer">
                        Este es un email automático de confirmación. Para consultas o cambios, utiliza nuestros canales de contacto oficiales.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = booking_data.get('client_email')
        msg['Subject'] = "¡Tu evento con Pablo's Pizza ha sido confirmado!"

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Generate and attach calendar invitation
        calendar_content = generate_calendar_invite(booking_data)
        if calendar_content:
            cal_attachment = MIMEText(calendar_content, 'calendar')
            cal_attachment['Content-Disposition'] = f'attachment; filename="evento_pablos_pizza.ics"'
            cal_attachment.set_type('text/calendar')
            cal_attachment.set_param('method', 'REQUEST')
            msg.attach(cal_attachment)
            print("Invitación de calendario agregada al email")

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        text = msg.as_string()
        server.sendmail(email_from, booking_data.get('client_email'), text)
        server.quit()

        # Save email record to Firestore
        try:
            email_data = {
                "recipient_email": booking_data.get('client_email'),
                "subject": "¡Tu evento con Pablo's Pizza ha sido confirmado!",
                "booking_id": booking_data.get('id'),
                "email_type": "confirmation",
                "sent_at": datetime.now(),
                "status": "sent"
            }
            db = get_db()
            db.collection("emails").add(email_data)
            print(f"Registro de email guardado en Firestore")
        except Exception as e:
            print(f"Error guardando registro de email: {e}")

        print(f"Email de confirmación enviado exitosamente a: {booking_data.get('client_email')}")
        return True

    except Exception as e:
        print(f"Error enviando email de confirmación: {e}")

        # Save error record
        try:
            error_email = {
                "recipient_email": booking_data.get('client_email'),
                "subject": "¡Tu evento con Pablo's Pizza ha sido confirmado!",
                "booking_id": booking_data.get('id'),
                "email_type": "confirmation",
                "sent_at": datetime.now(),
                "status": "failed",
                "error": str(e)
            }
            db = get_db()
            db.collection("emails").add(error_email)
        except:
            pass

        return False

def send_admin_email_notification(booking_data: dict) -> bool:
    """Send professional HTML email notification to admin about new booking"""
    try:
        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            print("Error: Configuración de email incompleta")
            return False

        service_name = format_service_name(booking_data.get('service_type', ''))

        # Format participants info
        participants_display = ""
        service_type = booking_data.get('service_type', '')
        if 'workshop' in service_type or 'pizzeros' in service_type:
            participants_display = f"{booking_data.get('pizzeros_participants', booking_data.get('participants', 0))} niños"
        elif 'pizza_party' in service_type or 'party' in service_type:
            participants_display = f"{booking_data.get('party_participants', booking_data.get('participants', 0))} personas"
        else:
            participants_display = f"{booking_data.get('participants', 0)} participantes"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nuevo Agendamiento - Pablo's Pizza</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background-color: #f8f9fa;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    padding: 40px 30px;
                    text-align: center;
                }}
                .logo-image {{
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    box-shadow: 0 8px 24px rgba(255, 193, 7, 0.4);
                    margin-bottom: 20px;
                    border: 3px solid #FFC107;
                }}
                .header h1 {{
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 700;
                    margin: 0;
                }}
                .status-badge {{
                    display: inline-block;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-weight: 700;
                    font-size: 14px;
                    margin-top: 15px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .section-title {{
                    color: #000000;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #FFC107;
                    padding-bottom: 10px;
                }}
                .info-grid {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border: 2px solid #FFC107;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .info-row {{
                    display: flex;
                    align-items: flex-start;
                    margin-bottom: 12px;
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }}
                .info-row:last-child {{ border-bottom: none; margin-bottom: 0; }}
                .info-icon {{ width: 24px; font-size: 18px; margin-right: 12px; }}
                .info-label {{ font-weight: 600; color: #2c2c2c; min-width: 120px; }}
                .info-value {{ color: #4a4a4a; flex: 1; }}
                .price-highlight {{
                    color: #FFC107 !important;
                    font-weight: 700;
                    font-size: 20px;
                }}
                .action-section {{
                    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
                    border-radius: 12px;
                    padding: 25px;
                    margin: 30px 0;
                    text-align: center;
                }}
                .action-btn {{
                    display: inline-block;
                    padding: 14px 32px;
                    background: linear-gradient(135deg, #FFC107 0%, #FFD54F 100%);
                    color: #000000;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 700;
                    font-size: 16px;
                    margin: 10px;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <img src="https://pablospizza.web.app/assets/logo-nqn6pSjR.png" alt="Pablo's Pizza" class="logo-image">
                    <h1>🎉 ¡Nuevo Agendamiento Recibido!</h1>
                    <div class="status-badge">⚡ ACCIÓN REQUERIDA</div>
                </div>

                <div class="content">
                    <div class="section-title">👤 Información del Cliente</div>
                    <div class="info-grid">
                        <div class="info-row">
                            <span class="info-icon">👤</span>
                            <span class="info-label">Nombre:</span>
                            <span class="info-value"><strong>{booking_data.get('client_name', 'N/A')}</strong></span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📱</span>
                            <span class="info-label">Teléfono:</span>
                            <span class="info-value">{booking_data.get('client_phone', 'N/A')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">✉️</span>
                            <span class="info-label">Email:</span>
                            <span class="info-value">{booking_data.get('client_email', 'N/A')}</span>
                        </div>
                    </div>

                    <div class="section-title">🍕 Detalles del Evento</div>
                    <div class="info-grid">
                        <div class="info-row">
                            <span class="info-icon">🍕</span>
                            <span class="info-label">Servicio:</span>
                            <span class="info-value"><strong>{service_name}</strong></span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📅</span>
                            <span class="info-label">Fecha:</span>
                            <span class="info-value">{booking_data.get('event_date', 'N/A')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">⏰</span>
                            <span class="info-label">Hora:</span>
                            <span class="info-value">{booking_data.get('event_time', 'N/A')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">👥</span>
                            <span class="info-label">Participantes:</span>
                            <span class="info-value">{participants_display}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">📍</span>
                            <span class="info-label">Ubicación:</span>
                            <span class="info-value">{booking_data.get('location', 'N/A')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">💰</span>
                            <span class="info-label">Precio Estimado:</span>
                            <span class="info-value price-highlight">${booking_data.get('estimated_price', 0):,.0f} CLP</span>
                        </div>
                    </div>

                    <div class="action-section">
                        <h3 style="color: #FFC107; margin-bottom: 15px;">🎯 Próximos Pasos</h3>
                        <p style="color: #cccccc; margin-bottom: 20px;">
                            Revisa los detalles del evento y contacta al cliente para confirmar disponibilidad
                        </p>
                        <a href="https://pablospizza.web.app/admin/agendamientos" class="action-btn">
                            📊 Ver en Admin Panel
                        </a>
                        <a href="https://wa.me/{booking_data.get('client_phone', '').replace('+', '')}" class="action-btn">
                            💬 Contactar por WhatsApp
                        </a>
                    </div>
                </div>

                <div class="footer">
                    <p style="color: #6c757d; font-size: 14px; margin: 0;">
                        Este es un email automático de notificación • Pablo's Pizza Admin System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_from
        msg['Subject'] = f"🍕 NUEVO AGENDAMIENTO - {booking_data.get('client_name', 'Cliente')}"

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        server.send_message(msg)
        server.quit()

        print(f"✅ Email de notificación admin enviado exitosamente")
        return True

    except Exception as e:
        print(f"❌ Error sending admin email: {e}")
        return False
