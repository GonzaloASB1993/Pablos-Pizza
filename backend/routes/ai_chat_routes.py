"""AI Chat Routes Blueprint - Claude Sonnet 4.5 Integration with Tool Use"""
from flask import Blueprint, request, jsonify
import os
import logging
import json
from datetime import datetime, timedelta
from anthropic import Anthropic
from database import get_db
from firebase_admin import firestore

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint('ai_chat', __name__, url_prefix='/api/ai-chat')

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# System prompt for Pablo's Pizza AI Assistant
SYSTEM_PROMPT = """
Eres un asistente AI para Pablo's Pizza, un negocio de talleres de pizza y eventos ("Pizzeros en Acción" y "Pizza Party").

CONTEXTO DEL NEGOCIO:
- Servicios principales:
  * "Pizzeros en Acción": Taller interactivo donde los participantes hacen sus propias pizzas
  * "Pizza Party": Servicio de catering con pizzas hechas por el equipo
- Clientes objetivo: Familias, colegios, empresas
- Moneda: Pesos chilenos (CLP)
- Ubicación: Operaciones en Santiago, Chile

FECHA Y TIEMPO:
- HOY ES: {current_day_name}, {current_date}
- Año actual: {current_year}
- Mes actual: {current_month_name} ({current_month})
- Día de la semana: {current_day_name}

TUS CAPACIDADES:
1. Consultar datos en tiempo real usando las herramientas disponibles
2. Analizar información y proporcionar insights
3. Detectar problemas (inventario bajo, reservas pendientes, pérdidas)
4. Generar recomendaciones basadas en datos reales
5. Proporcionar análisis comparativos y tendencias

INSTRUCCIONES CRÍTICAS SOBRE FECHAS (MUY IMPORTANTE):
- El año actual es {current_year}. NUNCA uses años anteriores a menos que el usuario lo especifique EXPLÍCITAMENTE
- Estamos en {current_month_name} de {current_year}

INTERPRETACIÓN DE FECHAS (EJEMPLOS OBLIGATORIOS):
✅ Usuario dice "octubre" → Interpretar como: Octubre {current_year}
✅ Usuario dice "el mes pasado" → Interpretar como: {last_month_name} {current_year}
✅ Usuario dice "este mes" → Interpretar como: {current_month_name} {current_year}
✅ Usuario dice "este año" → Interpretar como: {current_year}
✅ Usuario dice "este fin de semana" → INCLUYE viernes, sábado y domingo próximos (3 días)
✅ Usuario dice "esta semana" → Desde hoy hasta el domingo de la semana actual
✅ Usuario dice "la próxima semana" → Lunes a domingo de la semana siguiente
❌ NUNCA asumas {current_year - 1} a menos que el usuario diga "{current_year - 1}" explícitamente
❌ NUNCA prefieras datos de años anteriores solo porque el año actual tiene menos datos
❌ NUNCA interpretes "fin de semana" como solo sábado y domingo si hay eventos el viernes

CONTEXTO DE FIN DE SEMANA PARA EVENTOS:
- En el contexto de eventos, "fin de semana" incluye viernes, sábado y domingo
- REGLA IMPORTANTE: Cuando el usuario pregunta por "fin de semana":
  * Si HOY es jueves ({current_day_name}): "fin de semana" = viernes, sábado, domingo (3 días: mañana + sábado + domingo)
  * Si HOY es viernes: "fin de semana" = hoy + sábado + domingo (3 días)
  * Si HOY es sábado: "fin de semana" = hoy + domingo (2 días)
  * Si HOY es domingo: "fin de semana" = solo hoy (1 día)
  * Si HOY es lunes-miércoles: "fin de semana" = próximo viernes + sábado + domingo (3 días)
- SIEMPRE incluye el viernes en "fin de semana" porque es un día común para eventos

CUANDO EL AÑO ACTUAL TIENE DATOS VACÍOS:
- Si octubre {current_year} tiene 0 eventos, REPORTA ESO (no busques en años anteriores)
- Solo sugiere revisar años anteriores DESPUÉS de reportar los datos del año actual
- Deja que el usuario pida datos históricos si los necesita

INSTRUCCIONES GENERALES:
- SIEMPRE usa las herramientas para obtener datos actualizados antes de responder
- NO inventes números o datos - solo usa información real de las herramientas
- Si una herramienta devuelve un error, informa al usuario de manera clara

ESTILO DE RESPUESTA:
- Profesional pero amigable (usa "tú" en español)
- Conciso y accionable
- Incluye números específicos y fechas cuando sea relevante
- Destaca información urgente con ⚠️
- Usa emojis moderadamente para mejor lectura (✅ ⚡ 📊 💰 📈)
- Estructura tus respuestas con:
  * Respuesta directa primero
  * Detalles específicos con bullets o números
  * Insights o recomendaciones al final

LIMITACIONES:
- No tienes acceso a información de pagos sensible
- No puedes modificar configuraciones críticas del sistema
- Refiere temas legales/tributarios complejos al administrador

RECUERDA:
- Siempre responde en español chileno
- Se directo y útil
- Prioriza información accionable
- Sugiere próximos pasos cuando sea relevante
"""

