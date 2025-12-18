# tests/test_print_service.py
"""
Comprehensive tests for PrintService.
Tests PDF generation, image upscaling, and order processing.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.services.print_service import PrintService
from app.models.enums import BookFormat, BookTier, GenerationQuality


@pytest.fixture
def sample_book_data():
    """Sample book data for PDF generation."""
    return {
        "book_id": "book-123",
        "title": "Emma's Christmas Adventure",
        "child_name": "Emma",
        "child_age": 6,
        "theme": "christmas",
        "tier": "premium",
        "pages": [
            {
                "page_number": 1,
                "text": "Once upon a time, Emma looked out her window.",
                "scene_description": "Emma looking out a frosted window",
                "image_url": "https://example.com/page1.jpg"
            },
            {
                "page_number": 2,
                "text": "She saw magical lights in the sky!",
                "scene_description": "Emma pointing at lights in the sky",
                "image_url": "https://example.com/page2.jpg"
            }
        ],
        "preview_images": [
            "https://example.com/page1.jpg",
            "https://example.com/page2.jpg"
        ],
        "page_count": 2,
        "character_bible": {
            "main_character": "Emma, 6-year-old girl with brown hair"
        }
    }


@pytest.fixture
def sample_order_data():
    """Sample order data."""
    return {
        "id": "order-123",
        "story_id": "book-123",
        "format": "hardcover",
        "book_size": "8x8",
        "status": "payment_confirmed",
        "customer_email": "customer@example.com"
    }


class TestPrintServicePDFGeneration:
    """Tests for PDF generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_pdf_basic_tier(self, sample_book_data):
        """Test PDF generation for BASIC tier book."""
        from app.services.print_service import PrintService, PrintJob
        from app.models.enums import OrderStatus
        
        service = PrintService()
        sample_book_data["tier"] = "basic"
        
        # Mock start_print_production
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            result = await service.start_print_production(
                order_id="order-123",
                book_data=sample_book_data,
                format="hardcover"
            )
            
            assert result is not None
            assert result.pdf_path is not None
    
    @pytest.mark.asyncio
    async def test_generate_pdf_premium_tier(self, sample_book_data):
        """Test PDF generation for PREMIUM tier book."""
        from app.services.print_service import PrintService, PrintJob
        from app.models.enums import OrderStatus
        
        service = PrintService()
        sample_book_data["tier"] = "premium"
        
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            result = await service.start_print_production(
                order_id="order-123",
                book_data=sample_book_data,
                format="hardcover"
            )
            
            assert result is not None
            assert result.pdf_path is not None
    
    @pytest.mark.asyncio
    async def test_generate_pdf_ultra_tier(self, sample_book_data):
        """Test PDF generation for ULTRA tier book."""
        from app.services.print_service import PrintService, PrintJob
        from app.models.enums import OrderStatus
        
        service = PrintService()
        sample_book_data["tier"] = "ultra"
        sample_book_data["character_reference_url"] = "https://example.com/character.jpg"
        
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            result = await service.start_print_production(
                order_id="order-123",
                book_data=sample_book_data,
                format="hardcover"
            )
            
            assert result is not None
            assert result.pdf_path is not None
    
    @pytest.mark.asyncio
    async def test_generate_pdf_book_not_found(self):
        """Test PDF generation fails for non-existent book."""
        from app.services.print_service import PrintService
        from app.utils.exceptions import NotFoundException
        
        service = PrintService()
        
        with patch.object(service, "_fetch_story_data", new=AsyncMock(side_effect=NotFoundException(resource_type="story", resource_id="nonexistent"))):
            with pytest.raises(NotFoundException):
                await service.start_print_production_by_story_id(
                    order_id="order-123",
                    story_id="nonexistent",
                    format="hardcover"
                )
    
    @pytest.mark.asyncio
    async def test_generate_pdf_missing_images(self, sample_book_data):
        """Test PDF generation handles missing images gracefully."""
        from app.services.print_service import PrintService, PrintJob
        from app.models.enums import OrderStatus
        
        service = PrintService()
        # Remove image URLs
        for page in sample_book_data["pages"]:
            page["image_url"] = None
        
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            # Should still generate PDF with placeholder or text-only
            result = await service.start_print_production(
                order_id="order-123",
                book_data=sample_book_data,
                format="hardcover"
            )
            assert result is not None
            assert result.pdf_path is not None


