#!/bin/bash
# GoldenTales API - Complete cURL Test Script
# This script tests all API endpoints in sequence

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "GoldenTales API - cURL Test Suite"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

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
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
    fi
    
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""
    echo "----------------------------------------"
    echo ""
    
    # Return the body for extraction
    echo "$body"
}

# Test 1: Health Check
echo -e "${BLUE}=== Test 1: Health Check ===${NC}"
api_call "GET" "/api/health" "" "Health check endpoint"
echo ""

# Test 2: Create Book
echo -e "${BLUE}=== Test 2: Create Book ===${NC}"
BOOK_DATA='{
  "child_name": "Emma",
  "child_gender": "girl",
  "child_age": 6,
  "skin_tone": "light skin",
  "hair_color": "brown hair",
  "hair_style": "hair in pigtails",
  "eye_color": "blue eyes",
  "body_type": "average build",
  "has_freckles": true,
  "favorite_color": "purple",
  "theme": "christmas",
  "art_style": "watercolor",
  "occasion": "birthday",
  "special_details": "Emma loves unicorns and fairy tales"
}'

BOOK_RESPONSE=$(api_call "POST" "/api/books/create" "$BOOK_DATA" "Create a personalized storybook")

# Extract book_id
BOOK_ID=$(echo "$BOOK_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('book_id', ''))" 2>/dev/null)

if [ -z "$BOOK_ID" ]; then
    echo -e "${RED}✗ Failed to extract book_id. Cannot continue.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Book created! Book ID: $BOOK_ID${NC}"
echo ""

# Test 3: Get Book
echo -e "${BLUE}=== Test 3: Get Book ===${NC}"
api_call "GET" "/api/books/$BOOK_ID" "" "Get book details"
echo ""

# Test 4: Get Book Preview
echo -e "${BLUE}=== Test 4: Get Book Preview ===${NC}"
api_call "GET" "/api/books/$BOOK_ID/preview" "" "Get preview images"
echo ""

# Test 5: Get Book Price (Digital)
echo -e "${BLUE}=== Test 5: Get Book Price (Digital) ===${NC}"
api_call "GET" "/api/books/$BOOK_ID/price?format=digital&shipping=digital&gift_wrap=false" "" "Calculate digital book price"
echo ""

# Test 6: Get Book Price (Hardcover)
echo -e "${BLUE}=== Test 6: Get Book Price (Hardcover) ===${NC}"
api_call "GET" "/api/books/$BOOK_ID/price?format=hardcover&shipping=standard&gift_wrap=true" "" "Calculate hardcover book price"
echo ""

# Test 7: Get Shipping Options
echo -e "${BLUE}=== Test 7: Get Shipping Options ===${NC}"
api_call "GET" "/api/shipping-options" "" "Get shipping options"
echo ""

# Test 8: Create Order
echo -e "${BLUE}=== Test 8: Create Order ===${NC}"
ORDER_DATA="{
  \"book_id\": \"$BOOK_ID\",
  \"format\": \"hardcover\",
  \"shipping_tier\": \"standard\",
  \"gift_wrap\": true,
  \"gift_message\": \"Happy Birthday! Love, Grandma\",
  \"recipient_email\": \"recipient@example.com\"
}"

ORDER_RESPONSE=$(api_call "POST" "/api/orders/create" "$ORDER_DATA" "Create an order")

# Extract order_id
ORDER_ID=$(echo "$ORDER_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order_id', ''))" 2>/dev/null)

if [ -n "$ORDER_ID" ]; then
    echo -e "${GREEN}✓ Order created! Order ID: $ORDER_ID${NC}"
    echo ""
    
    # Test 9: Get Order Status
    echo -e "${BLUE}=== Test 9: Get Order Status ===${NC}"
    api_call "GET" "/api/orders/$ORDER_ID/status" "" "Get order status"
    echo ""
else
    echo -e "${YELLOW}⚠ Could not extract order_id${NC}"
    echo ""
fi

# Test 10: Regenerate Page (if book was created)
if [ -n "$BOOK_ID" ]; then
    echo -e "${BLUE}=== Test 10: Regenerate Page ===${NC}"
    REGEN_DATA='{
      "scene_description": "Emma playing in a magical forest with unicorns",
      "character_action": "running through the forest",
      "mood": "magical"
    }'
    api_call "POST" "/api/books/$BOOK_ID/regenerate-page/3" "$REGEN_DATA" "Regenerate page 3"
    echo ""
fi

echo "=========================================="
echo -e "${GREEN}All tests complete!${NC}"
echo ""
echo "Book ID: $BOOK_ID"
if [ -n "$ORDER_ID" ]; then
    echo "Order ID: $ORDER_ID"
fi
echo "=========================================="

