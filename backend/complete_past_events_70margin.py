"""Script to complete all past/today events with a 70% profit margin.

The closing logic lives in services/auto_close_service.py (also used by the
scheduler's automatic close). This script is kept for manual/backlog runs.

Usage:
    python complete_past_events_70margin.py [--dry-run]

    --dry-run   Preview what would be updated without making any changes.
"""
import sys
import argparse
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv('.env')

CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from database import get_db
from services.auto_close_service import parse_event_date, close_booking, AUTO_CLOSE_MARGIN

TODAY = date.today().isoformat()


def complete_past_events(dry_run: bool = False):
    print(f"{'[DRY RUN] ' if dry_run else ''}Cerrando eventos pasados con margen del {AUTO_CLOSE_MARGIN:.0%}")
    print(f"Fecha de corte: {TODAY}")
    print("=" * 60)

    db = get_db()

    updated = 0
    skipped_already_done = 0
    skipped_future = 0
    skipped_no_price = 0
    errors = 0

    for doc in db.collection("bookings").stream():
        data = doc.to_dict()
        data['id'] = doc.id
        client = data.get('client_name', 'Sin nombre')

        event_date_str = parse_event_date(data.get('event_date', ''))

        if not event_date_str or event_date_str > TODAY:
            skipped_future += 1
            continue

        if data.get('status', '') not in ('pending', 'confirmed'):
            skipped_already_done += 1
            continue

        estimated_price = float(data.get('estimated_price') or 0)
        if estimated_price <= 0:
            print(f"  [SKIP] {doc.id} ({client} - {event_date_str}): sin precio estimado")
            skipped_no_price += 1
            continue

        event_cost = round(estimated_price * (1 - AUTO_CLOSE_MARGIN), 2)
        profit = round(estimated_price * AUTO_CLOSE_MARGIN, 2)

        print(f"  {'[DRY] ' if dry_run else 'OK'} {doc.id} | {client} | {event_date_str} | "
              f"Precio: ${estimated_price:.2f} | Costo: ${event_cost:.2f} | "
              f"Ganancia: ${profit:.2f} ({AUTO_CLOSE_MARGIN:.0%})")

        if not dry_run:
            try:
                close_booking(db, data)
                updated += 1
            except Exception as e:
                print(f"    ❌ Error en {doc.id}: {e}")
                errors += 1
        else:
            updated += 1

    print()
    print("=" * 60)
    print(f"Resultado{'  [DRY RUN - sin cambios reales]' if dry_run else ''}:")
    print(f"  [OK] Eventos cerrados:              {updated}")
    print(f"  [--] Ya completados/cancelados:    {skipped_already_done}")
    print(f"  [--] Eventos futuros (omitidos):   {skipped_future}")
    print(f"  [--] Sin precio estimado (omitidos):{skipped_no_price}")
    if errors:
        print(f"  [ERR] Errores:                    {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cerrar eventos pasados con margen 70%")
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo muestra qué se actualizaría, sin modificar la base de datos')
    args = parser.parse_args()

    complete_past_events(dry_run=args.dry_run)
