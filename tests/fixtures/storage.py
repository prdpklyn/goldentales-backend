# tests/fixtures/storage.py
"""
Mock fixtures for Storage Service.
"""

import pytest
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock


class MockStorageService:
    """Mock StorageService for testing."""
    
    def __init__(self):
        self.uploaded_files = {}
        self.signed_urls = {}
    
    async def upload_order_pdf(
        self,
        order_id: str,
        book_id: str,
        pdf_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Mock PDF upload."""
        storage_path = f"pdfs/orders/{order_id}/{book_id}_print.pdf"
        signed_url = f"https://mock-storage.com/{storage_path}?signed=true"
        
        self.uploaded_files[storage_path] = {
            "order_id": order_id,
            "book_id": book_id,
            "local_path": pdf_path,
            "metadata": metadata
        }
        
        self.signed_urls[storage_path] = signed_url
        
        return {
            "storage_path": storage_path,
            "signed_url": signed_url,
            "uploaded_at": "2024-01-01T00:00:00"
        }
    
    async def get_order_pdf_url(
        self,
        order_id: str,
        book_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """Mock get PDF URL."""
        storage_path = f"pdfs/orders/{order_id}/{book_id}_print.pdf"
        return self.signed_urls.get(storage_path)
    
    async def upload_print_images(
        self,
        book_id: str,
        image_urls: List[str]
    ) -> List[Optional[str]]:
        """Mock print images upload."""
        storage_urls = []
        
        for i, url in enumerate(image_urls):
            if url:
                storage_path = f"images/print/{book_id}/page_{i+1}.jpg"
                storage_url = f"https://mock-storage.com/{storage_path}"
                self.uploaded_files[storage_path] = {"original_url": url}
                storage_urls.append(storage_url)
            else:
                storage_urls.append(None)
        
        return storage_urls
    
    async def delete_order_assets(self, order_id: str) -> bool:
        """Mock delete order assets."""
        deleted = []
        for path in list(self.uploaded_files.keys()):
            if order_id in path:
                del self.uploaded_files[path]
                if path in self.signed_urls:
                    del self.signed_urls[path]
                deleted.append(path)
        
        return len(deleted) > 0


class MockPrintService:
    """Mock PrintService for testing."""
    
    def __init__(self):
        self.generated_pdfs = []
    
    async def generate_pdf(
        self,
        book_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """Mock PDF generation."""
        self.generated_pdfs.append({
            "book_id": book_data.get("book_id"),
            "output_path": output_path
        })
        
        return output_path
    
    async def create_print_job(
        self,
        story_id: str,
        format: str = "hardcover",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock print job creation."""
        return {
            "job_id": f"job-{story_id}",
            "story_id": story_id,
            "format": format,
            "status": "pending"
        }


@pytest.fixture
def mock_storage_service():
    """Fixture providing a mock StorageService."""
    return MockStorageService()


@pytest.fixture
def mock_print_service():
    """Fixture providing a mock PrintService."""
    return MockPrintService()

