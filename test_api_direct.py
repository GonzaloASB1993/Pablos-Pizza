#!/usr/bin/env python3
"""
Test directo al API para verificar cálculo de precios
"""
import requests
import json

def test_precio_api():
    # Test directo al API
    data = {
        'client_name': 'Test User',
        'client_email': 'test@example.com',
        'client_phone': '+56912345678',
        'service_type': 'workshop',
        'event_type': 'birthday',
        'event_date': '2025-09-30T15:00:00',
        'event_time': '15:00',
        'duration_hours': 4,
        'participants': 12,
        'location': 'Test Location, Santiago',
        'special_requests': 'Test request'
    }

    print("=== PRUEBA DIRECTA AL API ===")
    print(f"Enviando: {data['service_type']} con {data['participants']} participantes")
    print("Precio esperado: $162,000 CLP (13,500 x 12)")

    try:
        response = requests.post('http://localhost:8000/api/bookings/', json=data)
        print(f"Status HTTP: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            precio_recibido = result.get('estimated_price', 'N/A')
            print(f"Precio recibido del backend: ${precio_recibido} CLP")
            print(f"Booking ID: {result.get('id', 'N/A')}")

            # Verificar si el precio es correcto
            precio_esperado = 162000.0
            if precio_recibido == precio_esperado:
                print("✅ PRECIO CORRECTO!")
            else:
                print(f"❌ PRECIO INCORRECTO - Esperado: ${precio_esperado}, Recibido: ${precio_recibido}")

        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    test_precio_api()