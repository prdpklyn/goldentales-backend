# app/routers/common/health.py
"""
GoldenTales Health Endpoints
============================
Version-agnostic health check and root endpoints with connectivity verification.
"""

import httpx
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# App version
APP_VERSION = "3.0.0"


async def check_edge_function_connectivity() -> Dict:
    """
    Check connectivity to Supabase Edge Functions.

    Returns:
        Dict with status and response time
    """
    if not settings.supabase_url or not settings.supabase_pdf_api_key:
        return {
            "status": "unconfigured",
            "available": False,
            "message": "Supabase URL or API key not configured"
        }

    try:
        start = datetime.now()
        # Try to call a health endpoint or simple Edge Function
        base_url = settings.supabase_url.rstrip('/')
        if '/functions/v1' not in base_url:
            health_url = f"{base_url}/functions/v1/"
        else:
            health_url = base_url

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                health_url,
                headers={"x-api-key": settings.supabase_pdf_api_key}
            )
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            return {
                "status": "healthy",
                "available": True,
                "response_time_ms": duration_ms,
                "status_code": response.status_code
            }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "available": False,
            "message": "Connection timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "message": str(e)
        }


async def check_fal_ai_connectivity() -> Dict:
    """
    Check connectivity to Fal.ai API.

    Returns:
        Dict with status and response time
    """
    if not settings.fal_key:
        return {
            "status": "unconfigured",
            "available": False,
            "message": "Fal.ai API key not configured"
        }

    try:
        start = datetime.now()
        # Simple health check to Fal.ai
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://queue.fal.run/",
                headers={"Authorization": f"Key {settings.fal_key}"}
            )
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            return {
                "status": "healthy",
                "available": True,
                "response_time_ms": duration_ms,
                "status_code": response.status_code
            }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "available": False,
            "message": "Connection timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "message": str(e)
        }


async def check_gemini_connectivity() -> Dict:
    """
    Check connectivity to Gemini API.

    Returns:
        Dict with status and response time
    """
    if not settings.gemini_api_key:
        return {
            "status": "unconfigured",
            "available": False,
            "message": "Gemini API key not configured"
        }

    try:
        start = datetime.now()
        # Simple connectivity test to Gemini API
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}"
            )
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            return {
                "status": "healthy",
                "available": True,
                "response_time_ms": duration_ms,
                "status_code": response.status_code
            }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "available": False,
            "message": "Connection timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "message": str(e)
        }


@router.get("/")
async def root():
    """Root endpoint / basic health check."""
    return {
        "service": "GoldenTales API",
        "version": APP_VERSION,
        "status": "healthy"
    }


@router.get("/api/health")
async def health_check() -> Dict:
    """
    Detailed health check endpoint with connectivity verification.

    Returns status of all dependencies, configuration, and actual connectivity.
    """
    # Configuration checks
    config_checks = {
        "fal_key_configured": bool(settings.fal_key),
        "gemini_key_configured": bool(settings.gemini_api_key),
        "supabase_configured": bool(settings.supabase_url and settings.supabase_pdf_api_key),
        "shopify_configured": bool(settings.shopify_webhook_secret),
    }

    # Connectivity checks (only run if configured)
    connectivity = {}
    
    if config_checks["supabase_configured"]:
        connectivity["edge_functions"] = await check_edge_function_connectivity()
    else:
        connectivity["edge_functions"] = {
            "status": "unconfigured",
            "available": False
        }
    
    if config_checks["fal_key_configured"]:
        connectivity["fal_ai"] = await check_fal_ai_connectivity()
    else:
        connectivity["fal_ai"] = {
            "status": "unconfigured",
            "available": False
        }
    
    if config_checks["gemini_key_configured"]:
        connectivity["gemini"] = await check_gemini_connectivity()
    else:
        connectivity["gemini"] = {
            "status": "unconfigured",
            "available": False
        }

    # Determine overall health status
    critical_services_available = all([
        connectivity.get("edge_functions", {}).get("available", False),
        connectivity.get("fal_ai", {}).get("available", False),
        connectivity.get("gemini", {}).get("available", False)
    ])

    critical_services_configured = all([
        config_checks["fal_key_configured"],
        config_checks["gemini_key_configured"],
        config_checks["supabase_configured"]
    ])

    if critical_services_available:
        overall_status = "healthy"
    elif critical_services_configured:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "version": APP_VERSION,
        "environment": settings.environment.value,
        "configuration": config_checks,
        "connectivity": connectivity,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/v1/health")
async def health_check_v1() -> Dict:
    """V1 API health check."""
    return await health_check()
