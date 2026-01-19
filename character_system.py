# character_system.py
"""
GoldenTales Character Consistency System
========================================
Ensures characters look identical across all pages by:
1. Collecting detailed character attributes upfront
2. Generating a "character bible" description
3. Using consistent prompts with full descriptions on every page
4. Supporting photo-based character extraction
5. Managing multiple characters (siblings, pets, etc.)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from enum import Enum
import json


# ============================================
# CHARACTER ATTRIBUTE ENUMS
# ============================================

class Gender(str, Enum):
    BOY = "boy"
    GIRL = "girl"
    
class SkinTone(str, Enum):
    VERY_LIGHT = "very light/pale skin"
    LIGHT = "light skin"
    MEDIUM_LIGHT = "light olive/medium-light skin"
    MEDIUM = "medium/olive skin"
    MEDIUM_DARK = "medium-dark/tan skin"
    DARK = "dark brown skin"
    VERY_DARK = "very dark/deep brown skin"

class HairColor(str, Enum):
    BLACK = "black hair"
    DARK_BROWN = "dark brown hair"
    BROWN = "brown hair"
    LIGHT_BROWN = "light brown hair"
    AUBURN = "auburn/reddish-brown hair"
    RED = "red/ginger hair"
    STRAWBERRY_BLONDE = "strawberry blonde hair"
    BLONDE = "blonde hair"
    PLATINUM = "platinum/white blonde hair"
    GRAY = "gray hair"
    WHITE = "white hair"

class HairStyle(str, Enum):
    # Short styles
    BUZZ = "very short buzz cut"
    SHORT_NEAT = "short neat hair"
    SHORT_MESSY = "short messy/tousled hair"
    SHORT_CURLY = "short curly hair"
    
    # Medium styles
    MEDIUM_STRAIGHT = "medium-length straight hair"
    MEDIUM_WAVY = "medium-length wavy hair"
    MEDIUM_CURLY = "medium-length curly hair"
    BOB = "bob haircut"
    
    # Long styles
    LONG_STRAIGHT = "long straight hair"
    LONG_WAVY = "long wavy hair"
    LONG_CURLY = "long curly hair"
    
    # Styled
    PONYTAIL = "hair in a ponytail"
    PIGTAILS = "hair in pigtails"
    BRAIDS = "hair in braids"
    BUN = "hair in a bun"
    AFRO = "afro hairstyle"
    LOCS = "locs/dreadlocks"

class EyeColor(str, Enum):
    BROWN = "brown eyes"
    DARK_BROWN = "dark brown eyes"
    HAZEL = "hazel eyes"
    GREEN = "green eyes"
    BLUE = "blue eyes"
    GRAY = "gray eyes"
    AMBER = "amber eyes"

class BodyType(str, Enum):
    SLIM = "slim build"
    AVERAGE = "average build"
    ATHLETIC = "athletic build"
    STOCKY = "stocky/sturdy build"
    CHUBBY = "chubby/round build"


# ============================================
# CHARACTER MODELS
# ============================================

class CharacterAccessories(BaseModel):
    """Optional accessories that should appear consistently."""
    glasses: bool = False
    glasses_type: Optional[str] = None  # "round", "rectangular", etc.
    headwear: Optional[str] = None  # "red bow", "blue cap", etc.
    jewelry: Optional[str] = None
    other: Optional[str] = None  # "hearing aid", "wheelchair", etc.

class CharacterClothing(BaseModel):
    """Default clothing style for consistency."""
    style: Optional[str] = None  # "casual", "formal", "sporty"
    favorite_color: Optional[str] = None
    specific_outfit: Optional[str] = None  # "red dress with white polka dots"

class DistinctiveFeatures(BaseModel):
    """Unique identifying features."""
    freckles: bool = False
    dimples: bool = False
    birthmark: Optional[str] = None  # "small birthmark on left cheek"
    gap_teeth: bool = False
    other: Optional[str] = None

class MainCharacter(BaseModel):
    """The hero of the story - the child the book is for."""
    name: str = Field(..., min_length=1, max_length=30)
    gender: Gender
    age: int = Field(..., ge=2, le=12)
    
    # Physical appearance
    skin_tone: SkinTone
    hair_color: HairColor
    hair_style: HairStyle
    eye_color: EyeColor
    body_type: BodyType = BodyType.AVERAGE
    
    # Optional details
    accessories: Optional[CharacterAccessories] = None
    clothing: Optional[CharacterClothing] = None
    distinctive_features: Optional[DistinctiveFeatures] = None
    
    # Photo reference
    photo_url: Optional[str] = None
    photo_description: Optional[str] = None  # AI-extracted description from photo

class AdditionalCharacterType(str, Enum):
    SIBLING = "sibling"
    PARENT = "parent"
    GRANDPARENT = "grandparent"
    FRIEND = "friend"
    PET = "pet"
    IMAGINARY = "imaginary friend"
    OTHER = "other"

class AdditionalCharacter(BaseModel):
    """Supporting characters in the story."""
    name: str = Field(..., min_length=1, max_length=30)
    character_type: AdditionalCharacterType
    relationship: str  # "little sister", "best friend", "pet dog"
    
    # For humans
    gender: Optional[Gender] = None
    age_description: Optional[str] = None  # "toddler", "teenager", "elderly"
    skin_tone: Optional[SkinTone] = None
    hair_color: Optional[HairColor] = None
    hair_style: Optional[HairStyle] = None
    
    # For pets
    pet_species: Optional[str] = None  # "golden retriever", "tabby cat"
    pet_color: Optional[str] = None  # "golden fur", "orange and white stripes"
    
    # Common
    distinctive_feature: Optional[str] = None  # "always wears a blue bow"


# ============================================
# EDUCATIONAL CONCEPT CHARACTERS
# ============================================

class ConceptCharacterType(str, Enum):
    """Types of conceptual characters in educational stories."""
    AGENT = "agent"                 # Active entity (e.g., RL agent)
    ENVIRONMENT = "environment"     # Context/setting (e.g., maze, market)
    PROCESS = "process"             # Actions/transformations (e.g., photosynthesis)
    ENTITY = "entity"               # Objects/concepts (e.g., neuron, atom)
    GUIDE = "guide"                 # Teacher/mentor character


class ConceptCharacter(BaseModel):
    """
    Character representing an abstract concept in educational stories.
    
    These characters personify concepts to make them easier to understand.
    For example, in a story about reinforcement learning:
    - "Agent Alpha" (agent type) represents the learning agent
    - "Rewardy" (entity type) represents reward signals
    - "Professor Pi" (guide type) explains concepts
    """
    name: str = Field(..., min_length=1, max_length=100)
    character_type: ConceptCharacterType
    concept_name: str = Field(..., min_length=1, max_length=200)  # The concept it represents
    
    # Visual description
    visual_form: str  # "friendly robot", "glowing orb", "wise owl"
    primary_colors: List[str] = Field(default_factory=list)  # ["blue", "silver"]
    distinctive_features: str  # "digital display on chest", "sparkles when happy"
    
    # Personality/role
    personality_traits: Optional[str] = None  # "curious, determined"
    role_in_story: Optional[str] = None  # "helps learner understand rewards"
    
    # Consistency tracking
    character_slug: Optional[str] = None  # URL-safe identifier for reuse
    reference_image_url: Optional[str] = None  # Reference image for consistency

class CharacterProfile(BaseModel):
    """Complete character profile for a story."""
    main_character: MainCharacter
    additional_characters: List[AdditionalCharacter] = []
    concept_characters: List[ConceptCharacter] = []  # For educational stories
    
    # Story context
    theme: str
    art_style: str
    book_type: str = "children"  # "children" or "educational"


# ============================================
# CHARACTER DESCRIPTION GENERATOR
# ============================================

class CharacterDescriptionGenerator:
    """
    Generates consistent, detailed character descriptions
    to be used in every image prompt.
    """
    
    @staticmethod
    def generate_main_character_description(char: MainCharacter) -> str:
        """Generate a detailed, consistent description of the main character."""
        
        # Base description
        parts = [
            f"a {char.age}-year-old {char.gender.value}",
            f"named {char.name}",
            f"with {char.skin_tone.value}",
            f"{char.hair_color.value}",
            f"in {char.hair_style.value} style",
            f"and {char.eye_color.value}",
        ]
        
        # Body type if not average
        if char.body_type != BodyType.AVERAGE:
            parts.append(f"with a {char.body_type.value}")
        
        # Accessories
        if char.accessories:
            if char.accessories.glasses:
                glasses_desc = char.accessories.glasses_type or "glasses"
                parts.append(f"wearing {glasses_desc}")
            if char.accessories.headwear:
                parts.append(f"wearing {char.accessories.headwear}")
            if char.accessories.other:
                parts.append(char.accessories.other)
        
        # Distinctive features
        if char.distinctive_features:
            features = []
            if char.distinctive_features.freckles:
                features.append("freckles")
            if char.distinctive_features.dimples:
                features.append("dimples")
            if char.distinctive_features.gap_teeth:
                features.append("a cute gap in front teeth")
            if char.distinctive_features.birthmark:
                features.append(char.distinctive_features.birthmark)
            if char.distinctive_features.other:
                features.append(char.distinctive_features.other)
            if features:
                parts.append(f"with {', '.join(features)}")
        
        # Clothing
        if char.clothing and char.clothing.specific_outfit:
            parts.append(f"wearing {char.clothing.specific_outfit}")
        elif char.clothing and char.clothing.favorite_color:
            parts.append(f"wearing {char.clothing.favorite_color} clothes")
        
        description = ", ".join(parts)
        
        # Add photo description if available
        if char.photo_description:
            description += f". Character based on reference: {char.photo_description}"
        
        return description
    
    @staticmethod
    def generate_additional_character_description(char: AdditionalCharacter) -> str:
        """Generate description for supporting character."""
        
        if char.character_type == AdditionalCharacterType.PET:
            parts = [
                f"{char.name} the {char.pet_species or 'pet'}",
                f"({char.relationship})",
            ]
            if char.pet_color:
                parts.append(f"with {char.pet_color}")
            if char.distinctive_feature:
                parts.append(char.distinctive_feature)
        else:
            parts = [
                f"{char.name}",
                f"({char.relationship})",
            ]
            if char.age_description:
                parts.append(f"a {char.age_description}")
            if char.gender:
                parts.append(char.gender.value)
            if char.skin_tone:
                parts.append(f"with {char.skin_tone.value}")
            if char.hair_color:
                parts.append(f"{char.hair_color.value}")
            if char.distinctive_feature:
                parts.append(char.distinctive_feature)
        
        return " ".join(parts)
    
    @staticmethod
    def generate_concept_character_description(char: ConceptCharacter) -> str:
        """
        Generate description for a concept character.
        
        These characters represent abstract concepts in educational stories.
        """
        parts = [
            f"{char.name}",
            f"(represents: {char.concept_name})",
            f"appears as {char.visual_form}",
        ]
        
        if char.primary_colors:
            parts.append(f"in {' and '.join(char.primary_colors)} colors")
        
        if char.distinctive_features:
            parts.append(f"with {char.distinctive_features}")
        
        if char.personality_traits:
            parts.append(f"personality: {char.personality_traits}")
        
        return ", ".join(parts)
    
    @classmethod
    def generate_full_character_bible(cls, profile: CharacterProfile) -> Dict[str, str]:
        """
        Generate complete character descriptions for use in prompts.
        Returns a dict that should be included in EVERY image generation.
        """
        
        main_desc = cls.generate_main_character_description(profile.main_character)
        
        additional_descs = []
        for char in profile.additional_characters:
            additional_descs.append(cls.generate_additional_character_description(char))
        
        concept_descs = []
        for char in profile.concept_characters:
            concept_descs.append(cls.generate_concept_character_description(char))
        
        # Build summary with all character types
        summary_parts = [main_desc]
        if additional_descs:
            summary_parts.append("Also featuring: " + "; ".join(additional_descs))
        if concept_descs:
            summary_parts.append("Concept characters: " + "; ".join(concept_descs))
        
        # Create the "character bible" - this goes in every prompt
        character_bible = {
            "main_character": main_desc,
            "main_character_short": f"{profile.main_character.name}, {profile.main_character.age}-year-old {profile.main_character.gender.value}",
            "additional_characters": additional_descs,
            "concept_characters": concept_descs,
            "all_characters_summary": ". ".join(summary_parts)
        }
        
        return character_bible
    
    @classmethod
    def build_page_prompt(
        cls,
        character_bible: Dict[str, str],
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        include_additional_characters: List[str] = None  # Names of additional chars in this scene
    ) -> str:
        """
        Build a complete prompt for a single page that maintains character consistency.
        """
        
        style_descriptions = {
            "watercolor": "soft watercolor illustration style, gentle flowing colors, dreamy brushstrokes",
            "cartoon": "vibrant cartoon illustration, bold outlines, bright cheerful colors, Pixar-inspired",
            "anime": "anime/manga illustration style, expressive features, soft shading, Studio Ghibli inspired",
            "storybook": "classic children's book illustration, warm nostalgic colors, golden age storybook art",
            "pixar": "3D animated style illustration, Pixar-quality, soft lighting, expressive characters",
            "ghibli": "Studio Ghibli style, hand-painted aesthetic, detailed backgrounds, magical atmosphere"
        }
        
        mood_lighting = {
            "happy": "warm golden lighting, bright and cheerful atmosphere",
            "excited": "dynamic lighting, energetic sparkles, vibrant scene",
            "curious": "soft mysterious lighting, sense of wonder",
            "brave": "dramatic heroic lighting, bold atmosphere",
            "peaceful": "soft diffused lighting, calm serene atmosphere",
            "magical": "ethereal glowing light, sparkles and magic particles",
            "cozy": "warm indoor lighting, comfortable inviting atmosphere"
        }
        
        # Build the complete prompt
        prompt_parts = [
            # 1. ALWAYS start with character description for consistency
            f"MAIN CHARACTER (must match exactly): {character_bible['main_character']}",
            
            # 2. Scene and action
            f"\nSCENE: {scene_description}",
            f"ACTION: The main character is {character_action}",
            
            # 3. Additional characters if present
        ]
        
        if include_additional_characters and character_bible.get('additional_characters'):
            for char_desc in character_bible['additional_characters']:
                for name in include_additional_characters:
                    if name.lower() in char_desc.lower():
                        prompt_parts.append(f"ALSO IN SCENE: {char_desc}")
        
        # 4. Style and mood
        prompt_parts.extend([
            f"\nSTYLE: {style_descriptions.get(art_style, style_descriptions['storybook'])}",
            f"MOOD & LIGHTING: {mood_lighting.get(mood, mood_lighting['happy'])}",
            
            # 5. Quality and safety
            "\nQUALITY: Professional children's book illustration, high detail, clear focal point",
            "IMPORTANT: Character appearance must remain EXACTLY consistent - same face, hair, clothes, features",
            
            # 6. Anatomical correctness (CRITICAL for avoiding extra hands/heads)
            "\nANATOMY RULES:",
            "- Exactly TWO hands, each with FIVE fingers",
            "- Exactly ONE head, properly attached to shoulders",
            "- Natural pose with correct body proportions",
            "- Clear separation between character and background",
            "- No overlapping or merged body parts",
            "- Arms connect naturally to torso, hands connect to arms"
        ])
        
        return "\n".join(prompt_parts)


# ============================================
# PHOTO ANALYSIS (Using Gemini Vision)
# ============================================

import re

def _extract_json_from_response(response_text: str) -> Optional[Dict]:
    """
    Extract and parse JSON from LLM response, handling common issues.
    
    Handles:
    - Markdown code blocks (```json ... ```)
    - Extra text before/after JSON
    - Trailing commas
    """
    if not response_text:
        return None
    
    text = response_text.strip()
    
    # Step 1: Remove markdown code blocks
    if text.startswith('```'):
        text = re.sub(r'^```(?:json|JSON)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()
    
    # Step 2: Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Step 3: Extract JSON object using bracket matching
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[start_idx:], start_idx):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                json_text = text[start_idx:i + 1]
                # Fix trailing commas
                json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    return None
    
    return None


async def analyze_photo_for_character(
    photo_url: str,
    gemini_api_key: str
) -> Dict[str, str]:
    """
    Use Gemini Vision to extract character details from a photo.
    Returns a description that can be used for character consistency.
    """
    import google.generativeai as genai
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = """
    Analyze this photo of a child and extract visual characteristics for an illustrated character.
    
    Provide a JSON response with these fields:
    {
        "gender_presentation": "boy" or "girl",
        "estimated_age": number (2-12),
        "skin_tone": "very light" | "light" | "medium-light" | "medium" | "medium-dark" | "dark" | "very dark",
        "hair_color": "black" | "dark brown" | "brown" | "light brown" | "auburn" | "red" | "blonde" | "platinum",
        "hair_style": description of hair style and length,
        "eye_color": "brown" | "hazel" | "green" | "blue" | "gray" (if visible),
        "distinctive_features": list of notable features like "freckles", "dimples", "glasses", "gap teeth",
        "overall_description": A 2-3 sentence description suitable for an illustrator
    }
    
    Return ONLY valid JSON, no markdown, no extra text.
    """
    
    try:
        # Download image and convert to base64
        import httpx
        import base64
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_response = await client.get(photo_url)
            if img_response.status_code != 200:
                print(f"Photo download failed: HTTP {img_response.status_code}")
                return {
                    "overall_description": "Unable to download photo, using default character design"
                }
            image_data = base64.b64encode(img_response.content).decode('utf-8')
        
        # Determine mime type from URL or default to jpeg
        mime_type = "image/jpeg"
        if photo_url.lower().endswith('.png'):
            mime_type = "image/png"
        elif photo_url.lower().endswith('.webp'):
            mime_type = "image/webp"
        
        # Analyze with Gemini
        response = await model.generate_content_async([
            prompt,
            {"mime_type": mime_type, "data": image_data}
        ])
        
        # Use robust JSON extraction
        result = _extract_json_from_response(response.text)
        
        if result is None:
            print(f"Photo analysis: Could not parse JSON from response")
            print(f"Raw response (first 500 chars): {response.text[:500] if response.text else 'empty'}")
            return {
                "overall_description": "Unable to analyze photo, using default character design"
            }
        
        return result
        
    except Exception as e:
        print(f"Photo analysis error: {e}")
        return {
            "overall_description": "Unable to analyze photo, using default character design"
        }


# ============================================
# API REQUEST/RESPONSE MODELS
# ============================================

class CreateCharacterRequest(BaseModel):
    """Request to create a character profile."""
    
    # Required fields
    name: str = Field(..., min_length=1, max_length=30)
    gender: Gender
    age: int = Field(..., ge=2, le=12)
    
    # Physical appearance
    skin_tone: SkinTone
    hair_color: HairColor
    hair_style: HairStyle
    eye_color: EyeColor = EyeColor.BROWN
    body_type: BodyType = BodyType.AVERAGE
    
    # Optional
    has_glasses: bool = False
    glasses_type: Optional[str] = None
    has_freckles: bool = False
    has_dimples: bool = False
    other_features: Optional[str] = None
    
    favorite_color: Optional[str] = None
    
    # Photo
    photo_url: Optional[str] = None
    
    # Additional characters
    additional_characters: List[Dict] = []
    
    # Story settings
    theme: str = "christmas"
    art_style: str = "watercolor"

class AddCharacterRequest(BaseModel):
    """Request to add an additional character."""
    name: str
    character_type: AdditionalCharacterType
    relationship: str  # "little sister", "pet dog"
    
    # For humans
    gender: Optional[Gender] = None
    age_description: Optional[str] = None
    skin_tone: Optional[SkinTone] = None
    hair_color: Optional[HairColor] = None
    
    # For pets
    pet_species: Optional[str] = None
    pet_color: Optional[str] = None
    
    distinctive_feature: Optional[str] = None


# ============================================
# HELPER FUNCTIONS
# ============================================

def create_character_profile_from_request(request: CreateCharacterRequest) -> CharacterProfile:
    """Convert API request to CharacterProfile."""
    
    # Build accessories
    accessories = None
    if request.has_glasses or request.other_features:
        accessories = CharacterAccessories(
            glasses=request.has_glasses,
            glasses_type=request.glasses_type,
            other=request.other_features
        )
    
    # Build distinctive features
    distinctive = None
    if request.has_freckles or request.has_dimples:
        distinctive = DistinctiveFeatures(
            freckles=request.has_freckles,
            dimples=request.has_dimples
        )
    
    # Build clothing
    clothing = None
    if request.favorite_color:
        clothing = CharacterClothing(favorite_color=request.favorite_color)
    
    # Create main character
    main_char = MainCharacter(
        name=request.name,
        gender=request.gender,
        age=request.age,
        skin_tone=request.skin_tone,
        hair_color=request.hair_color,
        hair_style=request.hair_style,
        eye_color=request.eye_color,
        body_type=request.body_type,
        accessories=accessories,
        distinctive_features=distinctive,
        clothing=clothing,
        photo_url=request.photo_url
    )
    
    # Process additional characters
    additional = []
    for char_data in request.additional_characters:
        additional.append(AdditionalCharacter(**char_data))
    
    return CharacterProfile(
        main_character=main_char,
        additional_characters=additional,
        theme=request.theme,
        art_style=request.art_style
    )


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Example: Create a character profile
    profile = CharacterProfile(
        main_character=MainCharacter(
            name="Emma",
            gender=Gender.GIRL,
            age=6,
            skin_tone=SkinTone.LIGHT,
            hair_color=HairColor.BROWN,
            hair_style=HairStyle.PIGTAILS,
            eye_color=EyeColor.BLUE,
            accessories=CharacterAccessories(glasses=True, glasses_type="small round pink glasses"),
            distinctive_features=DistinctiveFeatures(freckles=True, dimples=True),
            clothing=CharacterClothing(favorite_color="purple")
        ),
        additional_characters=[
            AdditionalCharacter(
                name="Max",
                character_type=AdditionalCharacterType.PET,
                relationship="pet dog",
                pet_species="golden retriever puppy",
                pet_color="fluffy golden fur",
                distinctive_feature="wearing a red collar with a star tag"
            ),
            AdditionalCharacter(
                name="Lily",
                character_type=AdditionalCharacterType.SIBLING,
                relationship="little sister",
                gender=Gender.GIRL,
                age_description="toddler (3 years old)",
                skin_tone=SkinTone.LIGHT,
                hair_color=HairColor.BLONDE,
                distinctive_feature="always carries a stuffed bunny"
            )
        ],
        theme="christmas",
        art_style="watercolor"
    )
    
    # Generate character bible
    generator = CharacterDescriptionGenerator()
    bible = generator.generate_full_character_bible(profile)
    
    print("=" * 60)
    print("CHARACTER BIBLE")
    print("=" * 60)
    print(f"\nMain Character:\n{bible['main_character']}")
    print(f"\nAdditional Characters:")
    for desc in bible['additional_characters']:
        print(f"  - {desc}")
    print(f"\nFull Summary:\n{bible['all_characters_summary']}")
    
    # Generate a page prompt
    print("\n" + "=" * 60)
    print("SAMPLE PAGE PROMPT")
    print("=" * 60)
    
    page_prompt = generator.build_page_prompt(
        character_bible=bible,
        scene_description="A cozy living room decorated for Christmas with a sparkling tree and warm fireplace",
        character_action="excitedly opening a magical glowing present, eyes wide with wonder",
        mood="magical",
        art_style="watercolor",
        page_number=5,
        include_additional_characters=["Max", "Lily"]
    )
    print(page_prompt)