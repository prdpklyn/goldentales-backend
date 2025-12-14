#!/usr/bin/env python3
"""
Simple print job test using in-memory book data from API.
This works without requiring a database connection.
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
        print("\n   Example:")
        print("   curl -X POST http://localhost:8000/api/books/create \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{...}'")
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
        print("   Book creation takes 30-60 seconds for image generation.")
        return
    
    # Check if images are valid URLs
    valid_images = [img for img in book['preview_images'] if img and img.startswith('http')]
    if len(valid_images) < book['page_count']:
        print(f"\n⚠ WARNING: Only {len(valid_images)}/{book['page_count']} valid image URLs found")
        print("   Some images may not have been generated yet.")
        response = input("   Continue anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            return
    
    # Show first few preview images
    print("\nPreview Images:")
    for i, img_url in enumerate(book['preview_images'][:3], 1):
        if img_url:
            print(f"  Page {i}: {img_url[:60]}...")
        else:
            print(f"  Page {i}: (no URL)")
    if len(book['preview_images']) > 3:
        print(f"  ... and {len(book['preview_images']) - 3} more")
    
    # Prepare book data for print service
    # The print service expects pages with image_url
    pages = []
    for i, page in enumerate(book.get('pages', [])):
        page_data = page.copy()
        # Add image_url from preview_images array
        if i < len(book['preview_images']) and book['preview_images'][i]:
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
    print(f"  Estimated time: ~{book['page_count'] * 5}s for upscaling")
    print(f"  Output: /tmp/goldentales_print/verification/")
    print("=" * 60)
    
    confirm = input("\nStart print production? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        print_service = get_print_service()
        print_service.upscale_method = UpscaleMethod.REAL_ESRGAN
        
        print("\n🚀 Starting print production...")
        print("   (This runs in the background, check server logs for progress)")
        
        try:
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
                    print(f"\n   Or view it directly:")
                    print(f"   open /tmp/goldentales_print/verification/job_{final_job.job_id}.pdf")
                
                if final_job.error_message:
                    print(f"\n  ❌ Error: {final_job.error_message}")
                
                if final_job.print_image_urls:
                    print(f"\n  ✓ Upscaled {len(final_job.print_image_urls)} images")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
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
        help="Book ID from API book creation (e.g., from POST /api/books/create)"
    )
    parser.add_argument(
        "--creative",
        action="store_true",
        help="Use Creative Upscaler instead of Real-ESRGAN (better quality, slower)"
    )
    
    args = parser.parse_args()
    
    # Set upscale method if requested
    if args.creative:
        import sys
        sys.path.insert(0, '.')
        from app.services.print_service import get_print_service, UpscaleMethod
        print_service = get_print_service()
        print_service.upscale_method = UpscaleMethod.CREATIVE_UPSCALER
    
    asyncio.run(test_print_job_from_api(args.book_id))

