"""Validation of PUBLIC (token-less) form input. Raises ValueError with a user-facing message."""
import re

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

CONTACT_LIMITS = {'name': 100, 'email': 120, 'phone': 20, 'subject': 200, 'message': 1000}
CONTACT_LABELS = {'name': 'el nombre', 'email': 'el email', 'phone': 'el teléfono', 'subject': 'el asunto', 'message': 'el mensaje'}
CONTACT_REQUIRED = ('name', 'email', 'subject', 'message')


def sanitize_public_contact(data):
    """Whitelist of the contact form. `priority` is NOT accepted from the client (always 'normal'; the admin changes it)."""
    if not isinstance(data, dict) or not data:
        raise ValueError('No data provided')
    clean = {}
    for key, limit in CONTACT_LIMITS.items():
        value = data.get(key)
        label = CONTACT_LABELS[key]
        if value is None or value == '':
            if key in CONTACT_REQUIRED:
                raise ValueError(f'Falta {label}')
            clean[key] = None
            continue
        if not isinstance(value, str):
            raise ValueError(f'{label} no es válido')
        value = value.strip()
        if not value and key in CONTACT_REQUIRED:
            raise ValueError(f'Falta {label}')
        if len(value) > limit:
            raise ValueError(f'{label} es demasiado largo (máximo {limit} caracteres)')
        clean[key] = value or None
    if not EMAIL_RE.match(clean['email']):
        raise ValueError('El email no es válido')
    clean['priority'] = 'normal'
    return clean
