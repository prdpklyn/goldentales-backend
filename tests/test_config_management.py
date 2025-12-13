# tests/test_config_management.py
"""
GoldenTales Configuration Management Tests
==========================================
Tests for AI config, prompt templates, and feature flags.
"""

import pytest
import asyncio
from datetime import datetime

from app.config.ai_config import (
    AIConfigManager, AIModelConfig, AIProvider, QualityTier, DEFAULT_CONFIGS
)
from app.config.prompt_config import (
    PromptTemplateManager, PromptTemplate, PromptCategory, DEFAULT_TEMPLATES
)
from app.config.feature_flags import (
    FeatureFlagManager, FeatureFlag, RolloutStrategy, DEFAULT_FLAGS
)
from app.config.loader import ConfigLoader


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ============================================
# AI Config Manager Tests
# ============================================

class TestAIConfigManager:
    """Tests for AI model configuration manager."""

    @pytest.fixture
    def manager(self):
        """Create a config manager without database."""
        return AIConfigManager(database=None)

    def test_get_default_preview_config(self, manager):
        """Should return default preview config."""
        config = run_async(manager.get_model_config(QualityTier.PREVIEW))

        assert config is not None
        assert config.quality_tier == QualityTier.PREVIEW
        assert config.provider == AIProvider.FAL
        assert "schnell" in config.model_id

    def test_get_default_print_config(self, manager):
        """Should return default print config."""
        config = run_async(manager.get_model_config(QualityTier.PRINT))

        assert config is not None
        assert config.quality_tier == QualityTier.PRINT
        assert "flux-pro" in config.model_id

    def test_get_config_with_provider(self, manager):
        """Should filter by provider when specified."""
        config = run_async(manager.get_model_config(
            QualityTier.STANDARD,
            AIProvider.GEMINI
        ))

        assert config is not None
        assert config.provider == AIProvider.GEMINI

    def test_config_caching(self, manager):
        """Should cache configs after first load."""
        # First call
        config1 = run_async(manager.get_model_config(QualityTier.PREVIEW))

        # Cache key should exist
        cache_key = manager._get_cache_key(QualityTier.PREVIEW, None)
        assert manager._is_cache_valid(cache_key)

        # Second call should use cache
        config2 = run_async(manager.get_model_config(QualityTier.PREVIEW))

        assert config1.name == config2.name

    def test_cache_invalidation(self, manager):
        """Should invalidate cache correctly."""
        # Load config to populate cache
        run_async(manager.get_model_config(QualityTier.PREVIEW))

        cache_key = manager._get_cache_key(QualityTier.PREVIEW, None)
        assert manager._is_cache_valid(cache_key)

        # Invalidate
        manager.invalidate_cache()

        assert not manager._is_cache_valid(cache_key)

    def test_ai_model_config_serialization(self):
        """Should serialize and deserialize AIModelConfig."""
        config = AIModelConfig(
            name="test_config",
            provider=AIProvider.FAL,
            model_id="test-model",
            quality_tier=QualityTier.PREVIEW,
            parameters={"test": "value"},
            cost_per_call=0.05,
        )

        data = config.to_dict()
        restored = AIModelConfig.from_dict(data)

        assert restored.name == config.name
        assert restored.provider == config.provider
        assert restored.parameters == config.parameters


# ============================================
# Prompt Template Manager Tests
# ============================================

