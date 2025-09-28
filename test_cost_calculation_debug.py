#!/usr/bin/env python3
"""
Comprehensive Test Suite for Event-Inventory Cost Calculation Debugging
Pablo's Pizza - Event-Inventory Integration

This test suite helps identify where the cost calculation integration is failing.

Usage:
    python test_cost_calculation_debug.py

Requirements:
    - Backend running on localhost:8000 OR production at main-4kqeqojbsq-uc.a.run.app
    - Valid booking with confirmed status
    - Inventory items with sufficient stock
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
# Change this to your backend URL
BACKEND_URL = "https://main-4kqeqojbsq-uc.a.run.app"  # Production
# BACKEND_URL = "http://localhost:8000"  # Local development

class EventCostCalculationTester:
    """Comprehensive tester for event-inventory cost calculation system"""

    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        self.test_booking_id = None
        self.test_supplies_id = None
        self.test_consumption_id = None

    def log_test(self, test_name: str, success: bool, details: Any = None, error: str = None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'error': error
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"      Error: {error}")
        if details and not success:
            print(f"      Details: {json.dumps(details, indent=2)}")

    def test_backend_health(self) -> bool:
        """Test 1: Verify backend is accessible"""
        try:
            response = self.session.get(f"{self.backend_url}/api/health")
            success = response.status_code == 200
            self.log_test(
                "Backend Health Check",
                success,
                {"status_code": response.status_code, "response": response.text[:200]},
                None if success else f"Backend not accessible: {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_test("Backend Health Check", False, error=str(e))
            return False

    def test_get_bookings(self) -> Optional[List[Dict]]:
        """Test 2: Get bookings and identify a confirmed booking for testing"""
        try:
            response = self.session.get(f"{self.backend_url}/api/bookings/")

            if response.status_code != 200:
                self.log_test("Get Bookings API", False, error=f"Status: {response.status_code}")
                return None

            bookings = response.json()
            confirmed_bookings = [b for b in bookings if b.get('status') == 'confirmed']

            success = len(confirmed_bookings) > 0
            self.log_test(
                "Get Bookings API",
                success,
                {
                    "total_bookings": len(bookings),
                    "confirmed_bookings": len(confirmed_bookings),
                    "first_confirmed": confirmed_bookings[0] if confirmed_bookings else None
                },
                "No confirmed bookings found for testing" if not success else None
            )

            if confirmed_bookings:
                # Use first confirmed booking for testing
                self.test_booking_id = confirmed_bookings[0]['id']
                return bookings

            return None

        except Exception as e:
            self.log_test("Get Bookings API", False, error=str(e))
            return None

    def test_get_inventory(self) -> Optional[List[Dict]]:
        """Test 3: Get inventory items for supplies testing"""
        try:
            response = self.session.get(f"{self.backend_url}/api/inventory/")

            if response.status_code != 200:
                self.log_test("Get Inventory API", False, error=f"Status: {response.status_code}")
                return None

            inventory = response.json()
            available_items = [item for item in inventory if item.get('current_stock', 0) > 0]

            success = len(available_items) > 0
            self.log_test(
                "Get Inventory API",
                success,
                {
                    "total_items": len(inventory),
                    "available_items": len(available_items),
                    "sample_items": available_items[:3] if available_items else []
                },
                "No inventory items with stock available" if not success else None
            )

            return inventory if success else None

        except Exception as e:
            self.log_test("Get Inventory API", False, error=str(e))
            return None

    def test_create_event_supplies(self, inventory_items: List[Dict]) -> bool:
        """Test 4: Create event supplies (estimation)"""
        if not self.test_booking_id:
            self.log_test("Create Event Supplies", False, error="No test booking ID available")
            return False

        try:
            # Select first available inventory item for testing
            test_item = next((item for item in inventory_items if item.get('current_stock', 0) > 1), None)
            if not test_item:
                self.log_test("Create Event Supplies", False, error="No suitable inventory item for testing")
                return False

            supplies_payload = {
                "booking_id": self.test_booking_id,
                "items": [
                    {
                        "item_id": test_item['id'],
                        "estimated_quantity": 1.0
                    }
                ],
                "notes": "Test supplies estimation for cost calculation debugging"
            }

            response = self.session.post(
                f"{self.backend_url}/api/event-supplies/",
                json=supplies_payload,
                headers={'Content-Type': 'application/json'}
            )

            success = response.status_code == 201
            response_data = response.json() if response.status_code in [200, 201] else {}

            if success:
                self.test_supplies_id = response_data.get('supplies_id')

            self.log_test(
                "Create Event Supplies",
                success,
                {
                    "status_code": response.status_code,
                    "payload": supplies_payload,
                    "response": response_data,
                    "supplies_id": self.test_supplies_id
                },
                f"Failed to create supplies: {response.text}" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Create Event Supplies", False, error=str(e))
            return False

    def test_verify_booking_after_supplies(self) -> Optional[Dict]:
        """Test 5: Verify booking data after supplies creation"""
        if not self.test_booking_id:
            self.log_test("Verify Booking After Supplies", False, error="No test booking ID")
            return None

        try:
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            bookings = response.json()
            test_booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not test_booking:
                self.log_test("Verify Booking After Supplies", False, error="Test booking not found")
                return None

            has_financials = 'financials' in test_booking
            financials_data = test_booking.get('financials', {})

            self.log_test(
                "Verify Booking After Supplies",
                True,  # This is informational
                {
                    "booking_id": self.test_booking_id,
                    "has_financials": has_financials,
                    "financials": financials_data,
                    "booking_structure": {
                        "id": test_booking.get('id'),
                        "status": test_booking.get('status'),
                        "has_expenses": 'expenses' in test_booking,
                        "expenses_count": len(test_booking.get('expenses', [])),
                        "has_financials": has_financials
                    }
                }
            )

            return test_booking

        except Exception as e:
            self.log_test("Verify Booking After Supplies", False, error=str(e))
            return None

    def test_create_event_consumption(self, inventory_items: List[Dict]) -> bool:
        """Test 6: Create event consumption (actual quantities) - THE CRITICAL TEST"""
        if not self.test_booking_id:
            self.log_test("Create Event Consumption", False, error="No test booking ID")
            return False

        try:
            # Use same item as supplies for consistency
            test_item = next((item for item in inventory_items if item.get('current_stock', 0) > 1), None)
            if not test_item:
                self.log_test("Create Event Consumption", False, error="No suitable inventory item")
                return False

            consumption_payload = {
                "booking_id": self.test_booking_id,
                "items_consumed": [
                    {
                        "item_id": test_item['id'],
                        "actual_quantity_consumed": 0.8  # Slightly less than estimated
                    }
                ],
                "total_other_expenses": 50.0,  # Test with some other expenses
                "notes": "Test consumption for cost calculation debugging"
            }

            print(f"\n🔍 CRITICAL TEST: Creating consumption for booking {self.test_booking_id}")
            print(f"📦 Item: {test_item['name']} (ID: {test_item['id']})")
            print(f"💰 Other expenses: 50.0")

            response = self.session.post(
                f"{self.backend_url}/api/event-consumption/",
                json=consumption_payload,
                headers={'Content-Type': 'application/json'}
            )

            success = response.status_code == 201
            response_data = response.json() if response.status_code in [200, 201] else {}

            if success:
                self.test_consumption_id = response_data.get('consumption_id')
                consumption_data = response_data.get('consumption', {})

                print(f"✅ Consumption created with ID: {self.test_consumption_id}")
                print(f"💰 Total supply cost: {consumption_data.get('total_supply_cost', 'N/A')}")
                print(f"💰 Total other expenses: {consumption_data.get('total_other_expenses', 'N/A')}")
                print(f"💰 TOTAL COST: {consumption_data.get('total_cost', 'N/A')}")

            self.log_test(
                "Create Event Consumption",
                success,
                {
                    "status_code": response.status_code,
                    "payload": consumption_payload,
                    "response": response_data,
                    "consumption_id": self.test_consumption_id
                },
                f"Failed to create consumption: {response.text}" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Create Event Consumption", False, error=str(e))
            return False

    def test_verify_booking_financials_after_consumption(self) -> bool:
        """Test 7: CRITICAL - Verify booking.financials after consumption"""
        if not self.test_booking_id:
            self.log_test("Verify Booking Financials", False, error="No test booking ID")
            return False

        try:
            print(f"\n🔍 CRITICAL VERIFICATION: Checking booking {self.test_booking_id} financials")

            response = self.session.get(f"{self.backend_url}/api/bookings/")
            bookings = response.json()
            test_booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not test_booking:
                self.log_test("Verify Booking Financials", False, error="Test booking not found")
                return False

            # CRITICAL CHECK: Does booking have financials?
            has_financials = 'financials' in test_booking
            financials = test_booking.get('financials', {})

            # Check specific financial fields
            has_total_expenses = 'total_expenses' in financials
            has_supply_cost = 'supply_cost' in financials
            has_other_expenses = 'other_expenses' in financials

            total_expenses = financials.get('total_expenses')
            supply_cost = financials.get('supply_cost')
            other_expenses = financials.get('other_expenses')

            print(f"📊 FINANCIALS CHECK:")
            print(f"   Has financials object: {has_financials}")
            print(f"   Has total_expenses: {has_total_expenses} = {total_expenses}")
            print(f"   Has supply_cost: {has_supply_cost} = {supply_cost}")
            print(f"   Has other_expenses: {has_other_expenses} = {other_expenses}")

            # This test passes if financials exist and have the expected structure
            success = has_financials and has_total_expenses

            self.log_test(
                "Verify Booking Financials",
                success,
                {
                    "booking_id": self.test_booking_id,
                    "has_financials": has_financials,
                    "financials_structure": {
                        "total_expenses": total_expenses,
                        "supply_cost": supply_cost,
                        "other_expenses": other_expenses
                    },
                    "full_booking": test_booking
                },
                "Booking does not have proper financials structure" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Verify Booking Financials", False, error=str(e))
            return False

    def test_frontend_data_structure(self) -> bool:
        """Test 8: Simulate frontend data access pattern"""
        if not self.test_booking_id:
            self.log_test("Frontend Data Structure", False, error="No test booking ID")
            return False

        try:
            # Simulate what the frontend does: loadBookings()
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            bookings = response.json()
            test_booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not test_booking:
                self.log_test("Frontend Data Structure", False, error="Test booking not found")
                return False

            # Simulate handleOpenCostDialog logic
            accumulated_expenses = sum(expense.get('amount', 0) for expense in test_booking.get('expenses', []))
            financials_total = test_booking.get('financials', {}).get('total_expenses')
            total_cost_with_supplies = financials_total or accumulated_expenses or test_booking.get('event_cost', '')

            print(f"\n🎯 FRONTEND SIMULATION:")
            print(f"   Accumulated expenses: {accumulated_expenses}")
            print(f"   Financials total_expenses: {financials_total}")
            print(f"   Final calculated cost: {total_cost_with_supplies}")

            # Test what frontend would see
            success = financials_total is not None and financials_total > 0

            self.log_test(
                "Frontend Data Structure",
                success,
                {
                    "booking_id": self.test_booking_id,
                    "accumulated_expenses": accumulated_expenses,
                    "financials_total_expenses": financials_total,
                    "final_cost": total_cost_with_supplies,
                    "would_show_supplies_cost": success
                },
                "Frontend would not see supply costs" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Frontend Data Structure", False, error=str(e))
            return False

    def test_api_response_timing(self) -> bool:
        """Test 9: Check if there are timing issues with data consistency"""
        if not self.test_booking_id:
            self.log_test("API Response Timing", False, error="No test booking ID")
            return False

        try:
            import time

            # Test multiple rapid requests to see if data is consistent
            results = []
            for i in range(5):
                response = self.session.get(f"{self.backend_url}/api/bookings/")
                bookings = response.json()
                test_booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

                if test_booking:
                    financials = test_booking.get('financials', {})
                    results.append({
                        'request': i + 1,
                        'has_financials': 'financials' in test_booking,
                        'total_expenses': financials.get('total_expenses'),
                        'timestamp': datetime.now().isoformat()
                    })

                time.sleep(0.1)  # Small delay between requests

            # Check consistency
            has_financials_results = [r['has_financials'] for r in results]
            total_expenses_results = [r['total_expenses'] for r in results]

            is_consistent = (
                len(set(has_financials_results)) == 1 and  # All same
                len(set(total_expenses_results)) == 1      # All same
            )

            self.log_test(
                "API Response Timing",
                is_consistent,
                {
                    "results": results,
                    "consistency_check": {
                        "financials_consistent": len(set(has_financials_results)) == 1,
                        "total_expenses_consistent": len(set(total_expenses_results)) == 1
                    }
                },
                "Data inconsistency detected across multiple requests" if not is_consistent else None
            )

            return is_consistent

        except Exception as e:
            self.log_test("API Response Timing", False, error=str(e))
            return False

    def cleanup_test_data(self):
        """Clean up test data (optional)"""
        print(f"\n🧹 CLEANUP:")
        print(f"   Test booking ID: {self.test_booking_id}")
        print(f"   Test supplies ID: {self.test_supplies_id}")
        print(f"   Test consumption ID: {self.test_consumption_id}")
        print(f"   Note: Test data left in database for manual inspection")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests in sequence"""
        print("🧪 Starting Event-Inventory Cost Calculation Debug Tests")
        print(f"🌐 Backend URL: {self.backend_url}")
        print(f"⏰ Started at: {datetime.now().isoformat()}")
        print("=" * 70)

        # Test sequence
        if not self.test_backend_health():
            print("❌ Backend not accessible, aborting tests")
            return self.generate_report()

        bookings = self.test_get_bookings()
        if not bookings:
            print("❌ No confirmed bookings available, aborting tests")
            return self.generate_report()

        inventory = self.test_get_inventory()
        if not inventory:
            print("❌ No inventory available, aborting tests")
            return self.generate_report()

        # Run the critical test sequence
        if self.test_create_event_supplies(inventory):
            self.test_verify_booking_after_supplies()

            if self.test_create_event_consumption(inventory):
                # CRITICAL TESTS
                self.test_verify_booking_financials_after_consumption()
                self.test_frontend_data_structure()
                self.test_api_response_timing()

        self.cleanup_test_data()
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        passed_tests = [r for r in self.test_results if r['success']]
        failed_tests = [r for r in self.test_results if not r['success']]

        report = {
            'test_summary': {
                'total_tests': len(self.test_results),
                'passed': len(passed_tests),
                'failed': len(failed_tests),
                'success_rate': len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
            },
            'backend_url': self.backend_url,
            'test_booking_id': self.test_booking_id,
            'test_supplies_id': self.test_supplies_id,
            'test_consumption_id': self.test_consumption_id,
            'test_results': self.test_results,
            'failed_tests': failed_tests,
            'diagnosis': self.diagnose_issues()
        }

        print("\n" + "=" * 70)
        print("📊 TEST REPORT")
        print("=" * 70)
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']:.1f}%")

        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['error']}")

        diagnosis = report['diagnosis']
        if diagnosis:
            print(f"\n🔍 DIAGNOSIS:")
            for issue in diagnosis:
                print(f"   - {issue}")

        return report

    def diagnose_issues(self) -> List[str]:
        """Diagnose potential issues based on test results"""
        issues = []

        # Check if backend is working
        backend_tests = [r for r in self.test_results if 'Backend' in r['test_name'] or 'API' in r['test_name']]
        if any(not r['success'] for r in backend_tests):
            issues.append("Backend API issues detected - check server status and connectivity")

        # Check if event-consumption worked
        consumption_test = next((r for r in self.test_results if 'Event Consumption' in r['test_name']), None)
        if consumption_test and not consumption_test['success']:
            issues.append("Event consumption creation failed - check inventory stock and validation logic")

        # Check if financials were updated
        financials_test = next((r for r in self.test_results if 'Booking Financials' in r['test_name']), None)
        if financials_test and not financials_test['success']:
            issues.append("CRITICAL: Booking financials not updated after consumption - check backend update logic")

        # Check frontend data access
        frontend_test = next((r for r in self.test_results if 'Frontend Data' in r['test_name']), None)
        if frontend_test and not frontend_test['success']:
            issues.append("CRITICAL: Frontend cannot access calculated costs - cost modal will show old data")

        # Check timing issues
        timing_test = next((r for r in self.test_results if 'Timing' in r['test_name']), None)
        if timing_test and not timing_test['success']:
            issues.append("Data consistency issues detected - possible caching or race condition")

        if not issues:
            issues.append("All tests passed - the integration should be working correctly")

        return issues


def main():
    """Run the comprehensive test suite"""
    tester = EventCostCalculationTester(BACKEND_URL)
    report = tester.run_all_tests()

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"cost_calculation_debug_report_{timestamp}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Detailed report saved to: {report_file}")

    # Exit with error code if tests failed
    if report['test_summary']['failed'] > 0:
        print("\n⚠️  Some tests failed - review the report for debugging information")
        sys.exit(1)
    else:
        print("\n✅ All tests passed - cost calculation should be working correctly")
        sys.exit(0)


if __name__ == "__main__":
    main()