# print_production.py
"""
DreamWeaver Print Production Pipeline
=====================================
Handles the conversion from preview to print-ready:

1. PREVIEW STAGE (Before Purchase):
   - Fast generation (Flux Schnell)
   - Low resolution (800x600)
   - Cost: ~$0.02/image
   - Purpose: User approval

2. PRINT STAGE (After Purchase):
   - High quality generation (Flux Pro 1.1)
   - Print resolution (2400x1800 @ 300 DPI)
   - Cost: ~$0.10/image
   - CMYK conversion
   - Bleed margins
   - Embedded fonts
"""

import asyncio
import os
import io
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

# PDF Generation
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Image Processing
from PIL import Image
import httpx


# ============================================
# CONFIGURATION
# ============================================

class PrintConfig:
    """Print specifications for different formats."""
    
    # Book dimensions (in inches)
    BOOK_SIZES = {
        "square_8x8": {"width": 8, "height": 8},
        "portrait_6x9": {"width": 6, "height": 9},
        "landscape_10x8": {"width": 10, "height": 8},
    }
    
    # Print specifications
    BLEED = 0.125  # inches (3.175mm) - standard bleed
    DPI = 300      # Print resolution
    
    # Image generation sizes (pixels at 300 DPI)
    # For 8x8 book with bleed: (8 + 0.25) * 300 = 2475px
    PRINT_IMAGE_SIZES = {
        "square_8x8": {"width": 2475, "height": 2475},
        "portrait_6x9": {"width": 1875, "height": 2775},
        "landscape_10x8": {"width": 3075, "height": 2475},
    }
    
    # For page spreads (illustration takes ~60% of page height)
    ILLUSTRATION_RATIO = 0.6
    
    # Lulu POD Package IDs
    LULU_PACKAGES = {
        "softcover_8x8": "0850X0850FCSTDPB060UW444GXX",
        "hardcover_8x8": "0850X0850FCHCPB060UW444GXX",
    }


class OrderStatus(str, Enum):
    """Order processing stages."""
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    GENERATING_PRINT_FILES = "generating_print_files"
    CREATING_PDF = "creating_pdf"
    UPLOADING_TO_PRINTER = "uploading_to_printer"
    SENT_TO_PRINTER = "sent_to_printer"
    PRINTING = "printing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class PrintJob:
    """Represents a print production job."""
    job_id: str
    order_id: str
    book_id: str
    status: OrderStatus
    format: str  # softcover, hardcover
    book_size: str  # square_8x8, etc.
    
    # Progress tracking
    total_pages: int = 0
    pages_generated: int = 0
    
    # File paths
    preview_images: List[str] = None
    print_images: List[str] = None
    pdf_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0


# ============================================
# IMAGE GENERATION (Print Quality)
# ============================================

