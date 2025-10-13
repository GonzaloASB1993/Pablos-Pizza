"""Gallery Routes Blueprint"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from firebase_admin import firestore
from utils.pagination import paginate_query, create_pagination_response

gallery_bp = Blueprint('gallery', __name__, url_prefix='/api/gallery')

@gallery_bp.route('/', methods=['GET'])
def get_gallery_images():
    try:
        eid,page,limit = request.args.get('event_id'),int(request.args.get('page',1)),int(request.args.get('limit',30))
        db = get_db()
        ir = db.collection("gallery").where("event_id","==",eid).order_by("uploaded_at",direction=firestore.Query.DESCENDING) if eid else db.collection("gallery").order_by("uploaded_at",direction=firestore.Query.DESCENDING)
        pi,hm,ts = paginate_query(ir,page,limit)
        gi = [{'id':i.get('id'),'title':i.get('title','Imagen'),'url':i.get('url',''),'is_published':i.get('is_published',False),'uploaded_at':i.get('uploaded_at'),'event_id':i.get('event_id')} for i in pi]
        return jsonify(create_pagination_response(gi,page,limit,hm,ts)), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@gallery_bp.route('/event/<event_id>', methods=['GET','OPTIONS'])
def get_gallery_by_event(event_id):
    if request.method == 'OPTIONS': return jsonify({'status':'OK'}), 200
    try:
        db = get_db()
        if not db: return jsonify({"error":"DB failed"}), 500
        ir = db.collection("gallery").where("event_id","==",event_id)
        imgs = []
        for doc in ir.stream():
            i = doc.to_dict()
            i['id'] = doc.id
            imgs.append(i)
        return jsonify(imgs), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@gallery_bp.route('/<photo_id>/publish', methods=['PUT','OPTIONS'])
def publish_gallery_photo(photo_id):
    if request.method == 'OPTIONS': return jsonify({'status':'OK'}), 200
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        dr = get_db().collection("gallery").document(photo_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.update({'is_published':data.get('is_published',False),'updated_at':datetime.now()})
        up = dr.get().to_dict()
        up['id'] = photo_id
        return jsonify(up), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@gallery_bp.route('/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    try:
        dr = get_db().collection("gallery").document(photo_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.delete()
        return jsonify({"message":"Deleted"}), 200
    except Exception as e: return jsonify({"error":str(e)}), 500
