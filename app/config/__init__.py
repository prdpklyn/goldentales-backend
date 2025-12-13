# app/config/__init__.py
"""
GoldenTales Configuration Management
====================================
Dynamic configuration system for AI models, prompts, and feature flags.

This package provides:
- AIConfigManager: Manage AI model configurations
- PromptTemplateManager: Manage prompt templates with variable substitution
- FeatureFlagManager: Manage feature flags with rollout support
- ConfigLoader: Central configuration loader with caching
"""

from app.config.ai_config import AIConfigManager, AIModelConfig, AIProvider
from app.config.prompt_config import PromptTemplateManager, PromptTemplate
from app.config.feature_flags import FeatureFlagManager, FeatureFlag
from app.config.loader import ConfigLoader, get_config_loader

__all__ = [
    "AIConfigManager",
    "AIModelConfig",
    "AIProvider",
    "PromptTemplateManager",
    "PromptTemplate",
    "FeatureFlagManager",
    "FeatureFlag",
    "ConfigLoader",
    "get_config_loader",
]