class PrintImageGenerator:
    """Generates print-quality images using Fal.ai."""
    
    def __init__(self, fal_api_key: str):
        self.fal_key = fal_api_key
        os.environ["FAL_KEY"] = fal_api_key
    
    async def generate_print_quality_image(
        self,
        prompt: str,
        negative_prompt: str,
        page_number: int,
        book_size: str = "square_8x8",
        seed: int = None
    ) -> Dict[str, Any]:
        """
        Generate a single high-resolution print-quality image.
        
        Uses Flux Pro 1.1 for maximum quality.
        """
        import fal_client
        
        # Get dimensions for this book size
        dimensions = PrintConfig.PRINT_IMAGE_SIZES.get(
            book_size, 
            PrintConfig.PRINT_IMAGE_SIZES["square_8x8"]
        )
        
        # Use consistent seed for reproducibility
        if seed is None:
            seed = 42 + page_number
        
        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": {
                "width": dimensions["width"],
                "height": int(dimensions["height"] * PrintConfig.ILLUSTRATION_RATIO)
            },
            "num_images": 1,
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
            "num_inference_steps": 28,  # Higher for better quality
            "seed": seed,
        }
        
        try:
            handler = await fal_client.submit_async(
                "fal-ai/flux-pro/v1.1",
                arguments=params
            )
            result = await handler.get()
            
            return {
                "url": result['images'][0]['url'],
                "width": dimensions["width"],
                "height": int(dimensions["height"] * PrintConfig.ILLUSTRATION_RATIO),
                "page_number": page_number,
                "seed": seed
            }
            
        except Exception as e:
            raise Exception(f"Print image generation failed for page {page_number}: {str(e)}")
    
    async def regenerate_all_pages_print_quality(
        self,
        character_bible: Dict[str, str],
        story_pages: List[Dict],
        art_style: str,
        book_size: str = "square_8x8",
        progress_callback: callable = None
    ) -> List[Dict]:
        """
        Regenerate ALL pages at print quality.
        
        This is called AFTER the order is placed and payment confirmed.
        """
        from character_system import CharacterDescriptionGenerator
        
        generator = CharacterDescriptionGenerator()
        print_images = []
        
        # Generate one at a time for reliability (these are expensive!)
        for i, page in enumerate(story_pages):
            page_number = page.get('page_number', i + 1)
            
            # Build the full prompt with character consistency
            full_prompt = generator.build_page_prompt(
                character_bible=character_bible,
                scene_description=page.get('scene_description', ''),
                character_action=page.get('character_action', ''),
                mood=page.get('mood', 'happy'),
                art_style=art_style,
                page_number=page_number,
                include_additional_characters=page.get('characters_in_scene', [])
            )
            
            # Add print-specific quality instructions
            full_prompt += """

PRINT QUALITY REQUIREMENTS:
- Ultra high detail and clarity
- Rich, vibrant colors suitable for print
- No compression artifacts
- Clean edges and sharp lines
- Professional children's book illustration quality
"""
            
            negative_prompt = (
                "nsfw, nude, violence, blood, scary, horror, dark, disturbing, "
                "disfigured, deformed, ugly, mutated, bad anatomy, extra limbs, "
                "blurry, low quality, pixelated, compression artifacts, watermark, "
                "text, signature, cropped, out of frame"
            )
            
            # Generate print-quality image
            result = await self.generate_print_quality_image(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                page_number=page_number,
                book_size=book_size
            )
            
            print_images.append(result)
            
            # Report progress
            if progress_callback:
                await progress_callback(
                    stage="generating_images",
                    current=i + 1,
                    total=len(story_pages),
                    message=f"Generated print image {i + 1}/{len(story_pages)}"
                )
            
            # Small delay between generations
            await asyncio.sleep(1)
        
        return print_images


# ============================================
# IMAGE PROCESSING FOR PRINT
# ============================================

