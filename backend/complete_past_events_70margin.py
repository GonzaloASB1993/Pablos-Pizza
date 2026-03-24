"""Script to complete all past/today events with a 70% profit margin.

Usage:
    python complete_past_events_70margin.py [--dry-run]

    --dry-run   Preview what would be updated without making any changes.
"""
import os
import sys
import uuid
import argparse
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv('.env')

CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from database import get_db

MARGIN = 0.70  # 70% profit margin → cost = 30% of price
TODAY = date.today().isoformat()  # e.g. "2026-03-23"


def parse_event_date(raw) -> str | None:
    """Return ISO date string (YYYY-MM-DD) or None if unparseable."""
    if not raw:
        return None
    if hasattr(raw, 'strftime'):          # datetime / date object
        return raw.strftime('%Y-%m-%d')
    s = str(raw).strip()
    # Accept YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(s[:10], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def build_event(booking_data: dict, event_cost: float, profit: float) -> dict:
    """Build the Firestore event document from booking + financial data."""
    booking_id = booking_data.get('id')
    estimated_price = float(booking_data.get('estimated_price') or 0)
    event_date = parse_event_date(booking_data.get('event_date')) or datetime.now().strftime('%Y-%m-%d')

    service_types = booking_data.get('service_type', '')
    services = [s.strip() for s in service_types.split(',') if s.strip()]

    if len(services) > 1:
        service_name = 'Pizza Party + Pizzeros en Acción'
    elif any(k in services for k in ('workshop', 'pizzeros')):
        service_name = 'Pizzeros en Acción'
    else:
        service_name = 'Pizza Party'

    client_name = booking_data.get('client_name', 'Cliente')
    location = booking_data.get('location', 'nuestra ubicación')
    pizzeros_count = booking_data.get('pizzeros_participants', 0)
    party_guests = booking_data.get('party_guests', booking_data.get('party_participants', 0))
    pizza_qty = booking_data.get('pizza_quantity', 10)

    if len(services) > 1:
        description = (f"Evento de {service_name} con {pizzeros_count} "
                       f"niños en el taller y {party_guests} invitados en la pizza party.")
    elif any(k in services for k in ('workshop', 'pizzeros')):
        description = f"Taller Pizzeros en Acción con {pizzeros_count} participantes."
    else:
        description = f"Pizza Party con {pizza_qty} pizzas para {party_guests} invitados."

    profit_margin_pct = round((profit / estimated_price * 100), 2) if estimated_price > 0 else 0

    return {
        "id": str(uuid.uuid4()),
        "booking_id": booking_id,
        "title": f"{service_name} - {client_name}",
        "description": description,
        "event_date": event_date,
        "participants": booking_data.get('participants', 0),
        "final_price": estimated_price,
        "event_cost": event_cost,
        "profit": profit,
        "notes": f"Evento en {location}. Cliente: {client_name}. Cerrado automáticamente con margen 70%.",
        "status": "completed",
        "created_at": datetime.now(),
        "is_published": False,
        "is_featured": False,
        "category": "workshop" if any(k in services for k in ('workshop', 'pizzeros')) else "party",
        "satisfaction": 5,
        "highlight": service_name,
        "age_group": "Niños y familias",
        "source": "auto_complete_70margin",
        "financials": {
            "income": estimated_price,
            "total_expenses": event_cost,
            "supply_cost": 0,
            "other_expenses": event_cost,
            "profit": profit,
            "profit_margin": profit_margin_pct,
        },
    }


def complete_past_events(dry_run: bool = False):
    print(f"{'[DRY RUN] ' if dry_run else ''}Cerrando eventos pasados con margen del 70%")
    print(f"Fecha de corte: {TODAY}")
    print("=" * 60)

    db = get_db()
    bookings_ref = db.collection("bookings")

    updated = 0
    skipped_already_done = 0
    skipped_future = 0
    skipped_no_price = 0
    errors = 0

    for doc in bookings_ref.stream():
        data = doc.to_dict()
        booking_id = doc.id
        status = data.get('status', '')
        raw_date = data.get('event_date', '')
        client = data.get('client_name', 'Sin nombre')

        event_date_str = parse_event_date(raw_date)

        # Skip future events
        if not event_date_str or event_date_str > TODAY:
            skipped_future += 1
            continue

        # Skip already closed / cancelled
        if status not in ('pending', 'confirmed'):
            skipped_already_done += 1
            continue

        estimated_price = float(data.get('estimated_price') or 0)
        if estimated_price <= 0:
            print(f"  [SKIP] {booking_id} ({client} - {event_date_str}): sin precio estimado")
            skipped_no_price += 1
            continue

        event_cost = round(estimated_price * (1 - MARGIN), 2)
        profit = round(estimated_price * MARGIN, 2)

        print(f"  {'[DRY] ' if dry_run else 'OK'} {booking_id} | {client} | {event_date_str} | "
              f"Precio: ${estimated_price:.2f} | Costo: ${event_cost:.2f} | "
              f"Ganancia: ${profit:.2f} (70%)")

        if not dry_run:
            try:
                # Check if event already exists for this booking
                existing_events = list(
                    db.collection('events')
                      .where('booking_id', '==', booking_id)
                      .limit(1)
                      .stream()
                )

                if not existing_events:
                    data['id'] = booking_id  # needed by build_event
                    event_doc = build_event(data, event_cost, profit)
                    db.collection("events").document(event_doc['id']).set(event_doc)

                bookings_ref.document(booking_id).update({
                    'status': 'completed',
                    'event_cost': event_cost,
                    'event_profit': profit,
                    'updated_at': datetime.now(),
                })
                updated += 1
            except Exception as e:
                print(f"    ❌ Error en {booking_id}: {e}")
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
