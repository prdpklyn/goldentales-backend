# app/services/story_generator.py
"""
GoldenTales Story Generator
===========================
Generates personalized children's stories using Google Gemini.
"""

import json
import re
from typing import List, Dict, Optional, Any

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.security import sanitize_input
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException
from app.utils.json_parser import parse_story_json

logger = get_logger(__name__)


class StoryGenerator:
    """
    Service for generating personalized stories using Gemini AI.
    
    Example:
        generator = StoryGenerator()
        pages = await generator.generate_story(
            character_bible={"main_character": "Emma, 6-year-old girl..."},
            child_name="Emma",
            age=6,
            theme="christmas"
        )
    """
    
    # Theme elements for story generation
    THEME_ELEMENTS = {
        "christmas": "Christmas magic, Santa, elves, snow, presents, giving",
        "space": "planets, stars, rockets, friendly aliens, exploration",
        "ocean": "underwater, dolphins, mermaids, coral reefs, sea creatures",
        "forest": "magical woods, talking animals, fairies, enchanted trees",
        "dinosaur": "prehistoric world, friendly dinosaurs, adventure",
        "superhero": "superpowers, helping others, saving the day",
        "birthday": "celebration, cake, wishes, friends, surprises",
        "bedtime": "dreams, stars, peaceful night, cozy sleep"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the story generator.
        
        Args:
            api_key: Gemini API key. Defaults to settings.
        """
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            logger.warning("Gemini API key not configured")
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=20.0,
        circuit_breaker_name="gemini_ai"
    )
    async def _call_gemini_with_retry(
        self,
        prompt: str
    ) -> str:
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
    
    async def generate_story(
        self,
        character_bible: Dict[str, str],
        child_name: str,
        age: int,
        theme: str,
        occasion: Optional[str] = None,
        special_details: Optional[str] = None,
        additional_characters: Optional[List[Any]] = None
    ) -> List[Dict]:
        """
        Generate a personalized story with character consistency.
        
        Args:
            character_bible: Character description dictionary
            child_name: Name of the main character
            age: Age of the child (2-12)
            theme: Story theme
            occasion: Optional occasion (e.g., "birthday")
            special_details: Optional personalization details
            additional_characters: List of additional characters
            
        Returns:
            List of page dictionaries with text and scene descriptions
        """
        import google.generativeai as genai
        
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Sanitize inputs
        safe_details = sanitize_input(special_details or "")
        safe_occasion = sanitize_input(occasion or "")
        
        # Build additional characters list for story
        additional_chars_text = ""
        if additional_characters:
            chars = []
            for char in additional_characters:
                if hasattr(char, 'name') and hasattr(char, 'relationship'):
                    chars.append(f"- {char.name} ({char.relationship})")
            additional_chars_text = "\n".join(chars)
        
        prompt = self._build_prompt(
            character_bible=character_bible,
            child_name=child_name,
            age=age,
            theme=theme,
            occasion=safe_occasion,
            special_details=safe_details,
            additional_chars_text=additional_chars_text
        )
        
        try:
            logger.info(f"Generating story for {child_name}, theme: {theme}")
            response_text = await self._call_gemini_with_retry(prompt)
            
            # Use robust JSON parser that handles LLM quirks
            try:
                story_pages = parse_story_json(response_text)
            except ValueError as e:
                logger.error(f"Failed to parse story JSON: {e}")
                logger.debug(f"Raw response (first 1000 chars): {response_text[:1000]}")
                raise ValueError("Failed to generate story. Please try again.")
            
            # Ensure character description is in every scene
            story_pages = self._enhance_scene_descriptions(
                story_pages, 
                character_bible
            )
            
            logger.info(f"Generated {len(story_pages)} story pages")
            return story_pages[:10]  # Ensure exactly 10 pages
            
        except ValueError:
            # Re-raise ValueError as-is (from JSON parsing)
            raise
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            raise ExternalServiceException(
                service_name="Gemini AI",
                message=f"Story generation failed: {str(e)}",
                is_transient=False
            )
    
    def _build_prompt(
        self,
        character_bible: Dict[str, str],
        child_name: str,
        age: int,
        theme: str,
        occasion: str,
        special_details: str,
        additional_chars_text: str
    ) -> str:
        """Build the complete story generation prompt."""
        
        theme_elements = self.THEME_ELEMENTS.get(theme, '')
        
        return f"""
You are creating a 10-page children's storybook. The main character must be described CONSISTENTLY.

=== MAIN CHARACTER (use this EXACT description in scene descriptions) ===
{character_bible.get('main_character', f'{child_name}, {age}-year-old child')}

=== ADDITIONAL CHARACTERS ===
{additional_chars_text or "None"}

=== STORY SETTINGS ===
Theme: {theme.upper()} - {theme_elements}
Occasion: {occasion or 'A gift made with love'}
Special details: {special_details or 'None'}

=== REQUIREMENTS ===
1. {child_name} is the HERO - brave, kind, and special
2. Each page: 2-3 sentences (25-40 words max)
3. Simple vocabulary for age {age}
4. Story arc: Setup (1-3) → Adventure (4-7) → Resolution (8-10)
5. CRITICAL: In scene_description, ALWAYS describe the main character using the EXACT details above
6. Include character's specific features (hair color/style, skin tone, any glasses/freckles) in EVERY scene_description

=== OUTPUT FORMAT ===
Return ONLY a JSON array:
[
  {{
    "page_number": 1,
    "text": "Story text here...",
    "scene_description": "MUST include: [character's full appearance description]. Scene: [setting details]",
    "character_action": "What {child_name} is doing",
    "mood": "happy/excited/curious/brave/peaceful/magical",
    "characters_in_scene": ["{child_name}"]
  }}
]

IMPORTANT: scene_description MUST start with the character's appearance every time!
"""
    
    def _enhance_scene_descriptions(
        self,
        story_pages: List[Dict],
        character_bible: Dict[str, str]
    ) -> List[Dict]:
        """Ensure character description is prominent in every scene."""
        
        main_char_short = character_bible.get('main_character_short', '')
        main_char_full = character_bible.get('main_character', '')
        
        for page in story_pages:
            if 'scene_description' in page:
                desc = page['scene_description']
                # If character description isn't prominent, prepend it
                if main_char_short and main_char_short not in desc:
                    page['scene_description'] = f"{main_char_full}. {desc}"

        return story_pages

    async def generate_preview_story(
        self,
        character_bible: Dict[str, str],
        child_name: str,
        age: int,
        theme: str,
        num_pages: int = 2
    ) -> List[Dict]:
        """
        Generate a SHORT story for quick preview (2-3 pages).

        Args:
            character_bible: Character description dictionary
            child_name: Name of the main character
            age: Age of the child
            theme: Story theme
            num_pages: Number of pages to generate (default: 2)

        Returns:
            List of page dictionaries
        """
        import google.generativeai as genai

        if not self.api_key:
            raise ValueError("Gemini API key not configured")

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        theme_elements = self.THEME_ELEMENTS.get(theme, '')

        prompt = f"""
You are creating a SHORT {num_pages}-page preview of a children's storybook.

=== MAIN CHARACTER ===
{character_bible.get('main_character', f'{child_name}, {age}-year-old child')}

=== STORY SETTINGS ===
Theme: {theme.upper()} - {theme_elements}

=== REQUIREMENTS ===
1. {child_name} is the HERO
2. Each page: 2-3 sentences (20-35 words max)
3. Simple vocabulary for age {age}
4. {num_pages} pages total: exciting opening and action
5. CRITICAL: In scene_description, ALWAYS include the main character's full appearance

=== OUTPUT FORMAT ===
Return ONLY a JSON array with exactly {num_pages} pages:
[
  {{
    "page_number": 1,
    "text": "Story text...",
    "scene_description": "{child_name}'s full appearance. Scene details.",
    "character_action": "What {child_name} is doing",
    "mood": "happy/excited/curious/brave",
    "characters_in_scene": ["{child_name}"]
  }}
]
"""

        try:
            logger.info(f"Generating {num_pages}-page preview story for {child_name}")
            response_text = await self._call_gemini_with_retry(prompt)

            # Parse JSON response
            story_pages = parse_story_json(response_text)

            # Enhance scene descriptions
            story_pages = self._enhance_scene_descriptions(story_pages, character_bible)

            logger.info(f"Generated {len(story_pages)} preview pages")
            return story_pages[:num_pages]

        except Exception as e:
            logger.error(f"Preview story generation failed: {e}")
            raise ExternalServiceException(
                service_name="Gemini AI",
                message=f"Preview story generation failed: {str(e)}",
                is_transient=False
            )