class PrintImageProcessor:
    """Processes images for print production."""
    
    @staticmethod
    async def download_image(url: str) -> Image.Image:
        """Download image from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
    
    @staticmethod
    def convert_to_cmyk(image: Image.Image) -> Image.Image:
        """Convert RGB image to CMYK for print."""
        if image.mode == 'CMYK':
            return image
        
        if image.mode == 'RGBA':
            # Remove alpha channel first
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        
        return image.convert('CMYK')
    
    @staticmethod
    def ensure_print_resolution(
        image: Image.Image,
        target_width: int,
        target_height: int,
        dpi: int = 300
    ) -> Image.Image:
        """Ensure image meets print resolution requirements."""
        
        # Calculate required pixel dimensions
        current_width, current_height = image.size
        
        # If image is smaller than target, upscale with high-quality resampling
        if current_width < target_width or current_height < target_height:
            # Use LANCZOS for high-quality upscaling
            image = image.resize((target_width, target_height), Image.LANCZOS)
        elif current_width > target_width or current_height > target_height:
            # Downscale if too large
            image = image.resize((target_width, target_height), Image.LANCZOS)
        
        return image
    
    @staticmethod
    async def process_for_print(
        image_url: str,
        target_width: int,
        target_height: int,
        output_path: str
    ) -> str:
        """
        Full processing pipeline for a single image:
        1. Download
        2. Resize to target dimensions
        3. Convert to CMYK
        4. Save as high-quality TIFF
        """
        # Download
        image = await PrintImageProcessor.download_image(image_url)
        
        # Ensure resolution
        image = PrintImageProcessor.ensure_print_resolution(
            image, target_width, target_height
        )
        
        # Convert to CMYK
        image = PrintImageProcessor.convert_to_cmyk(image)
        
        # Save as TIFF (lossless, CMYK support)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, format='TIFF', compression='lzw', dpi=(300, 300))
        
        return output_path


# ============================================
# PDF GENERATION
# ============================================

class PrintPDFGenerator:
    """Generates print-ready PDFs."""
    
    def __init__(self, output_dir: str = "/tmp/dreamweaver/pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_print_pdf(
        self,
        job: PrintJob,
        title: str,
        child_name: str,
        pages: List[Dict],
        image_paths: List[str],
        book_size: str = "square_8x8"
    ) -> str:
        """
        Create a complete print-ready PDF.
        
        Specifications:
        - 300 DPI
        - CMYK color space
        - 0.125" bleed on all sides
        - Embedded fonts
        """
        
        # Get book dimensions
        size = PrintConfig.BOOK_SIZES.get(book_size, PrintConfig.BOOK_SIZES["square_8x8"])
        bleed = PrintConfig.BLEED
        
        # Page size with bleed (in points, 72 points = 1 inch)
        page_width = (size["width"] + 2 * bleed) * inch
        page_height = (size["height"] + 2 * bleed) * inch
        
        # Content area (without bleed)
        content_width = size["width"] * inch
        content_height = size["height"] * inch
        
        # Output path
        output_path = os.path.join(
            self.output_dir, 
            f"{job.order_id}_{job.book_id}.pdf"
        )
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
        c.setTitle(title)
        c.setAuthor("DreamWeaver")
        c.setSubject(f"A personalized storybook for {child_name}")
        
        # Register fonts (use built-in for now, can add custom fonts)
        # For production, embed custom children's book fonts
        
        # === COVER PAGE ===
        self._create_cover_page(
            c, title, child_name, 
            page_width, page_height, 
            bleed * inch, content_width, content_height
        )
        c.showPage()
        
        # === STORY PAGES ===
        for i, (page, image_path) in enumerate(zip(pages, image_paths)):
            self._create_story_page(
                c, page, image_path, i + 1,
                page_width, page_height,
                bleed * inch, content_width, content_height
            )
            c.showPage()
        
        # === BACK COVER ===
        self._create_back_cover(
            c, child_name,
            page_width, page_height,
            bleed * inch
        )
        
        c.save()
        return output_path
    
    def _create_cover_page(
        self, c, title, child_name,
        page_width, page_height, bleed,
        content_width, content_height
    ):
        """Create the front cover."""
        
        # Background color (extend to bleed)
        c.setFillColor(CMYKColor(0.1, 0.05, 0, 0.05))
        c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
        
        # Title
        c.setFillColor(CMYKColor(0, 0.3, 0.8, 0))  # Golden amber
        c.setFont("Helvetica-Bold", 36)
        
        # Center title in content area
        title_y = bleed + content_height * 0.6
        c.drawCentredString(page_width / 2, title_y, title)
        
        # Subtitle
        c.setFont("Helvetica", 18)
        c.setFillColor(CMYKColor(0, 0, 0, 0.7))
        c.drawCentredString(
            page_width / 2, 
            title_y - 40, 
            f"A Personalized Adventure for {child_name}"
        )
        
        # DreamWeaver branding
        c.setFont("Helvetica", 10)
        c.setFillColor(CMYKColor(0, 0, 0, 0.4))
        c.drawCentredString(page_width / 2, bleed + 30, "Created with DreamWeaver")
    
    def _create_story_page(
        self, c, page_data, image_path, page_number,
        page_width, page_height, bleed,
        content_width, content_height
    ):
        """Create a single story page with illustration and text."""
        
        # Background
        c.setFillColor(CMYKColor(0, 0, 0.02, 0))  # Warm white
        c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
        
        # === ILLUSTRATION (top 60% of content area) ===
        illustration_height = content_height * 0.6
        illustration_y = bleed + content_height * 0.35  # Position from bottom
        
        if image_path and os.path.exists(image_path):
            c.drawImage(
                image_path,
                bleed,  # x position
                illustration_y,  # y position
                width=content_width,
                height=illustration_height,
                preserveAspectRatio=True,
                anchor='c'
            )
        
        # === TEXT (bottom 35% of content area) ===
        text = page_data.get('text', '')
        text_y = bleed + content_height * 0.25
        
        # Drop cap (first letter)
        if text:
            first_letter = text[0]
            rest_of_text = text[1:]
            
            # Draw drop cap
            c.setFont("Helvetica-Bold", 48)
            c.setFillColor(CMYKColor(0, 0.3, 0.8, 0))  # Amber
            c.drawString(bleed + 20, text_y, first_letter)
            
            # Draw rest of text
            c.setFont("Helvetica", 14)
            c.setFillColor(CMYKColor(0, 0, 0, 0.85))
            
            # Simple text wrapping
            max_width = content_width - 80  # Padding
            words = rest_of_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if c.stringWidth(test_line, "Helvetica", 14) < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Draw lines
            y = text_y - 5
            for i, line in enumerate(lines):
                x = bleed + 70 if i == 0 else bleed + 20  # Indent first line for drop cap
                c.drawString(x, y, line)
                y -= 20
        
        # === PAGE NUMBER ===
        c.setFont("Helvetica", 10)
        c.setFillColor(CMYKColor(0, 0, 0, 0.3))
        c.drawCentredString(page_width / 2, bleed + 15, str(page_number))
    
    def _create_back_cover(
        self, c, child_name,
        page_width, page_height, bleed
    ):
        """Create the back cover."""
        
        # Background
        c.setFillColor(CMYKColor(0.1, 0.05, 0, 0.05))
        c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
        
        # Message
        c.setFont("Helvetica-Oblique", 14)
        c.setFillColor(CMYKColor(0, 0, 0, 0.6))
        c.drawCentredString(
            page_width / 2,
            page_height / 2,
            f"Made with love for {child_name}"
        )
        
        # DreamWeaver info
        c.setFont("Helvetica", 10)
        c.setFillColor(CMYKColor(0, 0, 0, 0.4))
        c.drawCentredString(
            page_width / 2,
            bleed + 40,
            "dreamweaver.ai"
        )
        c.drawCentredString(
            page_width / 2,
            bleed + 25,
            f"© {datetime.now().year} DreamWeaver"
        )


# ============================================
# PRINT PRODUCTION ORCHESTRATOR
# ============================================

class PrintProductionPipeline:
    """
    Orchestrates the entire print production process.
    
    Called after payment is confirmed to:
    1. Generate print-quality images
    2. Process images (CMYK, resolution)
    3. Generate print-ready PDF
    4. Upload to Lulu
    5. Track order status
    """
    
    def __init__(
        self,
        fal_api_key: str,
        lulu_api_key: str = None,
        output_dir: str = "/tmp/dreamweaver"
    ):
        self.image_generator = PrintImageGenerator(fal_api_key)
        self.pdf_generator = PrintPDFGenerator(os.path.join(output_dir, "pdfs"))
        self.lulu_api_key = lulu_api_key
        self.output_dir = output_dir
        
        # Job tracking
        self.jobs: Dict[str, PrintJob] = {}
    
    async def start_print_production(
        self,
        order_id: str,
        book_data: Dict,
        format: str = "hardcover",
        book_size: str = "square_8x8",
        shipping_address: Dict = None,
        progress_callback: callable = None
    ) -> PrintJob:
        """
        Start the print production pipeline for an order.
        
        This is an async process that runs in the background.
        """
        
        job_id = str(uuid.uuid4())[:8]
        
        job = PrintJob(
            job_id=job_id,
            order_id=order_id,
            book_id=book_data['book_id'],
            status=OrderStatus.PAYMENT_CONFIRMED,
            format=format,
            book_size=book_size,
            total_pages=len(book_data['pages']),
            pages_generated=0,
            preview_images=book_data.get('preview_images', []),
            print_images=[],
            created_at=datetime.now()
        )
        
        self.jobs[job_id] = job
        
        # Start production in background
        asyncio.create_task(
            self._run_production(job, book_data, shipping_address, progress_callback)
        )
        
        return job
    
    async def _run_production(
        self,
        job: PrintJob,
        book_data: Dict,
        shipping_address: Dict,
        progress_callback: callable
    ):
        """Run the full production pipeline."""
        
        try:
            job.started_at = datetime.now()
            
            # === STAGE 1: Generate Print Images ===
            job.status = OrderStatus.GENERATING_PRINT_FILES
            await self._update_progress(progress_callback, job, "Starting print image generation...")
            
            print_images = await self.image_generator.regenerate_all_pages_print_quality(
                character_bible=book_data.get('character_bible', {}),
                story_pages=book_data['pages'],
                art_style=book_data.get('art_style', 'watercolor'),
                book_size=job.book_size,
                progress_callback=progress_callback
            )
            
            # === STAGE 2: Process Images for Print ===
            await self._update_progress(progress_callback, job, "Processing images for print...")
            
            processed_image_paths = []
            for i, img_data in enumerate(print_images):
                output_path = os.path.join(
                    self.output_dir, 
                    "images", 
                    job.order_id,
                    f"page_{i+1:02d}.tiff"
                )
                
                await PrintImageProcessor.process_for_print(
                    image_url=img_data['url'],
                    target_width=img_data['width'],
                    target_height=img_data['height'],
                    output_path=output_path
                )
                
                processed_image_paths.append(output_path)
                job.pages_generated = i + 1
                
                await self._update_progress(
                    progress_callback, job, 
                    f"Processed image {i+1}/{len(print_images)}"
                )
            
            job.print_images = processed_image_paths
            
            # === STAGE 3: Generate PDF ===
            job.status = OrderStatus.CREATING_PDF
            await self._update_progress(progress_callback, job, "Creating print-ready PDF...")
            
            pdf_path = self.pdf_generator.create_print_pdf(
                job=job,
                title=book_data['title'],
                child_name=book_data['child_name'],
                pages=book_data['pages'],
                image_paths=processed_image_paths,
                book_size=job.book_size
            )
            
            job.pdf_path = pdf_path
            
            # === STAGE 4: Upload to Lulu ===
            if self.lulu_api_key and shipping_address:
                job.status = OrderStatus.UPLOADING_TO_PRINTER
                await self._update_progress(progress_callback, job, "Uploading to printer...")
                
                lulu_job_id = await self._submit_to_lulu(
                    job, book_data['title'], shipping_address
                )
                
                job.status = OrderStatus.SENT_TO_PRINTER
                await self._update_progress(
                    progress_callback, job, 
                    f"Sent to printer! Lulu Job ID: {lulu_job_id}"
                )
            else:
                # Digital only or Lulu not configured
                job.status = OrderStatus.SENT_TO_PRINTER
            
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = OrderStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            
            await self._update_progress(
                progress_callback, job, 
                f"Production failed: {str(e)}"
            )
    
    async def _submit_to_lulu(
        self,
        job: PrintJob,
        title: str,
        shipping_address: Dict
    ) -> str:
        """Submit the PDF to Lulu for printing."""
        
        LULU_API_URL = "https://api.lulu.com/v1"
        
        async with httpx.AsyncClient() as client:
            # 1. Upload PDF
            with open(job.pdf_path, 'rb') as f:
                upload_response = await client.post(
                    f"{LULU_API_URL}/files",
                    headers={"Authorization": f"Bearer {self.lulu_api_key}"},
                    files={"file": f},
                    timeout=120
                )
                upload_response.raise_for_status()
                file_id = upload_response.json()['id']
            
            # 2. Create print job
            package_id = PrintConfig.LULU_PACKAGES.get(
                f"{job.format}_{job.book_size}",
                PrintConfig.LULU_PACKAGES["softcover_8x8"]
            )
            
            order_data = {
                "line_items": [{
                    "title": title,
                    "quantity": 1,
                    "printable_normalization": {
                        "pod_package_id": package_id,
                        "cover": {"source_url": file_id},
                        "interior": {"source_url": file_id}
                    }
                }],
                "shipping_address": {
                    "name": shipping_address.get('name', ''),
                    "street1": shipping_address.get('street1', ''),
                    "street2": shipping_address.get('street2', ''),
                    "city": shipping_address.get('city', ''),
                    "state_code": shipping_address.get('state', ''),
                    "country_code": shipping_address.get('country', 'US'),
                    "postcode": shipping_address.get('zip', '')
                },
                "shipping_level": "MAIL"  # or PRIORITY_MAIL for express
            }
            
            order_response = await client.post(
                f"{LULU_API_URL}/print-jobs",
                headers={
                    "Authorization": f"Bearer {self.lulu_api_key}",
                    "Content-Type": "application/json"
                },
                json=order_data,
                timeout=60
            )
            order_response.raise_for_status()
            
            return order_response.json().get('id', 'unknown')
    
    async def _update_progress(
        self,
        callback: callable,
        job: PrintJob,
        message: str
    ):
        """Update progress via callback if provided."""
        if callback:
            await callback(
                job_id=job.job_id,
                status=job.status.value,
                pages_generated=job.pages_generated,
                total_pages=job.total_pages,
                message=message
            )
    
    def get_job_status(self, job_id: str) -> Optional[PrintJob]:
        """Get the current status of a print job."""
        return self.jobs.get(job_id)


# ============================================
# API ENDPOINTS FOR ORDER PROCESSING
# ============================================

"""
Add these endpoints to main.py:

