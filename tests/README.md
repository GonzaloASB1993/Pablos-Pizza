# Pablo's Pizza E2E Test Suite

## Overview

This comprehensive test suite verifies that the recent CORS and API fixes for Pablo's Pizza application are working correctly. The tests simulate the exact user scenarios that were previously failing due to CORS policy violations and API endpoint issues.

## 🎯 Test Coverage

### Core Scenarios Tested

1. **Contact Form E2E Test**
   - **URL**: https://pablospizza.web.app/contacto
   - **Test**: Fill and submit contact form
   - **Expected**: Successfully create chat room via `/api/chat/rooms`
   - **Previous Error**: `Access to XMLHttpRequest blocked by CORS policy`

2. **Photo Upload E2E Test**
   - **URL**: https://pablospizza.web.app/admin (Events Management)
   - **Test**: Upload photo to an event
   - **Expected**: Successfully upload via `/api/gallery/upload`
   - **Previous Error**: `POST /api/gallery/upload 400 (Bad Request)`

3. **Gallery Loading E2E Test**
   - **URL**: https://pablospizza.web.app/admin (Events Management)
   - **Test**: Load event photos
   - **Expected**: Successfully load via `/api/gallery/?event_id=...`
   - **Previous Error**: `No 'Access-Control-Allow-Origin' header`

### API Endpoints Tested

- ✅ **Health Check**: `https://main-4kqeqojbsq-uc.a.run.app/api/health`
- ✅ **Chat Rooms**: `https://main-4kqeqojbsq-uc.a.run.app/api/chat/rooms`
- ✅ **Gallery Public**: `https://main-4kqeqojbsq-uc.a.run.app/api/gallery/public`
- ✅ **Gallery with Event ID**: `https://main-4kqeqojbsq-uc.a.run.app/api/gallery/?event_id=test`
- ✅ **Gallery Upload**: `https://main-4kqeqojbsq-uc.a.run.app/api/gallery/upload`

### CORS Validation

- ✅ **Preflight OPTIONS requests** are handled correctly
- ✅ **Access-Control-Allow-Origin** headers are present
- ✅ **Access-Control-Allow-Methods** headers include required methods
- ✅ **Access-Control-Allow-Headers** headers include Content-Type and Authorization
- ✅ **Error responses** (like 404) still include CORS headers

## 🚀 Running the Tests

### Method 1: Automated Script (Recommended)

#### Windows
```bash
cd tests
run-tests.bat
```

#### Unix/Linux/macOS
```bash
cd tests
chmod +x run-tests.sh
./run-tests.sh
```

### Method 2: Individual Test Types

#### Node.js API Tests
```bash
cd tests
node node-api-tests.js
```

#### Browser-based Tests
```bash
# Open in your browser:
file:///path/to/tests/browser-test-runner.html

# Or use the interactive HTML runner
```

#### Playwright E2E Tests
```bash
cd tests
npm install @playwright/test
npx playwright install chromium
npx playwright test playwright-e2e-tests.js
```

### Method 3: NPM Scripts

```bash
cd tests
npm install

# Run API tests
npm run test:api

# Run Playwright tests
npm run test:playwright

# Run all tests
npm run test:all

# Quick CORS check
npm run cors:check
```

## 📁 Test Files

| File | Description |
|------|-------------|
| `e2e-cors-api-tests.js` | Core browser-based test suite |
| `node-api-tests.js` | Node.js API testing without browser |
| `playwright-e2e-tests.js` | Playwright browser automation tests |
| `browser-test-runner.html` | Interactive HTML test runner |
| `package.json` | NPM dependencies and scripts |
| `run-tests.bat` | Windows automated test runner |
| `run-tests.sh` | Unix/Linux/macOS automated test runner |

## 🔍 Test Results

### Expected Results

- ✅ **All CORS errors should be resolved**
- ✅ **Contact form should successfully submit**
- ✅ **Photo uploads should work without 400 errors**
- ✅ **Gallery loading should work without CORS blocks**
- ✅ **All endpoints should return proper CORS headers**

