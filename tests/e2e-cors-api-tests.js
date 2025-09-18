/**
 * End-to-End CORS and API Tests for Pablo's Pizza Application
 *
 * This test suite verifies that the recent CORS and API fixes are working correctly
 * by testing the exact scenarios that were previously failing.
 *
 * Test Coverage:
 * 1. Contact Form E2E Test - Chat room creation via API
 * 2. Photo Upload E2E Test - File upload functionality
 * 3. Gallery Loading E2E Test - Image loading with event IDs
 * 4. CORS Headers Verification - All endpoints return proper headers
 * 5. API Response Validation - Correct data structures and status codes
 */

const TEST_CONFIG = {
  // Production API endpoints
  BASE_URL: 'https://main-4kqeqojbsq-uc.a.run.app/api',

  // Frontend application URLs
  FRONTEND_URL: 'https://pablospizza.web.app',
  CONTACT_URL: 'https://pablospizza.web.app/contacto',
  ADMIN_URL: 'https://pablospizza.web.app/admin',

  // Test timeouts
  TIMEOUT: 30000,
  CORS_TIMEOUT: 10000,

  // Expected CORS headers
  EXPECTED_CORS_HEADERS: [
    'access-control-allow-origin',
    'access-control-allow-methods',
    'access-control-allow-headers'
  ]
}

/**
 * Utility Functions
 */
class TestUtils {

  /**
   * Make HTTP request with detailed logging
   */
  static async makeRequest(url, options = {}) {
    const requestId = Math.random().toString(36).substr(2, 9)

    console.log(`🚀 [${requestId}] Request:`, {
      url,
      method: options.method || 'GET',
      headers: options.headers,
      timestamp: new Date().toISOString()
    })

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      })

      console.log(`✅ [${requestId}] Response:`, {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        timestamp: new Date().toISOString()
      })

      return response
    } catch (error) {
      console.error(`❌ [${requestId}] Error:`, {
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      })
      throw error
    }
  }

  /**
   * Check CORS headers on a response
   */
  static validateCorsHeaders(response, testName) {
    const headers = response.headers
    const corsResults = {
      testName,
      success: true,
      headers: {},
      errors: []
    }

    // Check for required CORS headers
    TEST_CONFIG.EXPECTED_CORS_HEADERS.forEach(headerName => {
      const headerValue = headers.get(headerName)
      corsResults.headers[headerName] = headerValue

      if (!headerValue) {
        corsResults.success = false
        corsResults.errors.push(`Missing header: ${headerName}`)
      }
    })

    // Validate specific CORS values
    const origin = headers.get('access-control-allow-origin')
    if (origin && origin !== '*' && !origin.includes('pablospizza.web.app')) {
      corsResults.success = false
      corsResults.errors.push(`Invalid Access-Control-Allow-Origin: ${origin}`)
    }

    console.log(`🔍 CORS Validation [${testName}]:`, corsResults)
    return corsResults
  }

  /**
   * Test preflight OPTIONS request
   */
  static async testPreflightRequest(url, method = 'POST') {
    console.log(`🔍 Testing preflight OPTIONS request for: ${url}`)

    try {
      const response = await fetch(url, {
        method: 'OPTIONS',
        headers: {
          'Origin': TEST_CONFIG.FRONTEND_URL,
          'Access-Control-Request-Method': method,
          'Access-Control-Request-Headers': 'Content-Type,Authorization'
        }
      })

      console.log(`✅ Preflight response:`, {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries())
      })

      return response
    } catch (error) {
      console.error(`❌ Preflight request failed:`, error)
      throw error
    }
  }

  /**
   * Create test FormData for file uploads
   */
  static createTestFormData() {
    const formData = new FormData()

    // Create a test image blob
    const canvas = document.createElement('canvas')
    canvas.width = 100
    canvas.height = 100
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#FF6B6B'
    ctx.fillRect(0, 0, 100, 100)
    ctx.fillStyle = '#FFFFFF'
    ctx.font = '12px Arial'
    ctx.fillText('TEST', 35, 55)

    canvas.toBlob(blob => {
      formData.append('image', blob, 'test-image.png')
    }, 'image/png')

    formData.append('title', 'Test Upload Image')
    formData.append('description', 'E2E test image upload')
    formData.append('event_id', 'test-event-123')
    formData.append('category', 'event_photos')

    return formData
  }

  /**
   * Generate test contact form data
   */
  static generateContactFormData() {
    const timestamp = new Date().toISOString()
    return {
      client_name: `Test User ${timestamp}`,
      client_email: `test.${Date.now()}@example.com`,
      phone: '+56912345678',
      message: `E2E test message sent at ${timestamp}`,
      subject: 'E2E Test Contact'
    }
  }
}

