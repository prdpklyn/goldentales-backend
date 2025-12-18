# app/utils/security.py
"""
GoldenTales Security Utilities
==============================
Security functions for webhook verification, input sanitization, etc.
"""

import hmac
import hashlib
import base64
import re
from typing import Optional

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def verify_webhook_signature(
    body: bytes,
    signature: Optional[str],
    secret: Optional[str] = None
) -> bool:
    """
    Verify Shopify webhook HMAC-SHA256 signature.
    
    Args:
        body: Raw request body bytes
        signature: X-Shopify-Hmac-SHA256 header value
        secret: Webhook secret (defaults to settings)
        
    Returns:
        True if signature is valid, False otherwise
        
    Note:
        In production, this will NEVER return True if signature is missing.
        In development, it logs a warning but still requires verification
        if a signature is provided.
    """
    secret = secret or settings.shopify_webhook_secret
    
    if not secret:
        if settings.is_production:
            logger.error("Webhook secret not configured in production!")
            return False
        else:
            logger.warning(
                "Webhook secret not configured. "
                "This is only acceptable in development."
            )
            # In development without secret, only allow if no signature provided
            if signature:
                logger.error("Signature provided but no secret configured")
                return False
            return True
    
    if not signature:
        logger.warning("No signature provided for webhook")
        return False
    
    # Compute expected signature
    computed = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    
    computed_b64 = base64.b64encode(computed).decode('utf-8')
    
    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(computed_b64, signature)
    
    if not is_valid:
        logger.warning("Webhook signature verification failed")
    
    return is_valid


def sanitize_input(text: Optional[str], max_length: int = 500) -> str:
    """
    Sanitize user input for use in AI prompts.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text safe for AI prompts
    """
    if not text:
        return ""
    
    # Remove special characters that could affect prompts
    sanitized = re.sub(r'[<>\[\]{}|\\]', '', text)
    
    # Remove potential prompt injection patterns
    dangerous_patterns = [
        r'ignore\s+previous',
        r'disregard',
        r'forget\s+everything',
        r'new\s+instructions',
        r'system\s*:',
        r'assistant\s*:',
        r'user\s*:',
        r'\[INST\]',
        r'</s>',
        r'<\|',
        r'\|>',
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    # Limit length
    sanitized = sanitized[:max_length]
    
    # Remove multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


def validate_content_safety(text: str) -> tuple[bool, Optional[str]]:
    """
    Check text for inappropriate content.
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_safe, error_message)
    """
    if not text:
        return True, None
    
    # Blocked words for children's content
    blocked_words = [
        'kill', 'murder', 'death', 'blood', 'weapon', 'gun', 'knife',
        'sex', 'nude', 'naked', 'porn', 'drug', 'cocaine', 'hate', 'nazi',
        'violence', 'gore', 'horror', 'torture', 'abuse'
    ]
    
    text_lower = text.lower()
    
    for word in blocked_words:
        if word in text_lower:
            logger.warning(f"Blocked content detected: {word}")
            return False, "Content contains inappropriate language"
    
    return True, None


# Safety negative prompt for image generation
# Comprehensive negative prompts to prevent anatomical issues and ensure quality
SAFETY_NEGATIVE_PROMPT = (
    # Content safety
    "nsfw, nude, naked, violence, blood, gore, scary, horror, dark, "
    "disturbing, frightening, adult content, inappropriate, suggestive, "
    
    # ANATOMICAL - Hands (critical for preventing extra hands/fingers)
    "extra hands, multiple hands, extra fingers, too many fingers, missing fingers, "
    "fused fingers, mutated hands, malformed hands, bad hands, wrong hands, "
    "floating hands, disconnected hands, extra arms, multiple arms, "
    "six fingers, seven fingers, four fingers, "
    
    # ANATOMICAL - Head and Face
    "extra heads, two heads, multiple heads, split head, merged faces, "
    "disfigured face, deformed face, mutated face, ugly face, bad face, "
    "wrong facial proportions, asymmetrical face, cropped head, cut off head, "
    "floating head, disconnected head, neck too long, neck too short, "
    
    # ANATOMICAL - Body
    "extra limbs, missing limbs, fused limbs, bad anatomy, wrong anatomy, "
    "mutated body, disfigured body, malformed body, bad proportions, "
    "body out of frame, poorly drawn body, extra legs, missing legs, "
    "merged bodies, conjoined, duplicate body parts, "
    
    # ANATOMICAL - Pose and Composition
    "anatomically incorrect, impossible pose, twisted limbs, contorted body, "
    "unnatural pose, awkward pose, broken anatomy, "
    
    # Quality issues
    "blurry, low quality, lowres, bad quality, worst quality, jpeg artifacts, "
    "pixelated, grainy, noisy, watermark, text, signature, logo, "
    "poorly drawn, amateur, sketch, unfinished, draft, "
    
    # Style issues
    "realistic photo, photograph, photorealistic, 3d render, cgi, "
    "out of focus, motion blur, chromatic aberration"
)

# Anatomical correctness positive guidance (to be added to prompts)
ANATOMICAL_POSITIVE_GUIDANCE = (
    "anatomically correct, proper body proportions, correct number of limbs, "
    "two hands with five fingers each, natural pose, well-formed features, "
    "proper head placement, correct facial features, natural body position"
)
