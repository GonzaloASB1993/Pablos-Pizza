# Pablo's Pizza Backend Test Suite Documentation

## Overview

This comprehensive test suite verifies the fixes for two critical issues:

1. **Dashboard Revenue Calculation**: Tests that confirmed bookings are properly included in revenue calculations, including future events and the specific $193,000 October 2025 booking scenario.

2. **Chat CORS Functionality**: Tests that the `/api/chat/rooms` endpoint works correctly with CORS headers and the `active_only` parameter.

## Test Structure

```
backend/tests/
├── conftest.py                    # Test configuration and fixtures
├── unit/
│   ├── __init__.py
│   └── test_revenue_calculation.py    # Unit tests for pricing logic
├── integration/
│   ├── __init__.py
│   ├── test_dashboard_revenue.py      # Dashboard revenue integration tests
│   └── test_chat_cors.py             # Chat CORS integration tests
├── test_requirements.txt         # Testing dependencies
├── pytest.ini                   # Pytest configuration
└── run_tests.py                 # Test runner script
```

## Key Test Scenarios

### 1. Dashboard Revenue Tests

#### Unit Tests (`test_revenue_calculation.py`)
- **Pricing Logic**: Tests workshop and pizza party pricing with different group sizes
- **Discount Calculation**: Verifies bulk discounts (10% for medium groups, 15% for large groups)
- **Edge Cases**: Tests zero participants, negative numbers, very large groups
- **$193k Scenario**: Validates the specific large corporate booking scenario
- **Status Filtering**: Tests filtering of confirmed vs pending bookings

#### Integration Tests (`test_dashboard_revenue.py`)
- **Complete Revenue Calculation**: Tests end-to-end revenue calculation with mock database
- **$193k Booking Integration**: Specifically tests the October 2025 $193,000 confirmed booking
- **Future Events Inclusion**: Verifies future confirmed events are included in revenue
- **Monthly vs Total Revenue**: Tests difference between monthly events and total confirmed revenue
- **Performance Testing**: Tests calculation performance with large datasets
- **Status Exclusion**: Verifies non-confirmed bookings are excluded from revenue

### 2. Chat CORS Tests

#### Integration Tests (`test_chat_cors.py`)
- **CORS Headers**: Verifies all API endpoints return proper CORS headers
- **active_only Parameter**: Tests filtering active vs all chat rooms
- **OPTIONS Preflight**: Tests CORS preflight requests
- **Error Handling**: Ensures CORS headers present even in error responses
- **Data Structure**: Validates frontend compatibility of API responses
- **Performance**: Tests API performance with large numbers of chat rooms

## Running the Tests

### Quick Start

1. **Install dependencies**:
   ```bash
   cd backend
   python run_tests.py --install
   ```

2. **Run all tests**:
   ```bash
   python run_tests.py
   ```

### Specific Test Suites

- **Revenue tests only**:
  ```bash
  python run_tests.py --revenue
  ```

- **Chat CORS tests only**:
  ```bash
  python run_tests.py --chat
  ```

- **Specific scenarios**:
  ```bash
  python run_tests.py --scenarios
  ```

- **Generate detailed report**:
  ```bash
  python run_tests.py --report
  ```

### Manual pytest Commands

- **All tests with coverage**:
  ```bash
  pytest tests/ -v --cov=. --cov-report=html
  ```

- **Revenue unit tests**:
  ```bash
  pytest tests/unit/test_revenue_calculation.py -v
  ```

- **Dashboard integration tests**:
  ```bash
  pytest tests/integration/test_dashboard_revenue.py -v
  ```

- **Chat CORS tests**:
  ```bash
  pytest tests/integration/test_chat_cors.py -v
  ```

- **Specific test**:
  ```bash
  pytest tests/integration/test_dashboard_revenue.py::TestDashboardRevenueIntegration::test_dashboard_revenue_with_193k_booking -v -s
  ```

## Test Data and Fixtures

