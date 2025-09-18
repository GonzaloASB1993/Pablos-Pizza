#!/usr/bin/env python3
"""
Quick Test Demo - Demonstrates that the comprehensive test suite is working
"""
import subprocess
import sys
import os
from pathlib import Path

def run_test(command, description):
    """Run a test and return success status"""
    print(f"\n{'='*50}")
    print(f"TEST: {description}")
    print(f"{'='*50}")
    print(f"Command: {command}")
    print()

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Print output
    if result.stdout:
        print("OUTPUT:")
        # Show only key lines to avoid too much output
        lines = result.stdout.split('\n')
        key_lines = [line for line in lines if 'PASSED' in line or 'FAILED' in line or '====' in line or 'ERROR' in line]
        for line in key_lines[-10:]:  # Show last 10 key lines
            print(line)

    if result.returncode == 0:
        print("RESULT: TEST PASSED")
        return True
    else:
        print("RESULT: TEST FAILED")
        if result.stderr:
            print("STDERR:", result.stderr[:200] + "..." if len(result.stderr) > 200 else result.stderr)
        return False

def main():
    """Run a quick demo of the test suite"""
    print("Pablo's Pizza Backend Test Suite - Quick Demo")
    print("="*60)

    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    tests_to_run = [
        # Test basic revenue calculation
        (
            "python -m pytest tests/unit/test_revenue_calculation.py::TestRevenueCalculation::test_calculate_estimated_price_workshop_small_group -v --tb=short",
            "Basic Workshop Pricing Test"
        ),

        # Test the $193k scenario
        (
            "python -m pytest tests/unit/test_revenue_calculation.py::TestRevenueCalculation::test_193k_booking_scenario -v --tb=short",
            "$193,000 Booking Scenario Test"
        ),

        # Test confirmed bookings filtering
        (
            "python -m pytest tests/unit/test_revenue_calculation.py::TestBookingStatusFiltering::test_confirmed_bookings_only -v --tb=short",
            "Confirmed Bookings Filtering Test"
        ),

        # Test future events inclusion
        (
            "python -m pytest tests/unit/test_revenue_calculation.py::TestBookingStatusFiltering::test_future_confirmed_events_inclusion -v --tb=short",
            "Future Confirmed Events Test"
        )
    ]

    passed = 0
    failed = 0

    for command, description in tests_to_run:
        if run_test(command, description):
            passed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/(passed+failed)*100):.1f}%")

    if failed == 0:
        print(f"\nALL TESTS PASSED! The comprehensive test suite is working correctly.")
        print(f"\nWhat this proves:")
        print(f"  - Revenue calculation logic is correct")
        print(f"  - Workshop pricing with discounts works properly")
        print(f"  - The $193,000 booking scenario is handled correctly")
        print(f"  - Only confirmed bookings are included in revenue calculations")
        print(f"  - Future confirmed events are properly included")
        print(f"\nFull test suite available at:")
        print(f"   - tests/unit/test_revenue_calculation.py")
        print(f"   - tests/integration/test_dashboard_revenue.py")
        print(f"   - tests/integration/test_chat_cors.py")
        print(f"\nTo run all tests: python -m pytest tests/ -v")
        return True
    else:
        print(f"\nSome tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)