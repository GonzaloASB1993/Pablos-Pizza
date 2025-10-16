"""Events Routes Blueprint"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from firebase_admin import firestore
from utils.pagination import paginate_query, create_pagination_response
import os

events_bp = Blueprint('events', __name__, url_prefix='/api/events')

def generate_basic_description(title, service_type, participants, pizzeros_participants, party_guests, location):
    """Generate a basic description when AI is not available"""
    if 'workshop' in service_type or 'pizzeros' in service_type:
        if party_guests > 0:
            return f"Celebración combinada de Pizzeros en Acción y Pizza Party en {location}. {pizzeros_participants} niños participaron del taller donde aprendieron a crear sus propias pizzas, seguido de una pizza party para {party_guests} invitados. Una experiencia completa de diversión y aprendizaje culinario."
        else:
            return f"Taller Pizzeros en Acción en {location} donde {pizzeros_participants} niños aprendieron a preparar pizzas artesanales. Una experiencia educativa y divertida."
    else:
        return f"Pizza Party en {location} con pizzas artesanales recién horneadas para {party_guests} invitados. Celebración llena de sabor y alegría."

@events_bp.route('/', methods=['GET'])
def get_events():
    try:
        db,page,limit = get_db(),int(request.args.get('page',1)),int(request.args.get('limit',20))
        er = db.collection("events").order_by("created_at",direction=firestore.Query.DESCENDING)
        pe,hm,ts = paginate_query(er,page,limit)
        return jsonify(create_pagination_response(pe,page,limit,hm,ts)), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@events_bp.route('/', methods=['POST'])
def create_event():
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        for f in ['title','event_date']:
            if f not in data: return jsonify({"error":f"Missing {f}"}), 400
        ed = {'title':data['title'],'description':data.get('description',''),'event_date':data['event_date'],'participants':data.get('participants',0),'final_price':data.get('final_price',0),'event_cost':data.get('event_cost',0),'profit':data.get('profit',0),'notes':data.get('notes',''),'status':data.get('status','pending'),'booking_id':data.get('booking_id'),'created_at':datetime.now(),'updated_at':datetime.now(),'is_published':data.get('is_published',False),'is_featured':data.get('is_featured',False),'category':data.get('category','workshop'),'satisfaction':data.get('satisfaction',5),'highlight':data.get('highlight','Experiencia única'),'age_group':data.get('age_group','Todas las edades')}
        dr = get_db().collection("events").add(ed)
        eid = dr[1].id
        ed['id'] = eid
        return jsonify(ed), 201
    except Exception as e: return jsonify({"error":str(e)}), 500

@events_bp.route('/<event_id>', methods=['GET'])
def get_event(event_id):
    try:
        doc = get_db().collection("events").document(event_id).get()
        if doc.exists:
            e = doc.to_dict()
            e['id'] = doc.id
            return jsonify(e), 200
        return jsonify({"error":"Not found"}), 404
    except Exception as e: return jsonify({"error":str(e)}), 500

@events_bp.route('/<event_id>', methods=['PUT'])
def update_event(event_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        dr = get_db().collection("events").document(event_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        ud = {f:data[f] for f in ['title','description','notes','photos','final_price','event_cost','profit'] if f in data}
        ud['updated_at'] = datetime.now()
        dr.update(ud)
        ue = dr.get().to_dict()
        ue['id'] = event_id
        return jsonify(ue), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@events_bp.route('/<event_id>/publish', methods=['PUT','OPTIONS'])
def publish_event(event_id):
    if request.method == 'OPTIONS': return jsonify({'status':'OK'}), 200
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        dr = get_db().collection("events").document(event_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        ud = {'is_published':data.get('is_published',False),'updated_at':datetime.now()}
        if 'is_featured' in data: ud['is_featured'] = data['is_featured']
        dr.update(ud)
        ue = dr.get().to_dict()
        ue['id'] = event_id
        return jsonify(ue), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@events_bp.route('/generate-description', methods=['POST','OPTIONS'])
def generate_description():
    """Generate AI description for event using Claude API"""
    if request.method == 'OPTIONS': return jsonify({'status':'OK'}), 200
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400

        # Extract event details
        title = data.get('title', '')
        service_type = data.get('service_type', '')
        participants = data.get('participants', 0)
        pizzeros_participants = data.get('pizzeros_participants', 0)
        party_guests = data.get('party_guests', 0)
        location = data.get('location', '')
        notes = data.get('notes', '')

        # Build prompt for Claude
        prompt = f"""Genera una descripción en PASADO sobre este evento de Pablo's Pizza que ya ocurrió:

Título: {title}
Tipo de servicio: {service_type}
Participantes totales: {participants}
Niños en taller: {pizzeros_participants}
Invitados en pizza party: {party_guests}
Ubicación: {location}
Notas adicionales: {notes}

La descripción debe:
- Estar escrita completamente en PASADO (ej: "Estuvimos en...", "fue", "tuvimos", "disfrutaron")
- Ser PRECISA y CONCISA (máximo 2-3 oraciones, 100 palabras)
- Iniciar mencionando que estuvimos en el evento del cliente/nombre
- Mencionar los números exactos de participantes
- Sonar profesional pero cercana y entusiasta
- NO usar emojis
- Destacar brevemente la experiencia y las pizzas artesanales

Responde SOLO con la descripción en pasado, sin introducción ni explicaciones."""

        try:
            import anthropic

            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 503

            client = anthropic.Anthropic(api_key=api_key)

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            description = message.content[0].text.strip()
            return jsonify({"description": description}), 200

        except ImportError:
            # Fallback si no está instalado anthropic
            return jsonify({"error": "AI service not available. Please install anthropic package."}), 503
        except anthropic.APIError as e:
            # Handle API errors (like insufficient credits)
            if "credit balance" in str(e).lower():
                # Generate a basic description as fallback
                basic_desc = generate_basic_description(title, service_type, participants, pizzeros_participants, party_guests, location)
                return jsonify({
                    "description": basic_desc,
                    "warning": "IA no disponible (sin créditos). Descripción básica generada."
                }), 200
            print(f"Anthropic API Error: {e}")
            return jsonify({"error": f"AI service error: {str(e)}"}), 503
        except Exception as e:
            print(f"Error generating AI description: {e}")
            return jsonify({"error": f"Failed to generate description: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error":str(e)}), 500
