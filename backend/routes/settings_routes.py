"""Settings Routes Blueprint - Admin configuration endpoints"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db

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