### Sample Bookings
- **$193k Booking**: Large corporate workshop with 143 participants, confirmed status, October 2025
- **Future Bookings**: Various confirmed and pending bookings in future months
- **Mixed Status**: Bookings with different statuses to test filtering

### Mock Data Structure
```python
# Confirmed $193k booking
{
    "id": "booking-193k",
    "client_name": "Large Corporate Event",
    "service_type": "workshop",
    "participants": 143,
    "event_date": "2025-10-20",
    "estimated_price": 193000,
    "status": "confirmed"
}
```

### Chat Room Data
```python
# Sample chat room
{
    "id": "room-1",
    "client_name": "Test Client",
    "client_email": "client@example.com",
    "status": "open",
    "messages_count": 3
}
```

## Test Markers

Use pytest markers to run specific test categories:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.dashboard`: Dashboard-related tests
- `@pytest.mark.chat`: Chat functionality tests
- `@pytest.mark.slow`: Slow-running tests

Example:
```bash
pytest -m "dashboard and integration" -v
```

## Expected Test Results

### Dashboard Revenue Tests
✅ **Revenue Calculation**: Confirms correct pricing logic with discounts
✅ **$193k Inclusion**: Verifies the large October booking is included in total revenue
✅ **Status Filtering**: Only confirmed bookings count toward revenue
✅ **Future Events**: Future confirmed events are included regardless of date
✅ **Performance**: Calculations complete in under 1 second for 100+ bookings

### Chat CORS Tests
✅ **CORS Headers**: All endpoints return `Access-Control-Allow-Origin: *`
✅ **active_only Filter**: Properly filters active vs closed chat rooms
✅ **API Structure**: Response format matches frontend expectations
✅ **Error Handling**: CORS headers present even in error responses
✅ **Performance**: API responds in under 2 seconds for 200+ chat rooms

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the `backend/` directory
2. **Missing Dependencies**: Run `python run_tests.py --install`
3. **Firebase Errors**: Tests use mocked Firestore, no real Firebase connection needed
4. **Path Issues**: Tests automatically adjust Python path to import `main.py`

### Test Failures

If tests fail:
1. Check the specific error message in test output
2. Verify mock data matches expected structure
3. Ensure CORS configuration in `main.py` allows all origins
4. Check that booking status filtering logic is correct

## Coverage Goals

- **Overall Coverage**: 80%+ (configured in pytest.ini)
- **Revenue Logic**: 100% coverage of pricing calculations
- **CORS Endpoints**: 100% coverage of chat API endpoints
- **Error Handling**: Coverage of error scenarios

## Integration with CI/CD

This test suite is designed to integrate with CI/CD pipelines:

```bash
# In CI environment
pip install -r test_requirements.txt
python run_tests.py --report
```

The tests use mocked Firebase connections, so no external dependencies are required in CI.

## Test Maintenance

### Adding New Tests
1. Follow existing naming conventions
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Mock external dependencies (Firebase, email, etc.)
4. Include both success and failure scenarios

### Updating Mock Data
- Update fixtures in `conftest.py` when data structure changes
- Ensure test data reflects real-world scenarios
- Include edge cases and boundary conditions

---

## Verification Checklist

This test suite verifies the following fixes:

### Dashboard Revenue Calculation ✅
- [x] Events with status 'confirmed' are included in revenue calculation
- [x] Future confirmed events (beyond current month) are included
- [x] The $193,000 booking is correctly handled
- [x] Monthly events vs confirmed revenue logic works properly
- [x] Pending/cancelled bookings are excluded from revenue

### Chat CORS Functionality ✅
- [x] `/api/chat/rooms` endpoint works with `active_only` parameter
- [x] CORS headers (`Access-Control-Allow-Origin`, etc.) are present
- [x] Data structure matches frontend expectations
- [x] Error handling maintains CORS compatibility
- [x] OPTIONS preflight requests work correctly

**All critical functionality has been thoroughly tested and verified!** 🎉