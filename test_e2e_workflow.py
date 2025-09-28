#!/usr/bin/env python3
"""
End-to-End Integration Test for Event-Inventory Cost Calculation Workflow
Pablo's Pizza - Complete Workflow Testing

This test simulates the complete user workflow from booking confirmation
to event completion with cost calculation.

Usage:
    python test_e2e_workflow.py [--local] [--cleanup]

Workflow tested:
1. Create/Confirm booking
2. Add expense estimation (+gastos)
3. Add supply estimation (Insumos tab)
4. Register actual consumption
5. Open "Completar Evento" modal
6. Verify total cost = gastos + insumos
"""

import requests
import json
import sys
import argparse
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class E2EWorkflowTester:
    """End-to-end workflow tester"""

    def __init__(self, backend_url: str, cleanup: bool = False):
        self.backend_url = backend_url.rstrip('/')
        self.session = requests.Session()
        self.cleanup = cleanup
        self.test_results = []

        # Test data tracking
        self.test_booking_id = None
        self.test_supplies_id = None
        self.test_consumption_id = None
        self.created_resources = []

    def log_step(self, step_name: str, success: bool, details: Any = None, error: str = None):
        """Log workflow step result"""
        result = {
            'step': step_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'error': error
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {step_name}")
        if error:
            print(f"    ⚠️  {error}")
        if success and details and isinstance(details, dict) and 'summary' in details:
            print(f"    📊 {details['summary']}")

    def create_test_booking(self) -> bool:
        """Step 1: Create a test booking"""
        try:
            booking_data = {
                "client_name": "Test Cliente E2E",
                "client_phone": "+5491123456789",
                "client_email": "test.e2e@pablospizza.com",
                "event_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "event_time": "15:00",
                "event_address": "Calle Test 123, Ciudad Test",
                "number_of_children": 15,
                "estimated_price": 25000,
                "notes": "Booking creado para test E2E de integración evento-inventario",
                "status": "confirmed"  # Create directly as confirmed
            }

            response = self.session.post(
                f"{self.backend_url}/api/bookings/",
                json=booking_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 201:
                result = response.json()
                self.test_booking_id = result.get('booking_id')
                self.created_resources.append(('booking', self.test_booking_id))

                self.log_step(
                    "Create Test Booking",
                    True,
                    {
                        'summary': f'Booking created: {self.test_booking_id}',
                        'booking_data': booking_data,
                        'estimated_price': booking_data['estimated_price']
                    }
                )
                return True
            else:
                error_data = response.json() if response.status_code != 500 else {'error': response.text}
                self.log_step(
                    "Create Test Booking",
                    False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_step("Create Test Booking", False, error=str(e))
            return False

    def add_traditional_expenses(self) -> bool:
        """Step 2: Add traditional expenses (+gastos)"""
        if not self.test_booking_id:
            self.log_step("Add Traditional Expenses", False, error="No booking ID available")
            return False

        try:
            # Simulate adding expenses like the frontend does
            expenses = [
                {"description": "Decoración", "amount": 500, "category": "decoracion"},
                {"description": "Transporte", "amount": 800, "category": "transporte"},
                {"description": "Materiales adicionales", "amount": 300, "category": "otros"}
            ]

            total_expenses = sum(exp['amount'] for exp in expenses)

            # Update booking with expenses
            update_data = {
                "expenses": expenses
            }

            response = self.session.put(
                f"{self.backend_url}/api/bookings/{self.test_booking_id}",
                json=update_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                self.log_step(
                    "Add Traditional Expenses",
                    True,
                    {
                        'summary': f'Added {len(expenses)} expenses, total: ${total_expenses}',
                        'expenses': expenses,
                        'total_amount': total_expenses
                    }
                )
                return True
            else:
                error_data = response.json() if response.status_code != 500 else {'error': response.text}
                self.log_step(
                    "Add Traditional Expenses",
                    False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_step("Add Traditional Expenses", False, error=str(e))
            return False

    def get_available_inventory_items(self) -> List[Dict]:
        """Get inventory items for testing"""
        try:
            response = self.session.get(f"{self.backend_url}/api/inventory/")
            if response.status_code == 200:
                inventory = response.json()
                # Filter items with sufficient stock
                available_items = [item for item in inventory if item.get('current_stock', 0) > 2]
                return available_items[:3]  # Use first 3 items for testing
            return []
        except:
            return []

    def add_supply_estimation(self) -> bool:
        """Step 3: Add supply estimation (Insumos tab)"""
        if not self.test_booking_id:
            self.log_step("Add Supply Estimation", False, error="No booking ID available")
            return False

        try:
            # Get available inventory items
            available_items = self.get_available_inventory_items()
            if not available_items:
                self.log_step("Add Supply Estimation", False, error="No inventory items available")
                return False

            # Create supply estimation
            supplies_items = []
            estimated_total_cost = 0

            for i, item in enumerate(available_items[:2]):  # Use first 2 items
                estimated_quantity = 2.0 + i  # Different quantities for testing
                estimated_cost = estimated_quantity * item.get('cost_per_unit', 100)
                estimated_total_cost += estimated_cost

                supplies_items.append({
                    "item_id": item['id'],
                    "estimated_quantity": estimated_quantity
                })

            supplies_payload = {
                "booking_id": self.test_booking_id,
                "items": supplies_items,
                "notes": "Estimación de insumos para test E2E"
            }

            response = self.session.post(
                f"{self.backend_url}/api/event-supplies/",
                json=supplies_payload,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 201:
                result = response.json()
                self.test_supplies_id = result.get('supplies_id')
                self.created_resources.append(('supplies', self.test_supplies_id))

                self.log_step(
                    "Add Supply Estimation",
                    True,
                    {
                        'summary': f'Estimated {len(supplies_items)} items, cost: ~${estimated_total_cost:.2f}',
                        'supplies_id': self.test_supplies_id,
                        'items': supplies_items,
                        'estimated_cost': estimated_total_cost
                    }
                )
                return True
            else:
                error_data = response.json() if response.status_code != 500 else {'error': response.text}
                self.log_step(
                    "Add Supply Estimation",
                    False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_step("Add Supply Estimation", False, error=str(e))
            return False

    def register_actual_consumption(self) -> bool:
        """Step 4: Register actual consumption"""
        if not self.test_booking_id or not self.test_supplies_id:
            self.log_step("Register Actual Consumption", False, error="Missing booking or supplies ID")
            return False

        try:
            # Get the supplies to know what items were estimated
            supplies_response = self.session.get(
                f"{self.backend_url}/api/event-supplies/booking/{self.test_booking_id}"
            )

            if supplies_response.status_code != 200:
                self.log_step("Register Actual Consumption", False, error="Could not get supplies data")
                return False

            supplies_data = supplies_response.json()
            estimated_items = supplies_data.get('items', [])

            if not estimated_items:
                self.log_step("Register Actual Consumption", False, error="No estimated items found")
                return False

            # Create consumption with slightly different quantities (realistic variance)
            consumed_items = []
            total_supply_cost = 0

            for item in estimated_items:
                # Use 90% of estimated quantity (realistic consumption)
                actual_quantity = item['estimated_quantity'] * 0.9
                actual_cost = actual_quantity * item.get('cost_per_unit', 100)
                total_supply_cost += actual_cost

                consumed_items.append({
                    "item_id": item['item_id'],
                    "actual_quantity_consumed": actual_quantity
                })

            # Add some other expenses
            other_expenses = 750.0

            consumption_payload = {
                "booking_id": self.test_booking_id,
                "items_consumed": consumed_items,
                "total_other_expenses": other_expenses,
                "notes": "Consumo real registrado en test E2E"
            }

            response = self.session.post(
                f"{self.backend_url}/api/event-consumption/",
                json=consumption_payload,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 201:
                result = response.json()
                self.test_consumption_id = result.get('consumption_id')
                consumption_data = result.get('consumption', {})
                self.created_resources.append(('consumption', self.test_consumption_id))

                calculated_total = consumption_data.get('total_cost', 0)

                self.log_step(
                    "Register Actual Consumption",
                    True,
                    {
                        'summary': f'Consumed {len(consumed_items)} items, total cost: ${calculated_total}',
                        'consumption_id': self.test_consumption_id,
                        'supply_cost': consumption_data.get('total_supply_cost', 0),
                        'other_expenses': other_expenses,
                        'total_cost': calculated_total,
                        'items_consumed': len(consumed_items)
                    }
                )
                return True
            else:
                error_data = response.json() if response.status_code != 500 else {'error': response.text}
                self.log_step(
                    "Register Actual Consumption",
                    False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_step("Register Actual Consumption", False, error=str(e))
            return False

    def verify_booking_financial_update(self) -> bool:
        """Step 5: Verify booking was updated with financial data"""
        if not self.test_booking_id:
            self.log_step("Verify Financial Update", False, error="No booking ID available")
            return False

        try:
            # Wait a moment for async operations
            time.sleep(1)

            # Get updated booking
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            if response.status_code != 200:
                self.log_step("Verify Financial Update", False, error="Could not fetch bookings")
                return False

            bookings = response.json()
            updated_booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not updated_booking:
                self.log_step("Verify Financial Update", False, error="Booking not found")
                return False

            # Check financial structure
            has_financials = 'financials' in updated_booking
            financials = updated_booking.get('financials', {})

            required_fields = ['total_expenses', 'supply_cost', 'other_expenses']
            has_all_fields = all(field in financials for field in required_fields)

            # Verify values make sense
            total_expenses = financials.get('total_expenses', 0)
            supply_cost = financials.get('supply_cost', 0)
            other_expenses = financials.get('other_expenses', 0)

            calculation_correct = abs(total_expenses - (supply_cost + other_expenses)) < 0.01

            success = has_financials and has_all_fields and calculation_correct and total_expenses > 0

            self.log_step(
                "Verify Financial Update",
                success,
                {
                    'summary': f'Total: ${total_expenses} (Supply: ${supply_cost} + Other: ${other_expenses})',
                    'has_financials': has_financials,
                    'has_all_fields': has_all_fields,
                    'calculation_correct': calculation_correct,
                    'financials': financials,
                    'booking_structure': {
                        'has_expenses': 'expenses' in updated_booking,
                        'expenses_count': len(updated_booking.get('expenses', [])),
                        'has_financials': has_financials
                    }
                },
                None if success else "Booking financials not properly updated"
            )

            return success

        except Exception as e:
            self.log_step("Verify Financial Update", False, error=str(e))
            return False

    def simulate_completar_evento_modal(self) -> bool:
        """Step 6: Simulate opening 'Completar Evento' modal"""
        if not self.test_booking_id:
            self.log_step("Simulate Completar Evento Modal", False, error="No booking ID available")
            return False

        try:
            # Get booking as the frontend would
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            if response.status_code != 200:
                self.log_step("Simulate Completar Evento Modal", False, error="Could not fetch bookings")
                return False

            bookings = response.json()
            booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not booking:
                self.log_step("Simulate Completar Evento Modal", False, error="Booking not found")
                return False

            # Simulate handleOpenCostDialog logic exactly as in frontend
            accumulated_expenses = sum(expense.get('amount', 0) for expense in booking.get('expenses', []))
            total_cost_with_supplies = booking.get('financials', {}).get('total_expenses') or accumulated_expenses or booking.get('event_cost', '')

            # What would the modal show?
            estimated_price = booking.get('estimated_price', 0)
            profit = estimated_price - total_cost_with_supplies if total_cost_with_supplies else 0

            uses_supply_calculation = booking.get('financials', {}).get('total_expenses') is not None
            cost_breakdown = booking.get('financials', {}) if uses_supply_calculation else {
                'legacy_expenses': accumulated_expenses
            }

            success = uses_supply_calculation and total_cost_with_supplies > 0

            self.log_step(
                "Simulate Completar Evento Modal",
                success,
                {
                    'summary': f'Modal shows: ${total_cost_with_supplies} ({"Supply calc" if uses_supply_calculation else "Legacy calc"})',
                    'uses_supply_calculation': uses_supply_calculation,
                    'total_cost': total_cost_with_supplies,
                    'estimated_price': estimated_price,
                    'calculated_profit': profit,
                    'cost_breakdown': cost_breakdown,
                    'modal_would_show': {
                        'event_cost': total_cost_with_supplies,
                        'event_profit': estimated_price,
                        'cost_source': 'supply_calculation' if uses_supply_calculation else 'legacy_expenses'
                    }
                },
                "Modal would show legacy costs instead of calculated supply costs" if not success else None
            )

            return success

        except Exception as e:
            self.log_step("Simulate Completar Evento Modal", False, error=str(e))
            return False

    def complete_event(self) -> bool:
        """Step 7: Complete the event"""
        if not self.test_booking_id:
            self.log_step("Complete Event", False, error="No booking ID available")
            return False

        try:
            # Get the final cost from the booking
            response = self.session.get(f"{self.backend_url}/api/bookings/")
            bookings = response.json()
            booking = next((b for b in bookings if b['id'] == self.test_booking_id), None)

            if not booking:
                self.log_step("Complete Event", False, error="Booking not found")
                return False

            total_cost = booking.get('financials', {}).get('total_expenses', 0)
            estimated_price = booking.get('estimated_price', 0)

            completion_data = {
                "status": "completed",
                "event_cost": total_cost,
                "event_profit": estimated_price,
                "notes": "Evento completado via test E2E"
            }

            response = self.session.put(
                f"{self.backend_url}/api/bookings/{self.test_booking_id}",
                json=completion_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()

                self.log_step(
                    "Complete Event",
                    True,
                    {
                        'summary': f'Event completed with cost: ${total_cost}',
                        'final_cost': total_cost,
                        'estimated_price': estimated_price,
                        'profit': estimated_price - total_cost,
                        'booking_id': self.test_booking_id
                    }
                )
                return True
            else:
                error_data = response.json() if response.status_code != 500 else {'error': response.text}
                self.log_step(
                    "Complete Event",
                    False,
                    error=f"HTTP {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            self.log_step("Complete Event", False, error=str(e))
            return False

    def cleanup_test_data(self):
        """Clean up test data if requested"""
        if not self.cleanup:
            print("\n🗂️  Test data preserved for manual inspection:")
            print(f"   Booking ID: {self.test_booking_id}")
            print(f"   Supplies ID: {self.test_supplies_id}")
            print(f"   Consumption ID: {self.test_consumption_id}")
            return

        print("\n🧹 Cleaning up test data...")

        # Note: We don't actually delete in production to avoid data loss
        # In a real scenario, you might want to mark test data differently
        print("   (Cleanup skipped in production environment)")

    def run_e2e_test(self) -> Dict[str, Any]:
        """Run complete end-to-end test"""
        print("🎭 Starting End-to-End Event-Inventory Integration Test")
        print(f"🌐 Backend URL: {self.backend_url}")
        print(f"🧹 Cleanup: {'Enabled' if self.cleanup else 'Disabled'}")
        print("=" * 70)

        workflow_steps = [
            ("Creating test booking", self.create_test_booking),
            ("Adding traditional expenses", self.add_traditional_expenses),
            ("Adding supply estimation", self.add_supply_estimation),
            ("Registering actual consumption", self.register_actual_consumption),
            ("Verifying financial update", self.verify_booking_financial_update),
            ("Simulating Completar Evento modal", self.simulate_completar_evento_modal),
            ("Completing event", self.complete_event)
        ]

        print("📋 Workflow Steps:")
        for i, (step_name, _) in enumerate(workflow_steps, 1):
            print(f"   {i}. {step_name}")
        print()

        # Execute workflow
        for step_name, step_function in workflow_steps:
            print(f"🔄 {step_name}...")
            success = step_function()

            if not success:
                print(f"💥 Workflow failed at: {step_name}")
                break

            time.sleep(0.5)  # Small delay between steps

        self.cleanup_test_data()
        return self.generate_e2e_report()

    def generate_e2e_report(self) -> Dict[str, Any]:
        """Generate comprehensive E2E test report"""
        passed_steps = [r for r in self.test_results if r['success']]
        failed_steps = [r for r in self.test_results if not r['success']]

        report = {
            'test_summary': {
                'total_steps': len(self.test_results),
                'passed': len(passed_steps),
                'failed': len(failed_steps),
                'success_rate': len(passed_steps) / len(self.test_results) * 100 if self.test_results else 0,
                'workflow_completed': len(failed_steps) == 0
            },
            'backend_url': self.backend_url,
            'test_resources': {
                'booking_id': self.test_booking_id,
                'supplies_id': self.test_supplies_id,
                'consumption_id': self.test_consumption_id
            },
            'workflow_steps': self.test_results,
            'failed_steps': failed_steps,
            'diagnosis': self.diagnose_e2e_issues()
        }

        print("\n" + "=" * 70)
        print("📊 END-TO-END TEST REPORT")
        print("=" * 70)
        print(f"✅ Passed Steps: {len(passed_steps)}")
        print(f"❌ Failed Steps: {len(failed_steps)}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"🎯 Workflow Complete: {'Yes' if report['test_summary']['workflow_completed'] else 'No'}")

        if failed_steps:
            print("\n❌ FAILED STEPS:")
            for step in failed_steps:
                print(f"   - {step['step']}: {step['error']}")

        diagnosis = report['diagnosis']
        if diagnosis:
            print(f"\n🔍 DIAGNOSIS:")
            for issue in diagnosis:
                print(f"   - {issue}")

        return report

    def diagnose_e2e_issues(self) -> List[str]:
        """Diagnose E2E workflow issues"""
        issues = []

        # Check which steps failed
        failed_steps = [r for r in self.test_results if not r['success']]

        if not failed_steps:
            issues.append("✅ Complete workflow successful - cost calculation integration working correctly")
            return issues

        # Analyze failure patterns
        step_names = [r['step'] for r in failed_steps]

        if "Create Test Booking" in step_names:
            issues.append("❌ Cannot create test bookings - check backend booking API and validation")

        if "Add Supply Estimation" in step_names:
            issues.append("❌ Supply estimation failed - check inventory API and event-supplies endpoint")

        if "Register Actual Consumption" in step_names:
            issues.append("❌ CRITICAL: Consumption registration failed - check event-consumption API")

        if "Verify Financial Update" in step_names:
            issues.append("❌ CRITICAL: Booking financials not updated - backend not updating booking.financials")

        if "Simulate Completar Evento Modal" in step_names:
            issues.append("❌ CRITICAL: Modal simulation failed - frontend would show wrong costs")

        # Check specific issues
        financial_verification = next((r for r in self.test_results if r['step'] == 'Verify Financial Update'), None)
        if financial_verification and not financial_verification['success']:
            issues.append("🔥 ROOT CAUSE: Backend event-consumption not updating booking.financials correctly")

        modal_simulation = next((r for r in self.test_results if r['step'] == 'Simulate Completar Evento Modal'), None)
        if modal_simulation and not modal_simulation['success']:
            issues.append("🔥 ROOT CAUSE: Frontend cost dialog logic not finding calculated supply costs")

        return issues


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run End-to-End Event-Inventory Integration Test')
    parser.add_argument('--local', action='store_true', help='Test against local backend')
    parser.add_argument('--cleanup', action='store_true', help='Clean up test data after completion')
    args = parser.parse_args()

    backend_url = "http://localhost:8000" if args.local else "https://main-4kqeqojbsq-uc.a.run.app"

    tester = E2EWorkflowTester(backend_url, cleanup=args.cleanup)
    report = tester.run_e2e_test()

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"e2e_workflow_test_report_{timestamp}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Detailed report saved to: {report_file}")

    # Exit based on results
    if report['test_summary']['workflow_completed']:
        print("\n🎉 End-to-end workflow completed successfully!")
        print("💰 Cost calculation integration is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  End-to-end workflow failed - check the report for debugging information")
        sys.exit(1)


if __name__ == "__main__":
    main()