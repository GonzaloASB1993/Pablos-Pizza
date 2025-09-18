/**
 * Node.js API Tests for Pablo's Pizza Application
 *
 * This test runner can be executed in Node.js environment to test
 * the API endpoints directly without a browser.
 *
 * Usage:
 * node tests/node-api-tests.js
 */

const https = require('https')
const http = require('http')
const { URL } = require('url')
const fs = require('fs')
const path = require('path')

const TEST_CONFIG = {
  API_BASE_URL: 'https://main-4kqeqojbsq-uc.a.run.app/api',
  FRONTEND_ORIGIN: 'https://pablospizza.web.app',
  TIMEOUT: 30000,
  EXPECTED_CORS_HEADERS: [
    'access-control-allow-origin',
    'access-control-allow-methods',
    'access-control-allow-headers'
  ]
}

/**
 * HTTP Request utility for Node.js
 */
class NodeHttpClient {
  static makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      const urlObj = new URL(url)
      const isHttps = urlObj.protocol === 'https:'
      const client = isHttps ? https : http

      const requestOptions = {
        hostname: urlObj.hostname,
        port: urlObj.port || (isHttps ? 443 : 80),
        path: urlObj.pathname + urlObj.search,
        method: options.method || 'GET',
        headers: {
          'User-Agent': 'PablosPizza-E2E-Tests/1.0',
          'Origin': TEST_CONFIG.FRONTEND_ORIGIN,
          ...options.headers
        },
        timeout: TEST_CONFIG.TIMEOUT
      }

      const req = client.request(requestOptions, (res) => {
        let data = ''

        res.on('data', (chunk) => {
          data += chunk
        })

        res.on('end', () => {
          resolve({
            status: res.statusCode,
            statusMessage: res.statusMessage,
            headers: res.headers,
            data: data,
            url: url
          })
        })
      })

      req.on('error', (error) => {
        reject(new Error(`Request failed: ${error.message}`))
      })

      req.on('timeout', () => {
        req.destroy()
        reject(new Error(`Request timeout: ${url}`))
      })

      if (options.body) {
        req.write(options.body)
      }

      req.end()
    })
  }

  static async makeFormDataRequest(url, formData) {
    // For Node.js, we'll simulate a multipart form data request
    const boundary = '----formdata-polyfill-' + Math.random().toString(36)
    let body = ''

    for (const [key, value] of Object.entries(formData)) {
      body += `--${boundary}\r\n`
      body += `Content-Disposition: form-data; name="${key}"\r\n\r\n`
      body += `${value}\r\n`
    }

    // Add a fake file
    body += `--${boundary}\r\n`
    body += `Content-Disposition: form-data; name="image"; filename="test.png"\r\n`
    body += `Content-Type: image/png\r\n\r\n`
    body += 'fake-binary-data\r\n'
    body += `--${boundary}--\r\n`

    return this.makeRequest(url, {
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': Buffer.byteLength(body)
      },
      body: body
    })
  }
}

/**
 * Test utilities
 */
class NodeTestUtils {
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
      const headerValue = headers[headerName]
      corsResults.headers[headerName] = headerValue

      if (!headerValue) {
        corsResults.success = false
        corsResults.errors.push(`Missing header: ${headerName}`)
      }
    })

    // Validate specific CORS values
    const origin = headers['access-control-allow-origin']
    if (origin && origin !== '*' && !origin.includes('pablospizza.web.app')) {
      corsResults.success = false
      corsResults.errors.push(`Invalid Access-Control-Allow-Origin: ${origin}`)
    }

    return corsResults
  }

  static parseResponseData(response) {
    try {
      return JSON.parse(response.data)
    } catch (e) {
      return response.data
    }
  }
}

/**
 * Node.js Test Suite
 */