# Tool definitions for Anthropic API
TOOLS = [
    {
        "name": "get_bookings",
        "description": "Obtiene las reservas (agendamientos) del sistema con filtros opcionales. Usa esta herramienta para consultar información sobre eventos próximos, pendientes, confirmados o cancelados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "confirmed", "completed", "cancelled"],
                    "description": "Filtrar por estado de la reserva"
                },
                "date_from": {
                    "type": "string",
                    "description": "Fecha de inicio en formato YYYY-MM-DD"
                },
                "date_to": {
                    "type": "string",
                    "description": "Fecha de fin en formato YYYY-MM-DD"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (por defecto 50)",
                    "default": 50
                }
            }
        }
    },
    {
        "name": "get_events",
        "description": "Obtiene eventos completados del sistema con filtros de fecha. Usa esta herramienta para consultar eventos pasados con información financiera y de participantes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Fecha de inicio en formato YYYY-MM-DD"
                },
                "date_to": {
                    "type": "string",
                    "description": "Fecha de fin en formato YYYY-MM-DD"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (por defecto 50)",
                    "default": 50
                }
            }
        }
    },
    {
        "name": "get_inventory_status",
        "description": "Obtiene el estado actual del inventario incluyendo alertas de stock bajo. Usa esta herramienta para verificar disponibilidad de ingredientes y detectar productos que necesitan reabastecimiento.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_contacts",
        "description": "Obtiene los mensajes de contacto de clientes con filtros de prioridad y estado. Usa esta herramienta para revisar consultas pendientes o urgentes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Filtrar por prioridad del contacto"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "resolved"],
                    "description": "Filtrar por estado del contacto"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (por defecto 20)",
                    "default": 20
                }
            }
        }
    },
    {
        "name": "get_financial_summary",
        "description": "Obtiene un resumen financiero del negocio para un período específico. Incluye ingresos, costos, utilidades y márgenes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Año a consultar (ej: 2024)"
                },
                "month": {
                    "type": "integer",
                    "description": "Mes a consultar (1-12). Opcional, si no se especifica devuelve el año completo"
                }
            },
            "required": ["year"]
        }
    }
]


# ==================== TOOL IMPLEMENTATION FUNCTIONS ====================

def get_bookings_data(status=None, date_from=None, date_to=None, limit=50):
    """Get bookings from database with optional filters"""
    try:
        db = get_db()
        if not db:
            return {"error": "Database connection failed"}

        query = db.collection('bookings')

        # Apply filters
        if status:
            query = query.where('status', '==', status)

        if date_from:
            query = query.where('event_date', '>=', date_from)

        if date_to:
            query = query.where('event_date', '<=', date_to)

        # Order and limit
        query = query.order_by('event_date', direction=firestore.Query.DESCENDING).limit(int(limit))

        bookings = []
        for doc in query.stream():
            booking = doc.to_dict()
            booking['id'] = doc.id

            # Calculate day of week for the event date
            event_date_str = booking.get('event_date')
            day_of_week = None
            if event_date_str:
                try:
                    event_date_obj = datetime.strptime(event_date_str, "%Y-%m-%d")
                    day_names_spanish = {
                        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
                        4: "Viernes", 5: "Sábado", 6: "Domingo"
                    }
                    day_of_week = day_names_spanish[event_date_obj.weekday()]
                except:
                    pass

            # Clean up data for AI consumption
            cleaned_booking = {
                'id': booking.get('id'),
                'client_name': booking.get('client_name'),
                'service_type': booking.get('service_type'),
                'event_date': booking.get('event_date'),
                'day_of_week': day_of_week,  # Added day of week
                'event_time': booking.get('event_time'),
                'participants': booking.get('participants'),
                'status': booking.get('status'),
                'estimated_price': booking.get('estimated_price'),
                'location': booking.get('location', 'No especificada')
            }
            bookings.append(cleaned_booking)

        return {
            "count": len(bookings),
            "bookings": bookings
        }

    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        return {"error": f"Error al obtener reservas: {str(e)}"}