### Sample Output

```
🎯 Starting Pablo's Pizza Node.js API Tests
===============================================

🧪 Running: Health Check Endpoint
Response: 200 OK
CORS Headers: {
  'access-control-allow-origin': 'https://pablospizza.web.app',
  'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'access-control-allow-headers': 'Content-Type, Authorization'
}
✅ PASS: Health Check Endpoint

🧪 Running: Contact Form - Chat Room Creation
Response: 201 Created
✅ PASS: Contact Form - Chat Room Creation

...

===============================================
🏁 Test Results Summary
===============================================
Total Tests: 7
Passed: 7 ✅
Failed: 0 ❌
Success Rate: 100.0%
Duration: 2847ms
```

## 🛠 Configuration

The test suite uses these endpoints by default:

```javascript
const TEST_CONFIG = {
  API_BASE_URL: 'https://main-4kqeqojbsq-uc.a.run.app/api',
  FRONTEND_URL: 'https://pablospizza.web.app',
  CONTACT_URL: 'https://pablospizza.web.app/contacto',
  ADMIN_URL: 'https://pablospizza.web.app/admin',
  TIMEOUT: 30000
}
```

## 🏥 Troubleshooting

### Common Issues

1. **Network Errors**
   - Check internet connection
   - Verify API endpoints are accessible
   - Check if firewall is blocking requests

2. **CORS Failures**
   - Verify the backend has proper CORS configuration
   - Check that origins include `https://pablospizza.web.app`
   - Ensure preflight OPTIONS requests are handled

3. **Test Timeouts**
   - API might be slow or unresponsive
   - Increase timeout in configuration
   - Check API status directly

### Debug Commands

```bash
# Quick health check
curl -H "Origin: https://pablospizza.web.app" \
     https://main-4kqeqojbsq-uc.a.run.app/api/health

# Check CORS preflight
curl -X OPTIONS \
     -H "Origin: https://pablospizza.web.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     https://main-4kqeqojbsq-uc.a.run.app/api/chat/rooms
```

## 📊 Test Types

### 1. Browser-based Tests (`e2e-cors-api-tests.js`)

- Run in browser environment
- Test actual CORS behavior
- Simulate real frontend requests
- **Best for**: Verifying CORS fixes work in production

### 2. Node.js API Tests (`node-api-tests.js`)

- Run in Node.js environment
- Direct HTTP requests
- No browser CORS restrictions
- **Best for**: API endpoint validation

### 3. Playwright E2E Tests (`playwright-e2e-tests.js`)

- Full browser automation
- Real user interaction simulation
- Screenshots and video recording
- **Best for**: Full user journey testing

### 4. Interactive HTML Runner (`browser-test-runner.html`)

- Visual test execution
- Real-time results display
- Individual test controls
- **Best for**: Manual testing and debugging

## 🔐 Security Notes

- Tests use public endpoints only
- No sensitive data is transmitted
- Admin tests may require authentication
- All test data is clearly marked as test data

## 📝 Contributing

To add new tests:

1. Add test method to appropriate test class
2. Update test runner configurations
3. Document new test in this README
4. Test on both development and production environments

## 📈 Performance

Typical test execution times:

- **Node.js API Tests**: 2-5 seconds
- **Browser Tests**: 10-30 seconds
- **Playwright Tests**: 30-60 seconds
- **Full Suite**: 1-2 minutes

## 🎉 Success Criteria

The test suite passes when:

1. ✅ All API endpoints return status codes < 400
2. ✅ All endpoints include required CORS headers
3. ✅ Contact form creates chat rooms successfully
4. ✅ Gallery endpoints handle requests properly
5. ✅ Error responses include CORS headers
6. ✅ Preflight OPTIONS requests work correctly

---

**Last Updated**: September 17, 2025
**Version**: 1.0.0
**Maintainer**: Pablo's Pizza Development Team