class NodeApiTestSuite {
  constructor() {
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      tests: []
    }
  }

  logResult(testName, success, details = {}) {
    this.results.total++

    if (success) {
      this.results.passed++
      console.log(`✅ PASS: ${testName}`)
    } else {
      this.results.failed++
      console.error(`❌ FAIL: ${testName}`)
      if (details.error) {
        console.error(`   Error: ${details.error}`)
      }
    }

    this.results.tests.push({
      name: testName,
      success,
      details,
      timestamp: new Date().toISOString()
    })
  }

  async testHealthCheck() {
    const testName = 'Health Check Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/health`
      const response = await NodeHttpClient.makeRequest(url)

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status === 200
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)

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

  async testContactFormChatCreation() {
    const testName = 'Contact Form - Chat Room Creation'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/chat/rooms`
      const contactData = {
        client_name: `Test User ${Date.now()}`,
        client_email: `test.${Date.now()}@example.com`,
        phone: '+56912345678',
        message: `E2E test message sent at ${new Date().toISOString()}`,
        subject: 'E2E Test Contact'
      }

      console.log('Sending contact data:', contactData)

      const response = await NodeHttpClient.makeRequest(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(contactData)
      })

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status >= 200 && response.status < 300
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)
      console.log('Response Data:', responseData)

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

  async testGalleryPhotoUpload() {
    const testName = 'Gallery - Photo Upload'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/gallery/upload`
      const formData = {
        title: 'Test Upload Image',
        description: 'E2E test image upload',
        event_id: 'test-event-123',
        category: 'event_photos'
      }

      console.log('Sending form data:', formData)

      const response = await NodeHttpClient.makeFormDataRequest(url, formData)

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status >= 200 && response.status < 300
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)
      console.log('Response Data:', responseData)

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

  async testGalleryLoadingWithEventId() {
    const testName = 'Gallery - Loading with Event ID'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/gallery/?event_id=test-event-123`
      const response = await NodeHttpClient.makeRequest(url)

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status >= 200 && response.status < 300
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)

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

  async testGalleryPublic() {
    const testName = 'Gallery - Public Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/gallery/public`
      const response = await NodeHttpClient.makeRequest(url)

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status >= 200 && response.status < 300
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)

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

  async testErrorHandling() {
    const testName = 'Error Handling - 404 Endpoint'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/nonexistent-endpoint`
      const response = await NodeHttpClient.makeRequest(url)

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const is404 = response.status === 404
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)
      const responseData = NodeTestUtils.parseResponseData(response)

      console.log('CORS Headers:', corsValidation.headers)

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

  async testPreflightRequest() {
    const testName = 'CORS - Preflight OPTIONS Request'
    console.log(`\n🧪 Running: ${testName}`)

    try {
      const url = `${TEST_CONFIG.API_BASE_URL}/chat/rooms`
      const response = await NodeHttpClient.makeRequest(url, {
        method: 'OPTIONS',
        headers: {
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'Content-Type,Authorization'
        }
      })

      console.log(`Response: ${response.status} ${response.statusMessage}`)

      const success = response.status >= 200 && response.status < 300
      const corsValidation = NodeTestUtils.validateCorsHeaders(response, testName)

      console.log('CORS Headers:', corsValidation.headers)

      this.logResult(testName, success && corsValidation.success, {
        status: response.status,
        cors: corsValidation
      })

      return success && corsValidation.success
    } catch (error) {
      this.logResult(testName, false, { error: error.message })
      return false
    }
  }

  async runAllTests() {
    console.log('🎯 Starting Pablo\'s Pizza Node.js API Tests')
    console.log('===============================================\n')

    const startTime = Date.now()

    // Run all tests
    await this.testHealthCheck()
    await this.testPreflightRequest()
    await this.testContactFormChatCreation()
    await this.testGalleryPhotoUpload()
    await this.testGalleryLoadingWithEventId()
    await this.testGalleryPublic()
    await this.testErrorHandling()

    const endTime = Date.now()
    const duration = endTime - startTime

    // Print final results
    console.log('\n===============================================')
    console.log('🏁 Test Results Summary')
    console.log('===============================================')
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

    // Save results to file
    const resultsFile = path.join(__dirname, 'test-results.json')
    fs.writeFileSync(resultsFile, JSON.stringify(this.results, null, 2))
    console.log(`\n📄 Results saved to: ${resultsFile}`)

    return {
      success: this.results.failed === 0,
      summary: this.results,
      duration
    }
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  const testSuite = new NodeApiTestSuite()
  testSuite.runAllTests().then(result => {
    console.log(`\n🎯 Tests completed. Overall success: ${result.success}`)
    process.exit(result.success ? 0 : 1)
  }).catch(error => {
    console.error(`\n❌ Test suite failed: ${error.message}`)
    process.exit(1)
  })
}

module.exports = {
  NodeApiTestSuite,
  NodeTestUtils,
  NodeHttpClient,
  TEST_CONFIG
}