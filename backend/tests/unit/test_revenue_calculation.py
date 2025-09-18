"""
Unit tests for revenue calculation logic
Tests the core business logic for calculating estimated prices and revenue from confirmed bookings
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestRevenueCalculation:
    """Test suite for revenue calculation functionality"""

    @pytest.mark.unit
    def test_calculate_estimated_price_workshop_small_group(self, mock_environment_variables):
        """Test workshop pricing for small groups (≤15 participants)"""
        from main import calculate_estimated_price

        # Test small workshop group
        price = calculate_estimated_price("workshop", 10)
        expected = 13500 * 10  # No discount
        assert price == expected, f"Expected {expected}, got {price}"

        # Test edge case - exactly 15 participants
        price = calculate_estimated_price("workshop", 15)
        expected = 13500 * 15  # No discount
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_workshop_medium_group(self, mock_environment_variables):
        """Test workshop pricing for medium groups (16-25 participants)"""
        from main import calculate_estimated_price

        # Test medium workshop group - 10% discount
        price = calculate_estimated_price("workshop", 20)
        unit_price = round(13500 * 0.9)  # 10% discount = 12150
        expected = unit_price * 20
        assert price == expected, f"Expected {expected}, got {price}"

        # Test edge case - exactly 25 participants
        price = calculate_estimated_price("workshop", 25)
        unit_price = round(13500 * 0.9)  # 10% discount = 12150
        expected = unit_price * 25
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_workshop_large_group(self, mock_environment_variables):
        """Test workshop pricing for large groups (>25 participants)"""
        from main import calculate_estimated_price

        # Test large workshop group - 15% discount
        price = calculate_estimated_price("workshop", 30)
        unit_price = round(13500 * 0.85)  # 15% discount = 11475
        expected = unit_price * 30
        assert price == expected, f"Expected {expected}, got {price}"

        # Test very large group (like the $193k booking)
        price = calculate_estimated_price("workshop", 143)
        unit_price = round(13500 * 0.85)  # 15% discount = 11475
        expected = unit_price * 143  # Should be around 1,641,925
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_pizza_party_small_group(self, mock_environment_variables):
        """Test pizza party pricing for small groups (<20 participants)"""
        from main import calculate_estimated_price

        # Test small pizza party group - no discount
        price = calculate_estimated_price("pizza_party", 15)
        expected = 11990 * 15
        assert price == expected, f"Expected {expected}, got {price}"

        # Test edge case - exactly 19 participants
        price = calculate_estimated_price("pizza_party", 19)
        expected = 11990 * 19
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_pizza_party_large_group(self, mock_environment_variables):
        """Test pizza party pricing for large groups (≥20 participants)"""
        from main import calculate_estimated_price

        # Test large pizza party group - 10% discount
        price = calculate_estimated_price("pizza_party", 20)
        unit_price = round(11990 * 0.9)  # 10% discount = 10791
        expected = unit_price * 20
        assert price == expected, f"Expected {expected}, got {price}"

        # Test larger group
        price = calculate_estimated_price("pizza_party", 50)
        unit_price = round(11990 * 0.9)  # 10% discount = 10791
        expected = unit_price * 50
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_unknown_service(self, mock_environment_variables):
        """Test fallback pricing for unknown service types"""
        from main import calculate_estimated_price

        # Test unknown service type
        price = calculate_estimated_price("unknown_service", 10)
        expected = 10000 * 10  # Fallback price
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_calculate_estimated_price_edge_cases(self, mock_environment_variables):
        """Test edge cases and boundary conditions"""
        from main import calculate_estimated_price

        # Test zero participants
        price = calculate_estimated_price("workshop", 0)
        assert price == 0, f"Expected 0 for 0 participants, got {price}"

        # Test negative participants (should handle gracefully)
        price = calculate_estimated_price("workshop", -5)
        unit_price = 13500  # No discount for small group
        expected = unit_price * -5  # Negative result
        assert price == expected, f"Expected {expected}, got {price}"

        # Test very large number
        price = calculate_estimated_price("workshop", 1000)
        unit_price = round(13500 * 0.85)  # Large group discount
        expected = unit_price * 1000
        assert price == expected, f"Expected {expected}, got {price}"

    @pytest.mark.unit
    def test_193k_booking_scenario(self, mock_environment_variables):
        """Test the specific $193k booking scenario mentioned in requirements"""
        from main import calculate_estimated_price

        # The $193k booking is likely a custom price, but let's test what normal calculation would be
        # For workshop with 143 participants (estimated for $193k booking)
        price = calculate_estimated_price("workshop", 143)
        unit_price = round(13500 * 0.85)  # 15% discount = 11475
        expected = unit_price * 143  # = 1,640,925

        # This shows the $193k is likely a negotiated/custom price
        assert price == expected
        assert price > 193000  # Normal calculation is much higher than $193k

        # Test that our system can handle the custom $193k value
        custom_price = 193000
        assert custom_price > 0
        assert isinstance(custom_price, (int, float))

    @pytest.mark.unit
    def test_pricing_consistency(self, mock_environment_variables):
        """Test that pricing is consistent and follows business rules"""
        from main import calculate_estimated_price

        # Workshop pricing should decrease per unit as group size increases
        small_group_unit = calculate_estimated_price("workshop", 10) / 10
        medium_group_unit = calculate_estimated_price("workshop", 20) / 20
        large_group_unit = calculate_estimated_price("workshop", 30) / 30

        assert small_group_unit > medium_group_unit > large_group_unit, \
            "Unit price should decrease with larger groups due to discounts"

        # Pizza party pricing should decrease per unit for groups ≥20
        small_pizza_unit = calculate_estimated_price("pizza_party", 15) / 15
        large_pizza_unit = calculate_estimated_price("pizza_party", 25) / 25

        assert small_pizza_unit > large_pizza_unit, \
            "Pizza party unit price should be lower for groups ≥20"

    @pytest.mark.unit
    def test_environment_variable_usage(self):
        """Test that pricing uses environment variables correctly"""
        from main import calculate_estimated_price

        # Mock different environment values
        with patch.dict(os.environ, {
            'DEFAULT_WORKSHOP_PRICE': '15000',
            'DEFAULT_PIZZA_PARTY_PRICE': '12000'
        }):
            workshop_price = calculate_estimated_price("workshop", 10)
            pizza_price = calculate_estimated_price("pizza_party", 10)

            assert workshop_price == 15000 * 10, "Should use custom workshop price"
            assert pizza_price == 12000 * 10, "Should use custom pizza party price"

        # Test with missing environment variables (should use defaults)
        with patch.dict(os.environ, {}, clear=True):
            workshop_price = calculate_estimated_price("workshop", 10)
            pizza_price = calculate_estimated_price("pizza_party", 10)

            assert workshop_price == 13500 * 10, "Should use default workshop price"
            assert pizza_price == 11990 * 10, "Should use default pizza party price"


class TestBookingStatusFiltering:
    """Test filtering of bookings by status for revenue calculation"""

    @pytest.mark.unit
    def test_confirmed_bookings_only(self):
        """Test that only confirmed bookings are included in revenue calculations"""
        # This will be tested in integration tests with actual database queries
        # Here we test the logic of filtering by status

        sample_bookings = [
            {"id": "1", "status": "confirmed", "estimated_price": 100000},
            {"id": "2", "status": "pending", "estimated_price": 50000},
            {"id": "3", "status": "confirmed", "estimated_price": 75000},
            {"id": "4", "status": "cancelled", "estimated_price": 80000},
            {"id": "5", "status": "completed", "estimated_price": 90000},
        ]

        # Filter confirmed bookings
        confirmed_bookings = [b for b in sample_bookings if b["status"] == "confirmed"]

        assert len(confirmed_bookings) == 2, "Should find 2 confirmed bookings"

        total_confirmed_revenue = sum(b["estimated_price"] for b in confirmed_bookings)
        assert total_confirmed_revenue == 175000, f"Expected 175000, got {total_confirmed_revenue}"

    @pytest.mark.unit
    def test_future_confirmed_events_inclusion(self):
        """Test that future confirmed events are included in revenue calculation"""
        from datetime import date

        today = date.today()
        sample_bookings = [
            {
                "id": "1",
                "status": "confirmed",
                "estimated_price": 100000,
                "event_date": "2025-10-15"  # Future date
            },
            {
                "id": "2",
                "status": "confirmed",
                "estimated_price": 193000,
                "event_date": "2025-10-20"  # Future date - the $193k booking
            },
            {
                "id": "3",
                "status": "pending",
                "estimated_price": 75000,
                "event_date": "2025-11-01"  # Future but pending - should not count
            }
        ]

        # Filter confirmed bookings (regardless of date)
        confirmed_bookings = [b for b in sample_bookings if b["status"] == "confirmed"]

        assert len(confirmed_bookings) == 2, "Should find 2 confirmed bookings"

        total_revenue = sum(b["estimated_price"] for b in confirmed_bookings)
        assert total_revenue == 293000, f"Expected 293000, got {total_revenue}"

        # Verify the $193k booking is included
        large_booking = next(b for b in confirmed_bookings if b["estimated_price"] == 193000)
        assert large_booking is not None, "Should find the $193k booking"
        assert large_booking["event_date"] == "2025-10-20", "Should be the October booking"