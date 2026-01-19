# app/services/concept_character_service.py
"""
GoldenTales Concept Character Service
=====================================
Manages conceptual characters for educational stories.
Transforms abstract concepts into personified characters.
"""

import re
from typing import Dict, List, Optional, Any

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException
from app.models.enums import ConceptCharacterType, TopicCategory
from character_system import ConceptCharacter

logger = get_logger(__name__)


class ConceptCharacterService:
    """
    Service for creating and managing concept characters.
    
    Concept characters personify abstract ideas to make them easier to
    understand in educational stories.
    
    Example:
        service = ConceptCharacterService()
        agent_char = await service.create_concept_character(
            concept_name="Reinforcement Learning Agent",
            topic="reinforcement_learning",
            art_style="cartoon"
        )
    """
    
    # Character archetype templates for different concept types
    ARCHETYPE_TEMPLATES = {
        ConceptCharacterType.AGENT: {
            "visual_forms": ["friendly robot", "explorer character", "curious creature"],
            "color_schemes": [
                ["blue", "silver"],
                ["green", "gold"],
                ["purple", "white"]
            ],
            "personality_base": "curious, determined, learns from experience"
        },
        ConceptCharacterType.ENVIRONMENT: {
            "visual_forms": ["magical landscape", "living world", "dimensional space"],
            "color_schemes": [
                ["earth tones", "green"],
                ["blue", "white"],
                ["multicolor", "vibrant"]
            ],
            "personality_base": "responsive, challenging, fair"
        },
        ConceptCharacterType.PROCESS: {
            "visual_forms": ["energy being", "transformation spirit", "flow entity"],
            "color_schemes": [
                ["flowing colors", "gradient"],
                ["bright yellow", "orange"],
                ["rainbow", "shimmer"]
            ],
            "personality_base": "dynamic, transformative, continuous"
        },
        ConceptCharacterType.ENTITY: {
            "visual_forms": ["glowing orb", "mystical artifact", "animated object"],
            "color_schemes": [
                ["golden", "luminous"],
                ["crystal", "transparent"],
                ["deep blue", "sparkle"]
            ],
            "personality_base": "informative, stable, reliable"
        },
        ConceptCharacterType.GUIDE: {
            "visual_forms": ["wise mentor", "professor figure", "helpful companion"],
            "color_schemes": [
                ["warm brown", "cream"],
                ["wise purple", "white"],
                ["gentle blue", "silver"]
            ],
            "personality_base": "patient, knowledgeable, encouraging"
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the concept character service.
        
        Args:
            api_key: Gemini API key. Defaults to settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            logger.warning("Gemini API key not configured")
    
    def _generate_character_slug(self, concept_name: str, topic: str) -> str:
        """Generate URL-safe slug for concept character."""
        # Combine concept and topic, clean, and slugify
        base = f"{concept_name}_{topic}"
        slug = re.sub(r'[^a-z0-9]+', '_', base.lower())
        slug = slug.strip('_')
        return slug[:100]  # Limit length
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=20.0,
        circuit_breaker_name="gemini_ai"
    )
    async def _call_gemini_with_retry(self, prompt: str) -> str:
        """Call Gemini API with retry logic."""
        import google.generativeai as genai
        
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = any(
                pattern in error_msg
                for pattern in ['timeout', 'rate limit', 'unavailable', '429', '503', 'quota']
            )
            
            raise ExternalServiceException(
                service_name="Gemini AI",
                message=str(e),
                is_transient=is_transient
            )
    
    async def create_concept_character(
        self,
        concept_name: str,
        topic: str,
        character_type: ConceptCharacterType,
        art_style: str = "cartoon",
        age_band: str = "adult",
        custom_details: Optional[str] = None
    ) -> ConceptCharacter:
        """
        Create a concept character to represent an abstract idea.
        
        Args:
            concept_name: The concept to personify (e.g., "Reward Signal")
            topic: The topic context (e.g., "reinforcement_learning")
            character_type: Type of concept character
            art_style: Visual style to match story
            age_band: Target age for appropriate complexity
            custom_details: Optional custom requirements
            
        Returns:
            ConceptCharacter object with full description
        """
        if not self.api_key:
            # Fallback to template-based generation without AI
            return self._create_from_template(
                concept_name, topic, character_type, art_style
            )
        
        # Get archetype template
        archetype = self.ARCHETYPE_TEMPLATES.get(
            character_type,
            self.ARCHETYPE_TEMPLATES[ConceptCharacterType.ENTITY]
        )
        
        # Build prompt for character generation
        prompt = self._build_character_creation_prompt(
            concept_name=concept_name,
            topic=topic,
            character_type=character_type,
            archetype=archetype,
            art_style=art_style,
            age_band=age_band,
            custom_details=custom_details
        )
        
        try:
            logger.info(f"Generating concept character for '{concept_name}' ({character_type.value})")
            response_text = await self._call_gemini_with_retry(prompt)
            
            # Parse response
            character_data = self._parse_character_response(
                response_text,
                concept_name,
                character_type,
                archetype
            )
            
            # Create character slug
            character_slug = self._generate_character_slug(concept_name, topic)
            
            character = ConceptCharacter(
                name=character_data["name"],
                character_type=character_type,
                concept_name=concept_name,
                visual_form=character_data["visual_form"],
                primary_colors=character_data["primary_colors"],
                distinctive_features=character_data["distinctive_features"],
                personality_traits=character_data["personality_traits"],
                role_in_story=character_data["role_in_story"],
                character_slug=character_slug
            )
            
            logger.info(f"Created concept character: {character.name}")
            return character
            
        except Exception as e:
            logger.error(f"Failed to create concept character: {e}")
            # Fallback to template-based generation
            return self._create_from_template(
                concept_name, topic, character_type, art_style
            )
    
    def _build_character_creation_prompt(
        self,
        concept_name: str,
        topic: str,
        character_type: ConceptCharacterType,
        archetype: Dict,
        art_style: str,
        age_band: str,
        custom_details: Optional[str]
    ) -> str:
        """Build prompt for concept character generation."""
        
        age_complexity = {
            "child": "simple and friendly",
            "teen": "engaging and relatable",
            "adult": "sophisticated and nuanced"
        }
        complexity = age_complexity.get(age_band, "engaging")
        
        return f"""
Create a personified character to represent the concept "{concept_name}" in an educational story about {topic}.

CHARACTER TYPE: {character_type.value}
ART STYLE: {art_style}
TARGET AUDIENCE: {age_band} learners
COMPLEXITY: {complexity}

ARCHETYPE GUIDELINES:
- Visual forms: {', '.join(archetype['visual_forms'])}
- Color schemes: {', '.join([' & '.join(colors) for colors in archetype['color_schemes']])}
- Base personality: {archetype['personality_base']}

{f"CUSTOM REQUIREMENTS: {custom_details}" if custom_details else ""}

Generate a character design with the following:

1. CHARACTER NAME: Creative, memorable name that hints at the concept
2. VISUAL FORM: How the character appears (must be one phrase, suitable for {art_style} style)
3. PRIMARY COLORS: 2-3 main colors (comma-separated)
4. DISTINCTIVE FEATURES: Unique visual markers that make them recognizable
5. PERSONALITY TRAITS: 3-5 traits that reflect the concept's nature
6. ROLE IN STORY: How this character helps teach the concept

FORMAT YOUR RESPONSE EXACTLY AS:
NAME: [character name]
VISUAL_FORM: [visual description]
COLORS: [color1, color2, color3]
FEATURES: [distinctive features]
PERSONALITY: [trait1, trait2, trait3]
ROLE: [teaching role]

Keep descriptions clear, visual, and suitable for {art_style} illustration style.
"""
    
    def _parse_character_response(
        self,
        response_text: str,
        concept_name: str,
        character_type: ConceptCharacterType,
        archetype: Dict
    ) -> Dict[str, Any]:
        """Parse AI response into character data."""
        
        lines = response_text.strip().split('\n')
        data = {
            "name": "",
            "visual_form": "",
            "primary_colors": [],
            "distinctive_features": "",
            "personality_traits": "",
            "role_in_story": ""
        }
        
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            
            if key == "NAME":
                data["name"] = value
            elif key == "VISUAL_FORM" or key == "VISUAL":
                data["visual_form"] = value
            elif key == "COLORS" or key == "PRIMARY_COLORS":
                # Parse comma-separated colors
                data["primary_colors"] = [c.strip() for c in value.split(',')]
            elif key == "FEATURES" or key == "DISTINCTIVE_FEATURES":
                data["distinctive_features"] = value
            elif key == "PERSONALITY" or key == "PERSONALITY_TRAITS":
                data["personality_traits"] = value
            elif key == "ROLE" or key == "ROLE_IN_STORY":
                data["role_in_story"] = value
        
        # Fallback to defaults if parsing failed
        if not data["name"]:
            data["name"] = self._generate_default_name(concept_name, character_type)
        if not data["visual_form"]:
            data["visual_form"] = archetype["visual_forms"][0]
        if not data["primary_colors"]:
            data["primary_colors"] = archetype["color_schemes"][0]
        if not data["personality_traits"]:
            data["personality_traits"] = archetype["personality_base"]
        
        return data
    
    def _generate_default_name(
        self,
        concept_name: str,
        character_type: ConceptCharacterType
    ) -> str:
        """Generate a default character name from concept."""
        # Take first word and capitalize
        words = concept_name.split()
        if not words:
            return f"The {character_type.value.title()}"
        
        base = words[0].title()
        
        # Add suffix based on type
        suffixes = {
            ConceptCharacterType.AGENT: "Agent",
            ConceptCharacterType.GUIDE: "Professor",
            ConceptCharacterType.ENTITY: "the Oracle",
            ConceptCharacterType.PROCESS: "the Flow",
            ConceptCharacterType.ENVIRONMENT: "World"
        }
        
        suffix = suffixes.get(character_type, "")
        if suffix and not base.endswith(suffix):
            return f"{base} {suffix}" if suffix.startswith("the") else f"{suffix} {base}"
        return base
    
    def _create_from_template(
        self,
        concept_name: str,
        topic: str,
        character_type: ConceptCharacterType,
        art_style: str
    ) -> ConceptCharacter:
        """Create concept character from template (fallback when AI unavailable)."""
        
        archetype = self.ARCHETYPE_TEMPLATES.get(
            character_type,
            self.ARCHETYPE_TEMPLATES[ConceptCharacterType.ENTITY]
        )
        
        name = self._generate_default_name(concept_name, character_type)
        character_slug = self._generate_character_slug(concept_name, topic)
        
        return ConceptCharacter(
            name=name,
            character_type=character_type,
            concept_name=concept_name,
            visual_form=archetype["visual_forms"][0],
            primary_colors=archetype["color_schemes"][0],
            distinctive_features=f"unique markings that represent {concept_name}",
            personality_traits=archetype["personality_base"],
            role_in_story=f"helps explain {concept_name}",
            character_slug=character_slug
        )
    
    async def create_multiple_concept_characters(
        self,
        concepts: List[str],
        topic: str,
        art_style: str = "cartoon",
        age_band: str = "adult"
    ) -> List[ConceptCharacter]:
        """
        Create multiple concept characters for a story.
        
        Args:
            concepts: List of concept names to create characters for
            topic: Topic context
            art_style: Visual style
            age_band: Target age
            
        Returns:
            List of ConceptCharacter objects
        """
        characters = []
        
        for concept in concepts:
            # Infer character type from concept name
            char_type = self._infer_character_type(concept)
            
            character = await self.create_concept_character(
                concept_name=concept,
                topic=topic,
                character_type=char_type,
                art_style=art_style,
                age_band=age_band
            )
            
            characters.append(character)
        
        logger.info(f"Created {len(characters)} concept characters for {topic}")
        return characters
    
    def _infer_character_type(self, concept_name: str) -> ConceptCharacterType:
        """Infer character type from concept name."""
        concept_lower = concept_name.lower()
        
        # Keywords to identify type
        if any(word in concept_lower for word in ['agent', 'actor', 'learner', 'player']):
            return ConceptCharacterType.AGENT
        elif any(word in concept_lower for word in ['environment', 'world', 'space', 'maze', 'grid']):
            return ConceptCharacterType.ENVIRONMENT
        elif any(word in concept_lower for word in ['process', 'algorithm', 'method', 'flow', 'cycle']):
            return ConceptCharacterType.PROCESS
        elif any(word in concept_lower for word in ['guide', 'teacher', 'mentor', 'professor', 'helper']):
            return ConceptCharacterType.GUIDE
        else:
            # Default to entity for most concepts
            return ConceptCharacterType.ENTITY
