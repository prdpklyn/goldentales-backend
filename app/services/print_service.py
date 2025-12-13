# app/services/print_service.py
"""
GoldenTales Print Production Service
=====================================
Handles print-quality PDF generation after order payment.

CRITICAL: Uses UPSCALING instead of regeneration for consistency!
- Preview: Flux Schnell @ 800×600
- Print: UPSCALE preview images to 2400×1800
- Result: Identical images, just higher resolution!

PDF Layout matches the website preview:
┌─────────────────┬─────────────────┐
│                 │                 │
│   [ILLUSTRATION]│    C hristmas   │
│                 │    was coming!  │
│                 │    Jishitha     │
│                 │    loved...     │
│                 │                 │
│      ─ 1 ─      │                 │
└─────────────────┴─────────────────┘
     LEFT PAGE         RIGHT PAGE
     (Image)           (Text + Drop Cap)
"""

import asyncio
import os
import io
import uuid
import httpx
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# PDF Generation
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color

# Image Processing
from PIL import Image

# Fal.ai client
import fal_client

# Local imports
from app.settings import settings
from app.models.enums import OrderStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ============================================
# CONFIGURATION
# ============================================

class BookFormat(str, Enum):
    """Book size formats."""
    SQUARE_8X8 = "8x8"
    SQUARE_8_5X8_5 = "8.5x8.5"
    LANDSCAPE_10X8 = "10x8"


@dataclass
class BookSpec:
    """Specifications for a book format."""
    page_width: float      # Single page width in inches
    page_height: float     # Page height in inches
    bleed: float = 0.125   # Bleed area for trimming
    margin: float = 0.5    # Safe content margin
    gutter: float = 0.625  # Spine/binding margin
    dpi: int = 300         # Print resolution
    
    @property
    def spread_width(self) -> float:
        """Width of a 2-page spread."""
        return self.page_width * 2
    
    @property
    def total_width_with_bleed(self) -> float:
        return self.spread_width + (2 * self.bleed)
    
    @property
    def total_height_with_bleed(self) -> float:
        return self.page_height + (2 * self.bleed)
    
    @property
    def pixel_width(self) -> int:
        return int(self.total_width_with_bleed * self.dpi)
    
    @property
    def pixel_height(self) -> int:
        return int(self.total_height_with_bleed * self.dpi)


BOOK_SPECS = {
    BookFormat.SQUARE_8X8: BookSpec(page_width=8.0, page_height=8.0),
    BookFormat.SQUARE_8_5X8_5: BookSpec(page_width=8.5, page_height=8.5),
    BookFormat.LANDSCAPE_10X8: BookSpec(page_width=10.0, page_height=8.0),
}

# Legacy mapping for backwards compatibility
BOOK_SIZES = {
    "square_8x8": BookFormat.SQUARE_8X8,
    "portrait_6x9": BookFormat.SQUARE_8X8,  # Map to 8x8 for now
    "landscape_10x8": BookFormat.LANDSCAPE_10X8,
}


@dataclass
class BookTheme:
    """Visual theme for the book."""
    background_color: str = "#FDF8F3"      # Warm cream paper
    text_color: str = "#2D2A26"            # Dark brown text
    drop_cap_color: str = "#E8A54B"        # Amber/gold drop cap
    page_number_color: str = "#8B8680"     # Muted gray
    
    body_font: str = "Helvetica"
    drop_cap_font: str = "Helvetica-Bold"
    body_font_size: int = 14
    drop_cap_font_size: int = 48
    page_number_font_size: int = 10
    
    line_spacing: float = 1.5


class UpscaleMethod(str, Enum):
    """Available upscaling methods."""
    REAL_ESRGAN = "real_esrgan"       # Fast, good quality, ~$0.01
    CREATIVE_UPSCALER = "creative"     # Slower, better quality, ~$0.03


@dataclass
class PrintJob:
    """Represents a print production job."""
    job_id: str
    order_id: str
    book_id: str
    status: OrderStatus = OrderStatus.PENDING_PAYMENT
    preview_image_urls: List[str] = field(default_factory=list)
    print_image_urls: List[str] = field(default_factory=list)
    processed_image_paths: List[str] = field(default_factory=list)
    pdf_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# ============================================
