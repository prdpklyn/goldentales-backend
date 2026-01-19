# app/services/educational_story_generator.py
"""
GoldenTales Educational Story Generator
=======================================
Generates pedagogically-structured stories that teach complex topics.
"""

import json
from typing import List, Dict, Optional, Any

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.security import sanitize_input
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException
from app.utils.json_parser import parse_story_json
from app.models.enums import LearningLevel, TopicCategory

logger = get_logger(__name__)


class EducationalStoryGenerator:
    """
    Service for generating educational stories with pedagogical structure.
    
    Unlike children's stories, educational stories follow a learning-focused
    arc that introduces concepts progressively and reinforces understanding.
    
    Example:
        generator = EducationalStoryGenerator()
        pages = await generator.generate_educational_story(
            topic="Reinforcement Learning",
            concepts=["agents", "environments", "rewards"],
            learner_level=LearningLevel.BEGINNER,
            character_bible={...},
            concept_characters=[...]
        )
    """
    
    # Pedagogical structure by page type
    PEDAGOGICAL_STRUCTURE = {
        "setup": {
            "pages": [1, 2],
            "focus": "Introduce the topic, create context, establish why it matters"
        },
        "core_concepts": {
            "pages": [3, 4, 5, 6],
            "focus": "Teach main concepts one at a time with examples"
        },
        "application": {
            "pages": [7, 8],
            "focus": "Show how concepts work together in practice"
        },
        "reinforcement": {
            "pages": [9],
            "focus": "Review and test understanding"
        },
        "summary": {
            "pages": [10],
            "focus": "Recap key learnings and next steps"
        }
    }
    
    # Age-appropriate vocabulary guidance
    VOCABULARY_GUIDANCE = {
        "child": {
            "complexity": "simple, concrete terms",
            "sentence_length": "short (5-10 words)",
            "examples": "everyday situations kids can relate to"
        },
        "teen": {
            "complexity": "clear terms with some technical vocabulary",
            "sentence_length": "medium (10-20 words)",
            "examples": "relatable scenarios from school or hobbies"
        },
        "adult": {
            "complexity": "professional terminology with clear explanations",
            "sentence_length": "varied (15-30 words)",
            "examples": "real-world applications and case studies"
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the educational story generator.
        
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
    
    async def generate_educational_story(
        self,
        topic: str,
        topic_category: TopicCategory,
        concepts: List[str],
        learner_name: str,
        learner_level: LearningLevel,
        age_band: str,
        character_bible: Dict[str, Any],
        concept_characters: List[Dict[str, str]],
        chapter_number: int = 1,
        total_chapters: int = 5,
        previous_concepts: Optional[List[str]] = None,
        art_style: str = "cartoon",
        custom_focus: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate an educational story with pedagogical structure.
        
        Args:
            topic: Main topic being taught
            topic_category: Category of the topic
            concepts: Concepts to teach in this story
            learner_name: Name of the learner (main character)
            learner_level: Proficiency level
            age_band: Age group (child/teen/adult)
            character_bible: Learner character description
            concept_characters: List of concept character descriptions
            chapter_number: Current chapter in series
            total_chapters: Total chapters in series
            previous_concepts: Concepts covered in previous chapters
            art_style: Visual art style
            custom_focus: Optional custom focus override
            
        Returns:
            List of page dictionaries with educational content
        """
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Build comprehensive prompt
        prompt = self._build_educational_prompt(
            topic=topic,
            topic_category=topic_category,
            concepts=concepts,
            learner_name=learner_name,
            learner_level=learner_level,
            age_band=age_band,
            character_bible=character_bible,
            concept_characters=concept_characters,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            previous_concepts=previous_concepts or [],
            art_style=art_style,
            custom_focus=custom_focus
        )
        
        try:
            logger.info(f"Generating educational story: {topic} (Chapter {chapter_number}/{total_chapters})")
            response_text = await self._call_gemini_with_retry(prompt)
            
            # Parse JSON response
            try:
                story_pages = parse_story_json(response_text)
            except ValueError as e:
                logger.error(f"Failed to parse educational story JSON: {e}")
                logger.debug(f"Raw response (first 1000 chars): {response_text[:1000]}")
                raise ValueError("Failed to generate educational story. Please try again.")
            
            # Enhance scene descriptions with character consistency
            story_pages = self._enhance_educational_scenes(
                story_pages,
                character_bible,
                concept_characters
            )
            
            logger.info(f"Generated {len(story_pages)} educational story pages")
            return story_pages[:10]  # Ensure exactly 10 pages
            
        except ValueError:
            # Re-raise ValueError as-is (from JSON parsing)
            raise
        except Exception as e:
            logger.error(f"Educational story generation failed: {e}")
            raise ExternalServiceException(
                service_name="Gemini AI",
                message=f"Educational story generation failed: {str(e)}",
                is_transient=False
            )
    
    def _build_educational_prompt(
        self,
        topic: str,
        topic_category: TopicCategory,
        concepts: List[str],
        learner_name: str,
        learner_level: LearningLevel,
        age_band: str,
        character_bible: Dict[str, Any],
        concept_characters: List[Dict[str, str]],
        chapter_number: int,
        total_chapters: int,
        previous_concepts: List[str],
        art_style: str,
        custom_focus: Optional[str]
    ) -> str:
        """Build comprehensive prompt for educational story generation."""
        
        vocab_guide = self.VOCABULARY_GUIDANCE.get(age_band, self.VOCABULARY_GUIDANCE["adult"])
        
        # Build concept characters section
        concept_chars_text = ""
        if concept_characters:
            concept_chars_text = "\n".join([
                f"- {char['name']}: {char.get('description', '')} (represents: {char.get('concept_name', 'concept')})"
                for char in concept_characters
            ])
        
        # Build previous concepts section
        previous_text = ""
        if previous_concepts:
            previous_text = f"\nPrevious chapters covered: {', '.join(previous_concepts)}"
        
        return f"""
You are creating an EDUCATIONAL storybook to teach {topic} ({topic_category.value}).

=== CHAPTER CONTEXT ===
Chapter {chapter_number} of {total_chapters}
This chapter's concepts: {', '.join(concepts)}{previous_text}
{f"Custom focus: {custom_focus}" if custom_focus else ""}

=== LEARNER CHARACTER (Main character - use EXACT description in scenes) ===
{character_bible.get('main_character', f'{learner_name}, learner')}

=== CONCEPT CHARACTERS (Personified concepts to help teach) ===
{concept_chars_text or "None"}

=== LEARNER PROFILE ===
Name: {learner_name}
Level: {learner_level.value.upper()}
Age band: {age_band}
Art style: {art_style}

=== VOCABULARY GUIDANCE for {age_band} ===
- Complexity: {vocab_guide['complexity']}
- Sentence length: {vocab_guide['sentence_length']}
- Examples: {vocab_guide['examples']}

=== PEDAGOGICAL STRUCTURE (10 pages) ===
Pages 1-2 (SETUP): Introduce the topic, create context, show why it matters
Pages 3-6 (CORE CONCEPTS): Teach the concepts one at a time with clear examples
  - Each concept gets focused attention
  - Use concept characters to personify abstract ideas
  - Include visual metaphors and analogies
Pages 7-8 (APPLICATION): Show how concepts work together in practice
Pages 9 (REINFORCEMENT): Review and test understanding with a scenario
Page 10 (SUMMARY): Recap key learnings, celebrate progress

=== REQUIREMENTS ===
1. {learner_name} is the MAIN CHARACTER learning throughout
2. Each page: 3-5 sentences appropriate for {age_band} level
3. Use concept characters to make abstract ideas tangible
4. Include concrete examples appropriate for {learner_level.value} level
5. Build on previous concepts progressively
6. CRITICAL: In scene_description, ALWAYS describe the learner using EXACT details from character bible
7. For educational scenes, describe the visual representation of concepts clearly

=== OUTPUT FORMAT ===
Return ONLY a JSON array of 10 pages:
[
  {{
    "page_number": 1,
    "text": "Educational story text...",
    "scene_description": "MUST include: [learner's full appearance]. Scene: [educational setting and visual metaphors]",
    "teaching_focus": "What concept this page teaches",
    "concept_characters_in_scene": ["character names if any"],
    "mood": "curious/engaged/excited/thoughtful/confident",
    "pedagogical_type": "setup|concept|application|reinforcement|summary"
  }}
]

IMPORTANT: 
- Start with setup pages (1-2) to create context
- Introduce ONE concept at a time in pages 3-6
- Use visual metaphors that can be illustrated
- Make it engaging but educationally sound
- scene_description MUST include learner's appearance for consistency
"""
    
    def _enhance_educational_scenes(
        self,
        story_pages: List[Dict],
        character_bible: Dict[str, Any],
        concept_characters: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Enhance scene descriptions with character consistency.
        
        Ensures learner and concept characters are consistently described.
        """
        main_char_desc = character_bible.get('main_character', '')
        
        for page in story_pages:
            if 'scene_description' not in page:
                continue
            
            desc = page['scene_description']
            
            # Ensure main character description is prominent
            if main_char_desc and main_char_desc[:30] not in desc:
                page['scene_description'] = f"{main_char_desc}. {desc}"
            
            # Add concept character descriptions if they appear in this scene
            if 'concept_characters_in_scene' in page and page['concept_characters_in_scene']:
                for char_name in page['concept_characters_in_scene']:
                    # Find the character description
                    for char in concept_characters:
                        if char.get('name') == char_name:
                            char_desc = char.get('description', '')
                            if char_desc and char_desc[:20] not in desc:
                                page['scene_description'] += f" Also present: {char_desc}."
                            break
        
        return story_pages
    
    async def generate_chapter_continuation(
        self,
        topic: str,
        topic_category: TopicCategory,
        learner_name: str,
        learner_level: LearningLevel,
        age_band: str,
        character_bible: Dict[str, Any],
        concept_characters: List[Dict[str, str]],
        previous_chapters: List[Dict[str, Any]],
        next_concepts: List[str],
        chapter_number: int,
        total_chapters: int,
        art_style: str = "cartoon"
    ) -> List[Dict]:
        """
        Generate next chapter in a series with continuity.
        
        Args:
            topic: Main topic
            topic_category: Category
            learner_name: Learner's name
            learner_level: Proficiency level
            age_band: Age group
            character_bible: Character descriptions
            concept_characters: Concept character list
            previous_chapters: List of previous chapter data
            next_concepts: Concepts for this chapter
            chapter_number: Current chapter number
            total_chapters: Total chapters
            art_style: Visual style
            
        Returns:
            List of page dictionaries
        """
        # Extract concepts from previous chapters
        previous_concepts = []
        for chapter in previous_chapters:
            chapter_concepts = chapter.get('concepts_covered', [])
            previous_concepts.extend(chapter_concepts)
        
        # Add continuity prompt
        continuity_note = f"""
CONTINUITY NOTE:
This is Chapter {chapter_number} in an ongoing learning journey.
- Previous chapters taught: {', '.join(previous_concepts)}
- Reference these concepts naturally when relevant
- Build on established knowledge
- Maintain same characters and visual style
"""
        
        return await self.generate_educational_story(
            topic=topic,
            topic_category=topic_category,
            concepts=next_concepts,
            learner_name=learner_name,
            learner_level=learner_level,
            age_band=age_band,
            character_bible=character_bible,
            concept_characters=concept_characters,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            previous_concepts=previous_concepts,
            art_style=art_style,
            custom_focus=continuity_note
        )
