# app/config/feature_flags.py
"""
GoldenTales Feature Flags System
================================
Manage feature flags with gradual rollout and targeting support.
"""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RolloutStrategy(str, Enum):
    """Feature flag rollout strategies."""
    ALL = "all"                  # Enable for all users
    PERCENTAGE = "percentage"    # Percentage-based rollout
    USER_LIST = "user_list"      # Specific user list
    CONDITION = "condition"      # Custom conditions


@dataclass
class FeatureFlag:
    """
    A feature flag with rollout configuration.

    Attributes:
        name: Unique identifier for the flag
        description: Human-readable description
        is_enabled: Master switch for the feature
        rollout_percentage: Percentage of users (0-100) for gradual rollout
        strategy: Rollout strategy
        conditions: Additional targeting conditions
        metadata: Extra data (experiment info, etc.)
        version: Version for tracking changes
    """
    name: str
    description: str = ""
    is_enabled: bool = False
    rollout_percentage: int = 0  # 0-100
    strategy: RolloutStrategy = RolloutStrategy.PERCENTAGE
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureFlag":
        """Create from dictionary."""
        data = data.copy()
        if "strategy" in data:
            data["strategy"] = RolloutStrategy(data["strategy"])
        return cls(**data)


# Default feature flags
DEFAULT_FLAGS: Dict[str, FeatureFlag] = {
    "use_flux_pro": FeatureFlag(
        name="use_flux_pro",
        description="Use Flux Pro 1.1 for print-quality images instead of upscaling",
        is_enabled=True,
        rollout_percentage=100,
        strategy=RolloutStrategy.ALL,
    ),
    "enable_ab_testing": FeatureFlag(
        name="enable_ab_testing",
        description="Enable A/B testing for story generation prompts",
        is_enabled=False,
        rollout_percentage=0,
        strategy=RolloutStrategy.PERCENTAGE,
    ),
    "new_character_system": FeatureFlag(
        name="new_character_system",
        description="Use enhanced character consistency system",
        is_enabled=False,
        rollout_percentage=10,
        strategy=RolloutStrategy.PERCENTAGE,
        metadata={"experiment_id": "char_v2", "variant": "enhanced"},
    ),
    "gemini_flash_2": FeatureFlag(
        name="gemini_flash_2",
        description="Use Gemini 2.0 Flash for story generation",
        is_enabled=False,
        rollout_percentage=0,
        strategy=RolloutStrategy.PERCENTAGE,
    ),
    "parallel_image_generation": FeatureFlag(
        name="parallel_image_generation",
        description="Generate multiple images in parallel",
        is_enabled=True,
        rollout_percentage=100,
        strategy=RolloutStrategy.ALL,
    ),
    "pdf_compression": FeatureFlag(
        name="pdf_compression",
        description="Apply compression to generated PDFs",
        is_enabled=True,
        rollout_percentage=100,
        strategy=RolloutStrategy.ALL,
    ),
    "digital_delivery": FeatureFlag(
        name="digital_delivery",
        description="Enable digital-only delivery option",
        is_enabled=True,
        rollout_percentage=100,
        strategy=RolloutStrategy.ALL,
    ),
    "gift_wrapping": FeatureFlag(
        name="gift_wrapping",
        description="Enable gift wrapping option at checkout",
        is_enabled=True,
        rollout_percentage=100,
        strategy=RolloutStrategy.ALL,
    ),
}


