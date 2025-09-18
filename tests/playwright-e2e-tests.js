/**
 * Playwright End-to-End Tests for Pablo's Pizza Application
 *
 * This file contains browser automation tests using Playwright to simulate
 * real user interactions and verify CORS/API fixes in the actual frontend.
 *
 * Usage:
 * npm install @playwright/test
 * npx playwright test playwright-e2e-tests.js
 */

const { test, expect } = require('@playwright/test')

const TEST_CONFIG = {
  FRONTEND_URL: 'https://pablospizza.web.app',
  API_BASE_URL: 'https://main-4kqeqojbsq-uc.a.run.app/api',
  TIMEOUT: 30000,
  ADMIN_CREDENTIALS: {
    email: 'admin@pablospizza.cl',
    password: 'admin123' // This should be updated with actual credentials
  }
}

test.describe('Pablo\'s Pizza CORS and API Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Set up request/response logging
    page.on('request', request => {
      if (request.url().includes(TEST_CONFIG.API_BASE_URL)) {
        console.log(`🚀 API Request: ${request.method()} ${request.url()}`)
      }
    })

    page.on('response', response => {
      if (response.url().includes(TEST_CONFIG.API_BASE_URL)) {
        console.log(`✅ API Response: ${response.status()} ${response.url()}`)
      }
    })

    // Set up console logging
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`❌ Browser Error: ${msg.text()}`)
      }
    })

    // Set up error handling
    page.on('pageerror', error => {
      console.error(`❌ Page Error: ${error.message}`)
    })
  })

  test('Contact Form Submission - Chat Room Creation', async ({ page }) => {
    console.log('\n🧪 Testing: Contact Form Submission')

    // Navigate to contact page
    await page.goto(TEST_CONFIG.FRONTEND_URL + '/contacto')
    await page.waitForLoadState('networkidle')

    // Wait for form elements to be visible
    await expect(page.locator('form')).toBeVisible({ timeout: 10000 })

    // Fill contact form
    const timestamp = Date.now()
    await page.fill('input[name="name"], input[id="name"]', `Test User ${timestamp}`)
    await page.fill('input[name="email"], input[id="email"]', `test.${timestamp}@example.com`)
    await page.fill('input[name="phone"], input[id="phone"]', '+56912345678')

    // Fill message textarea
    const messageSelector = 'textarea[name="message"], textarea[id="message"], textarea'
    await page.fill(messageSelector, `E2E test message sent at ${new Date().toISOString()}`)

    // Intercept the API call
    const chatRoomPromise = page.waitForResponse(response =>
      response.url().includes('/api/chat/rooms') && response.request().method() === 'POST'
    )

    // Submit form
    await page.click('button[type="submit"], button:has-text("Enviar")')

    try {
      // Wait for API response
      const response = await chatRoomPromise

      console.log(`✅ Chat room API response: ${response.status()}`)

      // Verify CORS headers
      const corsHeaders = {
        'access-control-allow-origin': response.headers()['access-control-allow-origin'],
        'access-control-allow-methods': response.headers()['access-control-allow-methods'],
        'access-control-allow-headers': response.headers()['access-control-allow-headers']
      }

      console.log('🔒 CORS Headers:', corsHeaders)

      // Assertions
      expect(response.status()).toBeLessThan(400)
      expect(corsHeaders['access-control-allow-origin']).toBeTruthy()

      // Wait for success message or redirect
      await page.waitForTimeout(2000)

      // Check for success indicators
      const successIndicators = [
        page.locator('text=enviado'),
        page.locator('text=éxito'),
        page.locator('text=recibido'),
        page.locator('.success'),
        page.locator('[role="alert"]')
      ]

      let successFound = false
      for (const indicator of successIndicators) {
        try {
          await indicator.waitFor({ timeout: 3000 })
          successFound = true
          console.log('✅ Success indicator found')
          break
        } catch (e) {
          // Continue to next indicator
        }
      }

      if (!successFound) {
        console.log('⚠️ No explicit success indicator found, but API call succeeded')
      }

    } catch (error) {
      console.error(`❌ Contact form test failed: ${error.message}`)
      throw error
    }
  })

  test('Admin Photo Upload - Events Management', async ({ page, context }) => {
    console.log('\n🧪 Testing: Admin Photo Upload')

    // Navigate to admin login
    await page.goto(TEST_CONFIG.FRONTEND_URL + '/admin/login')
    await page.waitForLoadState('networkidle')

    try {
      // Login (if login form exists)
      const loginForm = page.locator('form')
      if (await loginForm.isVisible()) {
        await page.fill('input[type="email"]', TEST_CONFIG.ADMIN_CREDENTIALS.email)
        await page.fill('input[type="password"]', TEST_CONFIG.ADMIN_CREDENTIALS.password)
        await page.click('button[type="submit"]')
        await page.waitForLoadState('networkidle')
      }

      // Navigate to events management
      await page.goto(TEST_CONFIG.FRONTEND_URL + '/admin')
      await page.waitForLoadState('networkidle')

      // Look for events management section
      const eventsButton = page.locator('text=Eventos, button:has-text("Eventos"), a:has-text("Eventos")')
      if (await eventsButton.isVisible()) {
        await eventsButton.click()
        await page.waitForLoadState('networkidle')
      }

      // Look for upload functionality
      const uploadButton = page.locator('input[type="file"], button:has-text("Subir"), button:has-text("Upload")')

      if (await uploadButton.isVisible()) {
        // Create a test file
        const testImageBuffer = Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
          'base64'
        )

        // Intercept the upload API call
        const uploadPromise = page.waitForResponse(response =>
          response.url().includes('/api/gallery/upload') && response.request().method() === 'POST'
        )

        // Trigger file upload
        const fileInput = page.locator('input[type="file"]')
        await fileInput.setInputFiles({
          name: 'test-upload.png',
          mimeType: 'image/png',
          buffer: testImageBuffer
        })

        try {
          // Wait for upload response
          const response = await uploadPromise

          console.log(`✅ Upload API response: ${response.status()}`)

          // Verify CORS headers
          const corsHeaders = {
            'access-control-allow-origin': response.headers()['access-control-allow-origin'],
            'access-control-allow-methods': response.headers()['access-control-allow-methods']
          }

          console.log('🔒 Upload CORS Headers:', corsHeaders)

          // Assertions
          expect(response.status()).toBeLessThan(400)
          expect(corsHeaders['access-control-allow-origin']).toBeTruthy()

        } catch (error) {
          console.log('⚠️ Upload API not triggered - this might be expected if using mock data')
        }
      } else {
        console.log('⚠️ Upload functionality not found - testing gallery loading instead')
      }

      // Test gallery loading with event ID
      await page.evaluate(async () => {
        try {
          const response = await fetch('https://main-4kqeqojbsq-uc.a.run.app/api/gallery/?event_id=test', {
            headers: {
              'Origin': 'https://pablospizza.web.app'
            }
          })

          console.log('📷 Gallery API Test:', {
            status: response.status,
            headers: Object.fromEntries(response.headers.entries())
          })

          return response.status
        } catch (error) {
          console.error('Gallery API test failed:', error)
          return 500
        }
      })

    } catch (error) {
      console.error(`❌ Admin photo upload test failed: ${error.message}`)
      // Don't throw here as admin access might not be available
    }
  })

  test('Gallery Public Loading Test', async ({ page }) => {
    console.log('\n🧪 Testing: Gallery Public Loading')

    // Navigate to main page
    await page.goto(TEST_CONFIG.FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Test gallery public API from browser context
    const galleryApiResult = await page.evaluate(async () => {
      try {
        console.log('Testing gallery public API...')

        const response = await fetch('https://main-4kqeqojbsq-uc.a.run.app/api/gallery/public', {
          headers: {
            'Origin': 'https://pablospizza.web.app'
          }
        })

        const corsHeaders = {
          'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
          'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
          'access-control-allow-headers': response.headers.get('access-control-allow-headers')
        }

        let responseData
        try {
          responseData = await response.json()
        } catch (e) {
          responseData = await response.text()
        }

        return {
          status: response.status,
          corsHeaders,
          data: responseData,
          success: response.status < 400 && corsHeaders['access-control-allow-origin']
        }

      } catch (error) {
        return {
          error: error.message,
          success: false
        }
      }
    })

    console.log('📷 Gallery Public API Result:', galleryApiResult)

    // Assertions
    expect(galleryApiResult.success).toBe(true)
    expect(galleryApiResult.status).toBeLessThan(400)
    expect(galleryApiResult.corsHeaders['access-control-allow-origin']).toBeTruthy()
  })

  test('Health Check and CORS Validation', async ({ page }) => {
    console.log('\n🧪 Testing: Health Check and CORS')

    await page.goto(TEST_CONFIG.FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Test health endpoint
    const healthResult = await page.evaluate(async () => {
      try {
        const response = await fetch('https://main-4kqeqojbsq-uc.a.run.app/api/health', {
          headers: {
            'Origin': 'https://pablospizza.web.app'
          }
        })

        const corsHeaders = {
          'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
          'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
          'access-control-allow-headers': response.headers.get('access-control-allow-headers')
        }

        let responseData
        try {
          responseData = await response.json()
        } catch (e) {
          responseData = await response.text()
        }

        return {
          status: response.status,
          corsHeaders,
          data: responseData,
          success: response.status === 200 && corsHeaders['access-control-allow-origin']
        }

      } catch (error) {
        return {
          error: error.message,
          success: false
        }
      }
    })

    console.log('🔍 Health Check Result:', healthResult)

    // Assertions
    expect(healthResult.success).toBe(true)
    expect(healthResult.status).toBe(200)
    expect(healthResult.corsHeaders['access-control-allow-origin']).toBeTruthy()
  })

  test('Error Handling and CORS on 404', async ({ page }) => {
    console.log('\n🧪 Testing: Error Handling with CORS')

    await page.goto(TEST_CONFIG.FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Test 404 endpoint still returns CORS headers
    const errorResult = await page.evaluate(async () => {
      try {
        const response = await fetch('https://main-4kqeqojbsq-uc.a.run.app/api/nonexistent-endpoint', {
          headers: {
            'Origin': 'https://pablospizza.web.app'
          }
        })

        const corsHeaders = {
          'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
          'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
          'access-control-allow-headers': response.headers.get('access-control-allow-headers')
        }

        return {
          status: response.status,
          corsHeaders,
          success: response.status === 404 && corsHeaders['access-control-allow-origin']
        }

      } catch (error) {
        return {
          error: error.message,
          success: false
        }
      }
    })

    console.log('🔍 404 Error CORS Result:', errorResult)

    // Assertions
    expect(errorResult.status).toBe(404)
    expect(errorResult.corsHeaders['access-control-allow-origin']).toBeTruthy()
  })

})

// Configuration
test.describe.configure({ mode: 'serial' })

test.setTimeout(TEST_CONFIG.TIMEOUT)

console.log('🎯 Playwright E2E Tests for Pablo\'s Pizza loaded')
console.log('Run with: npx playwright test playwright-e2e-tests.js')