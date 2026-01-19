# app/config/prompt_config.py
"""
GoldenTales Prompt Template System
==================================
Manage prompt templates with variable substitution and versioning.
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Set

from app.utils.logging import get_logger

logger = get_logger(__name__)


class PromptCategory(str, Enum):
    """Categories for prompt templates."""
    STORY = "story"           # Story generation prompts
    IMAGE = "image"           # Image generation prompts
    CHARACTER = "character"   # Character description prompts
    SCENE = "scene"           # Scene description prompts
    SYSTEM = "system"         # System/instruction prompts


@dataclass
class PromptTemplate:
    """
    A prompt template with variable substitution.

    Attributes:
        name: Unique identifier for the template
        category: Template category
        template: The template string with {{ variable }} placeholders
        variables: List of required variable names
        description: Human-readable description
        version: Version number
        is_active: Whether this version is active
    """
    name: str
    category: PromptCategory
    template: str
    variables: List[str] = field(default_factory=list)
    description: str = ""
    version: int = 1
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """Create from dictionary."""
        data = data.copy()
        data["category"] = PromptCategory(data["category"])
        return cls(**data)


# Default prompt templates (fallback when database is unavailable)
DEFAULT_TEMPLATES: Dict[str, PromptTemplate] = {
    "story_generation": PromptTemplate(
        name="story_generation",
        category=PromptCategory.STORY,
        template="""You are creating a personalized children's storybook for {{ child_name }}, age {{ child_age }}.

Character Description:
{{ character_description }}

Theme: {{ theme }}
Art Style: {{ art_style }}
{% if additional_characters %}Additional Characters: {{ additional_characters }}{% endif %}
{% if pets %}Pets: {{ pets }}{% endif %}
{% if siblings %}Siblings: {{ siblings }}{% endif %}

Create a {{ page_count }}-page children's story with the following requirements:
1. Age-appropriate vocabulary and concepts for a {{ child_age }}-year-old
2. Include {{ child_name }} as the main character in every scene
3. Follow the {{ theme }} theme throughout
4. Each page should have 2-3 short sentences
5. End with a positive, uplifting message

For each page, provide:
- page_number: The page number (1-{{ page_count }})
- text: The story text for that page
- scene_description: A detailed visual description for illustration
- mood: The emotional tone (happy, excited, curious, peaceful, etc.)

Return as a JSON array of page objects.""",
        variables=["child_name", "child_age", "character_description", "theme", "art_style", "page_count"],
        description="Main story generation prompt for creating personalized children's stories",
    ),

    "character_bible": PromptTemplate(
        name="character_bible",
        category=PromptCategory.CHARACTER,
        template="""Create a detailed character description for a {{ child_age }}-year-old {{ gender }} named {{ child_name }}.

Physical Attributes:
- Skin Tone: {{ skin_tone }}
- Hair Color: {{ hair_color }}
- Hair Style: {{ hair_style }}
- Eye Color: {{ eye_color }}
{% if body_type %}- Body Type: {{ body_type }}{% endif %}
{% if special_features %}- Special Features: {{ special_features }}{% endif %}

Create a consistent character description that will be used for ALL illustrations.
The description should be detailed enough to maintain visual consistency across 10+ images.

Return a JSON object with:
- main_character: Full detailed description
- main_character_short: Brief identifier (name, age, key features)
- clothing_style: Default clothing description
- key_identifiers: List of unique visual markers""",
        variables=["child_name", "child_age", "gender", "skin_tone", "hair_color", "hair_style", "eye_color"],
        description="Generate consistent character description for illustration consistency",
    ),

    "image_prompt": PromptTemplate(
        name="image_prompt",
        category=PromptCategory.IMAGE,
        template="""{{ art_style }} illustration of {{ character_description }}.

Scene: {{ scene_description }}

Style requirements:
- {{ art_style }} art style
- Children's book illustration
- Warm, friendly atmosphere
- Age-appropriate content
- {{ mood }} mood

Important: The character must match the description exactly for consistency.""",
        variables=["art_style", "character_description", "scene_description", "mood"],
        description="Generate image prompts for story illustrations",
    ),

    "scene_enhancement": PromptTemplate(
        name="scene_enhancement",
        category=PromptCategory.SCENE,
        template="""Enhance the following scene description for a {{ art_style }} children's book illustration:

Original scene: {{ scene_description }}

