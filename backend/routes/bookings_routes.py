"""Bookings Routes Blueprint"""
from flask import Blueprint, request, jsonify
import uuid, os, asyncio
from datetime import datetime
from database import get_db
from firebase_admin import firestore
from utils.pagination import paginate_query, create_pagination_response
from services.whatsapp_service import send_whatsapp_template

bookings_bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')

try:
    from config import PricingConfig
except:
    class PricingConfig:
        PIZZEROS_MINIMUM = 135000
        PIZZA_PARTY_BASE_PRICE = 11990
        @staticmethod
        def get_pizzeros_price(p): return 13500 if p<=10 else (10500 if p<=14 else (9500 if p<=19 else 9000))
        @staticmethod
        def get_pizza_party_price(pizzas): return round(PricingConfig.PIZZA_PARTY_BASE_PRICE*0.9) if pizzas>=20 else PricingConfig.PIZZA_PARTY_BASE_PRICE

def calculate_estimated_price(service_types, pizzeros_participants=0, party_participants=0, participants=0, pizza_quantity=0):
    total = 0
    for s in [x.strip() for x in service_types.split(',') if x.strip()]:
        if s in ["workshop","pizzeros"]:
            sp = pizzeros_participants or participants
            if sp > 0:
                total += max(PricingConfig.PIZZEROS_MINIMUM if sp<=10 else 0, sp*PricingConfig.get_pizzeros_price(sp))
        elif s in ["pizza_party","party"]:
            pz = pizza_quantity or party_participants or participants
            if pz > 0: total += pz*PricingConfig.get_pizza_party_price(pz)
    return round(total, 2)

@bookings_bp.route('/', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No data"}), 400
        for f in ['service_type','participants']:
            if f not in data: return jsonify({"error": f"Missing {f}"}), 400
        bid = str(uuid.uuid4())
        ep = calculate_estimated_price(data.get('service_type',''),data.get('pizzeros_participants',0),data.get('party_participants',0),data.get('participants',0),data.get('pizza_quantity',0))
        bd = {"id":bid,**data,"status":"pending","created_at":datetime.now(),"estimated_price":ep}
        get_db().collection("bookings").document(bid).set(bd)
        try:
            for ph in [os.getenv('ADMIN_WHATSAPP_NUMBER','+56998960858'),os.getenv('PARTNER_WHATSAPP_NUMBER','+56998960858')]:
                asyncio.run(send_whatsapp_template(ph,'new_booking',bd))
        except: pass
        return jsonify(bd), 201
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/', methods=['GET'])
def get_bookings():
    try:
        db = get_db()
        if not db: return jsonify({'error':'DB failed'}), 500
        page,limit = int(request.args.get('page',1)),int(request.args.get('limit',20))
        br = db.collection("bookings").order_by('created_at',direction=firestore.Query.DESCENDING)
        pb,hm,ts = paginate_query(br,page,limit)
        for b in pb:
            try:
                fin = (b or {}).get('financials') or {}
                es,rs,oe = float(fin.get('estimated_supply_cost',0) or 0),float(fin.get('supply_cost',0) or 0),float(fin.get('other_expenses',0) or 0)
                cs,tc = (rs if rs>0 else es),(rs if rs>0 else es)+oe
                b['computed_costs'] = {'estimated_supply_cost':es,'real_supply_cost':rs,'other_expenses_total':oe,'current_supply_cost':cs,'total_cost':tc,'source':'real' if rs>0 else 'estimated'}
            except: pass
        return jsonify(create_pagination_response(pb,page,limit,hm,ts)), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        db = get_db()
        doc = db.collection("bookings").document(booking_id).get()
        if doc.exists:
            b = doc.to_dict()
            b['id'] = doc.id
            return jsonify(b), 200
        return jsonify({"error":"Not found"}), 404
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    try:
        data = request.get_json()
        if not data: return jsonify({"error":"No data"}), 400
        db = get_db()
        dr = db.collection("bookings").document(booking_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.update(data)
        ub = dr.get().to_dict()
        ub['id'] = booking_id
        return jsonify(ub), 200
    except Exception as e: return jsonify({"error":str(e)}), 500

@bookings_bp.route('/<booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    try:
        db = get_db()
        dr = db.collection("bookings").document(booking_id)
        if not dr.get().exists: return jsonify({"error":"Not found"}), 404
        dr.delete()
        return jsonify({"message":"Deleted"}), 200
    except Exception as e: return jsonify({"error":str(e)}), 500