def get_events_data(date_from=None, date_to=None, limit=50):
    """Get events from database with optional filters"""
    try:
        db = get_db()
        if not db:
            return {"error": "Database connection failed"}

        query = db.collection('events')

        # Apply date filters
        if date_from:
            query = query.where('event_date', '>=', date_from)

        if date_to:
            query = query.where('event_date', '<=', date_to)

        # Order by event_date (ASCENDING when using range filters)
        # Firestore requires the first orderBy to be on the range filter field
        if date_from or date_to:
            query = query.order_by('event_date', direction=firestore.Query.ASCENDING).limit(int(limit))
        else:
            query = query.order_by('event_date', direction=firestore.Query.DESCENDING).limit(int(limit))

        events = []
        total_revenue = 0
        total_cost = 0
        total_profit = 0

        for doc in query.stream():
            event = doc.to_dict()
            event['id'] = doc.id

            # Calculate financial metrics
            final_price = event.get('final_price', 0) or 0
            event_cost = event.get('event_cost', 0) or 0
            profit = final_price - event_cost

            total_revenue += final_price
            total_cost += event_cost
            total_profit += profit

            # Clean up data for AI consumption
            cleaned_event = {
                'id': event.get('id'),
                'title': event.get('title'),
                'event_date': event.get('event_date'),
                'participants': event.get('participants'),
                'category': event.get('category'),
                'final_price': final_price,
                'event_cost': event_cost,
                'profit': profit,
                'status': event.get('status')
            }
            events.append(cleaned_event)

        # If we used range filters, results are in ascending order - reverse them
        if date_from or date_to:
            events.reverse()

        return {
            "count": len(events),
            "events": events,
            "summary": {
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "average_profit_margin": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 2)
            }
        }

    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        return {"error": f"Error al obtener eventos: {str(e)}"}


def get_inventory_status():
    """Get current inventory status with low stock alerts"""
    try:
        db = get_db()
        if not db:
            return {"error": "Database connection failed"}

        inventory_ref = db.collection('inventory')
        items = []
        low_stock_items = []

        for doc in inventory_ref.stream():
            item = doc.to_dict()
            item['id'] = doc.id

            # Check for low stock
            if item.get('needs_restock', False):
                low_stock_items.append({
                    'name': item.get('name'),
                    'current_stock': item.get('current_stock', 0),
                    'min_stock': item.get('min_stock', 0),
                    'unit': item.get('unit', 'unidades'),
                    'category': item.get('category', 'Sin categoría')
                })

            # Add to full items list
            items.append({
                'name': item.get('name'),
                'current_stock': item.get('current_stock', 0),
                'min_stock': item.get('min_stock', 0),
                'unit': item.get('unit', 'unidades'),
                'category': item.get('category', 'Sin categoría'),
                'needs_restock': item.get('needs_restock', False)
            })

        return {
            "total_items": len(items),
            "low_stock_count": len(low_stock_items),
            "low_stock_items": low_stock_items,
            "all_items": items
        }

    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        return {"error": f"Error al obtener inventario: {str(e)}"}


