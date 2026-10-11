"""Helpers shared by the undo tests: seed the fake Firestore and run real actions through propose -> confirm"""
from datetime import datetime

from services import pending_actions_service as pas

USER = {'uid': 'whatsapp:+56911111111', 'email': 'whatsapp:+56911111111'}
PANEL_USER = {'uid': 'uid-admin', 'email': 'admin@pablospizza.cl'}


def no_audit(*args, **kwargs):
    return None


def seed_item(db, item_id='flour', name='Harina', stock=10.0, avg=1000.0, unit='kg', min_stock=2.0, **extra):
    item = {'id': item_id, 'name': name, 'category': 'Secos', 'unit': unit, 'current_stock': stock,
            'min_stock': min_stock, 'max_stock': 50.0, 'cost_per_unit': avg, 'weighted_avg_cost': avg,
            'total_value': stock * avg, 'needs_restock': stock <= min_stock, 'supplier': '', 'notes': '',
            'last_updated': datetime(2026, 1, 1), **extra}
    db.collection('inventory').document(item_id).set(item)
    return item


def seed_booking(db, booking_id='b1', status='confirmed', **extra):
    booking = {'id': booking_id, 'client_name': 'Ana Pérez', 'event_date': '2026-11-20T12:00:00', 'status': status,
               'participants': 12, 'service_type': 'workshop', **extra}
    db.collection('bookings').document(booking_id).set(booking)
    return booking


def item(db, item_id='flour'):
    return db.collection('inventory').document(item_id).get().to_dict()


def doc(db, collection, doc_id):
    snapshot = db.collection(collection).document(doc_id).get()
    return snapshot.to_dict() if snapshot.exists else None


def count(db, collection):
    return len(db.store.get(collection, {}))


def confirmed(db, action_type, payload, summary='Resumen', user=USER, context=None):
    """Create a proposal and confirm it exactly like a person answering SI would"""
    action = pas.create(db, action_type, payload, summary, user, context=context)
    pas.confirm(db, action['id'], user, audit=no_audit)
    return pas.get(db, action['id'])


def receipt_payload(*lines, supplier='Líder', folio='123'):
    return {'supplier': supplier, 'date': '2026-10-10', 'folio': folio, 'document_type': 'boleta', 'lines': list(lines)}


def existing_line(item_id='flour', quantity=5, amount=6000, description='Harina'):
    return {'description': description, 'classification': 'existing', 'item_id': item_id, 'quantity': quantity,
            'amount': amount}


def new_line(name='Queso', quantity=2, amount=10000, unit='kg'):
    return {'description': name, 'classification': 'new', 'name': name, 'category': 'Lácteos', 'unit': unit,
            'quantity': quantity, 'amount': amount}


def expense_line(description='Bencina', amount=8000):
    return {'description': description, 'classification': 'expense', 'amount': amount}
