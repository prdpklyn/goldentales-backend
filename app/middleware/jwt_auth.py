# app/middleware/jwt_auth.py
"""
GoldenTales JWT Authentication
================================
Validates JWT tokens from Supabase Auth for user-facing endpoints.

This is used for V2 APIs that require user authentication and RLS.
"""

from typing import Optional
try:
    import jwt
except ImportError:
    # Fallback if PyJWT not installed
    jwt = None
    import json
    import base64

from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class JWTUser:
    """Represents an authenticated user from JWT token."""
    
    def __init__(self, user_id: str, email: Optional[str] = None, raw_token: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.raw_token = raw_token  # Store for forwarding to Edge Functions
    
    def __repr__(self):
        return f"JWTUser(user_id={self.user_id}, email={self.email})"


def decode_supabase_jwt(token: str) -> Optional[dict]:
    """
    Decode and validate a Supabase JWT token.
    
    Note: In production, you should verify the signature using Supabase's JWT secret.
    For now, we decode without verification (development mode).
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        if jwt:
            # Decode without verification (for development)
            # In production, use: jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded
        else:
            # Fallback: Basic JWT decoding without PyJWT
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (base64url)
            payload_part = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_part) % 4
            if padding != 4:
                payload_part += '=' * padding
            
            payload_bytes = base64.urlsafe_b64decode(payload_part)
            decoded = json.loads(payload_bytes.decode('utf-8'))
            return decoded
    except Exception as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[JWTUser]:
    """
    FastAPI dependency to extract and validate JWT token from request.
    
    Returns None if no token is provided (for optional auth endpoints).
    Raises HTTPException if token is invalid.
    
    Usage:
        @router.post("/protected")
        async def protected_route(user: JWTUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = None
    
    if credentials:
        token = credentials.credentials
    elif auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    if not token:
        return None
    
    # Decode JWT token
    payload = decode_supabase_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract user_id from token
    # Supabase JWT typically has 'sub' as user_id
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    email = payload.get("email")
    
    return JWTUser(user_id=user_id, email=email, raw_token=token)


async def require_jwt_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> JWTUser:
    """
    FastAPI dependency that requires a valid JWT token.
    
    Raises HTTPException if token is missing or invalid.
    
    Usage:
        @router.post("/protected")
        async def protected_route(user: JWTUser = Depends(require_jwt_auth)):
            return {"user_id": user.user_id}
    """
    user = await get_current_user(request, credentials)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide JWT token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def extract_user_context_from_jwt(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract user_id and JWT token from request for use with Edge Functions.
    
    This is a helper function that can be used in route handlers
    to get user context without requiring the full JWTUser dependency.
    
    Returns:
        Tuple of (user_id, auth_token)
    """
    auth_header = request.headers.get("Authorization", "")
    token = None
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    if not token:
        return None, None
    
    # Decode to get user_id
    payload = decode_supabase_jwt(token)
    if not payload:
        return None, None
    
    user_id = payload.get("sub") or payload.get("user_id")
    return user_id, token

