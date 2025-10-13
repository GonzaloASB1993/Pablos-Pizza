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
        smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', 587))
        email_username = os.getenv('EMAIL_USERNAME')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM')

        if not all([email_username, email_password, email_from]):
            return False

        service_name = format_service_name(booking_data.get('service_type', ''))

        html_content = f"""
        <!DOCTYPE html>
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:linear-gradient(135deg,#000 0%,#1a1a1a 100%);padding:40px 30px;text-align:center">
        <img src="https://pablospizza.web.app/assets/logo-nqn6pSjR.png" style="width:180px;border-radius:50%;border:3px solid #FFC107">
        <h1 style="color:#fff;margin-top:20px">¡Tu evento ha sido confirmado!</h1>
        <div style="display:inline-block;background:#FFC107;color:#000;padding:8px 20px;border-radius:25px;margin-top:15px;font-weight:700">✅ CONFIRMADO</div>
        </div>
        <div style="padding:40px 30px">
        <p style="font-size:20px;font-weight:600;color:#000">¡Hola {booking_data.get('client_name','Cliente')}!</p>
        <p style="color:#4a4a4a;margin-bottom:30px">Tu evento ha sido <strong>confirmado oficialmente</strong>. Estamos emocionados de ser parte de tu celebración especial.</p>
        <div style="background:#f8f9fa;border:2px solid #FFC107;border-radius:16px;padding:25px;margin:30px 0">
        <h3 style="color:#000;margin-bottom:20px">📋 Detalles de tu evento</h3>
        <p><span style="font-weight:600">🍕 Servicio:</span> {service_name}</p>
        <p><span style="font-weight:600">📅 Fecha:</span> {booking_data.get('event_date','No especificada')}</p>
        <p><span style="font-weight:600">⏰ Hora:</span> {booking_data.get('event_time','No especificada')}</p>
        <p><span style="font-weight:600">📍 Ubicación:</span> {booking_data.get('location','No especificada')}</p>
        <p><span style="font-weight:600">💰 Precio:</span> <span style="color:#FFC107;font-weight:700;font-size:18px">${booking_data.get('estimated_price',0):,.0f} CLP</span></p>
        </div>
        <div style="text-align:center;margin:30px 0">
        <a href="https://wa.me/56989424566" style="display:inline-block;background:#FFC107;color:#000;padding:12px 20px;text-decoration:none;border-radius:25px;font-weight:600">📱 WhatsApp: +56 9 8942 4566</a>
        </div>
        </div>
        <div style="background:#f8f9fa;padding:30px;text-align:center;border-top:1px solid #e9ecef">
        <div style="color:#000;font-weight:700;font-size:16px;margin-bottom:8px">Pablo's Pizza</div>
        <div style="color:#6c757d;font-size:14px">Creando momentos deliciosos y memorables</div>
        </div>
        </body></html>
        """

        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = booking_data.get('client_email')
        msg['Subject'] = "¡Tu evento con Pablo's Pizza ha sido confirmado!"
        msg.attach(MIMEText(html_content, 'html'))

        calendar_content = generate_calendar_invite(booking_data)
        if calendar_content:
            cal_att = MIMEText(calendar_content, 'calendar')
            cal_att['Content-Disposition'] = 'attachment; filename="evento_pablos_pizza.ics"'
            cal_att.set_type('text/calendar')
            cal_att.set_param('method', 'REQUEST')
            msg.attach(cal_att)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(email_from, booking_data.get('client_email'), msg.as_string())
        server.quit()

        try:
            db = get_db()
            db.collection("emails").add({"recipient_email":booking_data.get('client_email'),"subject":"Confirmación","booking_id":booking_data.get('id'),"email_type":"confirmation","sent_at":datetime.now(),"status":"sent"})
        except: pass

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_admin_email_notification(booking_data: dict) -> bool:
    """Send email notification to admin about new booking"""
    try:
        smtp_server,smtp_port = os.getenv('EMAIL_SERVER','smtp.gmail.com'),int(os.getenv('EMAIL_PORT',587))
        email_username,email_password,email_from = os.getenv('EMAIL_USERNAME'),os.getenv('EMAIL_PASSWORD'),os.getenv('EMAIL_FROM')
        if not all([email_username,email_password,email_from]): return False
        
        service_name = format_service_name(booking_data.get('service_type',''))
        msg = MIMEMultipart()
        msg['From'],msg['To'],msg['Subject'] = email_from,email_from,f"🍕 NUEVO AGENDAMIENTO - {booking_data.get('client_name','Cliente')}"
        
        html_content = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#FFC107;text-align:center">🍕 Pablo's Pizza</h2>
        <h3 style="color:#000">¡NUEVO AGENDAMIENTO!</h3>
        <div style="background-color:#f8f9fa;padding:20px;border-radius:8px;margin:20px 0">
        <h4>👤 Información del Cliente:</h4>
        <p><strong>Nombre:</strong> {booking_data.get('client_name','N/A')}</p>
        <p><strong>Teléfono:</strong> {booking_data.get('client_phone','N/A')}</p>
        <p><strong>Email:</strong> {booking_data.get('client_email','N/A')}</p>
        <h4>🍕 Detalles del Evento:</h4>
        <p><strong>Servicio:</strong> {service_name}</p>
        <p><strong>Fecha:</strong> {booking_data.get('event_date','N/A')}</p>
        <p><strong>Hora:</strong> {booking_data.get('event_time','N/A')}</p>
        <p><strong>Participantes:</strong> {booking_data.get('participants','N/A')}</p>
        <p><strong>Ubicación:</strong> {booking_data.get('location','N/A')}</p>
        <p><strong>Precio estimado:</strong> ${booking_data.get('estimated_price',0):,.0f} CLP</p>
        </div>
        <div style="text-align:center;margin:30px 0">
        <a href="https://pablospizza.web.app/admin/agendamientos" style="background-color:#FFC107;color:black;padding:12px 24px;text-decoration:none;border-radius:5px;font-weight:bold">Ver en Admin Panel</a>
        </div></div>"""
        
        msg.attach(MIMEText(html_content,'html'))
        server = smtplib.SMTP(smtp_server,smtp_port)
        server.starttls()
        server.login(email_username,email_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending admin email: {e}")
        return False
