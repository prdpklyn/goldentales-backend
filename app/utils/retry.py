# app/utils/retry.py
"""
GoldenTales Retry Logic & Circuit Breaker
==========================================
Handles retries with exponential backoff and circuit breaker pattern
for resilient external API calls.
"""

import asyncio
import time
from typing import TypeVar, Callable, Optional, Any, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.utils.logging import get_logger
from app.utils.exceptions import (
    ExternalServiceException,
    CircuitBreakerOpenException,
    RetryExhaustedException
)

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Too many failures, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout: int = 60          # Seconds before trying half-open
    

@dataclass
class CircuitBreaker:
    """Circuit breaker for a service."""
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    
    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker {self.name}: Success in half-open state "
                f"({self.success_count}/{self.config.success_threshold})"
            )
            
            if self.success_count >= self.config.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    f"Circuit breaker {self.name}: Recovered, resetting failure count"
                )
            self.failure_count = 0
    
    def record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed while testing, reopen
            logger.warning(
                f"Circuit breaker {self.name}: Failed in half-open state, reopening"
            )
            self._open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.warning(
                f"Circuit breaker {self.name}: Failure {self.failure_count}/"
                f"{self.config.failure_threshold} - {str(error)}"
            )
            
            if self.failure_count >= self.config.failure_threshold:
                self._open()
    
    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.opened_at:
                elapsed = (datetime.now() - self.opened_at).total_seconds()
                if elapsed >= self.config.timeout:
                    self._half_open()
                    return True
            return False
        
        # HALF_OPEN: allow one attempt
        return True
    
    def _open(self) -> None:
        """Open the circuit breaker."""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.now()
        self.success_count = 0
        logger.error(
            f"Circuit breaker {self.name}: OPENED after {self.failure_count} failures. "
            f"Will retry in {self.config.timeout}s"
        )
    
    def _half_open(self) -> None:
        """Move to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(f"Circuit breaker {self.name}: HALF-OPEN, testing service")
    
    def _close(self) -> None:
        """Close the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        logger.info(f"Circuit breaker {self.name}: CLOSED, service recovered")


# Global circuit breakers registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            config=config or CircuitBreakerConfig()
        )
    return _circuit_breakers[name]


def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient (should retry).
    
    Transient errors:
    - Network timeouts
    - 429 (rate limit)
    - 500, 502, 503, 504 (server errors)
    - Connection errors
    
    Non-transient errors:
    - 400 (bad request)
    - 401 (unauthorized)
    - 404 (not found)
    - Validation errors
    """
    # Check if it's an HTTP error with status code
    if hasattr(error, 'status_code'):
        code = error.status_code
        # Retry on server errors and rate limits
        return code in [429, 500, 502, 503, 504]
    
    # Check error message for common transient patterns
    error_msg = str(error).lower()
    transient_patterns = [
        'timeout',
        'connection',
        'temporary',
        'unavailable',
        'rate limit',
        'too many requests'
    ]
    
    return any(pattern in error_msg for pattern in transient_patterns)


async def retry_async(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    circuit_breaker_name: Optional[str] = None,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays
        circuit_breaker_name: Name of circuit breaker to use
        
    Returns:
        Result of the function call
        
    Raises:
        RetryExhaustedException: If all retries fail
        CircuitBreakerOpenException: If circuit breaker is open
    """
    # Check circuit breaker
    circuit_breaker = None
    if circuit_breaker_name:
        circuit_breaker = get_circuit_breaker(circuit_breaker_name)
        if not circuit_breaker.can_attempt():
            retry_after = circuit_breaker.config.timeout
            if circuit_breaker.opened_at:
                elapsed = (datetime.now() - circuit_breaker.opened_at).total_seconds()
                retry_after = max(1, int(circuit_breaker.config.timeout - elapsed))
            
            raise CircuitBreakerOpenException(
                service_name=circuit_breaker_name,
                retry_after=retry_after
            )
    
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(
                f"Attempt {attempt}/{max_attempts} for {func.__name__}"
            )
            
            result = await func(*args, **kwargs)
            
            # Record success in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_success()
            
            if attempt > 1:
                logger.info(
                    f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                )
            
            return result
            
        except Exception as e:
            last_error = e
            
            # Record failure in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_failure(e)
            
            # Check if error is transient
            if not is_transient_error(e):
                logger.warning(
                    f"{func.__name__} failed with non-transient error: {e}"
                )
                raise
            
            # Don't retry if this was the last attempt
            if attempt >= max_attempts:
                logger.error(
                    f"{func.__name__} failed after {max_attempts} attempts: {e}"
                )
                break
            
            # Calculate delay with exponential backoff
            delay = min(
                initial_delay * (exponential_base ** (attempt - 1)),
                max_delay
            )
            
            # Add jitter to prevent thundering herd
            if jitter:
                import random
                delay = delay * (0.5 + random.random())
            
            logger.warning(
                f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            await asyncio.sleep(delay)
    
    # All retries exhausted
    raise RetryExhaustedException(
        operation=func.__name__,
        attempts=max_attempts,
        last_error=str(last_error) if last_error else None
    )


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    circuit_breaker_name: Optional[str] = None
):
    """
    Decorator to add retry logic to async functions.
    
    Usage:
        @with_retry(max_attempts=3, circuit_breaker_name="fal_ai")
        async def call_fal_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                circuit_breaker_name=circuit_breaker_name,
                **kwargs
            )
        return wrapper
    return decorator


def reset_circuit_breaker(name: str) -> None:
    """Manually reset a circuit breaker (for testing/admin)."""
    if name in _circuit_breakers:
        cb = _circuit_breakers[name]
        cb.state = CircuitState.CLOSED
        cb.failure_count = 0
        cb.success_count = 0
        cb.opened_at = None
        logger.info(f"Circuit breaker {name} manually reset")


def get_circuit_breaker_status() -> dict[str, dict[str, Any]]:
    """Get status of all circuit breakers."""
    return {
        name: {
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "success_count": cb.success_count,
            "opened_at": cb.opened_at.isoformat() if cb.opened_at else None,
        }
        for name, cb in _circuit_breakers.items()
    }

