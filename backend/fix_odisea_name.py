"""
Script para corregir el nombre 'La Odesea' → 'La Odisea' en Firestore.
Actualiza tanto la colección 'customers' como 'vacuum_sales'.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db

WRONG_NAME = "La Odesea"
CORRECT_NAME = "La Odisea"


def fix_customer():
    db = get_db()
    print(f"\n🔍 Buscando clientes con nombre '{WRONG_NAME}'...")

    docs = list(db.collection('customers').stream())
    found = []
    for doc in docs:
        data = doc.to_dict()
        name = data.get('name', '')
        if WRONG_NAME.lower() in name.lower():
            found.append((doc.id, name))
            print(f"   → Encontrado: ID={doc.id}, nombre='{name}'")

    if not found:
        print("   ⚠️  No se encontró ningún cliente con ese nombre.")
    else:
        for customer_id, old_name in found:
            new_name = old_name.replace(WRONG_NAME, CORRECT_NAME)
            db.collection('customers').document(customer_id).update({'name': new_name})
            print(f"   ✅ Cliente corregido: '{old_name}' → '{new_name}'")

    return [cid for cid, _ in found]


def fix_vacuum_sales(customer_ids):
    db = get_db()
    print(f"\n🔍 Buscando ventas al vacío con customer_name incorrecto...")

    docs = list(db.collection('vacuum_sales').stream())
    count = 0
    for doc in docs:
        data = doc.to_dict()
        customer_name = data.get('customer_name', '')
        if WRONG_NAME.lower() in customer_name.lower():
            new_name = customer_name.replace(WRONG_NAME, CORRECT_NAME)
            db.collection('vacuum_sales').document(doc.id).update({'customer_name': new_name})
            print(f"   ✅ Venta {doc.id}: '{customer_name}' → '{new_name}'")
            count += 1

    if count == 0:
        print("   ⚠️  No se encontraron ventas con ese nombre de cliente.")
    else:
        print(f"   ✅ {count} venta(s) corregida(s).")


def fix_inventory_movements():
    db = get_db()
    print(f"\n🔍 Buscando movimientos de inventario con notas incorrectas...")

    docs = list(db.collection('inventory_movements').stream())
    count = 0
    for doc in docs:
        data = doc.to_dict()
        notes = data.get('notes', '')
        if WRONG_NAME.lower() in notes.lower():
            new_notes = notes.replace(WRONG_NAME, CORRECT_NAME)
            db.collection('inventory_movements').document(doc.id).update({'notes': new_notes})
            print(f"   ✅ Movimiento {doc.id}: notas actualizadas")
            count += 1

    if count == 0:
        print("   ⚠️  No se encontraron movimientos con ese nombre.")
    else:
        print(f"   ✅ {count} movimiento(s) corregido(s).")


if __name__ == '__main__':
    print("=" * 60)
    print(f"Corrección de nombre: '{WRONG_NAME}' → '{CORRECT_NAME}'")
    print("=" * 60)

    customer_ids = fix_customer()
    fix_vacuum_sales(customer_ids)
    fix_inventory_movements()

    print("\n✅ Proceso completado.")
