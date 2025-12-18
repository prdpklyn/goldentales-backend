# app/services/edge_function_client.py
"""
GoldenTales Edge Function Client
=================================
Base client for calling Supabase Edge Functions with retry logic and error handling.

This provides a reusable pattern for calling any Supabase Edge Function,
following the pattern established in PDFDataService.
"""

from typing import Optional, Dict, Any, TypeVar, Generic
import httpx
from pydantic import BaseModel

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException, ResourceNotFoundException

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class EdgeFunctionClient:
    """
    Base client for calling Supabase Edge Functions.
    
    Provides:
    - HTTP client with retry logic
    - Authentication headers
    - Error handling and classification
    - Typed response parsing
    
    Example:
        client = EdgeFunctionClient(
            function_name="create-story",
            api_key=settings.supabase_pdf_api_key
        )
        result = await client.call({"child_name": "Emma", "theme": "christmas"})
    """
    
    def __init__(
        self,
        function_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        circuit_breaker_name: Optional[str] = None
    ):
        """
        Initialize Edge Function client.
        
        Args:
            function_name: Name of the Edge Function (e.g., "create-story")
            base_url: Supabase base URL (defaults to settings)
            api_key: API key for authentication (defaults to settings)
            circuit_breaker_name: Name for circuit breaker (defaults to function_name)
        """
        self.function_name = function_name
        self.base_url = base_url or settings.supabase_url
        self.api_key = api_key or settings.supabase_pdf_api_key
        self.circuit_breaker_name = circuit_breaker_name or f"edge_function_{function_name}"
        
        if not self.base_url:
            logger.warning(f"Supabase URL not configured for Edge Function: {function_name}")
        if not self.api_key:
            logger.warning(f"API key not configured for Edge Function: {function_name}")
    
    @property
    def endpoint_url(self) -> str:
        """Get the full endpoint URL for this Edge Function."""
        if not self.base_url:
            raise ValueError("Supabase URL not configured")
        
        # Handle both formats: with or without /functions/v1
        base = self.base_url.rstrip('/')
        if '/functions/v1' not in base:
            return f"{base}/functions/v1/{self.function_name}"
        return f"{base}/{self.function_name}"
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=15.0
    )
    async def _make_request(
        self,
        payload: Dict[str, Any],
        method: str = "POST",
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Edge Function with retry logic.
        
        Args:
            payload: Request payload
            method: HTTP method (default: POST)
            auth_token: Optional JWT token to forward for RLS (Bearer token)
            
        Returns:
            Raw JSON response
            
        Raises:
            ResourceNotFoundException: If resource not found (404)
            ExternalServiceException: For other errors
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # Forward JWT token if provided (for RLS policies)
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}"
                
                if method.upper() == "POST":
                    response = await client.post(
                        self.endpoint_url,
                        headers=headers,
                        json=payload
                    )
                elif method.upper() == "GET":
                    response = await client.get(
                        self.endpoint_url,
                        headers=headers,
                        params=payload
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle specific HTTP errors
                if response.status_code == 404:
                    error_data = response.json() if response.content else {}
                    raise ResourceNotFoundException(
                        resource_type=error_data.get("resource_type", "resource"),
                        resource_id=error_data.get("resource_id", "unknown")
                    )
                
                if response.status_code == 401:
                    raise ExternalServiceException(
                        service_name=f"Edge Function: {self.function_name}",
                        message="Authentication failed - invalid API key",
                        is_transient=False
                    )
                
                if response.status_code >= 500:
                    raise ExternalServiceException(
                        service_name=f"Edge Function: {self.function_name}",
                        message=f"Server error: {response.status_code}",
                        is_transient=True
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException as e:
                raise ExternalServiceException(
                    service_name=f"Edge Function: {self.function_name}",
                    message=f"Request timed out: {str(e)}",
                    is_transient=True
                )
            except httpx.RequestError as e:
                raise ExternalServiceException(
                    service_name=f"Edge Function: {self.function_name}",
                    message=f"Request failed: {str(e)}",
                    is_transient=True
                )
    
    async def call(
        self,
        payload: Dict[str, Any],
        method: str = "POST",
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call the Edge Function with the given payload.
        
        Args:
            payload: Request payload
            method: HTTP method (default: POST)
            auth_token: Optional JWT token to forward for RLS (Bearer token)
            
        Returns:
            Response data from Edge Function
            
        Raises:
            ValueError: If client not configured
            ResourceNotFoundException: If resource not found
            ExternalServiceException: For other errors
        """
        if not self.base_url or not self.api_key:
            raise ValueError(
                f"Edge Function client not properly configured for {self.function_name}"
            )
        
        logger.info(f"Calling Edge Function: {self.function_name}")
        logger.debug(f"Payload: {payload}")
        
        response = await self._make_request(payload, method, auth_token)
        
        logger.info(f"Edge Function {self.function_name} returned successfully")
        return response
    
    async def call_typed(
        self,
        payload: Dict[str, Any],
        response_model: type[T],
        method: str = "POST",
        auth_token: Optional[str] = None
    ) -> T:
        """
        Call Edge Function and parse response into a Pydantic model.
        
        Args:
            payload: Request payload
            response_model: Pydantic model class for response
            method: HTTP method (default: POST)
            auth_token: Optional JWT token to forward for RLS (Bearer token)
            
        Returns:
            Parsed response as Pydantic model instance
            
        Raises:
            ValueError: If client not configured or response invalid
            ResourceNotFoundException: If resource not found
            ExternalServiceException: For other errors
        """
        response = await self.call(payload, method, auth_token)
        
        try:
            return response_model(**response)
        except Exception as e:
            logger.error(f"Failed to parse response from {self.function_name}: {e}")
            raise ValueError(f"Invalid response format: {e}")


class EdgeFunctionResponse(BaseModel):
    """Standard Edge Function response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None

