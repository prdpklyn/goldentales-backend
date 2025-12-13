#!/bin/bash
# GoldenTales API Endpoint Testing Script
# This script helps test various API endpoints

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-${DEV_API_KEY:-}}"

echo "=========================================="
echo "GoldenTales API Endpoint Tester"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${YELLOW}Endpoint:${NC} $method $endpoint"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            ${API_KEY:+-H "X-API-Key: $API_KEY"} \
            -d "$data" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X "$method" \
            ${API_KEY:+-H "X-API-Key: $API_KEY"} \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ Success (HTTP $http_code)${NC}"
    else
        echo -e "${YELLOW}✗ Failed (HTTP $http_code)${NC}"
    fi
    
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Test 1: Root endpoint
api_call "GET" "/" "" "Root health check"

# Test 2: Health check (version-agnostic)
api_call "GET" "/api/health" "" "Health check endpoint"

# Test 3: Health check (v1)
api_call "GET" "/api/v1/health" "" "V1 health check endpoint"

# Test 4: Config endpoint (legacy - should show deprecation)
api_call "GET" "/api/config" "" "Legacy config endpoint (deprecated)"

# Test 5: Config endpoint (v1 - should show current)
api_call "GET" "/api/v1/config" "" "V1 config endpoint (current)"

# Test 6: Check deprecation headers
echo -e "${BLUE}Checking deprecation headers on legacy endpoint:${NC}"
echo -e "${YELLOW}Endpoint:${NC} GET /api/config"
headers=$(curl -s -I ${API_KEY:+-H "X-API-Key: $API_KEY"} "$BASE_URL/api/config")
echo "$headers" | grep -E "(Deprecation|Sunset|X-API-Warning|X-API-Version|X-API-Status)" || echo "No deprecation headers found"
echo ""
echo "=========================================="
echo "Testing complete!"
echo ""
echo "To test with a specific API key:"
echo "  export API_KEY=your-api-key"
echo "  ./test_api_endpoints.sh"
echo ""
echo "To test against a different server:"
echo "  export BASE_URL=https://api.goldentales.app"
echo "  ./test_api_endpoints.sh"
echo "=========================================="

