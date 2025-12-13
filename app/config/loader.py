# app/config/loader.py
"""
GoldenTales Configuration Loader
================================
Central configuration loader that coordinates all config managers.
"""

from typing import Optional, Dict, Any

from app.config.ai_config import AIConfigManager, AIModelConfig, AIProvider, QualityTier
from app.config.prompt_config import PromptTemplateManager, PromptTemplate, PromptCategory
from app.config.feature_flags import FeatureFlagManager, FeatureFlag
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    Central configuration loader and coordinator.

    Provides a unified interface to:
    - AI model configurations
    - Prompt templates
    - Feature flags

    Example usage:
        config = get_config_loader()

        # Get AI config for preview quality
        model = await config.get_ai_model(QualityTier.PREVIEW)

        # Render a prompt
        prompt = await config.get_prompt("story_generation", {
            "child_name": "Emma",
            "child_age": 6,
            ...
        })

        # Check if feature is enabled
        if await config.is_feature_enabled("new_character_system", user_id="123"):
            # Use new system
            pass
    """

    def __init__(self, database=None):
        """
        Initialize the config loader.

        Args:
            database: Database service for persistence
        """
        self.db = database
        self._ai_config = AIConfigManager(database=database)
        self._prompts = PromptTemplateManager(database=database)
        self._flags = FeatureFlagManager(database=database)
        self._initialized = False

    async def initialize(self):
        """
        Initialize configuration from database.

        Call this at application startup to pre-load configs.
        """
        if self._initialized:
            return

        try:
            # Pre-load common configs to cache
            for tier in QualityTier:
                await self._ai_config.get_model_config(tier)

            # Pre-load common templates
            for name in ["story_generation", "character_bible", "image_prompt"]:
                try:
                    await self._prompts.get_template(name)
                except ValueError:
                    pass  # Template not found

            # Pre-load all flags
            await self._flags.get_all_flags()

            self._initialized = True
            logger.info("Configuration loader initialized")

        except Exception as e:
            logger.warning(f"Config initialization partially failed: {e}")

    def invalidate_all_caches(self):
        """Invalidate all configuration caches."""
        self._ai_config.invalidate_cache()
        self._prompts.invalidate_cache()
        self._flags.invalidate_cache()
        logger.info("All configuration caches invalidated")

    # ==========================================
    # AI Model Configuration Methods
    # ==========================================

    async def get_ai_model(
        self,
        quality_tier: QualityTier,
        provider: Optional[AIProvider] = None
    ) -> AIModelConfig:
        """
        Get AI model configuration for a quality tier.

        Args:
            quality_tier: Quality tier (preview, standard, print)
            provider: Specific provider (optional)

        Returns:
            AIModelConfig for the tier
        """
        return await self._ai_config.get_model_config(quality_tier, provider)

    async def get_image_model(self, quality: str = "preview") -> AIModelConfig:
        """
        Get image generation model config.

        Convenience method for common use case.

        Args:
            quality: Quality level (preview, standard, print)

        Returns:
            AIModelConfig for image generation
        """
        tier = QualityTier(quality)
        return await self._ai_config.get_model_config(tier, AIProvider.FAL)

    async def get_story_model(self) -> AIModelConfig:
        """
        Get story generation model config.

        Returns:
            AIModelConfig for story generation (typically Gemini)
        """
        return await self._ai_config.get_model_config(
            QualityTier.STANDARD,
            AIProvider.GEMINI
        )

    # ==========================================
    # Prompt Template Methods
    # ==========================================

    async def get_prompt(
        self,
        name: str,
        variables: Dict[str, Any],
        version: Optional[int] = None
    ) -> str:
        """
        Get and render a prompt template.

        Args:
            name: Template name
            variables: Variable values to substitute
            version: Specific version (optional)

        Returns:
            Rendered prompt string
        """
        return await self._prompts.get_prompt(name, variables, version)

    async def get_story_prompt(
        self,
        child_name: str,
        child_age: int,
        character_description: str,
        theme: str,
        art_style: str,
        page_count: int = 10,
        **extra_vars
    ) -> str:
        """
        Get rendered story generation prompt.

        Convenience method with typed parameters.

        Args:
            child_name: Child's name
            child_age: Child's age
            character_description: Character bible description
            theme: Story theme
            art_style: Art style
            page_count: Number of pages
            **extra_vars: Additional template variables

        Returns:
            Rendered story prompt
        """
        variables = {
            "child_name": child_name,
            "child_age": child_age,
            "character_description": character_description,
            "theme": theme,
            "art_style": art_style,
            "page_count": page_count,
            **extra_vars
        }
        return await self._prompts.get_prompt("story_generation", variables)

    async def get_image_prompt(
        self,
        character_description: str,
        scene_description: str,
        art_style: str,
        mood: str = "happy"
    ) -> str:
        """
        Get rendered image generation prompt.

        Args:
            character_description: Character description
            scene_description: Scene description
            art_style: Art style
            mood: Scene mood

        Returns:
            Rendered image prompt
        """
        variables = {
            "character_description": character_description,
            "scene_description": scene_description,
            "art_style": art_style,
            "mood": mood
        }
        return await self._prompts.get_prompt("image_prompt", variables)

    async def get_template(
        self,
        name: str,
        version: Optional[int] = None
    ) -> PromptTemplate:
        """
        Get a prompt template without rendering.

        Args:
            name: Template name
            version: Specific version (optional)

        Returns:
            PromptTemplate object
        """
        return await self._prompts.get_template(name, version)

    # ==========================================
    # Feature Flag Methods
    # ==========================================

    async def is_feature_enabled(
        self,
        name: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        default: bool = False
    ) -> bool:
        """
        Check if a feature is enabled.

        Args:
            name: Feature flag name
            user_id: User identifier for rollout
            context: Additional context
            default: Default if flag not found

        Returns:
            True if feature is enabled
        """
        return await self._flags.is_feature_enabled(name, user_id, context, default)

    async def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """
        Get a feature flag.

        Args:
            name: Flag name

        Returns:
            FeatureFlag or None
        """
        return await self._flags.get_flag(name)

    async def get_enabled_flags(
        self,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Get all flags with their enabled state.

        Args:
            user_id: User identifier
            context: Additional context

        Returns:
            Dict mapping flag name to enabled state
        """
        return await self._flags.get_enabled_flags(user_id, context)

    # ==========================================
    # Admin/Management Methods
    # ==========================================

    async def update_ai_config(
        self,
        name: str,
        updates: Dict[str, Any]
    ) -> Optional[AIModelConfig]:
        """Update an AI model configuration."""
        return await self._ai_config.update_model_config(name, updates)

    async def update_prompt_template(
        self,
        name: str,
        updates: Dict[str, Any],
        create_new_version: bool = True
    ) -> Optional[PromptTemplate]:
        """Update a prompt template."""
        return await self._prompts.update_template(name, updates, create_new_version)

    async def update_feature_flag(
        self,
        name: str,
        updates: Dict[str, Any]
    ) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        return await self._flags.update_flag(name, updates)

    async def set_flag_rollout(
        self,
        name: str,
        percentage: int
    ) -> Optional[FeatureFlag]:
        """Set rollout percentage for a feature flag."""
        return await self._flags.set_rollout_percentage(name, percentage)

    # ==========================================
    # Bulk Export/Import
    # ==========================================

    async def export_all_configs(self) -> Dict[str, Any]:
        """
        Export all configurations.

        Returns:
            Dict with all configs (for backup/migration)
        """
        ai_configs = await self._ai_config.get_all_configs()
        templates = await self._prompts.get_all_templates()
        flags = await self._flags.get_all_flags()

        return {
            "ai_models": [c.to_dict() for c in ai_configs],
            "prompts": [t.to_dict() for t in templates],
            "feature_flags": [f.to_dict() for f in flags],
            "exported_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
        }

    async def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration.

        Useful for health checks and debugging.

        Returns:
            Summary of configs, templates, and flags
        """
        ai_configs = await self._ai_config.get_all_configs()
        templates = await self._prompts.get_all_templates()
        flags = await self._flags.get_all_flags()

        enabled_flags = [f.name for f in flags if f.is_enabled]

        return {
            "ai_models": {
                "count": len(ai_configs),
                "by_tier": {
                    tier.value: sum(1 for c in ai_configs if c.quality_tier == tier)
                    for tier in QualityTier
                }
            },
            "prompts": {
                "count": len(templates),
                "by_category": {
                    cat.value: sum(1 for t in templates if t.category == cat)
                    for cat in PromptCategory
                }
            },
            "feature_flags": {
                "total": len(flags),
                "enabled": len(enabled_flags),
                "enabled_names": enabled_flags
            },
            "cache_status": {
                "ai_config_entries": len(self._ai_config._cache),
                "prompt_entries": len(self._prompts._cache),
                "flag_entries": len(self._flags._cache)
            }
        }


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(database=None) -> ConfigLoader:
    """Get the configuration loader singleton."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(database=database)
    return _config_loader


async def initialize_config(database=None):
    """
    Initialize configuration at application startup.

    Call this in your application startup:
        @app.on_event("startup")
        async def startup():
            await initialize_config(database)
    """
    loader = get_config_loader(database)
    await loader.initialize()
    return loader
