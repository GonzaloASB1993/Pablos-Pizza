#!/bin/bash

# Pablo's Pizza E2E Test Runner for Unix/Linux/macOS
# This script runs the complete test suite

echo ""
echo "========================================"
echo " Pablo's Pizza E2E CORS and API Tests"
echo "========================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed or not in PATH"
    echo "   Please install Node.js from https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js is available: $(node --version)"
echo ""

# Change to tests directory
cd "$(dirname "$0")"

echo "🧪 Running Node.js API Tests..."
echo "=============================="
echo ""

# Run Node.js API tests
node node-api-tests.js
NODE_EXIT_CODE=$?

echo ""
echo "=============================="
echo ""

if [ $NODE_EXIT_CODE -eq 0 ]; then
    echo "✅ Node.js API tests completed successfully"
else
    echo "❌ Node.js API tests failed"
fi

echo ""
echo "🌐 Browser Tests Information:"
echo "============================"
echo ""
echo "To run browser-based tests:"
echo "1. Open browser-test-runner.html in your web browser"
echo "2. Or run: npm run test:playwright (requires Playwright setup)"
echo ""

# Check if Playwright is available
if [ -f "node_modules/.bin/playwright" ]; then
    echo "🎭 Playwright is available"
    echo "   Run: npm run test:playwright"
else
    echo "⚠️  Playwright not installed"
    echo "   Run: npm run setup"
fi

echo ""
echo "📋 Test Results Summary:"
echo "======================="

if [ $NODE_EXIT_CODE -eq 0 ]; then
    echo "✅ API Tests: PASSED"
else
    echo "❌ API Tests: FAILED"
fi

echo ""
echo "📄 Detailed results saved in test-results.json"
echo ""

if [ $NODE_EXIT_CODE -eq 0 ]; then
    echo "🎉 All automated tests completed successfully!"
else
    echo "⚠️  Some tests failed - check the output above"
fi

echo ""

exit $NODE_EXIT_CODE