#!/usr/bin/env python3
"""
Test script for print production with upscaling.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.config import settings
from app.services.database import get_database
from app.services.print_service import get_print_service, UpscaleMethod


async def test_print_job(story_id: str, use_creative: bool = False):
    """Test the print job process for a story."""
    
    print("=" * 60)
    print("GoldenTales Print Job Test (Upscaling Mode)")
    print("=" * 60)
    print(f"\nStory ID: {story_id}")
    
    # Step 1: Check configuration
    print("\n[1/5] Checking configuration...")
    print(f"  Supabase URL: {'✓' if settings.supabase_url else '✗'}")
    print(f"  Supabase Key: {'✓' if settings.supabase_key else '✗'}")
    print(f"  Fal Key: {'✓' if settings.fal_key else '✗'}")
    
    if not settings.supabase_url or not settings.supabase_key:
        print("\n❌ ERROR: Supabase credentials not configured!")
        return
    
    if not settings.fal_key:
        print("\n❌ ERROR: FAL_KEY not configured!")
        return
    
    # Step 2: Fetch story from database
    print("\n[2/5] Fetching story from Supabase...")
    db = get_database()
    
    try:
        book = await db.get_full_book(story_id)
    except Exception as e:
        print(f"\n❌ ERROR fetching story: {e}")
        return
    
    if not book:
        print(f"\n❌ ERROR: Story {story_id} not found in database!")
        return
    
    print(f"  ✓ Found story: {book['title']}")
    print(f"  ✓ Child: {book['child_name']}, Age: {book['child_age']}")
    print(f"  ✓ Theme: {book['theme']}")
    print(f"  ✓ Pages: {book['page_count']}")
    
    # Step 3: Show preview images
    print("\n[3/5] Preview Images:")
    pages = book.get('pages', [])
    for i, page in enumerate(pages[:3]):
        url = page.get('image_url', 'No URL')
        url_preview = url[:50] + '...' if len(url) > 50 else url
        print(f"    Page {page.get('page_number', i+1)}: {url_preview}")
    if len(pages) > 3:
        print(f"    ... and {len(pages) - 3} more pages")
    
    # Step 4: Upscale method selection
    method = UpscaleMethod.CREATIVE_UPSCALER if use_creative else UpscaleMethod.REAL_ESRGAN
    print(f"\n[4/5] Upscale Method: {method.value}")
    
    if method == UpscaleMethod.REAL_ESRGAN:
        print("  - Speed: ~5 seconds per image")
        print("  - Cost: ~$0.01 per image")
        print("  - Quality: Good")
    else:
        print("  - Speed: ~15 seconds per image")
        print("  - Cost: ~$0.03 per image")
        print("  - Quality: Better")
    
    # Step 5: Start print job
    print("\n[5/5] Print Job:")
    
    total_cost = book['page_count'] * (0.03 if use_creative else 0.01)
    
    print("\n" + "=" * 60)
    print("Ready to start print production!")
    print("=" * 60)
    print(f"  Method: {method.value}")
    print(f"  Pages: {book['page_count']}")
    print(f"  Estimated cost: ~${total_cost:.2f}")
    print(f"  Output: /tmp/goldentales_print/verification/")
    print("=" * 60)
    
    confirm = input("\nStart print production? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        print_service = get_print_service()
        print_service.upscale_method = method
        
        print("\n🚀 Starting print production...")
        print("   (This runs in the background, watch logs for progress)")
        
        job = await print_service.start_print_production(
            order_id="test-order-001",
            book_data=book,
            format="hardcover",
            book_size="square_8x8",
            shipping_address={"name": "Test User", "city": "Test City"}
        )
        
        print(f"\n✓ Print job started!")
        print(f"  Job ID: {job.job_id}")
        print(f"  Status: {job.status}")
        
        # Wait for completion
        print("\n⏳ Waiting for job completion...")
        max_wait = 300  # 5 minutes max
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
    
    parser = argparse.ArgumentParser(description="Test print job with upscaling")
    parser.add_argument(
        "--story-id",
        default="e921daea-d19c-4758-8129-e2b19e709687",
        help="Story ID to print"
    )
    parser.add_argument(
        "--creative",
        action="store_true",
        help="Use Creative Upscaler instead of Real-ESRGAN"
    )
    
    args = parser.parse_args()
    
    asyncio.run(test_print_job(args.story_id, args.creative))