class TestPromptTemplateManager:
    """Tests for prompt template manager."""

    @pytest.fixture
    def manager(self):
        """Create a prompt manager without database."""
        return PromptTemplateManager(database=None)

    def test_get_default_story_template(self, manager):
        """Should return default story generation template."""
        template = run_async(manager.get_template("story_generation"))

        assert template is not None
        assert template.name == "story_generation"
        assert template.category == PromptCategory.STORY
        assert "child_name" in template.variables

    def test_render_template_basic(self, manager):
        """Should render template with variables."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.STORY,
            template="Hello {{ name }}, you are {{ age }} years old!",
            variables=["name", "age"]
        )

        rendered = manager.render(template, {"name": "Emma", "age": 6})

        assert "Hello Emma" in rendered
        assert "6 years old" in rendered

    def test_render_template_with_conditionals(self, manager):
        """Should handle conditional blocks."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.STORY,
            template="Hello {{ name }}{% if pet %}, and your pet {{ pet }}{% endif %}!",
            variables=["name"]
        )

        # With pet
        rendered1 = manager.render(template, {"name": "Emma", "pet": "Max"}, strict=False)
        assert "your pet Max" in rendered1

        # Without pet
        rendered2 = manager.render(template, {"name": "Emma"}, strict=False)
        assert "your pet" not in rendered2

    def test_render_missing_required_variable(self, manager):
        """Should raise error for missing required variables."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.STORY,
            template="Hello {{ name }}!",
            variables=["name"]
        )

        with pytest.raises(ValueError) as exc_info:
            manager.render(template, {})

        assert "Missing required variables" in str(exc_info.value)

    def test_render_with_list_variable(self, manager):
        """Should handle list variables."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.STORY,
            template="Characters: {{ characters }}",
            variables=["characters"]
        )

        rendered = manager.render(template, {"characters": ["Emma", "Max", "Luna"]})

        assert "Emma, Max, Luna" in rendered

    def test_extract_variables(self, manager):
        """Should extract variable names from template."""
        template_text = """
        Hello {{ name }}, age {{ age }}.
        {% if pet %}You have a pet named {{ pet }}{% endif %}
        """

        variables = manager.extract_variables(template_text)

        assert "name" in variables
        assert "age" in variables
        assert "pet" in variables

    def test_get_prompt_convenience(self, manager):
        """Should get and render prompt in one call."""
        # Use a simple default template
        template = DEFAULT_TEMPLATES["image_prompt"]

        prompt = run_async(manager.get_prompt(
            "image_prompt",
            {
                "art_style": "watercolor",
                "character_description": "a 6-year-old girl named Emma",
                "scene_description": "playing in a garden",
                "mood": "happy"
            }
        ))

        assert "watercolor" in prompt
        assert "Emma" in prompt
        assert "garden" in prompt


# ============================================
# Feature Flag Manager Tests
# ============================================

class TestFeatureFlagManager:
    """Tests for feature flag manager."""

    @pytest.fixture
    def manager(self):
        """Create a flag manager without database."""
        return FeatureFlagManager(database=None)

    def test_get_default_flag(self, manager):
        """Should return default flag."""
        flag = run_async(manager.get_flag("use_flux_pro"))

        assert flag is not None
        assert flag.name == "use_flux_pro"
        assert flag.is_enabled is True

    def test_flag_enabled_all_strategy(self, manager):
        """Should be enabled for ALL strategy when is_enabled=True."""
        flag = FeatureFlag(
            name="test",
            is_enabled=True,
            strategy=RolloutStrategy.ALL
        )

        assert manager.is_enabled(flag) is True
        assert manager.is_enabled(flag, user_id="any_user") is True

    def test_flag_disabled_master_switch(self, manager):
        """Should be disabled when is_enabled=False regardless of strategy."""
        flag = FeatureFlag(
            name="test",
            is_enabled=False,
            rollout_percentage=100,
            strategy=RolloutStrategy.ALL
        )

        assert manager.is_enabled(flag) is False

    def test_percentage_rollout_consistency(self, manager):
        """Same user should always get same result for percentage rollout."""
        flag = FeatureFlag(
            name="test_flag",
            is_enabled=True,
            rollout_percentage=50,
            strategy=RolloutStrategy.PERCENTAGE
        )

        user_id = "user_123"

        # Check multiple times - should be consistent
        results = [manager.is_enabled(flag, user_id=user_id) for _ in range(10)]

        assert all(r == results[0] for r in results)

    def test_percentage_rollout_distribution(self, manager):
        """Percentage rollout should roughly match configured percentage."""
        flag = FeatureFlag(
            name="test_flag",
            is_enabled=True,
            rollout_percentage=50,
            strategy=RolloutStrategy.PERCENTAGE
        )

        # Test with many users
        enabled_count = sum(
            1 for i in range(1000)
            if manager.is_enabled(flag, user_id=f"user_{i}")
        )

        # Should be roughly 50% (within 10% margin)
        assert 400 <= enabled_count <= 600

    def test_user_list_strategy(self, manager):
        """Should only enable for users in the list."""
        flag = FeatureFlag(
            name="test",
            is_enabled=True,
            strategy=RolloutStrategy.USER_LIST,
            conditions={"users": ["user_1", "user_2", "user_3"]}
        )

        assert manager.is_enabled(flag, user_id="user_1") is True
        assert manager.is_enabled(flag, user_id="user_2") is True
        assert manager.is_enabled(flag, user_id="user_99") is False

    def test_condition_strategy_equals(self, manager):
        """Should evaluate equals conditions."""
        flag = FeatureFlag(
            name="test",
            is_enabled=True,
            strategy=RolloutStrategy.CONDITION,
            conditions={"plan": "premium"}
        )

        assert manager.is_enabled(flag, context={"plan": "premium"}) is True
        assert manager.is_enabled(flag, context={"plan": "free"}) is False

    def test_condition_strategy_in_list(self, manager):
        """Should evaluate in-list conditions."""
        flag = FeatureFlag(
            name="test",
            is_enabled=True,
            strategy=RolloutStrategy.CONDITION,
            conditions={"country": ["US", "CA", "UK"]}
        )

        assert manager.is_enabled(flag, context={"country": "US"}) is True
        assert manager.is_enabled(flag, context={"country": "DE"}) is False

    def test_condition_strategy_range(self, manager):
        """Should evaluate range conditions."""
        flag = FeatureFlag(
            name="test",
            is_enabled=True,
            strategy=RolloutStrategy.CONDITION,
            conditions={"age": {"gte": 18, "lte": 65}}
        )

        assert manager.is_enabled(flag, context={"age": 25}) is True
        assert manager.is_enabled(flag, context={"age": 17}) is False
        assert manager.is_enabled(flag, context={"age": 66}) is False

    def test_is_feature_enabled_convenience(self, manager):
        """Should check feature enabled status in one call."""
        enabled = run_async(manager.is_feature_enabled("use_flux_pro"))
        assert enabled is True

        disabled = run_async(manager.is_feature_enabled("nonexistent", default=False))
        assert disabled is False

    def test_get_enabled_flags(self, manager):
        """Should return all flags with their enabled state."""
        flags = run_async(manager.get_enabled_flags(user_id="test_user"))

        assert isinstance(flags, dict)
        assert "use_flux_pro" in flags
        assert flags["use_flux_pro"] is True


