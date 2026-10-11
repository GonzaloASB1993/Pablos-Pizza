"""Create (and optionally submit for approval) the WhatsApp template of the daily digest, through Twilio's Content API.

    python scripts/create_whatsapp_template.py --dry-run          # prints the request, touches nothing
    python scripts/create_whatsapp_template.py                    # creates the content, prints its SID (HX...)
    python scripts/create_whatsapp_template.py --approve          # ... and asks WhatsApp to approve it (UTILITY)
    python scripts/create_whatsapp_template.py --status HXxxxx    # approval state of an existing content

Credentials come ONLY from the environment (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN); they are never printed.
Afterwards set TEMPLATE_PABLITO_DIGEST_SID to the printed SID (see docs/WHATSAPP_ASISTENTE.md).
The twilio SDK in use (8.10) has no `create` for Content, hence plain `requests`.
"""
import argparse
import json
import os
import sys

CONTENT_URL = 'https://content.twilio.com/v1/Content'
TEMPLATE_NAME = 'pablito_resumen_diario'

TEMPLATE_BODY = ("Hola, soy Pablito de Pablo's Pizza 🍕 Tienes {{1}} aviso(s) nuevo(s) de la operación: {{2}}. "
                 "Toca Ver para el detalle.")


def content_payload():
    """Body of POST /v1/Content. The sample values are what the reviewers at WhatsApp see."""
    return {
        'friendly_name': TEMPLATE_NAME,
        'language': 'es',
        'variables': {'1': '2', '2': 'stock bajo de harina y 1 reserva por confirmar'},
        'types': {'twilio/quick-reply': {
            'body': TEMPLATE_BODY,
            'actions': [{'title': 'Ver', 'id': 'digest_ver'}],
        }},
    }


def approval_payload():
    return {'name': TEMPLATE_NAME, 'category': 'UTILITY'}


def _credentials(env):
    sid, token = env.get('TWILIO_ACCOUNT_SID', ''), env.get('TWILIO_AUTH_TOKEN', '')
    if not sid or not token:
        raise SystemExit('Faltan TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN en el entorno.')
    return sid, token


def _check(response, what):
    if not response.ok:
        # the body explains the rejection; it never contains our credentials
        raise SystemExit(f'{what} falló (HTTP {response.status_code}): {response.text[:500]}')
    return response.json()


def main(argv=None, post=None, get=None, env=None, out=print):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dry-run', action='store_true', help='show the requests without sending them')
    parser.add_argument('--approve', action='store_true', help='also submit the content for WhatsApp approval')
    parser.add_argument('--status', metavar='HX_SID', help='only check the approval status of this content')
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    if args.dry_run:
        out(f'POST {CONTENT_URL}')
        out(json.dumps(content_payload(), ensure_ascii=False, indent=2))
        if args.approve:
            out(f'POST {CONTENT_URL}/<HX sid>/ApprovalRequests/whatsapp')
            out(json.dumps(approval_payload(), ensure_ascii=False, indent=2))
        out('(dry run: nothing was sent)')
        return 0

    if post is None or get is None:
        import requests
        post, get = post or requests.post, get or requests.get
    auth = _credentials(env)

    if args.status:
        data = _check(get(f'{CONTENT_URL}/{args.status}/ApprovalRequests', auth=auth, timeout=20), 'La consulta')
        out(json.dumps(data.get('whatsapp', data), ensure_ascii=False, indent=2))
        return 0

    created = _check(post(CONTENT_URL, json=content_payload(), auth=auth, timeout=20), 'La creación')
    sid = created.get('sid')
    out(f'Plantilla creada: {sid}')
    if args.approve and sid:
        approval = _check(post(f'{CONTENT_URL}/{sid}/ApprovalRequests/whatsapp', json=approval_payload(),
                               auth=auth, timeout=20), 'La solicitud de aprobación')
        out(f"Aprobación solicitada: {approval.get('status', 'enviada')}")
    out(f'Siguiente paso: TEMPLATE_PABLITO_DIGEST_SID={sid}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
