"""
Migration: Merge "(Producido)" inventory items into their original SKUs.

For every item named "<X> (Producido)" that has a matching original "<X>":
  - Add its current_stock to the original item
  - Delete the "(Producido)" duplicate

Run once from the backend/ directory:
    python migrate_producido_stock.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv('.env')

import firebase_admin
from firebase_admin import credentials, firestore

SUFFIX = ' (Producido)'


def get_db():
    if not firebase_admin._apps:
        sa_path = os.path.join(os.path.dirname(__file__), 'ServiceAccount.json')
        if os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    return firestore.client()


def normalize(name):
    """Collapse multiple spaces and strip edges."""
    return ' '.join(name.split())


def run_migration(dry_run=False):
    db = get_db()
    inventory = db.collection('inventory')

    all_docs = {doc.id: doc.to_dict() | {'_ref': doc.reference}
                for doc in inventory.stream()}

    # Index by exact name AND normalized name for flexible lookup
    by_name = {}
    by_norm = {}
    for doc_id, data in all_docs.items():
        name = data['name']
        by_name[name] = (doc_id, data)
        by_norm[normalize(name)] = (doc_id, data)

    producido_items = [
        (doc_id, data)
        for doc_id, data in all_docs.items()
        if data.get('name', '').endswith(SUFFIX)
    ]

    if not producido_items:
        print('No items with "(Producido)" suffix found. Nothing to migrate.')
        return

    print(f'Found {len(producido_items)} "(Producido)" item(s):\n')

    for doc_id, data in producido_items:
        producido_name = data['name']
        original_name = producido_name[: -len(SUFFIX)]
        stock_to_merge = data.get('current_stock', 0)

        print(f'  [{producido_name}]  stock={stock_to_merge}')

        # Try exact match first, then normalized (handles extra spaces)
        match = by_name.get(original_name) or by_norm.get(normalize(original_name))
        if not match:
            print(f'    [WARN] No original item "{original_name.strip()}" found -- skipping.\n')
            continue
        orig_id, orig_data = match

        orig_ref = orig_data['_ref']
        new_stock = round(orig_data.get('current_stock', 0) + stock_to_merge, 2)
        needs_restock = new_stock <= orig_data.get('min_stock', 0)

        print(f'    >> Merge into "{original_name}" (id={orig_id})')
        print(f'      {orig_data.get("current_stock", 0)} + {stock_to_merge} = {new_stock}')

        if dry_run:
            print('    [DRY RUN — no changes written]\n')
            continue

        orig_ref.update({
            'current_stock': new_stock,
            'needs_restock': needs_restock,
            'last_updated': datetime.now(),
        })

        data['_ref'].delete()
        print(f'    OK Stock updated, "(Producido)" item deleted.\n')

    if not dry_run:
        print('Migration complete.')
    else:
        print('Dry run complete — rerun without --dry-run to apply changes.')


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    if dry:
        print('=== DRY RUN MODE ===\n')
    run_migration(dry_run=dry)