def get_contacts_data(priority=None, status=None, limit=20):
    """Get contact messages with optional filters"""
    try:
        db = get_db()
        if not db:
            return {"error": "Database connection failed"}

        query = db.collection('contacts')

        # Apply filters
        if priority:
            query = query.where('priority', '==', priority)

        if status:
            query = query.where('status', '==', status)

        # Order and limit
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(int(limit))

        contacts = []
        for doc in query.stream():
            contact = doc.to_dict()
            contact['id'] = doc.id

            # Clean up data for AI consumption
            cleaned_contact = {
                'id': contact.get('id'),
                'name': contact.get('name'),
                'email': contact.get('email'),
                'phone': contact.get('phone'),
                'subject': contact.get('subject'),
                'message': contact.get('message'),
                'priority': contact.get('priority', 'normal'),
                'status': contact.get('status', 'pending'),
                'created_at': contact.get('created_at')
            }
            contacts.append(cleaned_contact)

        # Count by status
        status_counts = {}
        for contact in contacts:
            status_key = contact['status']
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

        return {
            "count": len(contacts),
            "contacts": contacts,
            "status_counts": status_counts
        }

    except Exception as e:
        logger.error(f"Error fetching contacts: {str(e)}")
        return {"error": f"Error al obtener contactos: {str(e)}"}


def get_financial_summary(year, month=None):
    """
    Get financial summary for a specific period with intelligent fallback

    If the requested period has no data and it's the current year,
    automatically tries the previous year and notifies about the fallback.
    """
    try:
        db = get_db()
        if not db:
            return {"error": "Database connection failed"}

        current_year = datetime.now().year
        original_year = year
        fallback_used = False

        # Build date range
        if month:
            date_from = f"{year}-{month:02d}-01"
            # Calculate last day of month
            if month == 12:
                date_to = f"{year}-12-31"
            else:
                next_month = datetime(year, month + 1, 1)
                last_day = next_month - timedelta(days=1)
                date_to = last_day.strftime("%Y-%m-%d")
        else:
            date_from = f"{year}-01-01"
            date_to = f"{year}-12-31"

        # Get events for the period
        events_data = get_events_data(date_from=date_from, date_to=date_to, limit=1000)

        if "error" in events_data:
            return events_data

        # If no data found and it's the current year, try previous year
        if events_data["count"] == 0 and year == current_year:
            logger.info(f"No data found for {year}, trying {year-1} as fallback")
            previous_year = year - 1

            # Rebuild date range for previous year
            if month:
                date_from = f"{previous_year}-{month:02d}-01"
                if month == 12:
                    date_to = f"{previous_year}-12-31"
                else:
                    next_month = datetime(previous_year, month + 1, 1)
                    last_day = next_month - timedelta(days=1)
                    date_to = last_day.strftime("%Y-%m-%d")
            else:
                date_from = f"{previous_year}-01-01"
                date_to = f"{previous_year}-12-31"

            # Try again with previous year
            events_data = get_events_data(date_from=date_from, date_to=date_to, limit=1000)

            if "error" not in events_data and events_data["count"] > 0:
                year = previous_year
                fallback_used = True

        # Month names in Spanish for better reporting
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        result = {
            "period": f"{year}-{month:02d}" if month else str(year),
            "period_description": f"{month_names.get(month, '')} {year}" if month else f"Año {year}",
            "year": year,
            "month": month,
            "event_count": events_data["count"],
            "total_revenue": events_data["summary"]["total_revenue"],
            "total_cost": events_data["summary"]["total_cost"],
            "total_profit": events_data["summary"]["total_profit"],
            "profit_margin_percentage": events_data["summary"]["average_profit_margin"]
        }

        # Add fallback information if used
        if fallback_used:
            result["fallback_used"] = True
            result["original_year_requested"] = original_year
            result["note"] = f"No se encontraron datos para {month_names.get(month, '')} {original_year}. Mostrando datos de {month_names.get(month, '')} {year} en su lugar."

        return result

    except Exception as e:
        logger.error(f"Error getting financial summary: {str(e)}")
        return {"error": f"Error al obtener resumen financiero: {str(e)}"}


# ==================== TOOL EXECUTION ====================