# ============================================
# Config Loader Tests
# ============================================

class TestConfigLoader:
    """Tests for the central config loader."""

    @pytest.fixture
    def loader(self):
        """Create a config loader without database."""
        return ConfigLoader(database=None)

    def test_get_ai_model(self, loader):
        """Should get AI model config through loader."""
        config = run_async(loader.get_ai_model(QualityTier.PREVIEW))

        assert config is not None
        assert config.quality_tier == QualityTier.PREVIEW

    def test_get_image_model(self, loader):
        """Should get image model config."""
        config = run_async(loader.get_image_model("print"))

        assert config is not None
        assert config.quality_tier == QualityTier.PRINT

    def test_get_prompt(self, loader):
        """Should get and render prompt."""
        prompt = run_async(loader.get_prompt(
            "image_prompt",
            {
                "art_style": "watercolor",
                "character_description": "test character",
                "scene_description": "test scene",
                "mood": "happy"
            }
        ))

        assert "watercolor" in prompt

    def test_is_feature_enabled(self, loader):
        """Should check feature flag status."""
        enabled = run_async(loader.is_feature_enabled("use_flux_pro"))
        assert enabled is True

    def test_get_config_summary(self, loader):
        """Should return configuration summary."""
        summary = run_async(loader.get_config_summary())

        assert "ai_models" in summary
        assert "prompts" in summary
        assert "feature_flags" in summary
        assert "cache_status" in summary

    def test_invalidate_all_caches(self, loader):
        """Should invalidate all caches."""
        # Populate caches
        run_async(loader.get_ai_model(QualityTier.PREVIEW))
        run_async(loader.get_template("image_prompt"))
        run_async(loader.get_flag("use_flux_pro"))

        # Verify caches have entries
        summary_before = run_async(loader.get_config_summary())
        assert summary_before["cache_status"]["ai_config_entries"] > 0

        # Invalidate
        loader.invalidate_all_caches()

        # Verify caches are empty
        summary_after = run_async(loader.get_config_summary())
        assert summary_after["cache_status"]["ai_config_entries"] == 0


# ============================================
# Integration Tests
# ============================================

class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_full_story_generation_flow(self):
        """Test getting all configs needed for story generation."""
        loader = ConfigLoader(database=None)

        # Get story model config
        story_model = run_async(loader.get_story_model())
        assert story_model.provider == AIProvider.GEMINI

        # Get image model config
        image_model = run_async(loader.get_image_model("preview"))
        assert image_model.provider == AIProvider.FAL

        # Check feature flag
        use_flux_pro = run_async(loader.is_feature_enabled("use_flux_pro"))
        assert use_flux_pro is True

        # Get prompts
        story_prompt = run_async(loader.get_story_prompt(
            child_name="Emma",
            child_age=6,
            character_description="a 6-year-old girl named Emma with brown hair",
            theme="adventure",
            art_style="watercolor",
            page_count=10
        ))

        assert "Emma" in story_prompt
        assert "adventure" in story_prompt

    def test_export_configs(self):
        """Test exporting all configurations."""
        loader = ConfigLoader(database=None)

        export = run_async(loader.export_all_configs())

        assert "ai_models" in export
        assert "prompts" in export
        assert "feature_flags" in export
        assert "exported_at" in export

        assert len(export["ai_models"]) > 0
        assert len(export["feature_flags"]) > 0
