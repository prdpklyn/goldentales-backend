# app/config/ai_config.py
"""
GoldenTales AI Model Configuration
==================================
Manage AI model configurations with database persistence and caching.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List

from app.utils.logging import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""
    FAL = "fal"
    GEMINI = "gemini"
    OPENAI = "openai"
    REPLICATE = "replicate"
    ANTHROPIC = "anthropic"


class QualityTier(str, Enum):
    """Image/generation quality tiers."""
    PREVIEW = "preview"      # Fast, cheap - for initial preview
    STANDARD = "standard"    # Balanced - for user approval
    PRINT = "print"          # High quality - for final print


@dataclass
class AIModelConfig:
    """
    Configuration for an AI model.

    Attributes:
        name: Unique identifier for this config
        provider: AI provider (fal, gemini, etc.)
        model_id: Provider-specific model identifier
        quality_tier: Quality tier this config is for
        parameters: Model-specific parameters (temperature, etc.)
        cost_per_call: Estimated cost per API call
        avg_latency_ms: Average response time in milliseconds
        is_active: Whether this config is currently active
        version: Version number for tracking changes
    """
    name: str
    provider: AIProvider
    model_id: str
    quality_tier: QualityTier
    parameters: Dict[str, Any] = field(default_factory=dict)
    cost_per_call: float = 0.0
    avg_latency_ms: int = 0
    is_active: bool = True
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["provider"] = self.provider.value
        data["quality_tier"] = self.quality_tier.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIModelConfig":
        """Create from dictionary."""
        data = data.copy()
        data["provider"] = AIProvider(data["provider"])
        data["quality_tier"] = QualityTier(data["quality_tier"])
        return cls(**data)


# Default model configurations (fallback when database is unavailable)
DEFAULT_CONFIGS: Dict[str, AIModelConfig] = {
    "fal_preview": AIModelConfig(
        name="fal_preview",
        provider=AIProvider.FAL,
        model_id="fal-ai/flux/schnell",
        quality_tier=QualityTier.PREVIEW,
        parameters={
            "image_size": {"width": 800, "height": 600},
            "num_inference_steps": 4,
            "guidance_scale": 3.5,
        },
        cost_per_call=0.02,
        avg_latency_ms=2000,
    ),
    "fal_standard": AIModelConfig(
        name="fal_standard",
        provider=AIProvider.FAL,
        model_id="fal-ai/flux/dev",
        quality_tier=QualityTier.STANDARD,
        parameters={
            "image_size": {"width": 1024, "height": 768},
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        },
        cost_per_call=0.05,
        avg_latency_ms=5000,
    ),
    "fal_print": AIModelConfig(
        name="fal_print",
        provider=AIProvider.FAL,
        model_id="fal-ai/flux-pro/v1.1",
        quality_tier=QualityTier.PRINT,
        parameters={
            "image_size": {"width": 2400, "height": 1800},
            "num_inference_steps": 50,
            "guidance_scale": 3.5,
        },
        cost_per_call=0.10,
        avg_latency_ms=15000,
    ),
    "gemini_story": AIModelConfig(
        name="gemini_story",
        provider=AIProvider.GEMINI,
        model_id="gemini-1.5-flash",
        quality_tier=QualityTier.STANDARD,
        parameters={
            "temperature": 0.8,
            "max_output_tokens": 4096,
            "top_p": 0.95,
        },
        cost_per_call=0.01,
        avg_latency_ms=3000,
    ),
}


class AIConfigManager:
    """
    Manages AI model configurations with database persistence and caching.

    Features:
    - Database-backed configurations
    - In-memory caching with TTL
    - Fallback to default configs
    - Version tracking for updates
    """

    def __init__(
        self,
        database=None,
        cache_ttl: int = 300  # 5 minutes
    ):
        """
        Initialize the AI config manager.

        Args:
            database: Database service for persistence
            cache_ttl: Cache time-to-live in seconds
        """
        self.db = database
        self._cache: Dict[str, tuple] = {}  # {key: (config, expiry)}
        self._cache_ttl = cache_ttl

    def _get_cache_key(
        self,
        quality_tier: QualityTier,
        provider: Optional[AIProvider] = None
    ) -> str:
        """Generate cache key for a config lookup."""
        return f"ai_config:{quality_tier.value}:{provider.value if provider else 'default'}"

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid."""
        if key not in self._cache:
            return False
        _, expiry = self._cache[key]
        return datetime.now(timezone.utc).timestamp() < expiry

    def _set_cache(self, key: str, config: AIModelConfig):
        """Set a value in the cache."""
        expiry = datetime.now(timezone.utc).timestamp() + self._cache_ttl
        self._cache[key] = (config, expiry)

    def _get_cache(self, key: str) -> Optional[AIModelConfig]:
        """Get a value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache[key][0]
        return None

    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache entry or entire cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    async def get_model_config(
        self,
        quality_tier: QualityTier,
        provider: Optional[AIProvider] = None,
        use_cache: bool = True
    ) -> AIModelConfig:
        """
        Get active model config for a quality tier.

        Args:
            quality_tier: Quality tier (preview, standard, print)
            provider: Specific provider (optional)
            use_cache: Whether to use cached values

        Returns:
            Active AIModelConfig for the tier
        """
        cache_key = self._get_cache_key(quality_tier, provider)

        # Check cache first
        if use_cache:
            cached = self._get_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached

        # Try loading from database
        if self.db:
            try:
                config_data = await self._load_from_database(quality_tier, provider)
                if config_data:
                    config = AIModelConfig.from_dict(config_data)
                    self._set_cache(cache_key, config)
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from database: {e}")

        # Fallback to default configs
        config = self._get_default_config(quality_tier, provider)
        self._set_cache(cache_key, config)
        return config

    async def _load_from_database(
        self,
        quality_tier: QualityTier,
        provider: Optional[AIProvider]
    ) -> Optional[Dict[str, Any]]:
        """Load config from database."""
        if not self.db or not self.db.client:
            return None

        query = (
            self.db.client.table("ai_model_configs")
            .select("*")
            .eq("quality_tier", quality_tier.value)
            .eq("is_active", True)
        )

        if provider:
            query = query.eq("provider", provider.value)

        result = query.limit(1).execute()
        return result.data[0] if result.data else None

    def _get_default_config(
        self,
        quality_tier: QualityTier,
        provider: Optional[AIProvider] = None
    ) -> AIModelConfig:
        """Get default hardcoded config for a tier."""
        # Find matching default config
        for config in DEFAULT_CONFIGS.values():
            if config.quality_tier == quality_tier:
                if provider is None or config.provider == provider:
                    return config

        # Ultimate fallback
        logger.warning(f"No default config for {quality_tier}, using preview")
        return DEFAULT_CONFIGS["fal_preview"]

    async def get_all_configs(
        self,
        active_only: bool = True
    ) -> List[AIModelConfig]:
        """
        Get all model configurations.

        Args:
            active_only: Only return active configs

        Returns:
            List of AIModelConfig objects
        """
        if self.db and self.db.client:
            try:
                query = self.db.client.table("ai_model_configs").select("*")
                if active_only:
                    query = query.eq("is_active", True)
                result = query.execute()

                if result.data:
                    return [AIModelConfig.from_dict(d) for d in result.data]
            except Exception as e:
                logger.warning(f"Failed to load configs from database: {e}")

        # Return defaults
        return list(DEFAULT_CONFIGS.values())

    async def update_model_config(
        self,
        name: str,
        updates: Dict[str, Any]
    ) -> Optional[AIModelConfig]:
        """
        Update a model configuration.

        Args:
            name: Config name to update
            updates: Fields to update

        Returns:
            Updated AIModelConfig or None
        """
        if not self.db or not self.db.client:
            logger.warning("Database not available for config update")
            return None

        try:
            # Increment version
            updates["version"] = updates.get("version", 1) + 1
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = (
                self.db.client.table("ai_model_configs")
                .update(updates)
                .eq("name", name)
                .execute()
            )

            if result.data:
                config = AIModelConfig.from_dict(result.data[0])
                # Invalidate related cache entries
                self.invalidate_cache()
                logger.info(f"Updated AI config: {name}")
                return config

        except Exception as e:
            logger.error(f"Failed to update config {name}: {e}")

        return None

    async def create_model_config(
        self,
        config: AIModelConfig
    ) -> Optional[AIModelConfig]:
        """
        Create a new model configuration.

        Args:
            config: AIModelConfig to create

        Returns:
            Created AIModelConfig or None
        """
        if not self.db or not self.db.client:
            logger.warning("Database not available for config creation")
            return None

        try:
            data = config.to_dict()
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            data["updated_at"] = data["created_at"]

            result = (
                self.db.client.table("ai_model_configs")
                .insert(data)
                .execute()
            )

            if result.data:
                created = AIModelConfig.from_dict(result.data[0])
                self.invalidate_cache()
                logger.info(f"Created AI config: {config.name}")
                return created

        except Exception as e:
            logger.error(f"Failed to create config {config.name}: {e}")

        return None


# Singleton instance
_ai_config_manager: Optional[AIConfigManager] = None


def get_ai_config_manager(database=None) -> AIConfigManager:
    """Get the AI config manager singleton."""
    global _ai_config_manager
    if _ai_config_manager is None:
        _ai_config_manager = AIConfigManager(database=database)
    return _ai_config_manager
