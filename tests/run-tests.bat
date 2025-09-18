@echo off
REM Pablo's Pizza E2E Test Runner for Windows
REM This script runs the complete test suite

echo.
echo ========================================
echo  Pablo's Pizza E2E CORS and API Tests
echo ========================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed or not in PATH
    echo    Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js is available
echo.

REM Change to tests directory
cd /d "%~dp0"

echo 🧪 Running Node.js API Tests...
echo ==============================
echo.

REM Run Node.js API tests
node node-api-tests.js
set NODE_EXIT_CODE=%errorlevel%

echo.
echo ==============================
echo.

if %NODE_EXIT_CODE% equ 0 (
    echo ✅ Node.js API tests completed successfully
) else (
    echo ❌ Node.js API tests failed
)

echo.
echo 🌐 Browser Tests Information:
echo ============================
echo.
echo To run browser-based tests:
echo 1. Open browser-test-runner.html in your web browser
echo 2. Or run: npm run test:playwright (requires Playwright setup)
echo.

REM Check if Playwright is available
if exist "node_modules\.bin\playwright.cmd" (
    echo 🎭 Playwright is available
    echo    Run: npm run test:playwright
) else (
    echo ⚠️  Playwright not installed
    echo    Run: npm run setup
)

echo.
echo 📋 Test Results Summary:
echo =======================

if %NODE_EXIT_CODE% equ 0 (
    echo ✅ API Tests: PASSED
) else (
    echo ❌ API Tests: FAILED
)

echo.
echo 📄 Detailed results saved in test-results.json
echo.

if %NODE_EXIT_CODE% equ 0 (
    echo 🎉 All automated tests completed successfully!
) else (
    echo ⚠️  Some tests failed - check the output above
)

echo.
echo Press any key to exit...
pause >nul