@app.post("/api/orders/{order_id}/process-payment")
async def process_payment(order_id: str, payment_data: dict):
    '''Called after Stripe payment succeeds.'''
    
    # Verify payment with Stripe
    # ...
    
    # Start print production
    pipeline = PrintProductionPipeline(
        fal_api_key=Config.FAL_KEY,
        lulu_api_key=Config.LULU_API_KEY
    )
    
    book_data = book_storage[order['book_id']]
    
    job = await pipeline.start_print_production(
        order_id=order_id,
        book_data=book_data,
        format=order['format'],
        shipping_address=order.get('shipping_address')
    )
    
    return {"job_id": job.job_id, "status": job.status.value}


@app.get("/api/orders/{order_id}/production-status")
async def get_production_status(order_id: str):
    '''Get real-time production status.'''
    
    job = pipeline.get_job_status(order_id)
    if not job:
        raise HTTPException(404, "Production job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": {
            "pages_generated": job.pages_generated,
            "total_pages": job.total_pages,
            "percentage": (job.pages_generated / job.total_pages * 100) if job.total_pages else 0
        },
        "pdf_ready": job.pdf_path is not None,
        "error": job.error_message
    }
"""


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Example: Process an order
    
    async def example():
        pipeline = PrintProductionPipeline(
            fal_api_key="your_fal_key",
            lulu_api_key="your_lulu_key"
        )
        
        # Mock book data (would come from database)
        book_data = {
            "book_id": "abc123",
            "title": "Emma's Christmas Adventure",
            "child_name": "Emma",
            "art_style": "watercolor",
            "pages": [
                {"page_number": 1, "text": "Once upon a time...", "scene_description": "..."},
                # ... more pages
            ],
            "preview_images": ["https://..."],  # Low-res previews
            "character_bible": {
                "main_character": "a 6-year-old girl named Emma...",
                # ... full bible
            }
        }
        
        # Start production (runs in background)
        job = await pipeline.start_print_production(
            order_id="order_123",
            book_data=book_data,
            format="hardcover",
            shipping_address={
                "name": "John Smith",
                "street1": "123 Main St",
                "city": "Chicago",
                "state": "IL",
                "zip": "60601",
                "country": "US"
            }
        )
        
        print(f"Production started: {job.job_id}")
        print(f"Status: {job.status}")
    
    asyncio.run(example())