Character in scene: {{ character_description }}

Requirements:
1. Add specific visual details (colors, lighting, environment)
2. Ensure the character is prominently featured
3. Make it suitable for {{ art_style }} illustration style
4. Keep it child-friendly and warm
5. Include background elements that support the {{ theme }} theme

Return an enhanced scene description (2-3 sentences).""",
        variables=["scene_description", "character_description", "art_style", "theme"],
        description="Enhance basic scene descriptions for better illustrations",
    ),
    
    # Educational templates
    "educational_story": PromptTemplate(
        name="educational_story",
        category=PromptCategory.STORY,
        template="""Create an EDUCATIONAL storybook to teach {{ topic }} ({{ topic_category }}).

=== CHAPTER CONTEXT ===
Chapter {{ chapter_number }} of {{ total_chapters }}
Concepts to teach: {{ concepts }}
{% if previous_concepts %}Previous chapters covered: {{ previous_concepts }}{% endif %}

=== LEARNER CHARACTER ===
{{ learner_character }}

=== CONCEPT CHARACTERS ===
{{ concept_characters }}

=== LEARNER PROFILE ===
Name: {{ learner_name }}
Level: {{ learner_level }}
Age band: {{ age_band }}

=== PEDAGOGICAL STRUCTURE (10 pages) ===
Pages 1-2 (SETUP): Introduce topic and create context
Pages 3-6 (CORE CONCEPTS): Teach concepts progressively
Pages 7-8 (APPLICATION): Show concepts in practice
Page 9 (REINFORCEMENT): Review and test understanding
Page 10 (SUMMARY): Recap and celebrate progress

Generate a 10-page educational story as JSON array with pedagogical structure.""",
        variables=["topic", "topic_category", "concepts", "chapter_number", "total_chapters",
                   "learner_character", "concept_characters", "learner_name", "learner_level", "age_band"],
        description="Generate educational stories with pedagogical structure",
    ),
    
    "quiz_generation": PromptTemplate(
        name="quiz_generation",
        category=PromptCategory.SYSTEM,
        template="""Generate a {{ num_questions }}-question quiz to assess understanding of: {{ topic }}

TOPIC CATEGORY: {{ topic_category }}
DIFFICULTY: {{ difficulty_level }}
AGE BAND: {{ age_band }}

REQUIREMENTS:
1. Questions assess conceptual understanding
2. Mix of what/why/how questions
3. Each question has 4 options with ONE correct answer
4. Include explanations for correct answers

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Question text",
      "options": [{{"id": "A", "text": "Option A"}}, ...],
      "correct_answer": "B",
      "explanation": "Why B is correct",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}

Return ONLY valid JSON.""",
        variables=["topic", "topic_category", "num_questions", "difficulty_level", "age_band"],
        description="Generate assessment quizzes for educational topics",
    ),
    
    "concept_character": PromptTemplate(
        name="concept_character",
        category=PromptCategory.CHARACTER,
        template="""Create a personified character to represent the concept "{{ concept_name }}" in an educational story about {{ topic }}.

CHARACTER TYPE: {{ character_type }}
ART STYLE: {{ art_style }}
TARGET AUDIENCE: {{ age_band }}

Generate:
1. CHARACTER NAME: Creative name that hints at the concept
2. VISUAL FORM: How the character appears
3. PRIMARY COLORS: 2-3 main colors
4. DISTINCTIVE FEATURES: Unique visual markers
5. PERSONALITY TRAITS: Traits that reflect the concept
6. ROLE IN STORY: How this character teaches the concept

