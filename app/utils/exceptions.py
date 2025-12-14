# app/utils/exceptions.py
"""
GoldenTales Custom Exceptions
==============================
Custom exception classes for better error handling and standardized responses.
"""

from typing import Optional, Dict, Any
from fastapi import status


class GoldenTalesException(Exception):
    """Base exception for all GoldenTales errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        response = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response


class ValidationException(GoldenTalesException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            **kwargs
        )


class ResourceNotFoundException(GoldenTalesException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            error_code="resource_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class ExternalServiceException(GoldenTalesException):
    """Raised when an external service (Fal.ai, Gemini, etc.) fails."""
    
    def __init__(
        self,
        service_name: str,
        message: str,
        is_transient: bool = True,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["service"] = service_name
        details["is_transient"] = is_transient
        
        super().__init__(
            message=f"{service_name} error: {message}",
            error_code="external_service_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if is_transient else status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            **kwargs
        )


class RateLimitException(GoldenTalesException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, tier: str, limit: int, retry_after: int, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded for tier '{tier}'",
            error_code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "tier": tier,
                "limit": limit,
                "retry_after": retry_after
            },
            **kwargs
        )


class AuthenticationException(GoldenTalesException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code="authentication_error",
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class AuthorizationException(GoldenTalesException):
    """Raised when user is not authorized for an action."""
    
    def __init__(self, message: str = "Not authorized", **kwargs):
        super().__init__(
            message=message,
            error_code="authorization_error",
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs
        )


class ConfigurationException(GoldenTalesException):
    """Raised when there's a configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="configuration_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            **kwargs
        )


class CircuitBreakerOpenException(GoldenTalesException):
    """Raised when circuit breaker is open (too many failures)."""
    
    def __init__(self, service_name: str, retry_after: int = 60, **kwargs):
        super().__init__(
            message=f"Service '{service_name}' is temporarily unavailable",
            error_code="circuit_breaker_open",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "service": service_name,
                "retry_after": retry_after,
                "reason": "Too many recent failures"
            },
            **kwargs
        )


class RetryExhaustedException(GoldenTalesException):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(
        self,
        operation: str,
        attempts: int,
        last_error: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["operation"] = operation
        details["attempts"] = attempts
        if last_error:
            details["last_error"] = last_error
        
        super().__init__(
            message=f"Operation '{operation}' failed after {attempts} attempts",
            error_code="retry_exhausted",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            **kwargs
        )


class DatabaseException(GoldenTalesException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            **kwargs
        )


class StorageException(GoldenTalesException):
    """Raised when storage operation (S3, Supabase Storage) fails."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="storage_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            **kwargs
        )


class WebhookVerificationException(GoldenTalesException):
    """Raised when webhook signature verification fails."""
    
    def __init__(self, message: str = "Webhook signature verification failed", **kwargs):
        super().__init__(
            message=message,
            error_code="webhook_verification_failed",
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


# Error code mapping for quick lookup
ERROR_CODES = {
    "validation_error": ValidationException,
    "resource_not_found": ResourceNotFoundException,
    "external_service_error": ExternalServiceException,
    "rate_limit_exceeded": RateLimitException,
    "authentication_error": AuthenticationException,
    "authorization_error": AuthorizationException,
    "configuration_error": ConfigurationException,
    "circuit_breaker_open": CircuitBreakerOpenException,
    "retry_exhausted": RetryExhaustedException,
    "database_error": DatabaseException,
    "storage_error": StorageException,
    "webhook_verification_failed": WebhookVerificationException,
}

