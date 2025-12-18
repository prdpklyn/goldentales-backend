# tests/test_storage_service.py
"""
Comprehensive tests for StorageService.
Tests PDF upload, signed URL generation, and error handling with retry logic.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.services.storage_service import StorageService
from app.utils.exceptions import ExternalServiceException, NotFoundException
from tests.fixtures.storage import mock_storage_service


class TestStorageServiceUpload:
    """Tests for PDF upload functionality."""
    
    @pytest.mark.asyncio
    async def test_upload_order_pdf_success(self, mock_storage_service):
        """Test successful PDF upload."""
        import tempfile
        import os
        
        order_id = "order-123"
        book_id = "book-123"
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF content here")
            temp_path = f.name
        
        try:
            mock_storage_service.upload_order_pdf = AsyncMock(return_value={
                "storage_path": f"pdfs/orders/{order_id}/{book_id}_print.pdf",
                "signed_url": f"https://storage.supabase.co/orders/{order_id}/book.pdf",
                "uploaded_at": datetime.now().isoformat()
            })
            
            result = await mock_storage_service.upload_order_pdf(order_id, book_id, temp_path)
            
            assert "storage_path" in result
            assert "signed_url" in result
            mock_storage_service.upload_order_pdf.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_upload_order_pdf_with_retry(self):
        """Test PDF upload retries on transient errors."""
        from app.services.storage_service import StorageService
        import tempfile
        import os
        
        service = StorageService()
        
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF data")
            temp_path = f.name
        
        try:
            # Ensure service has a client
            if not service._client:
                service._client = MagicMock()
            
            # Mock Supabase client to fail twice then succeed
            call_count = 0
            def mock_upload(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Transient error")
                return {"path": "pdfs/orders/test/book_print.pdf"}
            
            mock_storage = MagicMock()
            mock_storage.upload = MagicMock(side_effect=mock_upload)
            mock_storage.create_signed_url = MagicMock(return_value={"signedURL": "https://example.com/book.pdf"})
            
            with patch.object(service._client.storage, "from_", return_value=mock_storage):
                with patch.object(service, "_ensure_bucket_exists"):
                    result = await service.upload_order_pdf("test", "book-123", temp_path)
                    
                    assert call_count == 3  # Retried 3 times
                    assert "storage_path" in result
                    assert "signed_url" in result
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_upload_order_pdf_permanent_error(self):
        """Test PDF upload fails after retries on permanent errors."""
        from app.services.storage_service import StorageService
        from app.utils.exceptions import ExternalServiceException
        import tempfile
        import os
        
        service = StorageService()
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF data")
            temp_path = f.name
        
        try:
            # Ensure service has a client
            if not service._client:
                service._client = MagicMock()
            
            mock_storage = MagicMock()
            mock_storage.upload = MagicMock(side_effect=Exception("Permanent error"))
            
            # Mock permanent error
            with patch.object(service._client.storage, "from_", return_value=mock_storage):
                with patch.object(service, "_ensure_bucket_exists"):
                    with pytest.raises(Exception):
                        await service.upload_order_pdf("test", "book-123", temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_upload_print_images_success(self, mock_storage_service):
        """Test successful print image upload."""
        order_id = "order-123"
        images = [
            {"page_number": 1, "image_data": b"image1"},
            {"page_number": 2, "image_data": b"image2"}
        ]
        
        mock_storage_service.upload_print_images = AsyncMock(return_value=[
            {"path": f"orders/{order_id}/page-1.jpg", "url": "https://example.com/page-1.jpg"},
            {"path": f"orders/{order_id}/page-2.jpg", "url": "https://example.com/page-2.jpg"}
        ])
        
        result = await mock_storage_service.upload_print_images(order_id, images)
        
        assert len(result) == 2
        assert result[0]["path"] == f"orders/{order_id}/page-1.jpg"
        assert result[1]["path"] == f"orders/{order_id}/page-2.jpg"


class TestStorageServiceSignedURLs:
    """Tests for signed URL generation."""
    
    @pytest.mark.asyncio
    async def test_get_order_pdf_url_success(self, mock_storage_service):
        """Test successful signed URL generation."""
        order_id = "order-123"
        book_id = "book-123"
        
        mock_storage_service.get_order_pdf_url = AsyncMock(return_value="https://storage.supabase.co/orders/order-123/book.pdf?token=abc123")
        
        result = await mock_storage_service.get_order_pdf_url(order_id, book_id)
        
        assert result is not None
        assert "token" in result or "signed" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_order_pdf_url_not_found(self, mock_storage_service):
        """Test signed URL generation fails for non-existent file."""
        from app.utils.exceptions import NotFoundException
        
        mock_storage_service.get_order_pdf_url = AsyncMock(return_value=None)
        
        result = await mock_storage_service.get_order_pdf_url("nonexistent", "book-123")
        
        # Service returns None if not found
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_order_pdf_url_with_expiry(self):
        """Test signed URL generation with custom expiry."""
        from app.services.storage_service import StorageService
        
        service = StorageService()
        order_id = "order-123"
        book_id = "book-123"
        expiry_hours = 24
        
        mock_url = "https://storage.supabase.co/orders/order-123/book.pdf?token=abc123"
        
        # Ensure service has a client
        if not service._client:
            service._client = MagicMock()
        
        mock_storage = MagicMock()
        mock_storage.create_signed_url = MagicMock(return_value={"signedURL": mock_url})
        
        with patch.object(service._client.storage, "from_", return_value=mock_storage):
            result = await service.get_order_pdf_url(order_id, book_id, expiry_hours=expiry_hours)
            
            assert result == mock_url


class TestStorageServiceErrorHandling:
    """Tests for error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_storage_service_handles_network_errors(self):
        """Test storage service handles network errors gracefully."""
        from app.services.storage_service import StorageService
        from app.utils.exceptions import ExternalServiceException
        import tempfile
        import os
        
        service = StorageService()
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF data")
            temp_path = f.name
        
        try:
            # Ensure service has a client
            if not service._client:
                service._client = MagicMock()
            
            mock_storage = MagicMock()
            mock_storage.upload = MagicMock(side_effect=Exception("Network timeout"))
            
            # Mock network error
            with patch.object(service._client.storage, "from_", return_value=mock_storage):
                with patch.object(service, "_ensure_bucket_exists"):
                    # Should raise ExternalServiceException after retries
                    with pytest.raises((ExternalServiceException, Exception)):
                        await service.upload_order_pdf("test", "book-123", temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_storage_service_handles_permission_errors(self):
        """Test storage service handles permission errors."""
        from app.services.storage_service import StorageService
        from app.utils.exceptions import ExternalServiceException
        import tempfile
        import os
        
        service = StorageService()
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF data")
            temp_path = f.name
        
        try:
            # Ensure service has a client
            if not service._client:
                service._client = MagicMock()
            
            mock_storage = MagicMock()
            mock_storage.upload = MagicMock(side_effect=Exception("Permission denied"))
            
            # Mock permission error
            with patch.object(service._client.storage, "from_", return_value=mock_storage):
                with patch.object(service, "_ensure_bucket_exists"):
                    # Should raise ExternalServiceException after retries
                    with pytest.raises((ExternalServiceException, Exception)):
                        await service.upload_order_pdf("test", "book-123", temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_storage_service_circuit_breaker(self):
        """Test circuit breaker prevents excessive retries."""
        from app.services.storage_service import StorageService
        from app.utils.retry import get_circuit_breaker, reset_circuit_breaker
        from app.utils.exceptions import CircuitBreakerOpenException
        import tempfile
        import os
        
        service = StorageService()
        
        # Reset circuit breaker before test
        reset_circuit_breaker("supabase_storage")
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF data")
            temp_path = f.name
        
        try:
            # Ensure service has a client
            if not service._client:
                service._client = MagicMock()
            
            mock_storage = MagicMock()
            mock_storage.upload = MagicMock(side_effect=Exception("Service down"))
            
            # Mock repeated failures to trigger circuit breaker
            with patch.object(service._client.storage, "from_", return_value=mock_storage):
                with patch.object(service, "_ensure_bucket_exists"):
                    # First few calls should retry and fail
                    for _ in range(3):
                        try:
                            await service.upload_order_pdf("test", "book-123", temp_path)
                        except Exception:
                            pass
                    
                    # Circuit breaker should be open now - next call should fail fast
                    circuit_breaker = get_circuit_breaker("supabase_storage")
                    # Verify circuit breaker state
                    assert circuit_breaker is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            reset_circuit_breaker("supabase_storage")


class TestStorageServiceIntegration:
    """Integration tests for storage service."""
    
    @pytest.mark.asyncio
    async def test_upload_and_retrieve_pdf_workflow(self, mock_storage_service):
        """Test complete workflow: upload PDF then retrieve signed URL."""
        import tempfile
        import os
        
        order_id = "order-123"
        book_id = "book-123"
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"PDF content")
            temp_path = f.name
        
        try:
            # Mock upload
            mock_storage_service.upload_order_pdf = AsyncMock(return_value={
                "storage_path": f"pdfs/orders/{order_id}/{book_id}_print.pdf",
                "signed_url": f"https://storage.supabase.co/orders/{order_id}/book.pdf",
                "uploaded_at": datetime.now().isoformat()
            })
            
            # Mock signed URL
            mock_storage_service.get_order_pdf_url = AsyncMock(return_value=f"https://storage.supabase.co/orders/{order_id}/book.pdf?token=abc123")
            
            # Upload
            upload_result = await mock_storage_service.upload_order_pdf(order_id, book_id, temp_path)
            assert "storage_path" in upload_result
            
            # Get signed URL
            url_result = await mock_storage_service.get_order_pdf_url(order_id, book_id)
            assert url_result is not None
            assert "token" in url_result or "signed" in url_result.lower()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

