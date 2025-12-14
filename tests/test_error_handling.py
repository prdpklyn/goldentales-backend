# tests/test_error_handling.py
"""
Tests for error handling and resilience features.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.utils.exceptions import (
    GoldenTalesException,
    ExternalServiceException,
    RetryExhaustedException,
    CircuitBreakerOpenException,
    ValidationException,
    ResourceNotFoundException
)
from app.utils.retry import (
    retry_async,
    get_circuit_breaker,
    reset_circuit_breaker,
    CircuitState,
    is_transient_error
)


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_goldentales_exception(self):
        """Test base GoldenTalesException."""
        exc = GoldenTalesException(
            message="Test error",
            error_code="test_error",
            status_code=500,
            details={"key": "value"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "test_error"
        assert exc.status_code == 500
        assert exc.details == {"key": "value"}
        
        exc_dict = exc.to_dict()
        assert exc_dict["error"] == "test_error"
        assert exc_dict["message"] == "Test error"
        assert exc_dict["details"] == {"key": "value"}
    
    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException(
            message="Invalid field",
            field="email"
        )
        
        assert exc.status_code == 400
        assert exc.error_code == "validation_error"
        assert exc.details["field"] == "email"
    
    def test_resource_not_found_exception(self):
        """Test ResourceNotFoundException."""
        exc = ResourceNotFoundException(
            resource_type="Book",
            resource_id="abc123"
        )
        
        assert exc.status_code == 404
        assert exc.error_code == "resource_not_found"
        assert "Book not found: abc123" in exc.message
    
    def test_external_service_exception(self):
        """Test ExternalServiceException."""
        exc = ExternalServiceException(
            service_name="Fal.ai",
            message="Connection timeout",
            is_transient=True
        )
        
        assert exc.status_code == 503
        assert exc.error_code == "external_service_error"
        assert exc.details["service"] == "Fal.ai"
        assert exc.details["is_transient"] is True


class TestRetryLogic:
    """Test retry logic and exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful call on first attempt."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_async(
            mock_func,
            max_attempts=3
        )
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful call after transient failures."""
        mock_func = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),  # Attempt 1: fail
                Exception("Connection timeout"),  # Attempt 2: fail
                "success"  # Attempt 3: success
            ]
        )
        
        result = await retry_async(
            mock_func,
            max_attempts=3,
            initial_delay=0.1,  # Fast for testing
            circuit_breaker_name="test_service_success"
        )
        
        assert result == "success"
        assert mock_func.call_count == 3
        
        # Clean up
        reset_circuit_breaker("test_service_success")
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhaustion after max attempts."""
        mock_func = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        
        with pytest.raises(RetryExhaustedException) as exc_info:
            await retry_async(
                mock_func,
                max_attempts=3,
                initial_delay=0.1
            )
        
        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_non_transient_error(self):
        """Test that non-transient errors are not retried."""
        # Create an error with a status code
        error = Exception("Bad request")
        error.status_code = 400
        
        mock_func = AsyncMock(side_effect=error)
        
        with pytest.raises(Exception) as exc_info:
            await retry_async(
                mock_func,
                max_attempts=3,
                initial_delay=0.1
            )
        
        # Should fail immediately, not retry
        assert mock_func.call_count == 1
        assert "Bad request" in str(exc_info.value)


class TestCircuitBreaker:
    """Test circuit breaker pattern."""
    
    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker starts in closed state."""
        cb = get_circuit_breaker("test_cb_init")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_attempt() is True
        reset_circuit_breaker("test_cb_init")
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = get_circuit_breaker("test_cb_open")
        
        # Record failures up to threshold
        for i in range(5):
            cb.record_failure(Exception(f"Failure {i+1}"))
        
        # Circuit should be open
        assert cb.state == CircuitState.OPEN
        assert cb.can_attempt() is False
        
        reset_circuit_breaker("test_cb_open")
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after success."""
        cb = get_circuit_breaker("test_cb_recovery")
        
        # Record some failures
        cb.record_failure(Exception("Failure 1"))
        cb.record_failure(Exception("Failure 2"))
        assert cb.failure_count == 2
        
        # Record success - should reset
        cb.record_success()
        assert cb.failure_count == 0
        
        reset_circuit_breaker("test_cb_recovery")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_requests(self):
        """Test circuit breaker blocks requests when open."""
        # Force open the circuit breaker
        cb = get_circuit_breaker("test_cb_block")
        for i in range(5):
            cb.record_failure(Exception(f"Failure {i+1}"))
        
        mock_func = AsyncMock(return_value="success")
        
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await retry_async(
                mock_func,
                max_attempts=3,
                circuit_breaker_name="test_cb_block"
            )
        
        assert "temporarily unavailable" in str(exc_info.value)
        # Function should not be called when circuit is open
        assert mock_func.call_count == 0
        
        reset_circuit_breaker("test_cb_block")


class TestIsTransientError:
    """Test transient error detection."""
    
    def test_timeout_is_transient(self):
        """Test timeout error is detected as transient."""
        error = Exception("Connection timeout")
        assert is_transient_error(error) is True
    
    def test_rate_limit_is_transient(self):
        """Test rate limit error is detected as transient."""
        error = Exception("Rate limit exceeded")
        assert is_transient_error(error) is True
    
    def test_503_is_transient(self):
        """Test 503 error is detected as transient."""
        error = Exception("Service unavailable")
        error.status_code = 503
        assert is_transient_error(error) is True
    
    def test_400_is_not_transient(self):
        """Test 400 error is not transient."""
        error = Exception("Bad request")
        error.status_code = 400
        assert is_transient_error(error) is False
    
    def test_404_is_not_transient(self):
        """Test 404 error is not transient."""
        error = Exception("Not found")
        error.status_code = 404
        assert is_transient_error(error) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

