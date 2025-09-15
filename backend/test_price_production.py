#!/usr/bin/env python3
"""
Test del cálculo de precios en producción
"""
import os
import sys
from dotenv import load_dotenv

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(__file__))

# Cargar variables de entorno de producción
load_dotenv('.env')

# Importar la función de cálculo
from routers.bookings import calculate_estimated_price

def test_price_calculation():
    print("=== TEST DE CÁLCULO DE PRECIOS - PRODUCCIÓN ===")
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
    print(f"DEBUG: {os.getenv('DEBUG', 'not set')}")
    print()

    # Test casos comunes
    test_cases = [
        ("workshop", 12, 13500 * 12),  # 162,000
        ("workshop", 20, 12150 * 20),  # 243,000 (10% descuento)
        ("pizza_party", 15, 11990 * 15),  # 179,850
        ("pizza_party", 25, round(11990 * 0.9) * 25),  # 269,775 (10% descuento)
    ]

    for service_type, participants, expected in test_cases:
        print(f"Testing: {service_type} with {participants} participants")
        result = calculate_estimated_price(service_type, participants)
        status = "✅" if result == expected else "❌"
        print(f"{status} Result: ${result:,.0f} (Expected: ${expected:,.0f})")
        print(f"   Difference: ${abs(result - expected):,.0f}")
        print()

if __name__ == "__main__":
    test_price_calculation()