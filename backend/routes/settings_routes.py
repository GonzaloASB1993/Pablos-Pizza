"""Settings Routes Blueprint - Admin configuration endpoints"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
from services.booking_service import read_recargo_nocturno_setting
from utils.auth import require_admin

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


@settings_bp.route('/comunas-lejanas', methods=['GET'])
def get_comunas_lejanas():
    """Get current distant communes configuration (public - used by booking form)"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        doc = db.collection('settings').document('comunas_lejanas').get()

        if doc.exists:
            data = doc.to_dict()
            return jsonify({
                'comunas': data.get('comunas', []),
                'cargo': data.get('cargo', 20000),
                'updated_at': data.get('updated_at').isoformat() if data.get('updated_at') else None
            }), 200

        return jsonify({
            'comunas': ['Quilicura', 'Lampa', 'Colina', 'Huechuraba'],
            'cargo': 20000,
            'updated_at': None
        }), 200

    except Exception as e:
        print(f"Error getting comunas lejanas config: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/comunas-lejanas', methods=['PUT'])
@require_admin
def update_comunas_lejanas():
    """Update distant communes configuration (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        comunas = data.get('comunas')
        cargo = data.get('cargo')

        if comunas is None or not isinstance(comunas, list):
            return jsonify({'error': 'comunas must be a list'}), 400

        if cargo is None or not isinstance(cargo, (int, float)) or cargo < 0:
            return jsonify({'error': 'cargo must be a non-negative number'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        settings_data = {
            'comunas': comunas,
            'cargo': int(cargo),
            'updated_at': datetime.now()
        }

        db.collection('settings').document('comunas_lejanas').set(settings_data)

        return jsonify({
            'message': 'Comunas lejanas updated successfully',
            'comunas': comunas,
            'cargo': int(cargo),
            'updated_at': settings_data['updated_at'].isoformat()
        }), 200

    except Exception as e:
        print(f"Error updating comunas lejanas config: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/recargo-nocturno', methods=['GET'])
def get_recargo_nocturno():
    """Get the night surcharge percentage (public - used by booking form)"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        doc = db.collection('settings').document('recargo_nocturno').get()
        updated_at = (doc.to_dict() or {}).get('updated_at') if doc.exists else None

        return jsonify({
            'porcentaje': read_recargo_nocturno_setting(db),
            'updated_at': updated_at.isoformat() if updated_at else None
        }), 200

    except Exception as e:
        print(f"Error getting recargo nocturno config: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/recargo-nocturno', methods=['PUT'])
@require_admin
def update_recargo_nocturno():
    """Update the night surcharge percentage, integer 0-100 (0 turns it off) (admin only)"""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        porcentaje = data.get('porcentaje')
        if isinstance(porcentaje, bool) or not isinstance(porcentaje, int) or not 0 <= porcentaje <= 100:
            return jsonify({'error': 'porcentaje must be an integer between 0 and 100'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500

        settings_data = {
            'porcentaje': porcentaje,
            'updated_at': datetime.now()
        }

        db.collection('settings').document('recargo_nocturno').set(settings_data)

        return jsonify({
            'message': 'Recargo nocturno updated successfully',
            'porcentaje': porcentaje,
            'updated_at': settings_data['updated_at'].isoformat()
        }), 200

    except Exception as e:
        print(f"Error updating recargo nocturno config: {e}")
        return jsonify({'error': str(e)}), 500