class FeatureFlagManager:
    """
    Manages feature flags with gradual rollout support.

    Features:
    - Database-backed flags
    - Percentage-based rollout using consistent hashing
    - User targeting with conditions
    - In-memory caching
    """

    def __init__(
        self,
        database=None,
        cache_ttl: int = 60  # 1 minute (shorter for flags)
    ):
        """
        Initialize the feature flag manager.

        Args:
            database: Database service for persistence
            cache_ttl: Cache time-to-live in seconds
        """
        self.db = database
        self._cache: Dict[str, tuple] = {}  # {name: (flag, expiry)}
        self._cache_ttl = cache_ttl

    def _is_cache_valid(self, name: str) -> bool:
        """Check if cached flag is still valid."""
        if name not in self._cache:
            return False
        _, expiry = self._cache[name]
        return datetime.now(timezone.utc).timestamp() < expiry

    def _set_cache(self, name: str, flag: FeatureFlag):
        """Set a flag in the cache."""
        expiry = datetime.now(timezone.utc).timestamp() + self._cache_ttl
        self._cache[name] = (flag, expiry)

    def _get_cache(self, name: str) -> Optional[FeatureFlag]:
        """Get a flag from cache if valid."""
        if self._is_cache_valid(name):
            return self._cache[name][0]
        return None

    def invalidate_cache(self, name: Optional[str] = None):
        """Invalidate cache entry or entire cache."""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

    async def get_flag(
        self,
        name: str,
        use_cache: bool = True
    ) -> Optional[FeatureFlag]:
        """
        Get a feature flag by name.

        Args:
            name: Flag name
            use_cache: Whether to use cached values

        Returns:
            FeatureFlag or None if not found
        """
        # Check cache first
        if use_cache:
            cached = self._get_cache(name)
            if cached:
                return cached

        # Try loading from database
        if self.db:
            try:
                flag_data = await self._load_from_database(name)
                if flag_data:
                    flag = FeatureFlag.from_dict(flag_data)
                    self._set_cache(name, flag)
                    return flag
            except Exception as e:
                logger.warning(f"Failed to load flag from database: {e}")

        # Fallback to default flags
        if name in DEFAULT_FLAGS:
            flag = DEFAULT_FLAGS[name]
            self._set_cache(name, flag)
            return flag

        return None

    async def _load_from_database(self, name: str) -> Optional[Dict[str, Any]]:
        """Load flag from database."""
        if not self.db or not self.db.client:
            return None

        result = (
            self.db.client.table("feature_flags")
            .select("*")
            .eq("name", name)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def is_enabled(
        self,
        flag: FeatureFlag,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for a user.

        Args:
            flag: FeatureFlag to check
            user_id: User identifier for percentage rollout
            context: Additional context for condition evaluation

        Returns:
            True if feature is enabled for this user
        """
        # Master switch check
        if not flag.is_enabled:
            return False

        # Strategy-based evaluation
        if flag.strategy == RolloutStrategy.ALL:
            return True

        if flag.strategy == RolloutStrategy.PERCENTAGE:
            if flag.rollout_percentage >= 100:
                return True
            if flag.rollout_percentage <= 0:
                return False
            if not user_id:
                # No user_id provided, use random bucket
                import random
                return random.randint(1, 100) <= flag.rollout_percentage
            # Consistent hashing for percentage rollout
            return self._is_in_rollout(flag.name, user_id, flag.rollout_percentage)

        if flag.strategy == RolloutStrategy.USER_LIST:
            user_list = flag.conditions.get("users", [])
            return user_id in user_list if user_id else False

        if flag.strategy == RolloutStrategy.CONDITION:
            return self._evaluate_conditions(flag.conditions, context or {})

        return False

    def _is_in_rollout(
        self,
        flag_name: str,
        user_id: str,
        percentage: int
    ) -> bool:
        """
        Determine if user is in rollout using consistent hashing.

        This ensures the same user always gets the same result for a flag.
        """
        # Create a stable hash from flag name + user id
        hash_input = f"{flag_name}:{user_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        # Map to 0-100 range
        bucket = hash_value % 100

        return bucket < percentage

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate flag conditions against context.

        Supports:
        - equals: {"field": "value"}
        - in: {"field": ["value1", "value2"]}
        - gte/lte: {"field": {"gte": 10}}
        """
        for key, expected in conditions.items():
            actual = context.get(key)

            if actual is None:
                return False

            if isinstance(expected, dict):
                # Range conditions
                if "gte" in expected and actual < expected["gte"]:
                    return False
                if "lte" in expected and actual > expected["lte"]:
                    return False
                if "gt" in expected and actual <= expected["gt"]:
                    return False
                if "lt" in expected and actual >= expected["lt"]:
                    return False
            elif isinstance(expected, list):
                # In list
                if actual not in expected:
                    return False
            else:
                # Exact match
                if actual != expected:
                    return False

        return True

    async def is_feature_enabled(
        self,
        name: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        default: bool = False
    ) -> bool:
        """
        Check if a named feature is enabled.

        Convenience method combining get_flag and is_enabled.

        Args:
            name: Flag name
            user_id: User identifier
            context: Additional context
            default: Default value if flag not found

        Returns:
            True if feature is enabled
        """
        flag = await self.get_flag(name)
        if flag is None:
            return default
        return self.is_enabled(flag, user_id, context)

    async def get_all_flags(self) -> List[FeatureFlag]:
        """Get all feature flags."""
        if self.db and self.db.client:
            try:
                result = self.db.client.table("feature_flags").select("*").execute()
                if result.data:
                    return [FeatureFlag.from_dict(d) for d in result.data]
            except Exception as e:
                logger.warning(f"Failed to load flags from database: {e}")

        return list(DEFAULT_FLAGS.values())

    async def get_enabled_flags(
        self,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Get all flags with their enabled state for a user.

        Useful for sending flag states to frontend.

        Args:
            user_id: User identifier
            context: Additional context

        Returns:
            Dict mapping flag name to enabled state
        """
        flags = await self.get_all_flags()
        return {
            flag.name: self.is_enabled(flag, user_id, context)
            for flag in flags
        }

    async def create_flag(self, flag: FeatureFlag) -> Optional[FeatureFlag]:
        """Create a new feature flag."""
        if not self.db or not self.db.client:
            logger.warning("Database not available for flag creation")
            return None

        try:
            data = flag.to_dict()
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            data["updated_at"] = data["created_at"]

            result = (
                self.db.client.table("feature_flags")
                .insert(data)
                .execute()
            )

            if result.data:
                created = FeatureFlag.from_dict(result.data[0])
                self.invalidate_cache(flag.name)
                logger.info(f"Created feature flag: {flag.name}")
                return created

        except Exception as e:
            logger.error(f"Failed to create flag {flag.name}: {e}")

        return None

    async def update_flag(
        self,
        name: str,
        updates: Dict[str, Any]
    ) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        if not self.db or not self.db.client:
            logger.warning("Database not available for flag update")
            return None

        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            updates["version"] = updates.get("version", 1) + 1

            result = (
                self.db.client.table("feature_flags")
                .update(updates)
                .eq("name", name)
                .execute()
            )

            if result.data:
                updated = FeatureFlag.from_dict(result.data[0])
                self.invalidate_cache(name)
                logger.info(f"Updated feature flag: {name}")
                return updated

        except Exception as e:
            logger.error(f"Failed to update flag {name}: {e}")

        return None

    async def set_rollout_percentage(
        self,
        name: str,
        percentage: int
    ) -> Optional[FeatureFlag]:
        """
        Set the rollout percentage for a flag.

        Convenience method for gradual rollouts.

        Args:
            name: Flag name
            percentage: New percentage (0-100)

        Returns:
            Updated FeatureFlag or None
        """
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")

        return await self.update_flag(name, {"rollout_percentage": percentage})

    async def enable_flag(self, name: str) -> Optional[FeatureFlag]:
        """Enable a feature flag (set is_enabled=True)."""
        return await self.update_flag(name, {"is_enabled": True})

    async def disable_flag(self, name: str) -> Optional[FeatureFlag]:
        """Disable a feature flag (set is_enabled=False)."""
        return await self.update_flag(name, {"is_enabled": False})


# Singleton instance
_flag_manager: Optional[FeatureFlagManager] = None


def get_flag_manager(database=None) -> FeatureFlagManager:
    """Get the feature flag manager singleton."""
    global _flag_manager
    if _flag_manager is None:
        _flag_manager = FeatureFlagManager(database=database)
    return _flag_manager
