#!/usr/bin/env python3
"""
Test runner script for Pablo's Pizza Backend Tests
Runs comprehensive tests to verify dashboard revenue calculation and chat CORS functionality
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Run a command and print results"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    print()

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.stdout:
        print("STDOUT:")
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    print(f"\nReturn code: {result.returncode}")
    return result.returncode == 0

def install_test_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")

    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if not in_venv:
        print("⚠️  Warning: Not in a virtual environment. Consider activating venv first.")

    # Install test requirements
    test_req_path = Path(__file__).parent / "test_requirements.txt"
    if test_req_path.exists():
        success = run_command(f"pip install -r {test_req_path}", "Installing test dependencies")
        if not success:
            print("❌ Failed to install test dependencies")
            return False
    else:
        print("❌ test_requirements.txt not found")
        return False

    return True

def run_revenue_tests():
    """Run dashboard revenue calculation tests"""
    print("\n💰 Running Dashboard Revenue Tests...")

    commands = [
        ("pytest tests/unit/test_revenue_calculation.py -v -m unit", "Unit Tests - Revenue Calculation Logic"),
        ("pytest tests/integration/test_dashboard_revenue.py -v -m dashboard", "Integration Tests - Dashboard Revenue with $193k Booking"),
    ]

    all_passed = True
    for command, description in commands:
        success = run_command(command, description)
        if not success:
            all_passed = False

    return all_passed

def run_chat_cors_tests():
    """Run chat CORS API tests"""
    print("\n💬 Running Chat CORS Tests...")

    commands = [
        ("pytest tests/integration/test_chat_cors.py -v -m chat", "Integration Tests - Chat CORS API"),
    ]

    all_passed = True
    for command, description in commands:
        success = run_command(command, description)
        if not success:
            all_passed = False

    return all_passed

def run_all_tests():
    """Run all tests with coverage"""
    print("\n🧪 Running All Tests with Coverage...")

    commands = [
        ("pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html", "All Tests with Coverage Report"),
    ]

    all_passed = True
    for command, description in commands:
        success = run_command(command, description)
        if not success:
            all_passed = False

    return all_passed

def run_specific_scenario_tests():
    """Run tests for specific scenarios mentioned in requirements"""
    print("\n🎯 Running Specific Scenario Tests...")

    commands = [
        # Test the $193k booking scenario specifically
        ("pytest tests/integration/test_dashboard_revenue.py::TestDashboardRevenueIntegration::test_dashboard_revenue_with_193k_booking -v -s",
         "Test $193,000 October 2025 Booking Scenario"),

        # Test confirmed vs pending booking filtering
        ("pytest tests/integration/test_dashboard_revenue.py::TestDashboardRevenueIntegration::test_dashboard_excludes_non_confirmed_bookings -v -s",
         "Test Confirmed Bookings Filtering"),

        # Test future events inclusion
        ("pytest tests/integration/test_dashboard_revenue.py::TestDashboardRevenueIntegration::test_future_confirmed_events_included_in_revenue -v -s",
         "Test Future Confirmed Events in Revenue"),

        # Test chat CORS with active_only parameter
        ("pytest tests/integration/test_chat_cors.py::TestChatCORSIntegration::test_chat_rooms_get_active_only_parameter -v -s",
         "Test Chat Rooms API with active_only Parameter"),

        # Test CORS headers
        ("pytest tests/integration/test_chat_cors.py::TestChatCORSIntegration::test_chat_rooms_get_with_cors_headers -v -s",
         "Test CORS Headers in Chat API"),
    ]

    all_passed = True
    for command, description in commands:
        success = run_command(command, description)
        if not success:
            all_passed = False

    return all_passed

def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n📊 Generating Test Report...")

    # Run tests with JSON output for detailed reporting
    json_report = run_command(
        "pytest tests/ --json-report --json-report-file=test_report.json -v",
        "Generating JSON Test Report"
    )

    # Generate HTML coverage report
    html_coverage = run_command(
        "pytest tests/ --cov=. --cov-report=html:htmlcov --cov-report=term",
        "Generating HTML Coverage Report"
    )

    if html_coverage:
        coverage_path = Path(__file__).parent / "htmlcov" / "index.html"
        if coverage_path.exists():
            print(f"📈 Coverage report generated: {coverage_path.absolute()}")

    return json_report and html_coverage

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Pablo's Pizza Backend Test Runner")
    parser.add_argument("--revenue", action="store_true", help="Run only revenue calculation tests")
    parser.add_argument("--chat", action="store_true", help="Run only chat CORS tests")
    parser.add_argument("--scenarios", action="store_true", help="Run specific scenario tests")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--report", action="store_true", help="Generate detailed test report")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")

    args = parser.parse_args()

    print("🍕 Pablo's Pizza Backend Test Suite")
    print("=" * 50)
    print("Testing Dashboard Revenue & Chat CORS Functionality")
    print("=" * 50)

    # Change to the script directory
    os.chdir(Path(__file__).parent)

    success = True

    # Install dependencies if requested
    if args.install or not Path("test_requirements.txt").exists():
        if not install_test_dependencies():
            print("❌ Failed to install dependencies")
            sys.exit(1)

    # Run specific test suites based on arguments
    if args.revenue:
        success = run_revenue_tests()
    elif args.chat:
        success = run_chat_cors_tests()
    elif args.scenarios:
        success = run_specific_scenario_tests()
    elif args.report:
        success = generate_test_report()
    else:  # Default: run all tests
        print("\n🏃 Running comprehensive test suite...")

        # Run revenue tests
        revenue_success = run_revenue_tests()

        # Run chat CORS tests
        chat_success = run_chat_cors_tests()

        # Run scenario tests
        scenario_success = run_specific_scenario_tests()

        success = revenue_success and chat_success and scenario_success

        # Generate coverage report
        if success:
            print("\n📊 All tests passed! Generating coverage report...")
            run_command("pytest tests/ --cov=. --cov-report=term --cov-report=html",
                       "Final Coverage Report")

    # Summary
    print("\n" + "="*60)
    print("🏁 TEST SUMMARY")
    print("="*60)

    if success:
        print("✅ All tests PASSED!")
        print("\nKey Verifications:")
        print("  ✅ Dashboard correctly calculates revenue from confirmed bookings")
        print("  ✅ Future confirmed events (including $193k Oct 2025) are included")
        print("  ✅ Chat API endpoints work with proper CORS headers")
        print("  ✅ active_only parameter filters chat rooms correctly")
        print("  ✅ Error handling maintains CORS compatibility")
        print("\nThe fixes have been verified and are working correctly! 🎉")
    else:
        print("❌ Some tests FAILED!")
        print("\nPlease review the test output above to identify issues.")
        print("Common fixes:")
        print("  - Check database connection mocking")
        print("  - Verify CORS configuration in main.py")
        print("  - Ensure booking status filtering logic")

    print(f"\nTest files created:")
    print(f"  - tests/unit/test_revenue_calculation.py")
    print(f"  - tests/integration/test_dashboard_revenue.py")
    print(f"  - tests/integration/test_chat_cors.py")
    print(f"  - test_requirements.txt")
    print(f"  - pytest.ini")

    if Path("htmlcov/index.html").exists():
        print(f"\nCoverage report: {Path('htmlcov/index.html').absolute()}")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()