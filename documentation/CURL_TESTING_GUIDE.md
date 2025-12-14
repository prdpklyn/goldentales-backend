# GoldenTales API - cURL Testing Guide

Complete guide for testing all API endpoints using cURL commands.

**Base URL**: `http://localhost:8000` (adjust if needed)

---

## 🚀 Quick Start

### 1. Start the Server

```bash
# Make sure server is running
uvicorn main:app --reload --port 8000
```

### 2. Test Basic Connectivity

```bash
# Test root endpoint
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/api/health
```

---

## 📚 Create Book API

### Basic Request (Minimal Required Fields)

```bash
curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }'
```

### Complete Request (All Fields)

```bash
curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "has_glasses": false,
    "glasses_type": null,
    "has_freckles": true,
    "has_dimples": false,
    "other_features": null,
    "favorite_outfit": "purple dress with white dots",
    "favorite_color": "purple",
    "photo_url": null,
    "additional_characters": [
      {
        "name": "Max",
        "character_type": "pet",
        "relationship": "pet dog",
        "gender": null,
        "age_description": null,
        "skin_tone": null,
        "hair_color": null,
        "pet_species": "golden retriever",
        "pet_color": "golden",
        "distinctive_feature": "red collar"
      }
    ],
    "theme": "christmas",
    "art_style": "watercolor",
    "occasion": "birthday",
    "special_details": "Emma loves unicorns and fairy tales"
  }'
```

### Pretty Print Response

```bash
curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }' | python -m json.tool
```

### Save Response to File

```bash
curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }' | python -m json.tool > book_response.json

# Extract book_id
BOOK_ID=$(cat book_response.json | python -c "import sys, json; print(json.load(sys.stdin)['book_id'])")
echo "Book ID: $BOOK_ID"
```

---

## 📖 Get Book API

```bash
# Replace abc12345 with actual book_id from create response
curl http://localhost:8000/api/books/abc12345 | python -m json.tool
```

### Using Variable

```bash
BOOK_ID="abc12345"  # Replace with your book_id
curl http://localhost:8000/api/books/$BOOK_ID | python -m json.tool
```

---

## 🖼️ Get Book Preview API

```bash
BOOK_ID="abc12345"  # Replace with your book_id
curl http://localhost:8000/api/books/$BOOK_ID/preview | python -m json.tool
```

---

## 🔄 Regenerate Page API

```bash
BOOK_ID="abc12345"  # Replace with your book_id
PAGE_NUMBER=3

curl -X POST http://localhost:8000/api/books/$BOOK_ID/regenerate-page/$PAGE_NUMBER \
  -H "Content-Type: application/json" \
  -d '{
    "scene_description": "Emma playing in a magical forest with unicorns",
    "character_action": "running through the forest",
    "mood": "magical",
    "include_characters": ["Emma"]
  }' | python -m json.tool
```

### Minimal Request (Uses Original Page Data)

```bash
BOOK_ID="abc12345"
PAGE_NUMBER=3

curl -X POST http://localhost:8000/api/books/$BOOK_ID/regenerate-page/$PAGE_NUMBER \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool
```

---

## 💰 Get Book Price API

### Digital Format

```bash
BOOK_ID="abc12345"
curl "http://localhost:8000/api/books/$BOOK_ID/price?format=digital&shipping=digital&gift_wrap=false" | python -m json.tool
```

### Softcover with Standard Shipping

```bash
BOOK_ID="abc12345"
curl "http://localhost:8000/api/books/$BOOK_ID/price?format=softcover&shipping=standard&gift_wrap=false" | python -m json.tool
```

### Hardcover with Express Shipping and Gift Wrap

```bash
BOOK_ID="abc12345"
curl "http://localhost:8000/api/books/$BOOK_ID/price?format=hardcover&shipping=express&gift_wrap=true" | python -m json.tool
```

---

## 🛒 Create Order API

### Basic Order (Digital)

```bash
BOOK_ID="abc12345"  # Replace with your book_id

curl -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d "{
    \"book_id\": \"$BOOK_ID\",
    \"format\": \"digital\",
    \"shipping_tier\": \"digital\",
    \"gift_wrap\": false
  }" | python -m json.tool
```

### Complete Order (Hardcover with Gift Wrap)

```bash
BOOK_ID="abc12345"  # Replace with your book_id

curl -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
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
  }" | python -m json.tool
```

### Save Order ID

```bash
BOOK_ID="abc12345"
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d "{
    \"book_id\": \"$BOOK_ID\",
    \"format\": \"hardcover\",
    \"shipping_tier\": \"standard\",
    \"gift_wrap\": false
  }")

echo "$ORDER_RESPONSE" | python -m json.tool

ORDER_ID=$(echo "$ORDER_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['order_id'])")
echo "Order ID: $ORDER_ID"
```

