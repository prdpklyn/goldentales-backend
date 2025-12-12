# app/config.py
"""
DreamWeaver Configuration
=========================
Centralized configuration using pydantic-settings for validation.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from datetime import datetime, timedelta
from enum import Enum


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings with environment variable loading.
    
    All settings can be overridden via environment variables.
    """
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS - CRITICAL: Don't use ["*"] in production
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )
    
    # API Keys - Required
    fal_key: Optional[str] = Field(default=None, alias="FAL_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    
    # API Keys - Optional
    lulu_api_key: Optional[str] = Field(default=None, alias="LULU_API_KEY")
    printful_api_key: Optional[str] = Field(default=None, alias="PRINTFUL_API_KEY")
    stripe_secret_key: Optional[str] = Field(default=None, alias="STRIPE_SECRET_KEY")
    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")
    
    # Shopify
    shopify_store_url: Optional[str] = Field(default=None, alias="SHOPIFY_STORE_URL")
    shopify_access_token: Optional[str] = Field(default=None, alias="SHOPIFY_ACCESS_TOKEN")
    shopify_webhook_secret: Optional[str] = Field(default=None, alias="SHOPIFY_WEBHOOK_SECRET")
    
    # Rate Limiting
    rate_limit_requests: int = 10  # requests per window
    rate_limit_window: int = 60   # seconds
    
    # Pricing (USD)
    price_digital: float = 9.99
    price_softcover: float = 24.99
    price_hardcover: float = 34.99
    
    # Shipping Costs (USD)
    shipping_standard: float = 5.99
    shipping_express: float = 14.99
    
    # Gift Wrap
    gift_wrap_cost: float = 5.00
    
    # Generation Costs (internal tracking)
    cost_preview: float = 0.02
    cost_standard: float = 0.05
    cost_print: float = 0.10
    
    # Christmas Timeline
    christmas_year: int = 2024
    standard_shipping_days: int = 10
    express_shipping_days: int = 4
    
    # Frontend URL (for emails, etc.)
    frontend_url: str = "https://taleom.lovable.app"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def christmas_date(self) -> datetime:
        """Get Christmas date for current timeline."""
        return datetime(self.christmas_year, 12, 25)
    
    @property
    def standard_deadline(self) -> datetime:
        """Last day for standard shipping to arrive by Christmas."""
        return self.christmas_date - timedelta(days=self.standard_shipping_days)
    
    @property
    def express_deadline(self) -> datetime:
        """Last day for express shipping to arrive by Christmas."""
        return self.christmas_date - timedelta(days=self.express_shipping_days)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION
    
    def validate_required_keys(self) -> List[str]:
        """Validate that required API keys are set. Returns list of missing keys."""
        missing = []
        if not self.fal_key:
            missing.append("FAL_KEY")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        return missing


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure only one instance is created.
    """
    return Settings()


# Convenience exports
settings = get_settings()