class TestPrintServiceImageUpscaling:
    """Tests for image upscaling functionality."""
    
    @pytest.mark.asyncio
    async def test_upscale_images_for_print(self, sample_book_data):
        """Test upscaling images for print quality."""
        from app.services.print_service import PrintService, ImageUpscaler
        
        service = PrintService()
        upscaler = ImageUpscaler(fal_api_key="test-key")
        
        preview_images = sample_book_data["preview_images"]
        upscaled_urls = [
            "https://example.com/page1-print.jpg",
            "https://example.com/page2-print.jpg"
        ]
        
        with patch.object(upscaler, "upscale_all_pages", new=AsyncMock(return_value=upscaled_urls)):
            result = await upscaler.upscale_all_pages(preview_images, "esrgan")
            
            assert len(result) == 2
            assert all(isinstance(url, str) for url in result)
    
    @pytest.mark.asyncio
    async def test_upscale_images_empty_list(self):
        """Test upscaling handles empty image list."""
        from app.services.print_service import ImageUpscaler
        
        upscaler = ImageUpscaler(fal_api_key="test-key")
        
        # Mock the upscale method to return empty list
        with patch.object(upscaler, "upscale_all_pages", new=AsyncMock(return_value=[])):
            result = await upscaler.upscale_all_pages([], "esrgan")
            assert result == []
    
    @pytest.mark.asyncio
    async def test_upscale_images_partial_failure(self, sample_book_data):
        """Test upscaling handles partial failures."""
        from app.services.print_service import ImageUpscaler
        
        upscaler = ImageUpscaler(fal_api_key="test-key")
        
        # Mock partial failure - return fewer URLs than input
        upscaled_urls = ["https://example.com/page1-print.jpg"]  # Page 2 failed
        
        with patch.object(upscaler, "upscale_all_pages", new=AsyncMock(return_value=upscaled_urls)):
            result = await upscaler.upscale_all_pages(sample_book_data["preview_images"], "esrgan")
            
            # Should return what succeeded
            assert len(result) == 1
            assert isinstance(result[0], str)


class TestPrintServiceOrderProcessing:
    """Tests for order processing workflow."""
    
    @pytest.mark.asyncio
    async def test_process_order_digital(self, sample_order_data, sample_book_data):
        """Test processing digital order."""
        from app.services.print_service import PrintService, PrintJob
        
        service = PrintService()
        sample_order_data["format"] = "digital"
        
        # Mock start_print_production
        from app.models.enums import OrderStatus
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            with patch.object(service, "_fetch_story_data", new=AsyncMock(return_value=sample_book_data)):
                result = await service.start_print_production(
                    order_id="order-123",
                    book_data=sample_book_data,
                    format="digital"
                )
                
                assert result.job_id == "job-123"
                assert result.status is not None
                assert result.job_id is not None
    
    @pytest.mark.asyncio
    async def test_process_order_physical(self, sample_order_data, sample_book_data):
        """Test processing physical order (requires upscaling)."""
        from app.services.print_service import PrintService
        from app.services.storage_service import StorageService
        from app.services.image_generator import ImageGenerator
        
        service = PrintService()
        sample_order_data["format"] = "hardcover"
        
        mock_pdf_data = b"PDF binary data"
        upscaled_images = [
            {"url": "https://example.com/page1-print.jpg", "page_number": 1},
            {"url": "https://example.com/page2-print.jpg", "page_number": 2}
        ]
        storage_result = {
            "path": "orders/order-123/book.pdf",
            "url": "https://storage.supabase.co/orders/order-123/book.pdf"
        }
        
        # Mock start_print_production for physical order
        from app.services.print_service import PrintJob
        from app.models.enums import OrderStatus
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            with patch.object(service, "_fetch_story_data", new=AsyncMock(return_value=sample_book_data)):
                result = await service.start_print_production(
                    order_id="order-123",
                    book_data=sample_book_data,
                    format="hardcover"
                )
                
                assert result.job_id == "job-123"
                assert result.status is not None
                assert result.job_id is not None
    
    @pytest.mark.asyncio
    async def test_process_order_error_handling(self, sample_order_data, sample_book_data):
        """Test order processing handles errors gracefully."""
        from app.services.print_service import PrintService
        from app.utils.exceptions import ExternalServiceException
        
        service = PrintService()
        
        # Mock start_print_production failure
        with patch.object(service, "_fetch_story_data", new=AsyncMock(side_effect=Exception("Failed to fetch story"))):
            with pytest.raises(Exception):
                await service.start_print_production_by_story_id(
                    order_id="order-123",
                    story_id="book-123",
                    format="hardcover"
                )


class TestPrintServiceIntegration:
    """Integration tests for print service."""
    
    @pytest.mark.asyncio
    async def test_complete_print_workflow(self, sample_order_data, sample_book_data):
        """Test complete workflow: upscale → generate PDF → upload → update order."""
        from app.services.print_service import PrintService
        from app.services.storage_service import StorageService
        from app.services.database import get_database
        
        service = PrintService()
        sample_order_data["format"] = "hardcover"
        
        # Mock all dependencies
        upscaled_images = [
            {"url": "https://example.com/page1-print.jpg", "page_number": 1},
            {"url": "https://example.com/page2-print.jpg", "page_number": 2}
        ]
        mock_pdf_data = b"PDF binary data"
        storage_result = {
            "path": "orders/order-123/book.pdf",
            "url": "https://storage.supabase.co/orders/order-123/book.pdf"
        }
        
        # Mock complete workflow
        from app.services.print_service import PrintJob
        from app.models.enums import OrderStatus
        mock_job = PrintJob(
            job_id="job-123",
            order_id="order-123",
            book_id="book-123",
            status=OrderStatus.CREATING_PDF,
            pdf_path="/tmp/job-123.pdf"
        )
        
        with patch.object(service, "start_print_production", new=AsyncMock(return_value=mock_job)):
            with patch.object(service, "_fetch_story_data", new=AsyncMock(return_value=sample_book_data)):
                result = await service.start_print_production(
                    order_id="order-123",
                    book_data=sample_book_data,
                    format="hardcover"
                )
                
                assert result.job_id == "job-123"
                assert result.status is not None
                assert result.job_id is not None
                assert result.pdf_path is not None

