#!/bin/bash
# Example curl commands for Create Book and Create Order APIs

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"

echo "=========================================="
echo "GoldenTales API - Book & Order Examples"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Example 1: Create a Book
echo -e "${BLUE}Example 1: Create a Book${NC}"
echo -e "${YELLOW}POST /api/v1/books/create${NC}"
echo ""

BOOK_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light",
    "hair_color": "brown",
    "hair_style": "pigtails",
    "eye_color": "blue",
    "body_type": "average",
    "has_freckles": true,
    "favorite_color": "purple",
    "theme": "adventure",
    "art_style": "watercolor",
    "occasion": "birthday",
    "special_details": "Emma loves unicorns and magic"
  }' \
  "$BASE_URL/api/v1/books/create")

echo "$BOOK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$BOOK_RESPONSE"
echo ""

# Extract book_id from response
BOOK_ID=$(echo "$BOOK_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('book_id', ''))" 2>/dev/null)

if [ -z "$BOOK_ID" ]; then
    echo -e "${YELLOW}⚠ Could not extract book_id. Using placeholder.${NC}"
    BOOK_ID="abc12345"
fi

echo -e "${GREEN}✓ Book created! Book ID: $BOOK_ID${NC}"
echo ""
echo "=========================================="
echo ""

# Example 2: Get Book Details
echo -e "${BLUE}Example 2: Get Book Details${NC}"
echo -e "${YELLOW}GET /api/v1/books/$BOOK_ID${NC}"
echo ""

curl -s ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  "$BASE_URL/api/v1/books/$BOOK_ID" | python3 -m json.tool
echo ""
echo "=========================================="
echo ""

# Example 3: Get Book Preview
echo -e "${BLUE}Example 3: Get Book Preview Images${NC}"
echo -e "${YELLOW}GET /api/v1/books/$BOOK_ID/preview${NC}"
echo ""

curl -s ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  "$BASE_URL/api/v1/books/$BOOK_ID/preview" | python3 -m json.tool
echo ""
echo "=========================================="
echo ""

# Example 4: Get Book Price
echo -e "${BLUE}Example 4: Get Book Price${NC}"
echo -e "${YELLOW}GET /api/v1/orders/books/$BOOK_ID/price?format=hardcover&shipping=standard&gift_wrap=true${NC}"
echo ""

curl -s ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  "$BASE_URL/api/v1/orders/books/$BOOK_ID/price?format=hardcover&shipping=standard&gift_wrap=true" | python3 -m json.tool
echo ""
echo "=========================================="
echo ""

# Example 5: Create Order
echo -e "${BLUE}Example 5: Create Order${NC}"
echo -e "${YELLOW}POST /api/v1/orders/create${NC}"
echo ""

ORDER_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  -d "{
    \"book_id\": \"$BOOK_ID\",
    \"format\": \"hardcover\",
    \"shipping_tier\": \"standard\",
    \"gift_wrap\": true,
    \"gift_message\": \"Happy Birthday! Love, Grandma\",
    \"recipient_email\": \"recipient@example.com\",
    \"recipient_address\": {
      \"name\": \"Emma Smith\",
      \"street\": \"123 Main St\",
      \"city\": \"San Francisco\",
      \"state\": \"CA\",
      \"postal_code\": \"94102\",
      \"country\": \"USA\"
    }
  }" \
  "$BASE_URL/api/v1/orders/create")

echo "$ORDER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ORDER_RESPONSE"
echo ""

ORDER_ID=$(echo "$ORDER_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order_id', ''))" 2>/dev/null)

if [ -n "$ORDER_ID" ]; then
    echo -e "${GREEN}✓ Order created! Order ID: $ORDER_ID${NC}"
    echo ""
    echo "=========================================="
    echo ""
    
    # Example 6: Get Order Status
    echo -e "${BLUE}Example 6: Get Order Status${NC}"
    echo -e "${YELLOW}GET /api/v1/orders/$ORDER_ID/status${NC}"
    echo ""
    
    curl -s ${API_KEY:+-H "X-API-Key: $API_KEY"} \
      "$BASE_URL/api/v1/orders/$ORDER_ID/status" | python3 -m json.tool
    echo ""
fi

echo "=========================================="
echo ""
echo -e "${GREEN}All examples complete!${NC}"
echo ""
echo "To use with a specific API key:"
echo "  export API_KEY=your-api-key"
echo "  ./test_book_order_examples.sh"
echo ""