FORMAT:
NAME: [name]
VISUAL_FORM: [description]
COLORS: [color1, color2, color3]
FEATURES: [features]
PERSONALITY: [traits]
ROLE: [teaching role]""",
        variables=["concept_name", "topic", "character_type", "art_style", "age_band"],
        description="Generate concept characters that personify abstract ideas",
    ),
}


class PromptTemplateManager:
    """
    Manages prompt templates with variable substitution and caching.

    Features:
    - Database-backed templates with versioning
    - In-memory caching
    - Variable validation
    - Jinja2-style template rendering
    """

    # Pattern for {{ variable }} placeholders
    VARIABLE_PATTERN = re.compile(r'\{\{\s*(\w+)\s*\}\}')
    # Pattern for {% if variable %} conditionals
    CONDITIONAL_PATTERN = re.compile(r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}', re.DOTALL)

    def __init__(
        self,
        database=None,
        cache_ttl: int = 300  # 5 minutes
    ):
        """
        Initialize the prompt template manager.

        Args:
            database: Database service for persistence
            cache_ttl: Cache time-to-live in seconds
        """
        self.db = database
        self._cache: Dict[str, tuple] = {}  # {key: (template, expiry)}
        self._cache_ttl = cache_ttl

    def _get_cache_key(self, name: str, version: Optional[int] = None) -> str:
        """Generate cache key for a template lookup."""
        return f"prompt:{name}:{version or 'latest'}"

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid."""
        if key not in self._cache:
            return False
        _, expiry = self._cache[key]
        return datetime.now(timezone.utc).timestamp() < expiry

    def _set_cache(self, key: str, template: PromptTemplate):
        """Set a value in the cache."""
        expiry = datetime.now(timezone.utc).timestamp() + self._cache_ttl
        self._cache[key] = (template, expiry)

    def _get_cache(self, key: str) -> Optional[PromptTemplate]:
        """Get a value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache[key][0]
        return None

    def invalidate_cache(self, name: Optional[str] = None):
        """Invalidate cache entry or entire cache."""
        if name:
            # Remove all versions of this template
            keys_to_remove = [k for k in self._cache if k.startswith(f"prompt:{name}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

    async def get_template(
        self,
        name: str,
        version: Optional[int] = None,
        use_cache: bool = True
    ) -> PromptTemplate:
        """
        Get a prompt template by name.

        Args:
            name: Template name
            version: Specific version (None for latest active)
            use_cache: Whether to use cached values

        Returns:
            PromptTemplate object

        Raises:
            ValueError: If template not found
        """
        cache_key = self._get_cache_key(name, version)

        # Check cache first
        if use_cache:
            cached = self._get_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached

        # Try loading from database
        if self.db:
            try:
                template_data = await self._load_from_database(name, version)
                if template_data:
                    template = PromptTemplate.from_dict(template_data)
                    self._set_cache(cache_key, template)
                    return template
            except Exception as e:
                logger.warning(f"Failed to load template from database: {e}")

        # Fallback to default templates
        if name in DEFAULT_TEMPLATES:
            template = DEFAULT_TEMPLATES[name]
            self._set_cache(cache_key, template)
            return template

        raise ValueError(f"Prompt template not found: {name}")

    async def _load_from_database(
        self,
        name: str,
        version: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Load template from database."""
        if not self.db or not self.db.client:
            return None

        query = (
            self.db.client.table("prompt_templates")
            .select("*")
            .eq("name", name)
        )

        if version:
            query = query.eq("version", version)
        else:
            query = query.eq("is_active", True)

        result = query.order("version", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    def render(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        strict: bool = True
    ) -> str:
        """
        Render a template with variables.

        Args:
            template: PromptTemplate to render
            variables: Variable values
            strict: If True, raise error for missing required variables

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If required variables are missing (when strict=True)
        """
        # Validate required variables
        if strict:
            missing = self._get_missing_variables(template, variables)
            if missing:
                raise ValueError(f"Missing required variables: {missing}")

        rendered = template.template

        # Process conditionals first ({% if var %}...{% endif %})
        def replace_conditional(match):
            var_name = match.group(1)
            content = match.group(2)
            if var_name in variables and variables[var_name]:
                # Recursively render the content
                return self._substitute_variables(content, variables)
            return ""

        rendered = self.CONDITIONAL_PATTERN.sub(replace_conditional, rendered)

        # Substitute remaining variables
        rendered = self._substitute_variables(rendered, variables)

        # Clean up extra whitespace
        rendered = re.sub(r'\n{3,}', '\n\n', rendered)
        return rendered.strip()

    def _substitute_variables(
        self,
        text: str,
        variables: Dict[str, Any]
    ) -> str:
        """Substitute {{ variable }} placeholders."""
        def replace_var(match):
            var_name = match.group(1)
            if var_name in variables:
                value = variables[var_name]
                if isinstance(value, list):
                    return ", ".join(str(v) for v in value)
                return str(value)
            return match.group(0)  # Keep original if not found

        return self.VARIABLE_PATTERN.sub(replace_var, text)

    def _get_missing_variables(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any]
    ) -> List[str]:
        """Get list of missing required variables."""
        return [v for v in template.variables if v not in variables]

    async def get_prompt(
        self,
        name: str,
        variables: Dict[str, Any],
        version: Optional[int] = None,
        strict: bool = True
    ) -> str:
        """
        Get and render a prompt template.

        Convenience method that combines get_template and render.

        Args:
            name: Template name
            variables: Variable values
            version: Specific version (None for latest)
            strict: Validate required variables

        Returns:
            Rendered prompt string
        """
        template = await self.get_template(name, version)
        return self.render(template, variables, strict)

    async def get_all_templates(
        self,
        category: Optional[PromptCategory] = None,
        active_only: bool = True
    ) -> List[PromptTemplate]:
        """
        Get all templates, optionally filtered by category.

        Args:
            category: Filter by category
            active_only: Only return active templates

        Returns:
            List of PromptTemplate objects
        """
        if self.db and self.db.client:
            try:
                query = self.db.client.table("prompt_templates").select("*")
                if category:
                    query = query.eq("category", category.value)
                if active_only:
                    query = query.eq("is_active", True)
                result = query.execute()

                if result.data:
                    return [PromptTemplate.from_dict(d) for d in result.data]
            except Exception as e:
                logger.warning(f"Failed to load templates from database: {e}")

        # Return defaults filtered by category
        templates = list(DEFAULT_TEMPLATES.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    async def create_template(
        self,
        template: PromptTemplate
    ) -> Optional[PromptTemplate]:
        """
        Create a new prompt template.

        Args:
            template: PromptTemplate to create

        Returns:
            Created PromptTemplate or None
        """
        if not self.db or not self.db.client:
            logger.warning("Database not available for template creation")
            return None

        try:
            data = template.to_dict()
            data["created_at"] = datetime.now(timezone.utc).isoformat()
            data["updated_at"] = data["created_at"]

            result = (
                self.db.client.table("prompt_templates")
                .insert(data)
                .execute()
            )

            if result.data:
                created = PromptTemplate.from_dict(result.data[0])
                self.invalidate_cache(template.name)
                logger.info(f"Created prompt template: {template.name}")
                return created

        except Exception as e:
            logger.error(f"Failed to create template {template.name}: {e}")

        return None

    async def update_template(
        self,
        name: str,
        updates: Dict[str, Any],
        create_new_version: bool = True
    ) -> Optional[PromptTemplate]:
        """
        Update a prompt template.

        Args:
            name: Template name
            updates: Fields to update
            create_new_version: If True, create new version instead of updating

        Returns:
            Updated/new PromptTemplate or None
        """
        if not self.db or not self.db.client:
            logger.warning("Database not available for template update")
            return None

        try:
            if create_new_version:
                # Get current template
                current = await self.get_template(name)
                if not current:
                    return None

                # Deactivate old version
                self.db.client.table("prompt_templates").update(
                    {"is_active": False}
                ).eq("name", name).execute()

                # Create new version
                new_template = PromptTemplate(
                    name=name,
                    category=current.category,
                    template=updates.get("template", current.template),
                    variables=updates.get("variables", current.variables),
                    description=updates.get("description", current.description),
                    version=current.version + 1,
                    is_active=True,
                )
                return await self.create_template(new_template)
            else:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                result = (
                    self.db.client.table("prompt_templates")
                    .update(updates)
                    .eq("name", name)
                    .eq("is_active", True)
                    .execute()
                )

                if result.data:
                    updated = PromptTemplate.from_dict(result.data[0])
                    self.invalidate_cache(name)
                    logger.info(f"Updated prompt template: {name}")
                    return updated

        except Exception as e:
            logger.error(f"Failed to update template {name}: {e}")

        return None

    def extract_variables(self, template_text: str) -> Set[str]:
        """
        Extract variable names from a template string.

        Args:
            template_text: Template string

        Returns:
            Set of variable names
        """
        variables = set()

        # Extract from {{ variable }}
        variables.update(self.VARIABLE_PATTERN.findall(template_text))

        # Extract from {% if variable %}
        for match in self.CONDITIONAL_PATTERN.finditer(template_text):
            variables.add(match.group(1))

        return variables


# Singleton instance
_prompt_manager: Optional[PromptTemplateManager] = None


def get_prompt_manager(database=None) -> PromptTemplateManager:
    """Get the prompt template manager singleton."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager(database=database)
    return _prompt_manager
