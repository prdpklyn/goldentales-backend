# Print Job Testing Guide

Complete guide for testing print production jobs in GoldenTales.

---

## 📋 Overview

Print jobs are the process of:
1. **Upscaling** preview images to print quality (2400×1800)
2. **Generating** a print-ready PDF
3. **Submitting** to fulfillment provider (Lulu/Printful)

**Key Point**: Print jobs use **UPSCALING**, not regeneration, to maintain character consistency!

---

## 🚀 Method 1: Using the Test Script (Recommended)

### Prerequisites

```bash
# Required environment variables
export FAL_KEY=your-fal-api-key
export SUPABASE_URL=your-supabase-url
export SUPABASE_PUBLISHABLE_KEY=your-supabase-key
```

### Run the Test Script

```bash
# Basic usage (uses default story_id)
python test_print_job.py

# With custom story_id
python test_print_job.py --story-id "your-story-id-here"

# Use Creative Upscaler (better quality, slower)
python test_print_job.py --story-id "your-story-id" --creative
```

### What It Does

1. ✅ Checks configuration (Supabase, Fal.ai)
2. ✅ Fetches book from database
3. ✅ Shows preview images
4. ✅ Starts print production
5. ✅ Monitors job status
6. ✅ Shows final PDF location

### Output

The script will:
- Show job progress in real-time
- Save PDF to: `/tmp/goldentales_print/verification/job_{job_id}.pdf`
- Display final status and any errors

---

## 🧪 Method 2: Test with In-Memory Book (No Database)

Create a simple test script that works with books created via API:

### Create Test Script

```bash
# Save as test_print_job_simple.py
```

```python
#!/usr/bin/env python3
"""
Simple print job test using in-memory book data.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.print_service import get_print_service, UpscaleMethod
from app.routers.books import get_book_storage

async def test_print_job_from_api(book_id: str):
    """Test print job using a book created via API."""
    
    print("=" * 60)
    print("GoldenTales Print Job Test (From API Book)")
    print("=" * 60)
    print(f"\nBook ID: {book_id}")
    
    # Get book from in-memory storage
    book_storage = get_book_storage()
    
    if book_id not in book_storage:
        print(f"\n❌ ERROR: Book {book_id} not found!")
        print("   Create a book first using: POST /api/books/create")
        return
    
    book = book_storage[book_id]
    
    print(f"\n✓ Found book: {book['title']}")
    print(f"✓ Child: {book['child_name']}, Age: {book['child_age']}")
    print(f"✓ Pages: {book['page_count']}")
    print(f"✓ Preview images: {len(book.get('preview_images', []))}")
    
    # Check if preview images exist
    if not book.get('preview_images'):
        print("\n❌ ERROR: No preview images found!")
        print("   Make sure the book was created successfully with images.")
        return
    
    # Show first few preview images
    print("\nPreview Images:")
    for i, img_url in enumerate(book['preview_images'][:3], 1):
        print(f"  Page {i}: {img_url[:60]}...")
    if len(book['preview_images']) > 3:
        print(f"  ... and {len(book['preview_images']) - 3} more")
    
    # Prepare book data for print service
    # The print service expects pages with image_url
    pages = []
    for i, page in enumerate(book.get('pages', [])):
        page_data = page.copy()
        # Add image_url from preview_images array
        if i < len(book['preview_images']):
            page_data['image_url'] = book['preview_images'][i]
        pages.append(page_data)
    
    book_data = {
        'book_id': book['book_id'],
        'title': book['title'],
        'child_name': book['child_name'],
        'pages': pages,
        'page_count': book['page_count']
    }
    
    # Confirm
    print("\n" + "=" * 60)
    print("Ready to start print production!")
    print("=" * 60)
    print(f"  Pages: {book['page_count']}")
    print(f"  Estimated cost: ~${book['page_count'] * 0.01:.2f} (Real-ESRGAN)")
    print(f"  Output: /tmp/goldentales_print/verification/")
    print("=" * 60)
    
    confirm = input("\nStart print production? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        print_service = get_print_service()
        print_service.upscale_method = UpscaleMethod.REAL_ESRGAN
        
        print("\n🚀 Starting print production...")
        
        job = await print_service.start_print_production(
            order_id=f"test-order-{book_id}",
            book_data=book_data,
            format="hardcover",
            book_size="square_8x8",
            shipping_address={"name": "Test User", "city": "Test City"}
        )
        
        print(f"\n✓ Print job started!")
        print(f"  Job ID: {job.job_id}")
        print(f"  Status: {job.status.value}")
        
        # Wait for completion
        print("\n⏳ Waiting for job completion...")
        print("   (Check server logs for detailed progress)")
        
        max_wait = 300  # 5 minutes
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(5)
            waited += 5
            
            current_job = print_service.get_job_status(job.job_id)
            if current_job:
                print(f"  Status: {current_job.status.value} ({waited}s)")
                
                if current_job.status.value in ["sent_to_printer", "failed"]:
                    break
        
        # Final status
        final_job = print_service.get_job_status(job.job_id)
        if final_job:
            print("\n" + "=" * 60)
            print("Final Status:")
            print("=" * 60)
            print(f"  Job ID: {final_job.job_id}")
            print(f"  Status: {final_job.status.value}")
            
            if final_job.pdf_path:
                print(f"  PDF: {final_job.pdf_path}")
                print(f"\n📄 Check the PDF at:")
                print(f"   /tmp/goldentales_print/verification/job_{final_job.job_id}.pdf")
            
            if final_job.error_message:
                print(f"  Error: {final_job.error_message}")
    else:
        print("\nPrint production cancelled.")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test print job with API-created book")
    parser.add_argument(
        "--book-id",
        required=True,
        help="Book ID from API book creation"
    )
    
    args = parser.parse_args()
    asyncio.run(test_print_job_from_api(args.book_id))
```

