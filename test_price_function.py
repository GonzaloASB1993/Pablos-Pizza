#!/usr/bin/env python3
"""
Test directo de la función calculate_estimated_price
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import the function directly
from routers.bookings import calculate_estimated_price

def test_function_directly():
    print("=== TEST DIRECTO DE LA FUNCIÓN ===")

    # Test workshop with 12 participants
    service_type = "workshop"
    participants = 12

    print(f"Calling calculate_estimated_price('{service_type}', {participants})")
    result = calculate_estimated_price(service_type, participants)
    print(f"Result: {result}")

    expected = 13500 * 12
    print(f"Expected: {expected}")

    if result == expected:
        print("✅ FUNCTION WORKS CORRECTLY!")
    else:
        print(f"❌ FUNCTION INCORRECT - Expected: {expected}, Got: {result}")

if __name__ == "__main__":
    test_function_directly()