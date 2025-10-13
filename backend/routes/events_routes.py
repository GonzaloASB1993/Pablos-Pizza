"""Events Routes Blueprint"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from firebase_admin import firestore
from utils.pagination import paginate_query, create_pagination_response

events_bp = Blueprint('events', __name__, url_prefix='/api/events')

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