### Usage

```bash
# 1. First, create a book via API
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

# Note the book_id from the response

# 2. Run the print job test
python test_print_job_simple.py --book-id "abc12345"
```

---

## 🔌 Method 3: Test via Shopify Webhook (Production Flow)

Print jobs are typically triggered via Shopify webhooks. You can simulate this:

### Simulate Order Created Webhook

```bash
# Create a book first and get book_id
BOOK_ID="abc12345"  # Replace with actual book_id

# Simulate Shopify webhook
curl -X POST http://localhost:8000/api/shopify/webhooks/orders/create \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Hmac-SHA256: test-signature" \
  -d "{
    \"id\": 123456789,
    \"order_number\": 1001,
    \"line_items\": [
      {
        \"title\": \"Personalized Storybook\",
        \"properties\": [
          {
            \"name\": \"story_id\",
            \"value\": \"$BOOK_ID\"
          }
        ],
        \"product_id\": 12345
      }
    ],
    \"shipping_address\": {
      \"name\": \"Test User\",
      \"address1\": \"123 Main St\",
      \"city\": \"San Francisco\",
      \"province\": \"CA\",
      \"zip\": \"94102\",
      \"country\": \"USA\"
    }
  }" | python -m json.tool
```

**Note**: This requires webhook signature verification. You may need to disable it for testing or use the correct signature.

---

## 📊 Method 4: Direct Python API Test

### Complete Test Script

```python
#!/usr/bin/env python3
"""
Complete print job test workflow.
"""

import asyncio
import requests
from app.services.print_service import get_print_service, UpscaleMethod

async def test_complete_workflow():
    """Test complete workflow: Create book → Create order → Print job."""
    
    BASE_URL = "http://localhost:8000"
    
    print("=" * 60)
    print("Complete Print Job Test Workflow")
    print("=" * 60)
    
    # Step 1: Create a book
    print("\n[1/4] Creating book...")
    book_response = requests.post(
        f"{BASE_URL}/api/books/create",
        json={
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
        }
    )
    
    if book_response.status_code != 200:
        print(f"❌ Failed to create book: {book_response.text}")
        return
    
    book_data = book_response.json()
    book_id = book_data['book_id']
    print(f"✓ Book created: {book_id}")
    print(f"  Title: {book_data['title']}")
    print(f"  Pages: {book_data['page_count']}")
    
    # Step 2: Create an order
    print("\n[2/4] Creating order...")
    order_response = requests.post(
        f"{BASE_URL}/api/orders/create",
        json={
            "book_id": book_id,
            "format": "hardcover",
            "shipping_tier": "standard",
            "gift_wrap": False
        }
    )
    
    if order_response.status_code != 200:
        print(f"❌ Failed to create order: {order_response.text}")
        return
    
    order_data = order_response.json()
    order_id = order_data['order_id']
    print(f"✓ Order created: {order_id}")
    
    # Step 3: Start print job
    print("\n[3/4] Starting print job...")
    print_service = get_print_service()
    
    # Prepare book data for print service
    pages = []
    for i, page in enumerate(book_data.get('pages', [])):
        page_copy = page.copy()
        if i < len(book_data.get('preview_images', [])):
            page_copy['image_url'] = book_data['preview_images'][i]
        pages.append(page_copy)
    
    book_for_print = {
        'book_id': book_id,
        'title': book_data['title'],
        'child_name': book_data['child_name'],
        'pages': pages,
        'page_count': book_data['page_count']
    }
    
    job = await print_service.start_print_production(
        order_id=order_id,
        book_data=book_for_print,
        format="hardcover",
        book_size="square_8x8",
        shipping_address={"name": "Test User", "city": "Test City"}
    )
    
    print(f"✓ Print job started: {job.job_id}")
    print(f"  Status: {job.status.value}")
    
    # Step 4: Monitor job
    print("\n[4/4] Monitoring job status...")
    max_wait = 300
    waited = 0
    
    while waited < max_wait:
        await asyncio.sleep(5)
        waited += 5
        
        current_job = print_service.get_job_status(job.job_id)
        if current_job:
            print(f"  Status: {current_job.status.value} ({waited}s)")
            
            if current_job.status.value in ["sent_to_printer", "failed"]:
                break
    
    # Final status
    final_job = print_service.get_job_status(job.job_id)
    if final_job:
        print("\n" + "=" * 60)
        print("Final Status:")
        print("=" * 60)
        print(f"  Job ID: {final_job.job_id}")
        print(f"  Status: {final_job.status.value}")
        
        if final_job.pdf_path:
            print(f"  PDF: {final_job.pdf_path}")
            print(f"\n📄 PDF Location:")
            print(f"   /tmp/goldentales_print/verification/job_{final_job.job_id}.pdf")
        
        if final_job.error_message:
            print(f"  Error: {final_job.error_message}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

---

## 🔍 Method 5: Check Job Status Programmatically

```python
from app.services.print_service import get_print_service