def execute_tool(tool_name, tool_input):
    """Execute a tool and return the result"""
    try:
        if tool_name == "get_bookings":
            return get_bookings_data(
                status=tool_input.get('status'),
                date_from=tool_input.get('date_from'),
                date_to=tool_input.get('date_to'),
                limit=tool_input.get('limit', 50)
            )

        elif tool_name == "get_events":
            return get_events_data(
                date_from=tool_input.get('date_from'),
                date_to=tool_input.get('date_to'),
                limit=tool_input.get('limit', 50)
            )

        elif tool_name == "get_inventory_status":
            return get_inventory_status()

        elif tool_name == "get_contacts":
            return get_contacts_data(
                priority=tool_input.get('priority'),
                status=tool_input.get('status'),
                limit=tool_input.get('limit', 20)
            )

        elif tool_name == "get_financial_summary":
            return get_financial_summary(
                year=tool_input.get('year'),
                month=tool_input.get('month')
            )

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        return {"error": f"Error al ejecutar herramienta: {str(e)}"}


# ==================== MAIN ENDPOINT ====================

@ai_chat_bp.route('/', methods=['POST'])
def chat():
    """
    Main AI chat endpoint with tool use support

    Request body:
    {
        "messages": [
            {"role": "user", "content": "¿Qué eventos tengo hoy?"}
        ]
    }

    Response:
    {
        "response": "...",
        "usage": {...},
        "tools_used": [...]
    }
    """
    try:
        # Validate Anthropic client
        if not anthropic_client:
            logger.error("Anthropic API key not configured")
            return jsonify({
                "error": "AI service not configured. Please add ANTHROPIC_API_KEY to environment variables."
            }), 500

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        # Validate message format
        for msg in messages:
            if 'role' not in msg or 'content' not in msg:
                return jsonify({"error": "Invalid message format"}), 400

        # Prepare system prompt with current date and time context
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = str(now.year)
        last_year = str(now.year - 1)
        current_month = str(now.month)

        # Month names in Spanish
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        current_month_name = month_names[now.month]

        # Day names in Spanish (0=Monday, 6=Sunday)
        day_names = {
            0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
            4: "Viernes", 5: "Sábado", 6: "Domingo"
        }
        current_day_name = day_names[now.weekday()]

        # Last month
        last_month = now.month - 1 if now.month > 1 else 12
        last_month_name = month_names[last_month]

        # Replace all placeholders (must replace "current_year - 1" before "current_year")
        system_prompt = SYSTEM_PROMPT.replace("{current_year - 1}", last_year)
        system_prompt = system_prompt.replace("{current_date}", current_date)
        system_prompt = system_prompt.replace("{current_day_name}", current_day_name)
        system_prompt = system_prompt.replace("{current_year}", current_year)
        system_prompt = system_prompt.replace("{current_month}", current_month)
        system_prompt = system_prompt.replace("{current_month_name}", current_month_name)
        system_prompt = system_prompt.replace("{last_month_name}", last_month_name)

        # Initial API call with tools
        logger.info(f"Sending request to Claude API with {len(messages)} messages and {len(TOOLS)} tools")

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            temperature=0.7,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )

        # Track total usage
        total_input_tokens = response.usage.input_tokens
        total_output_tokens = response.usage.output_tokens
        tools_used = []

        # Handle tool use loop
        while response.stop_reason == "tool_use":
            # Extract tool uses
            tool_results = []

            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
                    tools_used.append({"name": tool_name, "input": tool_input})

                    # Execute the tool
                    tool_result = execute_tool(tool_name, tool_input)

                    # Add result to messages
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Continue conversation with tool results
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )

            # Accumulate usage
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        # Extract final response text
        response_text = ""
        for content_block in response.content:
            if content_block.type == "text":
                response_text += content_block.text

        # Log final usage
        logger.info(f"Claude API complete - Total input tokens: {total_input_tokens}, Total output tokens: {total_output_tokens}, Tools used: {len(tools_used)}")

        return jsonify({
            "response": response_text,
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens
            },
            "tools_used": tools_used,
            "model": response.model,
            "stop_reason": response.stop_reason
        }), 200

    except Exception as e:
        logger.error(f"Error in AI chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "error": "An error occurred while processing your request",
            "details": str(e)
        }), 500


@ai_chat_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AI service"""
    try:
        api_configured = bool(ANTHROPIC_API_KEY and anthropic_client)

        return jsonify({
            "status": "ok" if api_configured else "error",
            "api_configured": api_configured,
            "tools_available": len(TOOLS),
            "message": "AI service is ready" if api_configured else "ANTHROPIC_API_KEY not configured"
        }), 200 if api_configured else 503

    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