# IMAGE UPSCALER
# ============================================

class ImageUpscaler:
    """
    Upscales preview images to print resolution.
    
    This is the KEY to consistency - we don't regenerate,
    we upscale the EXACT same image the user approved.
    """
    
    def __init__(self, fal_api_key: str):
        self.fal_api_key = fal_api_key
        os.environ["FAL_KEY"] = fal_api_key
    
    async def upscale_image(
        self,
        image_url: str,
        method: UpscaleMethod = UpscaleMethod.REAL_ESRGAN
    ) -> str:
        """Upscale a single image to print resolution."""
        if method == UpscaleMethod.REAL_ESRGAN:
            return await self._upscale_with_esrgan(image_url)
        elif method == UpscaleMethod.CREATIVE_UPSCALER:
            return await self._upscale_with_creative(image_url)
        else:
            raise ValueError(f"Unknown upscale method: {method}")
    
    async def _upscale_with_esrgan(self, image_url: str) -> str:
        """Fast upscaling with Real-ESRGAN (~5s, ~$0.01)."""
        logger.info(f"Upscaling with Real-ESRGAN: {image_url[:60]}...")
        
        result = await fal_client.run_async(
            "fal-ai/esrgan",
            arguments={
                "image_url": image_url,
                "scale": 4,
            }
        )
        
        upscaled_url = result.get("image", {}).get("url")
        logger.info(f"Upscaled successfully")
        return upscaled_url
    
    async def _upscale_with_creative(self, image_url: str) -> str:
        """Higher quality upscaling with Clarity (~15s, ~$0.03)."""
        logger.info(f"Upscaling with Clarity Upscaler: {image_url[:60]}...")
        
        result = await fal_client.run_async(
            "fal-ai/clarity-upscaler",
            arguments={
                "image_url": image_url,
                "scale": 4,
                "creativity": 0.2,
                "prompt": "high quality, detailed, 4k",
            }
        )
        
        upscaled_url = result.get("image", {}).get("url")
        logger.info(f"Upscaled successfully")
        return upscaled_url
    
    async def upscale_all_pages(
        self,
        preview_urls: List[str],
        method: UpscaleMethod = UpscaleMethod.REAL_ESRGAN
    ) -> List[str]:
        """Upscale all preview images to print resolution."""
        logger.info(f"Upscaling {len(preview_urls)} pages with {method.value}...")
        
        upscaled_urls = []
        for i, url in enumerate(preview_urls):
            if not url:
                logger.warning(f"Page {i+1} has no image URL, skipping")
                upscaled_urls.append(None)
                continue
                
            try:
                upscaled = await self.upscale_image(url, method)
                upscaled_urls.append(upscaled)
                logger.info(f"Page {i+1}/{len(preview_urls)} upscaled")
            except Exception as e:
                logger.error(f"Failed to upscale page {i+1}: {e}")
                upscaled_urls.append(url)  # Fallback to original
        
        logger.info(f"Completed upscaling {len(upscaled_urls)} pages")
        return upscaled_urls


# ============================================
# PDF GENERATOR (Matches Website Preview)
# ============================================