# Get print service
print_service = get_print_service()

# Check job status
job_id = "pj_abc123def456"
job = print_service.get_job_status(job_id)

if job:
    print(f"Job ID: {job.job_id}")
    print(f"Status: {job.status.value}")
    print(f"PDF: {job.pdf_path}")
    print(f"Error: {job.error_message}")
else:
    print("Job not found")
```

---

## 📁 Output Locations

### PDF Files

- **Temporary PDF**: `/tmp/goldentales_print/{job_id}.pdf`
- **Verification PDF**: `/tmp/goldentales_print/verification/job_{job_id}.pdf`

### Logs

Check server logs for detailed progress:
- Image upscaling progress
- PDF generation steps
- Error messages

---

## ⚙️ Configuration

### Required Environment Variables

```bash
# Required for print jobs
export FAL_KEY=your-fal-api-key

# Optional (for database-based testing)
export SUPABASE_URL=your-supabase-url
export SUPABASE_PUBLISHABLE_KEY=your-supabase-key

# Optional (for Lulu submission)
export LULU_API_KEY=your-lulu-api-key
```

### Upscale Methods

1. **Real-ESRGAN** (default)
   - Speed: ~5 seconds per image
   - Cost: ~$0.01 per image
   - Quality: Good

2. **Creative Upscaler**
   - Speed: ~15 seconds per image
   - Cost: ~$0.03 per image
   - Quality: Better

---

## 🐛 Troubleshooting

### "FAL_KEY not configured"

```bash
export FAL_KEY=your-fal-api-key
```

### "Book not found"

- Make sure you created the book via API first
- Check the book_id is correct
- For database testing, ensure story exists in Supabase

### "No preview images found"

- The book creation may have failed
- Check server logs for image generation errors
- Verify FAL_KEY is valid

### Job Status Stuck

- Check server logs for errors
- Verify FAL_KEY has sufficient credits
- Check network connectivity to Fal.ai

### PDF Not Generated

- Check `/tmp/goldentales_print/` directory exists
- Verify write permissions
- Check server logs for PDF generation errors

---

## 📊 Job Status Values

- `pending_payment` - Waiting for payment
- `payment_confirmed` - Payment received
- `generating_print_files` - Upscaling images
- `creating_pdf` - Generating PDF
- `uploading_to_printer` - Uploading to fulfillment
- `sent_to_printer` - Submitted successfully
- `printing` - Being printed
- `shipped` - Shipped to customer
- `delivered` - Delivered
- `failed` - Job failed (check error_message)

---

## 💡 Quick Test Workflow

```bash
# 1. Create a book
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

BOOK_ID=$(echo "$BOOK_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['book_id'])")
echo "Book ID: $BOOK_ID"

# 2. Wait for images to generate (30-60 seconds)
echo "Waiting for images to generate..."
sleep 60

# 3. Test print job
python test_print_job_simple.py --book-id "$BOOK_ID"
```

---

## 📚 Additional Resources

- **Print Service Code**: `app/services/print_service.py`
- **Test Script**: `test_print_job.py`
- **API Documentation**: `API_DOCUMENTATION.md`

---

**Happy Testing!** 🎨📖