/**
 * Test Suite Class
 */
class PablosPizzaE2ETests {

  constructor() {
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      tests: []
    }
  }

  /**
   * Log test result
   */
  logResult(testName, success, details = {}) {
    this.results.total++

    if (success) {
      this.results.passed++
      console.log(`✅ PASS: ${testName}`)
    } else {
      this.results.failed++
      console.error(`❌ FAIL: ${testName}`)
    }

    this.results.tests.push({
      name: testName,
      success,
      details,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Test 1: Health Check Endpoint
   */
  async testHealthCheck() {
    const testName = 'Health Check Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/health`
      const response = await TestUtils.makeRequest(url)

      // Validate response
      const success = response.status === 200
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        data: responseData
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Test 2: Contact Form Chat Room Creation
   */
  async testContactFormChatCreation() {
    const testName = 'Contact Form - Chat Room Creation'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/chat/rooms`

      // Test preflight request first
      await TestUtils.testPreflightRequest(url, 'POST')

      // Prepare test data
      const contactData = TestUtils.generateContactFormData()

      // Make the actual request
      const response = await TestUtils.makeRequest(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': TEST_CONFIG.FRONTEND_URL
        },
        body: JSON.stringify(contactData)
      })

      // Validate response
      const success = response.status >= 200 && response.status < 300
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        requestData: contactData,
        responseData: responseData
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Test 3: Gallery Photo Upload
   */
  async testGalleryPhotoUpload() {
    const testName = 'Gallery - Photo Upload'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/gallery/upload`

      // Test preflight request first
      await TestUtils.testPreflightRequest(url, 'POST')

      // Create test form data
      const formData = TestUtils.createTestFormData()

      // Make the upload request
      const response = await TestUtils.makeRequest(url, {
        method: 'POST',
        headers: {
          'Origin': TEST_CONFIG.FRONTEND_URL
          // Note: Don't set Content-Type for FormData - browser sets it automatically
        },
        body: formData
      })

      // Validate response
      const success = response.status >= 200 && response.status < 300
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        responseData: responseData
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Test 4: Gallery Loading with Event ID
   */
  async testGalleryLoadingWithEventId() {
    const testName = 'Gallery - Loading with Event ID'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/gallery/?event_id=test-event-123`

      const response = await TestUtils.makeRequest(url, {
        headers: {
          'Origin': TEST_CONFIG.FRONTEND_URL
        }
      })

      // Validate response
      const success = response.status >= 200 && response.status < 300
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        responseData: responseData
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Test 5: Gallery Public Endpoint
   */
  async testGalleryPublic() {
    const testName = 'Gallery - Public Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/gallery/public`

      const response = await TestUtils.makeRequest(url, {
        headers: {
          'Origin': TEST_CONFIG.FRONTEND_URL
        }
      })

      // Validate response
      const success = response.status >= 200 && response.status < 300
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        responseData: responseData
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Test 6: Multiple CORS Origins Test
   */
  async testCorsOrigins() {
    const testName = 'CORS - Multiple Origins Test'
    console.log(`\n🧪 Running: ${testName}`)

    const origins = [
      'https://pablospizza.web.app',
      'https://localhost:3000',
      'http://localhost:5173'
    ]

    const results = []

    for (const origin of origins) {
      try {
        const url = `${TEST_CONFIG.BASE_URL}/health`
        const response = await TestUtils.makeRequest(url, {
          headers: { 'Origin': origin }
        })

        const corsValidation = TestUtils.validateCorsHeaders(response, `${testName} - ${origin}`)
        results.push({
          origin,
          success: corsValidation.success,
          details: corsValidation
        })
      } catch (error) {
        results.push({
          origin,
          success: false,
          error: error.message
        })
      }
    }

    const allSuccess = results.every(r => r.success)

    this.logResult(testName, allSuccess, { results })
    return allSuccess
  }

  /**
   * Test 7: Error Handling Test
   */
  async testErrorHandling() {
    const testName = 'Error Handling - 404 Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.BASE_URL}/nonexistent-endpoint`

      const response = await TestUtils.makeRequest(url, {
        headers: {
          'Origin': TEST_CONFIG.FRONTEND_URL
        }
      })

      // Should return 404 but still have CORS headers
      const is404 = response.status === 404
      const corsValidation = TestUtils.validateCorsHeaders(response, testName)

      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }

      this.logResult(testName, is404 && corsValidation.success, {
        status: response.status,
        cors: corsValidation,
        responseData: responseData
      })

      return is404 && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  /**
   * Run all tests
   */
  async runAllTests() {
    console.log('🎯 Starting Pablo\'s Pizza E2E CORS and API Tests')
    console.log('================================================\n')

    const startTime = Date.now()

    // Run all tests
    await this.testHealthCheck()
    await this.testContactFormChatCreation()
    await this.testGalleryPhotoUpload()
    await this.testGalleryLoadingWithEventId()
    await this.testGalleryPublic()
    await this.testCorsOrigins()
    await this.testErrorHandling()

    const endTime = Date.now()
    const duration = endTime - startTime

    // Print final results
    console.log('\n================================================')
    console.log('🏁 Test Results Summary')
    console.log('================================================')
    console.log(`Total Tests: ${this.results.total}`)
    console.log(`Passed: ${this.results.passed} ✅`)
    console.log(`Failed: ${this.results.failed} ❌`)
    console.log(`Success Rate: ${((this.results.passed / this.results.total) * 100).toFixed(1)}%`)
    console.log(`Duration: ${duration}ms`)

    // Detailed results
    console.log('\n📋 Detailed Results:')
    this.results.tests.forEach(test => {
      const status = test.success ? '✅' : '❌'
      console.log(`${status} ${test.name}`)
      if (!test.success && test.details.error) {
        console.log(`   Error: ${test.details.error}`)
      }
    })

    // CORS summary
    const corsTests = this.results.tests.filter(t => t.details.cors)
    if (corsTests.length > 0) {
      console.log('\n🔒 CORS Headers Summary:')
      corsTests.forEach(test => {
        if (test.details.cors) {
          console.log(`${test.success ? '✅' : '❌'} ${test.name}:`)
          Object.entries(test.details.cors.headers).forEach(([header, value]) => {
            console.log(`   ${header}: ${value || 'MISSING'}`)
          })
        }
      })
    }

    return {
      success: this.results.failed === 0,
      summary: this.results,
      duration
    }
  }
}

/**
 * Browser Testing Functions
 * These functions can be run directly in the browser console
 */

// Global function to run tests
window.runPablosPizzaE2ETests = async function() {
  const testSuite = new PablosPizzaE2ETests()
  return await testSuite.runAllTests()
}

// Quick individual test functions
window.testCorsHeaders = async function(endpoint = '/health') {
  const url = `${TEST_CONFIG.BASE_URL}${endpoint}`
  const response = await TestUtils.makeRequest(url, {
    headers: { 'Origin': TEST_CONFIG.FRONTEND_URL }
  })
  return TestUtils.validateCorsHeaders(response, `Quick CORS Test - ${endpoint}`)
}

window.testContactForm = async function() {
  const url = `${TEST_CONFIG.BASE_URL}/chat/rooms`
  const data = TestUtils.generateContactFormData()

  const response = await TestUtils.makeRequest(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': TEST_CONFIG.FRONTEND_URL
    },
    body: JSON.stringify(data)
  })

  console.log('Contact Form Test Result:', {
    status: response.status,
    cors: TestUtils.validateCorsHeaders(response, 'Quick Contact Test'),
    data: await response.json().catch(() => response.text())
  })
}

// Export for Node.js if needed
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PablosPizzaE2ETests,
    TestUtils,
    TEST_CONFIG
  }
}

console.log('🎯 Pablo\'s Pizza E2E Tests Loaded')
console.log('Run: runPablosPizzaE2ETests() to start all tests')
console.log('Run: testCorsHeaders() for quick CORS check')
console.log('Run: testContactForm() for quick contact form test')