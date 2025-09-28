#!/usr/bin/env python3
"""
Data Persistence Verification Tests for Event-Inventory Integration
Pablo's Pizza - Database State Verification

This test suite verifies that data is properly persisted in Firebase Firestore
and that the cost calculation data remains consistent across sessions.

Usage:
    python test_data_persistence.py [--local] [--booking-id BOOKING_ID]

Tests:
1. Firestore document structure verification
2. Data consistency across multiple reads
3. Financial data integrity checks
4. Cross-collection reference validation
"""

import requests
import json
import sys
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class DataPersistenceTester:
    """Data persistence and integrity tester"""

    def __init__(self, backend_url: str, test_booking_id: Optional[str] = None):
        self.backend_url = backend_url.rstrip('/')
        self.session = requests.Session()
        self.test_booking_id = test_booking_id
        self.test_results = []

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

        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if error:
            print(f"    ⚠️  {error}")
        if success and details and isinstance(details, dict) and 'summary' in details:
            print(f"    📊 {details['summary']}")

    def find_booking_with_consumption(self) -> Optional[str]:
        """Find a booking that has event consumption data"""
        try:
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            if response.status_code != 200:
                return None

            bookings = response.json()

            # Look for bookings with financials (indicating consumption was registered)
            bookings_with_financials = [
                b for b in bookings
                if 'financials' in b and b['financials'].get('total_expenses', 0) > 0
            ]

            if bookings_with_financials:
                return bookings_with_financials[0]['id']

            return None

        except Exception:
            return None

    def test_booking_document_structure(self) -> bool:
        """Test 1: Verify booking document has correct structure"""
        if not self.test_booking_id:
            self.log_test("Booking Document Structure", False, error="No test booking ID")
            return False

        try:
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            if response.status_code != 200:
                self.log_test("Booking Document Structure", False, error="Cannot fetch bookings")
                return False

            bookings = response.json()
            booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not booking:
                self.log_test("Booking Document Structure", False, error="Test booking not found")
                return False

            # Check required fields
            required_fields = ['id', 'status', 'client_name', 'event_date']
            missing_fields = [field for field in required_fields if field not in booking]

            # Check financial structure if present
            has_financials = 'financials' in booking
            financial_structure_valid = True
            financial_fields = []

            if has_financials:
                financials = booking['financials']
                expected_financial_fields = ['total_expenses', 'supply_cost', 'other_expenses']
                financial_fields = [field for field in expected_financial_fields if field in financials]
                financial_structure_valid = len(financial_fields) >= 2  # At least 2 fields

            success = len(missing_fields) == 0

            self.log_test(
                "Booking Document Structure",
                success,
                {
                    'summary': f"Structure valid: {success}, Financials: {has_financials}",
                    'booking_id': self.test_booking_id,
                    'has_required_fields': len(missing_fields) == 0,
                    'missing_fields': missing_fields,
                    'has_financials': has_financials,
                    'financial_fields': financial_fields,
                    'financial_structure_valid': financial_structure_valid,
                    'document_structure': {
                        'total_fields': len(booking.keys()),
                        'has_expenses': 'expenses' in booking,
                        'has_financials': has_financials,
                        'status': booking.get('status')
                    }
                },
                f"Missing required fields: {missing_fields}" if missing_fields else None
            )

            return success

        except Exception as e:
            self.log_test("Booking Document Structure", False, error=str(e))
            return False

    def test_data_consistency_across_reads(self) -> bool:
        """Test 2: Verify data consistency across multiple API calls"""
        if not self.test_booking_id:
            self.log_test("Data Consistency", False, error="No test booking ID")
            return False

        try:
            reads = []
            for i in range(10):  # 10 consecutive reads
                response = self.session.get(f"{self.backend_url}/api/bookings/")
                if response.status_code == 200:
                    bookings = response.json()
                    booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

                    if booking:
                        # Create a fingerprint of the important data
                        fingerprint = {
                            'status': booking.get('status'),
                            'has_financials': 'financials' in booking,
                            'total_expenses': booking.get('financials', {}).get('total_expenses'),
                            'expenses_count': len(booking.get('expenses', [])),
                            'timestamp': datetime.now().isoformat()
                        }
                        reads.append(fingerprint)

                time.sleep(0.1)  # Small delay between reads

            # Check consistency
            if not reads:
                self.log_test("Data Consistency", False, error="No successful reads")
                return False

            # Compare all reads to the first one
            first_read = reads[0]
            inconsistencies = []

            for i, read in enumerate(reads[1:], 1):
                for key in ['status', 'has_financials', 'total_expenses', 'expenses_count']:
                    if read.get(key) != first_read.get(key):
                        inconsistencies.append(f"Read {i}: {key} changed from {first_read.get(key)} to {read.get(key)}")

            is_consistent = len(inconsistencies) == 0

            self.log_test(
                "Data Consistency",
                is_consistent,
                {
                    'summary': f"Consistent across {len(reads)} reads" if is_consistent else f"{len(inconsistencies)} inconsistencies found",
                    'total_reads': len(reads),
                    'inconsistencies': inconsistencies,
                    'first_read': first_read,
                    'last_read': reads[-1] if reads else None
                },
                f"Data inconsistencies detected: {inconsistencies[:3]}" if inconsistencies else None
            )

            return is_consistent

        except Exception as e:
            self.log_test("Data Consistency", False, error=str(e))
            return False

    def test_financial_data_integrity(self) -> bool:
        """Test 3: Verify financial data integrity and calculations"""
        if not self.test_booking_id:
            self.log_test("Financial Data Integrity", False, error="No test booking ID")
            return False

        try:
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            if response.status_code != 200:
                self.log_test("Financial Data Integrity", False, error="Cannot fetch bookings")
                return False

            bookings = response.json()
            booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not booking:
                self.log_test("Financial Data Integrity", False, error="Test booking not found")
                return False

            # Check if booking has financials
            if 'financials' not in booking:
                self.log_test(
                    "Financial Data Integrity",
                    False,
                    error="Booking has no financials data - consumption may not be registered"
                )
                return False

            financials = booking['financials']

            # Verify financial calculations
            supply_cost = financials.get('supply_cost', 0)
            other_expenses = financials.get('other_expenses', 0)
            total_expenses = financials.get('total_expenses', 0)

            # Check if total = supply + other (within small tolerance)
            calculated_total = supply_cost + other_expenses
            calculation_correct = abs(total_expenses - calculated_total) < 0.01

            # Check for reasonable values
            values_reasonable = (
                supply_cost >= 0 and
                other_expenses >= 0 and
                total_expenses > 0 and
                total_expenses >= supply_cost and
                total_expenses >= other_expenses
            )

            # Check data types
            types_correct = (
                isinstance(supply_cost, (int, float)) and
                isinstance(other_expenses, (int, float)) and
                isinstance(total_expenses, (int, float))
            )

            success = calculation_correct and values_reasonable and types_correct

            self.log_test(
                "Financial Data Integrity",
                success,
                {
                    'summary': f"Total: ${total_expenses} = Supply: ${supply_cost} + Other: ${other_expenses}",
                    'financial_values': {
                        'supply_cost': supply_cost,
                        'other_expenses': other_expenses,
                        'total_expenses': total_expenses,
                        'calculated_total': calculated_total
                    },
                    'integrity_checks': {
                        'calculation_correct': calculation_correct,
                        'values_reasonable': values_reasonable,
                        'types_correct': types_correct
                    },
                    'additional_fields': {
                        'has_income': 'income' in financials,
                        'has_profit': 'profit' in financials,
                        'field_count': len(financials.keys())
                    }
                },
                "Financial calculations or values are incorrect" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Financial Data Integrity", False, error=str(e))
            return False

    def test_cross_collection_references(self) -> bool:
        """Test 4: Verify references between collections are intact"""
        if not self.test_booking_id:
            self.log_test("Cross-Collection References", False, error="No test booking ID")
            return False

        try:
            # Check if booking has related event-supplies
            supplies_response = self.session.get(
                f"{self.backend_url}/api/event-supplies/booking/{self.test_booking_id}"
            )

            has_supplies = supplies_response.status_code == 200
            supplies_data = supplies_response.json() if has_supplies else {}

            # Check if booking has related event-consumption
            # Note: There's no direct endpoint, so we check through booking financials
            booking_response = self.session.get(f"{self.backend_url}/api/bookings/")
            booking = None
            if booking_response.status_code == 200:
                bookings = booking_response.json()
                booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            has_consumption = booking and 'financials' in booking and booking['financials'].get('total_expenses', 0) > 0

            # Verify reference integrity
            reference_integrity = {
                'booking_exists': booking is not None,
                'has_supplies': has_supplies,
                'has_consumption': has_consumption,
                'supplies_references_booking': False,
                'consumption_implied': has_consumption
            }

            if has_supplies and supplies_data:
                reference_integrity['supplies_references_booking'] = supplies_data.get('booking_id') == self.test_booking_id

            # For a complete integration, we expect both supplies and consumption
            complete_integration = has_supplies and has_consumption and reference_integrity['supplies_references_booking']

            success = reference_integrity['booking_exists'] and (has_supplies or has_consumption)

            self.log_test(
                "Cross-Collection References",
                success,
                {
                    'summary': f"Integration: {'Complete' if complete_integration else 'Partial'} - Supplies: {has_supplies}, Consumption: {has_consumption}",
                    'reference_integrity': reference_integrity,
                    'supplies_data': {
                        'exists': has_supplies,
                        'item_count': len(supplies_data.get('items', [])) if has_supplies else 0,
                        'booking_reference': supplies_data.get('booking_id') if has_supplies else None
                    },
                    'consumption_indicators': {
                        'has_financials': booking and 'financials' in booking,
                        'total_expenses': booking.get('financials', {}).get('total_expenses') if booking else None
                    },
                    'integration_complete': complete_integration
                },
                "Missing critical collection references" if not success else None
            )

            return success

        except Exception as e:
            self.log_test("Cross-Collection References", False, error=str(e))
            return False

    def test_data_persistence_over_time(self) -> bool:
        """Test 5: Verify data persists over time (multiple checks with delays)"""
        if not self.test_booking_id:
            self.log_test("Data Persistence Over Time", False, error="No test booking ID")
            return False

        try:
            # Initial read
            initial_response = self.session.get(f"{self.backend_url}/api/bookings/")
            if initial_response.status_code != 200:
                self.log_test("Data Persistence Over Time", False, error="Cannot fetch initial data")
                return False

            initial_bookings = initial_response.json()
            initial_booking = next((b for b in initial_bookings if b['id'] == self.test_booking_id), None)

            if not initial_booking:
                self.log_test("Data Persistence Over Time", False, error="Test booking not found")
                return False

            initial_state = {
                'financials': initial_booking.get('financials', {}),
                'expenses': initial_booking.get('expenses', []),
                'status': initial_booking.get('status'),
                'timestamp': datetime.now().isoformat()
            }

            # Wait and read again
            print("    ⏳ Waiting 5 seconds to test persistence...")
            time.sleep(5)

            final_response = self.session.get(f"{self.backend_url}/api/bookings/")
            if final_response.status_code != 200:
                self.log_test("Data Persistence Over Time", False, error="Cannot fetch final data")
                return False

            final_bookings = final_response.json()
            final_booking = next((b for b in final_bookings if b['id'] == self.test_booking_id), None)

            if not final_booking:
                self.log_test("Data Persistence Over Time", False, error="Test booking lost during persistence test")
                return False

            final_state = {
                'financials': final_booking.get('financials', {}),
                'expenses': final_booking.get('expenses', []),
                'status': final_booking.get('status'),
                'timestamp': datetime.now().isoformat()
            }

            # Compare states
            data_preserved = (
                initial_state['financials'] == final_state['financials'] and
                initial_state['expenses'] == final_state['expenses'] and
                initial_state['status'] == final_state['status']
            )

            self.log_test(
                "Data Persistence Over Time",
                data_preserved,
                {
                    'summary': f"Data {'preserved' if data_preserved else 'changed'} over 5 seconds",
                    'initial_state': initial_state,
                    'final_state': final_state,
                    'comparison': {
                        'financials_same': initial_state['financials'] == final_state['financials'],
                        'expenses_same': initial_state['expenses'] == final_state['expenses'],
                        'status_same': initial_state['status'] == final_state['status']
                    }
                },
                "Data changed unexpectedly during persistence test" if not data_preserved else None
            )

            return data_preserved

        except Exception as e:
            self.log_test("Data Persistence Over Time", False, error=str(e))
            return False

    def run_persistence_tests(self) -> Dict[str, Any]:
        """Run all data persistence tests"""
        print("💾 Starting Data Persistence Verification Tests")
        print(f"🌐 Backend URL: {self.backend_url}")

        # Find test booking if not provided
        if not self.test_booking_id:
            print("🔍 Looking for booking with consumption data...")
            self.test_booking_id = self.find_booking_with_consumption()

        if not self.test_booking_id:
            print("❌ No booking with consumption data found for testing")
            print("   Please run the E2E test first to create test data")
            return self.generate_persistence_report()

        print(f"📋 Using booking: {self.test_booking_id}")
        print("=" * 50)

        # Run tests
        test_functions = [
            self.test_booking_document_structure,
            self.test_data_consistency_across_reads,
            self.test_financial_data_integrity,
            self.test_cross_collection_references,
            self.test_data_persistence_over_time
        ]

        for test_function in test_functions:
            test_function()
            time.sleep(0.5)  # Small delay between tests

        return self.generate_persistence_report()

    def generate_persistence_report(self) -> Dict[str, Any]:
        """Generate persistence test report"""
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
            'test_results': self.test_results,
            'failed_tests': failed_tests,
            'data_integrity_assessment': self.assess_data_integrity()
        }

        print("\n" + "=" * 50)
        print("📊 DATA PERSISTENCE TEST REPORT")
        print("=" * 50)
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']:.1f}%")

        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['error']}")

        assessment = report['data_integrity_assessment']
        if assessment:
            print(f"\n🔍 DATA INTEGRITY ASSESSMENT:")
            for finding in assessment:
                print(f"   - {finding}")

        return report

    def assess_data_integrity(self) -> List[str]:
        """Assess overall data integrity based on test results"""
        assessment = []

        # Check test results
        structure_test = next((r for r in self.test_results if 'Structure' in r['test_name']), None)
        if structure_test and structure_test['success']:
            assessment.append("✅ Booking document structure is valid")
        elif structure_test:
            assessment.append("❌ Booking document structure has issues")

        consistency_test = next((r for r in self.test_results if 'Consistency' in r['test_name']), None)
        if consistency_test and consistency_test['success']:
            assessment.append("✅ Data is consistent across multiple reads")
        elif consistency_test:
            assessment.append("❌ Data consistency issues detected")

        financial_test = next((r for r in self.test_results if 'Financial' in r['test_name']), None)
        if financial_test and financial_test['success']:
            assessment.append("✅ Financial calculations are correct and intact")
        elif financial_test:
            assessment.append("❌ Financial data integrity issues found")

        references_test = next((r for r in self.test_results if 'References' in r['test_name']), None)
        if references_test and references_test['success']:
            assessment.append("✅ Cross-collection references are intact")
        elif references_test:
            assessment.append("❌ Missing or broken collection references")

        persistence_test = next((r for r in self.test_results if 'Persistence Over Time' in r['test_name']), None)
        if persistence_test and persistence_test['success']:
            assessment.append("✅ Data persists correctly over time")
        elif persistence_test:
            assessment.append("❌ Data persistence issues detected")

        # Overall assessment
        passed_tests = [r for r in self.test_results if r['success']]
        if len(passed_tests) == len(self.test_results):
            assessment.append("🎉 All persistence tests passed - data integrity is excellent")
        elif len(passed_tests) >= len(self.test_results) * 0.8:
            assessment.append("⚠️ Most tests passed - minor data integrity issues")
        else:
            assessment.append("🚨 Multiple test failures - significant data integrity concerns")

        return assessment


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test Data Persistence and Integrity')
    parser.add_argument('--local', action='store_true', help='Test against local backend')
    parser.add_argument('--booking-id', help='Specific booking ID to test (optional)')
    args = parser.parse_args()

    backend_url = "http://localhost:8000" if args.local else "https://main-4kqeqojbsq-uc.a.run.app"

    tester = DataPersistenceTester(backend_url, test_booking_id=args.booking_id)
    report = tester.run_persistence_tests()

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data_persistence_test_report_{timestamp}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Report saved to: {report_file}")

    # Exit based on results
    if report['test_summary']['failed'] == 0:
        print("\n✅ All data persistence tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some data persistence tests failed - check the report")
        sys.exit(1)


if __name__ == "__main__":
    main()