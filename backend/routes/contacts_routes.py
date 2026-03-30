"""Contacts Routes Blueprint"""
from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
from database import get_db
from firebase_admin import firestore

contacts_bp = Blueprint('contacts', __name__, url_prefix='/api/contacts')

@contacts_bp.route('/', methods=['POST'])
def create_contact():
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        for f in ['name','email','message']:
            if f not in data: return jsonify({"error":f"Missing {f}"}), 400
        cid = str(uuid.uuid4())
        cd = {"id":cid,**data,"status":"pending","created_at":datetime.now()}
        get_db().collection("contacts").document(cid).set(cd)
        return jsonify(cd), 201
    except Exception as e: return jsonify({"error":str(e)}), 500

@contacts_bp.route('/', methods=['GET'])
def get_contacts():
    try:
        db = get_db()
        status_filter = request.args.get('status')
        query = db.collection("contacts").order_by("created_at", direction=firestore.Query.DESCENDING)
        docs = query.stream()
        contacts = []
        for doc in docs:
            c = doc.to_dict()
            c['id'] = doc.id
            if status_filter and c.get('status') != status_filter:
                continue
            contacts.append(c)
        return jsonify(contacts), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@contacts_bp.route('/<contact_id>', methods=['GET'])
def get_contact(contact_id):
    try:
        doc = get_db().collection("contacts").document(contact_id).get()
        if doc.exists:
            c = doc.to_dict()
            c['id'] = doc.id
            return jsonify(c), 200
        return jsonify({"error":"Not found"}), 404
    except Exception as e: return jsonify({"error":str(e)}), 500

@contacts_bp.route('/<contact_id>', methods=['PUT'])
def update_contact(contact_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        dr = get_db().collection("contacts").document(contact_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.update(data)
        uc = dr.get().to_dict()
        uc['id'] = contact_id
        return jsonify(uc), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@contacts_bp.route('/<contact_id>/respond', methods=['POST'])
def respond_to_contact(contact_id):
    try:
        data = request.get_json()
        if not data or 'response_message' not in data:
            return jsonify({"error":"response_message required"}), 400
        dr = get_db().collection("contacts").document(contact_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.update({
            'status': 'resolved',
            'response_message': data['response_message'],
            'response_method': data.get('response_method', 'whatsapp'),
            'notes': data.get('notes', ''),
            'response_sent': True,
            'responded_at': datetime.now()
        })
        uc = dr.get().to_dict()
        uc['id'] = contact_id
        return jsonify(uc), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@contacts_bp.route('/<contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    try:
        dr = get_db().collection("contacts").document(contact_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.delete()
        return jsonify({"message":"Deleted"}), 200
    except Exception as e: return jsonify({"error":str(e)}), 500
