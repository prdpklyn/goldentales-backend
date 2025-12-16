# app/services/storage_service.py
"""
GoldenTales Storage Service
===========================
PDF and asset storage using Supabase Storage.

Storage Structure:
├── pdfs/
│   └── orders/
│       └── {order_id}/
│           ├── {book_id}_print.pdf       # Print-ready PDF
│           └── metadata.json             # Generation metadata
├── images/
│   ├── preview/
│   │   └── {book_id}/
│   │       └── page_{n}.jpg
│   └── print/
│       └── {book_id}/
│           └── page_{n}_upscaled.jpg
└── covers/
    └── {book_id}_cover.jpg
"""

import json
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Handles PDF and image storage with Supabase Storage.

    Provides:
    - PDF upload and signed URL generation
    - Print image storage
    - Asset cleanup for cancelled orders
    """

    BUCKET_NAME = "goldentales-assets"
    PDF_FOLDER = "pdfs/orders"
    IMAGES_FOLDER = "images"

    def __init__(self):
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Supabase client."""
        if not settings.supabase_url:
            logger.warning("Supabase URL not configured - storage disabled")
            return

        # Prefer service_role key for backend operations (bypasses RLS)
        api_key = settings.supabase_service_role_key or settings.supabase_key
        
        if not api_key:
            logger.warning("Supabase API key not configured - storage disabled")
            return

        try:
            from supabase import create_client
            self._client = create_client(
                settings.supabase_url,
                api_key
            )
            key_type = "service_role" if settings.supabase_service_role_key else "publishable"
            logger.info(f"Storage service initialized with {key_type} key")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")

    @property
    def is_available(self) -> bool:
        """Check if storage service is available."""
        return self._client is not None

    def _ensure_bucket_exists(self):
        """Create storage bucket if it doesn't exist."""
        if not self._client:
            return

        try:
            self._client.storage.get_bucket(self.BUCKET_NAME)
        except Exception:
            try:
                self._client.storage.create_bucket(
                    self.BUCKET_NAME,
                    options={
                        "public": False,
                        "file_size_limit": 100 * 1024 * 1024,  # 100MB max
                        "allowed_mime_types": [
                            "application/pdf",
                            "image/jpeg",
                            "image/png",
                            "application/json"
                        ]
                    }
                )
                logger.info(f"Created storage bucket: {self.BUCKET_NAME}")
            except Exception as e:
                logger.warning(f"Could not create bucket (may already exist): {e}")

    async def upload_order_pdf(
        self,
        order_id: str,
        book_id: str,
        pdf_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Upload print-ready PDF for an order.

        Args:
            order_id: Order UUID
            book_id: Book/story UUID
            pdf_path: Local path to PDF file
            metadata: Optional metadata to store alongside PDF

        Returns:
            Dict with 'storage_path', 'signed_url', 'uploaded_at'
        """
        if not self._client:
            raise ValueError("Storage service not available")

        self._ensure_bucket_exists()

        storage_path = f"{self.PDF_FOLDER}/{order_id}/{book_id}_print.pdf"

        # Upload PDF
        with open(pdf_path, 'rb') as f:
            self._client.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "application/pdf"}
            )

        logger.info(f"Uploaded PDF to {storage_path}")

        # Upload metadata if provided
        if metadata:
            meta_path = f"{self.PDF_FOLDER}/{order_id}/metadata.json"
            metadata_bytes = json.dumps(metadata, indent=2).encode('utf-8')
            self._client.storage.from_(self.BUCKET_NAME).upload(
                path=meta_path,
                file=metadata_bytes,
                file_options={"content-type": "application/json"}
            )

        # Generate signed URL (valid for 7 days)
        signed_result = self._client.storage.from_(self.BUCKET_NAME).create_signed_url(
            path=storage_path,
            expires_in=7 * 24 * 60 * 60  # 7 days in seconds
        )

        return {
            "storage_path": storage_path,
            "signed_url": signed_result.get("signedURL"),
            "uploaded_at": datetime.utcnow().isoformat()
        }

    async def get_order_pdf_url(
        self,
        order_id: str,
        book_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """
        Get a fresh signed URL for an order's PDF.

        Args:
            order_id: Order UUID
            book_id: Book/story UUID
            expiry_hours: How long the URL should be valid

        Returns:
            Signed URL or None if not found
        """
        if not self._client:
            return None

        storage_path = f"{self.PDF_FOLDER}/{order_id}/{book_id}_print.pdf"

        try:
            result = self._client.storage.from_(self.BUCKET_NAME).create_signed_url(
                path=storage_path,
                expires_in=expiry_hours * 60 * 60
            )
            return result.get("signedURL")
        except Exception as e:
            logger.error(f"Failed to get PDF URL: {e}")
            return None

    async def upload_print_images(
        self,
        book_id: str,
        image_urls: List[str]
    ) -> List[Optional[str]]:
        """
        Upload upscaled print images to permanent storage.

        Args:
            book_id: Book/story UUID
            image_urls: List of URLs to download and store

        Returns:
            List of storage URLs (None for failed uploads)
        """
        if not self._client:
            raise ValueError("Storage service not available")

        self._ensure_bucket_exists()
        storage_urls = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, url in enumerate(image_urls):
                if not url:
                    storage_urls.append(None)
                    continue

                try:
                    # Download image
                    response = await client.get(url)
                    response.raise_for_status()
                    image_data = response.content

                    # Upload to storage
                    storage_path = f"{self.IMAGES_FOLDER}/print/{book_id}/page_{i+1}.jpg"
                    self._client.storage.from_(self.BUCKET_NAME).upload(
                        path=storage_path,
                        file=image_data,
                        file_options={"content-type": "image/jpeg"}
                    )

                    # Get public URL
                    public_url = self._client.storage.from_(self.BUCKET_NAME).get_public_url(
                        storage_path
                    )
                    storage_urls.append(public_url)

                    logger.debug(f"Uploaded print image: {storage_path}")

                except Exception as e:
                    logger.error(f"Failed to upload print image {i+1}: {e}")
                    storage_urls.append(None)

        return storage_urls

    async def delete_order_assets(self, order_id: str) -> bool:
        """
        Delete all assets for an order (for cancellations/refunds).

        Args:
            order_id: Order UUID

        Returns:
            True if successful
        """
        if not self._client:
            return False

        folder_path = f"{self.PDF_FOLDER}/{order_id}"

        try:
            # List all files in order folder
            files = self._client.storage.from_(self.BUCKET_NAME).list(folder_path)

            if files:
                paths = [f"{folder_path}/{f['name']}" for f in files]
                self._client.storage.from_(self.BUCKET_NAME).remove(paths)
                logger.info(f"Deleted {len(paths)} files for order {order_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete order assets: {e}")
            return False

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        if not self._client:
            return {"available": False}

        try:
            # This is a placeholder - Supabase doesn't have a direct storage stats API
            return {
                "available": True,
                "bucket": self.BUCKET_NAME,
                "status": "healthy"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