---

## 📊 Get Order Status API

```bash
ORDER_ID="order123"  # Replace with your order_id
curl http://localhost:8000/api/orders/$ORDER_ID/status | python -m json.tool
```

---

## 🚚 Get Shipping Options API

```bash
curl http://localhost:8000/api/shipping-options | python -m json.tool
```

---

## 🔐 With API Key Authentication

If API key is required:

```bash
API_KEY="your-api-key-here"

curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }' | python -m json.tool
```

---

## 📝 Complete Workflow Example

Here's a complete workflow from creating a book to creating an order:

```bash
#!/bin/bash

# Step 1: Create a book
echo "Creating book..."
BOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }')

echo "$BOOK_RESPONSE" | python -m json.tool

# Extract book_id
BOOK_ID=$(echo "$BOOK_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['book_id'])")
echo -e "\n✓ Book created! Book ID: $BOOK_ID\n"

# Step 2: Get book details
echo "Getting book details..."
curl -s http://localhost:8000/api/books/$BOOK_ID | python -m json.tool | head -20
echo ""

# Step 3: Get preview images
echo "Getting preview images..."
curl -s http://localhost:8000/api/books/$BOOK_ID/preview | python -m json.tool
echo ""

# Step 4: Calculate price
echo "Calculating price..."
curl -s "http://localhost:8000/api/books/$BOOK_ID/price?format=hardcover&shipping=standard&gift_wrap=true" | python -m json.tool
echo ""

# Step 5: Create order
echo "Creating order..."
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d "{
    \"book_id\": \"$BOOK_ID\",
    \"format\": \"hardcover\",
    \"shipping_tier\": \"standard\",
    \"gift_wrap\": true
  }")

echo "$ORDER_RESPONSE" | python -m json.tool

ORDER_ID=$(echo "$ORDER_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['order_id'])")
echo -e "\n✓ Order created! Order ID: $ORDER_ID\n"

# Step 6: Get order status
echo "Getting order status..."
curl -s http://localhost:8000/api/orders/$ORDER_ID/status | python -m json.tool
```

Save this as `test_workflow.sh`, make it executable, and run:

```bash
chmod +x test_workflow.sh
./test_workflow.sh
```

---

## 🔍 Verbose Mode (See Headers)

To see request/response headers:

```bash
curl -v -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }'
```

---

## 🐛 Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl http://localhost:8000/

# If it fails, start the server:
uvicorn main:app --reload --port 8000
```

### JSON Parsing Errors

Make sure JSON is properly formatted. Use single quotes for the outer JSON and escape inner quotes:

```bash
# Wrong
curl -d "{"key": "value"}"

# Correct
curl -d '{"key": "value"}'
# OR
curl -d "{\"key\": \"value\"}"
```

### Pretty Print Not Working

If `python -m json.tool` doesn't work, try:

```bash
# Using jq (if installed)
curl ... | jq .

# Or just view raw JSON
curl ...
```

### Extract Values from Response

```bash
# Extract book_id
BOOK_ID=$(curl -s ... | python -c "import sys, json; print(json.load(sys.stdin)['book_id'])")

# Extract multiple values
curl -s ... | python -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Book ID: {data['book_id']}\")
print(f\"Title: {data['title']}\")
"
```

---

## 📋 Quick Reference

### Environment Variables

Set these for easier testing:

```bash
export BASE_URL="http://localhost:8000"
export API_KEY="your-api-key"  # Optional
export BOOK_ID="abc12345"       # Set after creating a book
export ORDER_ID="order123"      # Set after creating an order
```

Then use in commands:

```bash
curl $BASE_URL/api/books/$BOOK_ID
```

### Common Patterns

```bash
# Pretty print any response
curl ... | python -m json.tool

# Save response to file
curl ... > response.json

# Extract specific field
curl ... | python -c "import sys, json; print(json.load(sys.stdin)['field_name'])"

# Check HTTP status code
curl -w "\nHTTP Status: %{http_code}\n" ...

# Include response headers
curl -i ...

# Verbose (see everything)
curl -v ...
```

---

## 🎯 Testing Checklist

- [ ] Server is running
- [ ] Create a book
- [ ] Get book details
- [ ] Get preview images
- [ ] Calculate price (different formats)
- [ ] Create an order
- [ ] Get order status
- [ ] Get shipping options
- [ ] Test error cases (invalid book_id, etc.)

---

**Happy Testing!** 🚀