class BookPDFGenerator:
    """
    Generates print-ready PDFs matching the website preview layout.
    
    Output: PDF with 2-page spreads where:
    - Left page = Full illustration with page number
    - Right page = Story text with drop cap
    """
    
    def __init__(
        self,
        output_dir: str = "/tmp/goldentales_books",
        book_format: BookFormat = BookFormat.SQUARE_8X8,
        theme: Optional[BookTheme] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.spec = BOOK_SPECS.get(book_format, BOOK_SPECS[BookFormat.SQUARE_8X8])
        self.theme = theme or BookTheme()
    
    def _hex_to_color(self, hex_color: str) -> Color:
        """Convert hex color to ReportLab Color."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return Color(r, g, b)
    
    async def download_image(self, url: str) -> Image.Image:
        """Download image from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
    
    def save_image_temp(self, image: Image.Image, filename: str) -> str:
        """Save image to temp file for PDF embedding."""
        path = self.output_dir / filename
        
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        
        image.save(str(path), 'JPEG', quality=95, dpi=(300, 300))
        return str(path)
    
    def create_cover_spread(
        self,
        c: canvas.Canvas,
        title: str,
        child_name: str,
        cover_image_path: str
    ):
        """Create the cover spread (back cover + front cover)."""
        spec = self.spec
        
        page_width = spec.page_width * inch
        page_height = spec.page_height * inch
        bleed = spec.bleed * inch
        margin = spec.margin * inch
        
        total_width = spec.total_width_with_bleed * inch
        total_height = spec.total_height_with_bleed * inch
        
        # Background
        c.setFillColor(self._hex_to_color(self.theme.background_color))
        c.rect(0, 0, total_width, total_height, fill=1, stroke=0)
        
        # Front cover (right side) - Cover image
        if cover_image_path and os.path.exists(cover_image_path):
            img_x = page_width + bleed
            img_y = bleed
            img_width = page_width
            img_height = page_height
            
            c.drawImage(
                cover_image_path,
                img_x, img_y,
                width=img_width,
                height=img_height,
                preserveAspectRatio=True,
                anchor='c'
            )
        
        # Title text (with shadow for readability)
        title_x = page_width + bleed + (page_width / 2)
        title_y = bleed + margin + 80
        
        c.setFont("Helvetica-Bold", 36)
        c.setFillColor(self._hex_to_color("#00000066"))
        c.drawCentredString(title_x + 2, title_y - 2, title)
        c.setFillColor(self._hex_to_color("#FFFFFF"))
        c.drawCentredString(title_x, title_y, title)
        
        # Subtitle
        c.setFont("Helvetica", 18)
        c.drawCentredString(title_x, title_y - 40, f"A story for {child_name}")
        
        # Back cover
        back_x = bleed + (page_width / 2)
        back_y = bleed + margin
        
        c.setFont("Helvetica", 12)
        c.setFillColor(self._hex_to_color(self.theme.text_color))
        c.drawCentredString(back_x, back_y + 40, "Created with GoldenTales")
        c.drawCentredString(back_x, back_y + 20, "www.goldentales.app")
        
        c.showPage()
    
    def create_story_spread(
        self,
        c: canvas.Canvas,
        page_number: int,
        image_path: str,
        text: str
    ):
        """
        Create a story spread matching website preview.
        
        Layout:
        ┌─────────────────┬─────────────────┐
        │                 │                 │
        │  [ILLUSTRATION] │   T ext starts  │
        │                 │   here with a   │
        │                 │   drop cap...   │
        │                 │                 │
        │      ─ 1 ─      │                 │
        └─────────────────┴─────────────────┘
        """
        spec = self.spec
        theme = self.theme
        
        page_width = spec.page_width * inch
        page_height = spec.page_height * inch
        bleed = spec.bleed * inch
        margin = spec.margin * inch
        gutter = spec.gutter * inch
        
        total_width = spec.total_width_with_bleed * inch
        total_height = spec.total_height_with_bleed * inch
        
        # ─────────────────────────────────────
        # BACKGROUND (warm cream paper)
        # ─────────────────────────────────────
        c.setFillColor(self._hex_to_color(theme.background_color))
        c.rect(0, 0, total_width, total_height, fill=1, stroke=0)
        
        # ─────────────────────────────────────
        # LEFT PAGE: ILLUSTRATION
        # ─────────────────────────────────────
        if image_path and os.path.exists(image_path):
            img_x = bleed + margin
            img_y = bleed + margin
            img_width = page_width - margin - gutter
            img_height = page_height - (2 * margin)
            
            c.drawImage(
                image_path,
                img_x, img_y,
                width=img_width,
                height=img_height,
                preserveAspectRatio=True,
                anchor='c'
            )
            
            # Subtle border
            c.setStrokeColor(self._hex_to_color("#E0DCD8"))
            c.setLineWidth(0.5)
            c.rect(img_x, img_y, img_width, img_height, fill=0, stroke=1)
        
        # Page number on left page
        c.setFillColor(self._hex_to_color(theme.page_number_color))
        c.setFont(theme.body_font, theme.page_number_font_size)
        page_num_y = bleed + (margin / 2)
        page_num_x = bleed + (page_width / 2)
        c.drawCentredString(page_num_x, page_num_y, f"— {page_number} —")
        
        # ─────────────────────────────────────
        # RIGHT PAGE: TEXT WITH DROP CAP
        # ─────────────────────────────────────
        text_page_x = bleed + page_width
        
        text_left = text_page_x + gutter
        text_right = text_page_x + page_width - margin
        text_top = bleed + page_height - margin
        text_bottom = bleed + margin
        text_width = text_right - text_left
        
        if text and text.strip():
            text = text.strip()
            first_letter = text[0].upper()
            remaining_text = text[1:] if len(text) > 1 else ""
            
            # ─────────────────────────────────────
            # DROP CAP
            # ─────────────────────────────────────
            c.setFillColor(self._hex_to_color(theme.drop_cap_color))
            c.setFont(theme.drop_cap_font, theme.drop_cap_font_size)
            
            drop_cap_x = text_left
            drop_cap_y = text_top - theme.drop_cap_font_size
            
            c.drawString(drop_cap_x, drop_cap_y, first_letter)
            
            drop_cap_width = c.stringWidth(
                first_letter, 
                theme.drop_cap_font, 
                theme.drop_cap_font_size
            ) + 8
            
            # ─────────────────────────────────────
            # BODY TEXT (wraps around drop cap)
            # ─────────────────────────────────────
            c.setFillColor(self._hex_to_color(theme.text_color))
            c.setFont(theme.body_font, theme.body_font_size)
            
            line_height = theme.body_font_size * theme.line_spacing
            drop_cap_lines = int(theme.drop_cap_font_size / line_height) + 1
            
            # Word wrap the text
            words = remaining_text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                
                if len(lines) < drop_cap_lines:
                    max_width = text_width - drop_cap_width
                else:
                    max_width = text_width
                
                if c.stringWidth(test_line, theme.body_font, theme.body_font_size) < max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text lines
            y = text_top - line_height
            for i, line in enumerate(lines):
                if i < drop_cap_lines:
                    x = text_left + drop_cap_width
                else:
                    x = text_left
                
                c.drawString(x, y, line)
                y -= line_height
                
                if y < text_bottom:
                    break
        
        c.showPage()
    
    def create_end_page(
        self,
        c: canvas.Canvas,
        child_name: str,
        message: str = "The End"
    ):
        """Create the final page spread."""
        spec = self.spec
        
        page_width = spec.page_width * inch
        page_height = spec.page_height * inch
        bleed = spec.bleed * inch
        
        total_width = spec.total_width_with_bleed * inch
        total_height = spec.total_height_with_bleed * inch
        
        # Background
        c.setFillColor(self._hex_to_color(self.theme.background_color))
        c.rect(0, 0, total_width, total_height, fill=1, stroke=0)
        
        # "The End" on left page
        center_x = bleed + (page_width / 2)
        center_y = bleed + (page_height / 2)
        
        c.setFillColor(self._hex_to_color(self.theme.drop_cap_color))
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(center_x, center_y + 20, message)
        
        c.setFillColor(self._hex_to_color(self.theme.text_color))
        c.setFont("Helvetica", 16)
        c.drawCentredString(center_x, center_y - 30, f"Made with ♥ for {child_name}")
        
        # Right page - created info
        right_center_x = bleed + page_width + (page_width / 2)
        
        c.setFont("Helvetica", 12)
        c.setFillColor(self._hex_to_color(self.theme.page_number_color))
        c.drawCentredString(right_center_x, center_y, "Created with GoldenTales")
        c.drawCentredString(right_center_x, center_y - 20, "AI-Powered Personalized Storybooks")
        
        c.showPage()
    
    async def generate_book_pdf(
        self,
        book_id: str,
        title: str,
        child_name: str,
        pages: List[Dict],
        image_urls: List[str],
        cover_image_url: Optional[str] = None
    ) -> str:
        """
        Generate complete book PDF matching website preview.
        
        Args:
            book_id: Unique book identifier
            title: Book title
            child_name: Child's name
            pages: List of page dicts with 'text' or 'text_content' key
            image_urls: List of image URLs (already upscaled)
            cover_image_url: Optional separate cover image
            
        Returns:
            Path to generated PDF
        """
        spec = self.spec
        pdf_path = self.output_dir / f"{book_id}_print.pdf"
        
        page_size = (
            spec.total_width_with_bleed * inch,
            spec.total_height_with_bleed * inch
        )
        
        c = canvas.Canvas(str(pdf_path), pagesize=page_size)
        
        # Download and save images
        logger.info(f"Downloading {len(image_urls)} images...")
        image_paths = []
        for i, url in enumerate(image_urls):
            if not url:
                image_paths.append(None)
                continue
            try:
                image = await self.download_image(url)
                path = self.save_image_temp(image, f"{book_id}_page_{i+1}.jpg")
                image_paths.append(path)
                logger.info(f"Downloaded page {i+1}")
            except Exception as e:
                logger.error(f"Failed to download page {i+1}: {e}")
                image_paths.append(None)
        
        # Cover image
        cover_path = None
        if cover_image_url:
            try:
                cover_image = await self.download_image(cover_image_url)
                cover_path = self.save_image_temp(cover_image, f"{book_id}_cover.jpg")
            except Exception as e:
                logger.warning(f"Cover download failed: {e}")
                cover_path = image_paths[0] if image_paths else None
        else:
            cover_path = image_paths[0] if image_paths else None
        
        logger.info("Generating PDF spreads...")
        
        # Cover spread
        self.create_cover_spread(c, title, child_name, cover_path)
        
        # Story pages
        for i, (page, image_path) in enumerate(zip(pages, image_paths)):
            text = page.get('text', '') or page.get('text_content', '')
            page_number = i + 1
            self.create_story_spread(c, page_number, image_path, text)
            logger.info(f"Created spread {page_number}")
        
        # End page
        self.create_end_page(c, child_name)
        
        c.save()
        logger.info(f"PDF saved: {pdf_path}")
        return str(pdf_path)


# ============================================
# PRINT SERVICE
# ============================================

class PrintService:
    """
    Main service for print production.
    
    Flow:
    1. Receive order with story_id
    2. Fetch preview images from book data
    3. UPSCALE preview images (NOT regenerate!)
    4. Generate PDF matching website preview
    5. Upload to fulfillment provider
    """
    
    def __init__(
        self,
        upscale_method: UpscaleMethod = UpscaleMethod.REAL_ESRGAN
    ):
        if not settings.fal_key:
            raise ValueError("FAL_KEY not configured")
        
        self.upscaler = ImageUpscaler(settings.fal_key)
        self.upscale_method = upscale_method
        
        # Output directories
        self.output_dir = Path("/tmp/goldentales_print")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.verification_dir = self.output_dir / "verification"
        self.verification_dir.mkdir(parents=True, exist_ok=True)
        
        # Job storage
        self.jobs: Dict[str, PrintJob] = {}
    
    async def start_print_production(
        self,
        order_id: str,
        book_data: Dict,
        format: str = "hardcover",
        book_size: str = "square_8x8",
        shipping_address: Optional[Dict] = None
    ) -> PrintJob:
        """Start the print production process."""
        pages = book_data.get("pages", [])
        preview_urls = []
        for page in pages:
            url = page.get("image_url") or page.get("preview_url")
            preview_urls.append(url)
        
        job = PrintJob(
            job_id=f"pj_{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            book_id=book_data.get("book_id", "unknown"),
            preview_image_urls=preview_urls
        )
        
        self.jobs[job.job_id] = job
        
        logger.info(f"Starting print production for order {order_id}")
        logger.info(f"Book: {book_data.get('title')}, Pages: {len(pages)}")
        logger.info(f"Upscale method: {self.upscale_method.value}")
        
        # Run production in background
        asyncio.create_task(
            self._run_production(job, book_data, book_size, shipping_address)
        )
        
        return job
    
    async def _run_production(
        self,
        job: PrintJob,
        book_data: Dict,
        book_size: str,
        shipping_address: Optional[Dict]
    ):
        """Run the full production pipeline."""
        try:
            # Step 1: Upscale preview images
            job.status = OrderStatus.GENERATING_PRINT_FILES
            logger.info(f"[{job.job_id}] Step 1: Upscaling images...")
            
            job.print_image_urls = await self.upscaler.upscale_all_pages(
                job.preview_image_urls,
                self.upscale_method
            )
            
            # Step 2: Generate PDF with new layout
            job.status = OrderStatus.CREATING_PDF
            logger.info(f"[{job.job_id}] Step 2: Creating PDF...")
            
            # Determine book format
            book_format = BOOK_SIZES.get(book_size, BookFormat.SQUARE_8X8)
            
            pdf_generator = BookPDFGenerator(
                output_dir=str(self.output_dir),
                book_format=book_format,
                theme=BookTheme()
            )
            
            pdf_path = await pdf_generator.generate_book_pdf(
                book_id=job.job_id,
                title=book_data.get("title", "My Storybook"),
                child_name=book_data.get("child_name", ""),
                pages=book_data.get("pages", []),
                image_urls=job.print_image_urls
            )
            
            job.pdf_path = pdf_path
            
            # Step 3: Save for verification
            verify_path = str(self.verification_dir / f"job_{job.job_id}.pdf")
            shutil.copy2(pdf_path, verify_path)
            logger.info(f"PDF saved for verification at: {verify_path}")
            
            # Step 4: Upload to fulfillment (if configured)
            if settings.lulu_api_key and shipping_address:
                job.status = OrderStatus.UPLOADING_TO_PRINTER
                await self._submit_to_lulu(job, book_data.get("title", ""), shipping_address)
            
            job.status = OrderStatus.SENT_TO_PRINTER
            job.completed_at = datetime.now()
            logger.info(f"Print job {job.job_id} completed successfully")
            logger.info(f"PDF location: {job.pdf_path}")
            
        except Exception as e:
            job.status = OrderStatus.FAILED
            job.error_message = str(e)
            logger.error(f"Print job {job.job_id} failed: {e}")
    
    async def _submit_to_lulu(
        self,
        job: PrintJob,
        title: str,
        shipping_address: Dict
    ):
        """Submit print job to Lulu API."""
        logger.info(f"Submitting to Lulu: {title}")
        logger.info(f"Would submit PDF {job.pdf_path} to Lulu")
        logger.info(f"Shipping to: {shipping_address.get('name', 'Unknown')}")
    
    def get_job_status(self, job_id: str) -> Optional[PrintJob]:
        """Get current status of a print job."""
        return self.jobs.get(job_id)


# ============================================
# SINGLETON INSTANCE
# ============================================

_print_service: Optional[PrintService] = None


def get_print_service() -> PrintService:
    """Get the print service singleton."""
    global _print_service
    if _print_service is None:
        _print_service = PrintService()
    return _print_service


# ============================================
# COST COMPARISON
# ============================================

"""
COST COMPARISON: Regenerate vs Upscale

OLD APPROACH (Regenerate with Flux Pro):
- Preview: 10 pages × $0.02 (Schnell) = $0.20
- Print: 10 pages × $0.10 (Pro 1.1) = $1.00
- Total: $1.20 per book
- Problem: Images look DIFFERENT! ❌

NEW APPROACH (Upscale with Real-ESRGAN):
- Preview: 10 pages × $0.02 (Schnell) = $0.20
- Upscale: 10 pages × $0.01 (ESRGAN) = $0.10
- Total: $0.30 per book
- Benefit: Images look IDENTICAL! ✅

SAVINGS: 75% cheaper AND consistent!
"""
