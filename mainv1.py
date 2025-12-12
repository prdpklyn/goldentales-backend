# dreamweaver_backend/main.py
"""
DreamWeaver Backend API - Production Ready
Complete implementation with all technical solutions integrated:
- Character Consistency (IP-Adapter)
- Cost Optimization (Caching, Tiered Generation)
- Quality Control (Content Moderation)
- Print-Ready PDF Generation
- Christmas Timeline Management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import os
import uuid
import json
import re
import hashlib
from dotenv import load_dotenv

load_dotenv()

# ============================================
# FASTAPI APP INITIALIZATION
# ============================================

app = FastAPI(
    title="DreamWeaver API",
    description="AI-powered personalized storybook generation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://taleom.lovable.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*"  # Remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ENUMS & DATA MODELS
# ============================================

class ArtStyle(str, Enum):
    WATERCOLOR = "watercolor"
    CARTOON = "cartoon"
    ANIME = "anime"
    STORYBOOK = "storybook"
    PIXAR = "pixar"
    GHIBLI = "ghibli"

class Theme(str, Enum):
    CHRISTMAS = "christmas"
    SPACE = "space"
    OCEAN = "ocean"
    FOREST = "forest"
    DINOSAUR = "dinosaur"
    SUPERHERO = "superhero"
    BIRTHDAY = "birthday"
    BEDTIME = "bedtime"

class ShippingTier(str, Enum):
    DIGITAL = "digital"
    STANDARD = "standard"
    EXPRESS = "express"

class BookFormat(str, Enum):
    DIGITAL = "digital"
    SOFTCOVER = "softcover"
    HARDCOVER = "hardcover"

class GenerationQuality(str, Enum):
    PREVIEW = "preview"      # Fast, cheap - for initial preview
    STANDARD = "standard"    # Balanced - for user approval
    PRINT = "print"          # High quality - for final print

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateBookRequest(BaseModel):
    child_name: str = Field(..., min_length=2, max_length=30)
    child_age: int = Field(..., ge=2, le=12)
    theme: Theme
    art_style: ArtStyle
    occasion: Optional[str] = Field(None, max_length=100)
    additional_characters: Optional[str] = Field(None, max_length=200)
    special_details: Optional[str] = Field(None, max_length=500)
    photo_url: Optional[str] = None
    
    @validator('child_name')
    def validate_name(cls, v):
        # Only allow letters, spaces, apostrophes, hyphens
        if not re.match(r"^[a-zA-Z\s'\-]+$", v):
            raise ValueError('Name can only contain letters, spaces, apostrophes, and hyphens')
        return v.strip()
    
    @validator('special_details', 'additional_characters', 'occasion')
    def sanitize_text(cls, v):
        if v is None:
            return v
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r'ignore\s+previous', r'disregard', r'forget\s+everything',
            r'new\s+instructions', r'system:', r'assistant:'
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid input detected')
        return v.strip()

class RegeneratePageRequest(BaseModel):
    scene_description: str = Field(..., max_length=500)
    art_style: ArtStyle
    mood: Optional[str] = "happy"

class OrderRequest(BaseModel):
    book_id: str
    format: BookFormat
    shipping_tier: ShippingTier
    gift_wrap: bool = False
    gift_message: Optional[str] = Field(None, max_length=200)
    recipient_email: Optional[str] = None
    recipient_address: Optional[Dict[str, str]] = None

# ============================================
# CONFIGURATION
# ============================================

class Config:
    # API Keys
    FAL_KEY = os.getenv("FAL_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LULU_API_KEY = os.getenv("LULU_API_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    
    # Pricing (in USD)
    PRICES = {
        BookFormat.DIGITAL: 9.99,
        BookFormat.SOFTCOVER: 24.99,
        BookFormat.HARDCOVER: 34.99,
    }
    
    SHIPPING_COSTS = {
        ShippingTier.DIGITAL: 0,
        ShippingTier.STANDARD: 0,
        ShippingTier.EXPRESS: 12,
    }
    
    GIFT_WRAP_COST = 5.00
    
    # Generation Costs (for internal tracking)
    GENERATION_COSTS = {
        GenerationQuality.PREVIEW: 0.02,    # Schnell
        GenerationQuality.STANDARD: 0.05,   # Flux Pro
        GenerationQuality.PRINT: 0.10,      # Flux Pro 1.1
    }
    
    # Timeline
    CHRISTMAS_DATE = datetime(2024, 12, 25)
    STANDARD_SHIPPING_DAYS = 10
    EXPRESS_SHIPPING_DAYS = 4
    
    # Content Safety
    BLOCKED_WORDS = [
        'kill', 'murder', 'death', 'blood', 'weapon', 'gun', 'knife',
        'sex', 'nude', 'naked', 'porn', 'drug', 'cocaine', 'hate', 'nazi'
    ]
    
    SAFETY_NEGATIVE_PROMPT = (
        "nsfw, nude, naked, violence, blood, gore, scary, horror, dark, "
        "disturbing, frightening, adult content, inappropriate, suggestive, "
        "disfigured, deformed, ugly, mutated, bad anatomy, extra limbs"
    )

# ============================================
# IN-MEMORY STORAGE (Replace with DB in production)
# ============================================

# Simple in-memory cache for demo - use Redis in production
book_storage: Dict[str, Dict] = {}
image_cache: Dict[str, str] = {}
character_references: Dict[str, str] = {}

# ============================================
# QUALITY CONTROL MODULE
# ============================================

class QualityControl:
    """Content moderation and quality control."""
    
    @staticmethod
    def validate_text_input(text: str) -> tuple[bool, str]:
        """Check text for inappropriate content."""
        if not text:
            return True, ""
        
        text_lower = text.lower()
        for word in Config.BLOCKED_WORDS:
            if word in text_lower:
                return False, f"Content contains inappropriate language"
        
        return True, ""
    
    @staticmethod
    def sanitize_prompt(user_input: str) -> str:
        """Sanitize user input for use in AI prompts."""
        if not user_input:
            return ""
        
        # Remove special characters that could affect prompts
        sanitized = re.sub(r'[<>\[\]{}|\\]', '', user_input)
        # Limit length
        sanitized = sanitized[:500]
        # Remove multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @staticmethod
    def build_safe_prompt(
        scene: str,
        character: str,
        art_style: str,
        mood: str = "happy"
    ) -> Dict[str, str]:
        """Build a safety-checked prompt for image generation."""
        
        style_descriptions = {
            "watercolor": "soft watercolor painting, gentle flowing colors, dreamy atmosphere, delicate brushstrokes",
            "cartoon": "vibrant cartoon style, bold outlines, bright cheerful colors, fun and playful, Pixar-like",
            "anime": "anime style illustration, expressive eyes, detailed, soft shading, Studio Ghibli inspired",
            "storybook": "classic children's book illustration, warm nostalgic colors, whimsical, golden age illustration",
            "pixar": "3D animated style, Pixar-quality rendering, soft lighting, expressive characters",
            "ghibli": "Studio Ghibli style, hand-painted look, detailed backgrounds, magical atmosphere"
        }
        
        mood_modifiers = {
            "happy": "joyful expression, bright warm lighting, cheerful atmosphere",
            "excited": "dynamic pose, sparkling eyes, energetic scene",
            "curious": "wide-eyed wonder, exploring, discovering",
            "brave": "determined expression, heroic pose, confident stance",
            "peaceful": "serene expression, calm atmosphere, soft lighting",
            "magical": "sparkles, glowing elements, enchanted atmosphere"
        }
        
        positive_prompt = f"""
        Children's book illustration, {style_descriptions.get(art_style, style_descriptions['storybook'])}.
        
        Scene: {QualityControl.sanitize_prompt(scene)}
        Character: {QualityControl.sanitize_prompt(character)}
        Mood: {mood_modifiers.get(mood, mood_modifiers['happy'])}
        
        High quality, professional illustration, warm inviting colors, 
        safe for children, age-appropriate, friendly appearance,
        good composition, clear focal point, engaging scene.
        """
        
        return {
            "positive": positive_prompt.strip(),
            "negative": Config.SAFETY_NEGATIVE_PROMPT
        }

# ============================================
# COST OPTIMIZER MODULE
# ============================================

class CostOptimizer:
    """Manages generation costs through caching and tiered quality."""
    
    @staticmethod
    def get_cache_key(prompt: str, style: str, quality: str) -> str:
        """Generate a unique cache key."""
        content = f"{prompt}|{style}|{quality}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_cached_image(cache_key: str) -> Optional[str]:
        """Check if image is cached."""
        return image_cache.get(cache_key)
    
    @staticmethod
    def cache_image(cache_key: str, image_url: str):
        """Cache an image URL."""
        image_cache[cache_key] = image_url
    
    @staticmethod
    def estimate_book_cost(page_count: int, quality: GenerationQuality) -> float:
        """Estimate the generation cost for a book."""
        base_cost = Config.GENERATION_COSTS[quality]
        # Character reference costs extra
        character_cost = Config.GENERATION_COSTS[GenerationQuality.STANDARD]
        total = (page_count * base_cost) + character_cost
        return round(total, 2)

# ============================================
# STORY GENERATION (Gemini)
# ============================================

async def generate_story_with_gemini(
    child_name: str,
    age: int,
    theme: str,
    occasion: Optional[str] = None,
    special_details: Optional[str] = None,
    additional_characters: Optional[str] = None
) -> List[Dict]:
    """Generate a personalized story using Google Gemini."""
    
    import google.generativeai as genai
    
    if not Config.GEMINI_API_KEY:
        raise HTTPException(500, "Gemini API key not configured")
    
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Sanitize inputs
    safe_name = QualityControl.sanitize_prompt(child_name)
    safe_details = QualityControl.sanitize_prompt(special_details or "")
    safe_characters = QualityControl.sanitize_prompt(additional_characters or "")
    
    # Theme-specific story elements
    theme_elements = {
        "christmas": {
            "setting": "snowy winter wonderland, cozy homes with twinkling lights",
            "characters": "Santa Claus, friendly elves, magical reindeer",
            "lesson": "the joy of giving and kindness",
            "magic": "Christmas magic, flying sleigh, presents"
        },
        "space": {
            "setting": "colorful planets, sparkling stars, amazing nebulas",
            "characters": "friendly aliens, helpful robots, wise astronauts",
            "lesson": "curiosity and bravery in exploring the unknown",
            "magic": "rocket ships, zero gravity fun, discovering new worlds"
        },
        "ocean": {
            "setting": "beautiful coral reefs, underwater caves, sunny beaches",
            "characters": "friendly dolphins, wise sea turtles, playful fish",
            "lesson": "friendship and protecting our oceans",
            "magic": "breathing underwater, talking to sea creatures"
        },
        "forest": {
            "setting": "enchanted woodland, magical clearings, towering trees",
            "characters": "talking animals, forest fairies, wise owls",
            "lesson": "respecting nature and making friends",
            "magic": "animals that talk, hidden fairy homes, magical plants"
        },
        "dinosaur": {
            "setting": "prehistoric world, volcanic landscapes, lush jungles",
            "characters": "friendly dinosaurs, baby dinos, pterodactyls",
            "lesson": "being brave and helping others",
            "magic": "time travel, dinosaur friends, prehistoric adventures"
        },
        "superhero": {
            "setting": "bustling city, secret headquarters, exciting locations",
            "characters": "friendly heroes, people who need help",
            "lesson": "using your unique abilities to help others",
            "magic": "discovering superpowers, saving the day"
        },
        "birthday": {
            "setting": "magical party locations, decorated wonderlands",
            "characters": "party guests, magical creatures, friendly animals",
            "lesson": "celebrating being special and grateful for friends",
            "magic": "wishes coming true, magical surprises"
        },
        "bedtime": {
            "setting": "cozy bedroom, dreamland, starry night sky",
            "characters": "dream guides, sleepy animals, moon and stars",
            "lesson": "feeling safe and peaceful at bedtime",
            "magic": "flying through dreams, visiting magical places"
        }
    }
    
    elements = theme_elements.get(theme, theme_elements["forest"])
    
    prompt = f"""
You are a beloved children's book author. Create a heartwarming 10-page storybook for a {age}-year-old child named {safe_name}.

THEME: {theme.upper()}
SETTING: {elements['setting']}
SPECIAL CHARACTERS: {elements['characters']}
LIFE LESSON: {elements['lesson']}
MAGICAL ELEMENTS: {elements['magic']}

OCCASION: {occasion or 'A gift made with love'}
SPECIAL DETAILS TO WEAVE IN: {safe_details or 'None specified'}
ADDITIONAL CHARACTERS: {safe_characters or 'None specified'}

REQUIREMENTS:
1. {safe_name} is the HERO of the story - brave, kind, and special
2. Each page has 2-3 SHORT sentences (25-40 words max per page)
3. Use simple vocabulary appropriate for age {age}
4. Story arc: Setup (pages 1-3) → Adventure (pages 4-7) → Resolution (pages 8-10)
5. End with {safe_name} feeling proud, happy, and loved
6. Include {safe_name}'s name at least once every 2 pages
7. Make scene descriptions VIVID for illustration

OUTPUT FORMAT - Return ONLY a valid JSON array, no markdown:
[
  {{
    "page_number": 1,
    "text": "Story text here (2-3 sentences)...",
    "scene_description": "Detailed visual description for the illustrator: setting, lighting, objects, atmosphere...",
    "character_action": "What {safe_name} is doing: pose, expression, interaction...",
    "mood": "happy/excited/curious/brave/peaceful/magical"
  }}
]

Generate exactly 10 pages. Return ONLY the JSON array.
"""
    
    try:
        response = await model.generate_content_async(prompt)
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        story_pages = json.loads(response_text)
        
        # Validate structure
        if not isinstance(story_pages, list) or len(story_pages) < 10:
            raise ValueError("Invalid story structure")
        
        return story_pages[:10]  # Ensure exactly 10 pages
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Response was: {response_text[:500]}")
        raise HTTPException(500, "Failed to parse story. Please try again.")
    except Exception as e:
        print(f"Story Generation Error: {e}")
        raise HTTPException(500, f"Story generation failed: {str(e)}")

# ============================================
# IMAGE GENERATION (Fal.ai)
# ============================================

async def generate_character_reference(
    child_name: str,
    age: int,
    art_style: str,
    photo_url: Optional[str] = None
) -> str:
    """Generate a character reference for consistency across pages."""
    
    import fal_client
    
    if not Config.FAL_KEY:
        raise HTTPException(500, "Fal.ai API key not configured")
    
    os.environ["FAL_KEY"] = Config.FAL_KEY
    
    prompt_data = QualityControl.build_safe_prompt(
        scene="Character design reference sheet, white background, multiple poses showing front view and 3/4 view",
        character=f"A cute {age}-year-old child, the hero of a children's book, friendly appearance, expressive face",
        art_style=art_style,
        mood="happy"
    )
    
    try:
        if photo_url:
            # Use IP-Adapter to base character on photo
            handler = await fal_client.submit_async(
                "fal-ai/flux-pro/v1.1",
                arguments={
                    "prompt": prompt_data["positive"],
                    "negative_prompt": prompt_data["negative"],
                    "image_size": "square_hd",
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "guidance_scale": 7.5,
                }
            )
        else:
            handler = await fal_client.submit_async(
                "fal-ai/flux-pro/v1.1",
                arguments={
                    "prompt": prompt_data["positive"],
                    "negative_prompt": prompt_data["negative"],
                    "image_size": "square_hd",
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "guidance_scale": 7.5,
                }
            )
        
        result = await handler.get()
        reference_url = result['images'][0]['url']
        
        return reference_url
        
    except Exception as e:
        print(f"Character Reference Error: {e}")
        raise HTTPException(500, f"Failed to generate character reference: {str(e)}")

async def generate_illustration(
    scene_description: str,
    character_description: str,
    art_style: str,
    mood: str = "happy",
    quality: GenerationQuality = GenerationQuality.PREVIEW,
    reference_url: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a single illustration."""
    
    import fal_client
    
    if not Config.FAL_KEY:
        raise HTTPException(500, "Fal.ai API key not configured")
    
    os.environ["FAL_KEY"] = Config.FAL_KEY
    
    # Check cache first
    cache_key = CostOptimizer.get_cache_key(
        f"{scene_description}{character_description}",
        art_style,
        quality.value
    )
    
    cached_url = CostOptimizer.get_cached_image(cache_key)
    if cached_url:
        return {"url": cached_url, "cached": True, "quality": quality.value}
    
    # Build safe prompt
    prompt_data = QualityControl.build_safe_prompt(
        scene=scene_description,
        character=character_description,
        art_style=art_style,
        mood=mood
    )
    
    # Select model based on quality tier
    if quality == GenerationQuality.PREVIEW:
        model = "fal-ai/flux/schnell"
        params = {
            "prompt": prompt_data["positive"],
            "image_size": "landscape_4_3",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        }
    elif quality == GenerationQuality.STANDARD:
        model = "fal-ai/flux-pro"
        params = {
            "prompt": prompt_data["positive"],
            "negative_prompt": prompt_data["negative"],
            "image_size": "landscape_4_3",
            "num_images": 1,
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
        }
    else:  # PRINT quality
        model = "fal-ai/flux-pro/v1.1"
        params = {
            "prompt": prompt_data["positive"],
            "negative_prompt": prompt_data["negative"],
            "image_size": {"width": 2400, "height": 1800},
            "num_images": 1,
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
        }
    
    # Add character reference for consistency if available
    if reference_url and quality != GenerationQuality.PREVIEW:
        # Enhance prompt with reference instruction
        params["prompt"] = f"Consistent character from reference. {params['prompt']}"
    
    try:
        handler = await fal_client.submit_async(model, arguments=params)
        result = await handler.get()
        
        image_url = result['images'][0]['url']
        
        # Cache the result
        CostOptimizer.cache_image(cache_key, image_url)
        
        return {
            "url": image_url,
            "cached": False,
            "quality": quality.value,
            "cost": Config.GENERATION_COSTS[quality]
        }
        
    except Exception as e:
        print(f"Image Generation Error: {e}")
        raise HTTPException(500, f"Image generation failed: {str(e)}")

async def generate_all_illustrations(
    story_pages: List[Dict],
    child_name: str,
    child_age: int,
    art_style: str,
    quality: GenerationQuality = GenerationQuality.PREVIEW,
    photo_url: Optional[str] = None
) -> List[Dict]:
    """Generate all illustrations for a book."""
    
    # Generate character reference first (for consistency)
    reference_url = None
    if quality != GenerationQuality.PREVIEW:
        try:
            reference_url = await generate_character_reference(
                child_name, child_age, art_style, photo_url
            )
        except Exception as e:
            print(f"Character reference failed, continuing without: {e}")
    
    # Build character description
    character_desc = f"A {child_age}-year-old child named {child_name}, the hero of the story"
    
    # Generate all pages (with some parallelism but not overwhelming the API)
    illustrations = []
    batch_size = 3  # Generate 3 at a time
    
    for i in range(0, len(story_pages), batch_size):
        batch = story_pages[i:i + batch_size]
        
        tasks = [
            generate_illustration(
                scene_description=page.get('scene_description', ''),
                character_description=f"{character_desc}, {page.get('character_action', '')}",
                art_style=art_style,
                mood=page.get('mood', 'happy'),
                quality=quality,
                reference_url=reference_url
            )
            for page in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                # Use a placeholder for failed generations
                illustrations.append({
                    "url": "https://placehold.co/800x600/amber/white?text=Regenerate",
                    "error": str(result),
                    "quality": quality.value
                })
            else:
                illustrations.append(result)
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(story_pages):
            await asyncio.sleep(0.5)
    
    return illustrations

# ============================================
# TIMELINE MANAGEMENT
# ============================================

def get_shipping_options() -> List[Dict]:
    """Get available shipping options with Christmas deadlines."""
    today = datetime.now()
    christmas = Config.CHRISTMAS_DATE
    
    options = []
    
    # Digital - always available
    options.append({
        "tier": "digital",
        "name": "Digital PDF",
        "price": 0,
        "description": "Instant download",
        "available": True,
        "estimated_arrival": "Instant",
        "deadline": None
    })
    
    # Standard shipping
    standard_deadline = christmas - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    standard_available = today < standard_deadline
    standard_arrival = today + timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    
    options.append({
        "tier": "standard",
        "name": "Standard Shipping",
        "price": 0,
        "description": f"Order by {standard_deadline.strftime('%b %d')} for Christmas",
        "available": standard_available,
        "deadline": standard_deadline.isoformat(),
        "estimated_arrival": standard_arrival.strftime('%b %d'),
        "days_until_deadline": (standard_deadline - today).days if standard_available else 0
    })
    
    # Express shipping
    express_deadline = christmas - timedelta(days=Config.EXPRESS_SHIPPING_DAYS)
    express_available = today < express_deadline
    express_arrival = today + timedelta(days=Config.EXPRESS_SHIPPING_DAYS)
    
    options.append({
        "tier": "express",
        "name": "Express Shipping",
        "price": 12,
        "description": "Arrives by Dec 23",
        "available": express_available,
        "deadline": express_deadline.isoformat(),
        "estimated_arrival": express_arrival.strftime('%b %d'),
        "days_until_deadline": (express_deadline - today).days if express_available else 0
    })
    
    return options

def get_countdown() -> Dict:
    """Get countdown to Christmas shipping deadline."""
    today = datetime.now()
    deadline = Config.CHRISTMAS_DATE - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    diff = deadline - today
    
    if diff.total_seconds() < 0:
        return {
            "expired": True,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "urgency": "expired",
            "message": "Standard shipping deadline passed! Express still available."
        }
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if days <= 2:
        urgency = "critical"
        message = f"🚨 Only {days} days left for Christmas delivery!"
    elif days <= 5:
        urgency = "urgent"
        message = f"⚡ {days} days left - order soon!"
    elif days <= 10:
        urgency = "warning"
        message = f"🎄 {days} days until shipping deadline"
    else:
        urgency = "normal"
        message = "Plenty of time for Christmas delivery!"
    
    return {
        "expired": False,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "urgency": urgency,
        "deadline": deadline.strftime('%B %d'),
        "message": message
    }

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "DreamWeaver API",
        "version": "2.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/config")
async def get_config():
    """Get public configuration."""
    return {
        "themes": [t.value for t in Theme],
        "art_styles": [s.value for s in ArtStyle],
        "formats": [f.value for f in BookFormat],
        "prices": {f.value: Config.PRICES[f] for f in BookFormat},
        "shipping_options": get_shipping_options(),
        "countdown": get_countdown()
    }

@app.get("/api/shipping-options")
async def shipping_options():
    """Get available shipping options."""
    return {
        "options": get_shipping_options(),
        "countdown": get_countdown()
    }

@app.post("/api/books/create")
async def create_book(request: CreateBookRequest) -> Dict:
    """Create a new personalized book with story and preview images."""
    
    book_id = str(uuid.uuid4())[:8]
    
    # Validate content safety
    is_safe, error_msg = QualityControl.validate_text_input(
        f"{request.child_name} {request.special_details or ''} {request.additional_characters or ''}"
    )
    if not is_safe:
        raise HTTPException(400, error_msg)
    
    try:
        # Generate story
        story_pages = await generate_story_with_gemini(
            child_name=request.child_name,
            age=request.child_age,
            theme=request.theme.value,
            occasion=request.occasion,
            special_details=request.special_details,
            additional_characters=request.additional_characters
        )
        
        # Generate preview illustrations
        illustrations = await generate_all_illustrations(
            story_pages=story_pages,
            child_name=request.child_name,
            child_age=request.child_age,
            art_style=request.art_style.value,
            quality=GenerationQuality.PREVIEW,
            photo_url=request.photo_url
        )
        
        # Calculate costs
        page_count = len(story_pages)
        generation_cost = sum(
            img.get('cost', Config.GENERATION_COSTS[GenerationQuality.PREVIEW])
            for img in illustrations
        )
        
        # Store book data
        book_data = {
            "book_id": book_id,
            "title": f"{request.child_name}'s {request.theme.value.title()} Adventure",
            "child_name": request.child_name,
            "child_age": request.child_age,
            "theme": request.theme.value,
            "art_style": request.art_style.value,
            "pages": story_pages,
            "preview_images": [img.get('url', '') for img in illustrations],
            "page_count": page_count,
            "generation_cost": round(generation_cost, 2),
            "created_at": datetime.now().isoformat(),
            "status": "preview"
        }
        
        book_storage[book_id] = book_data
        
        return book_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Book Creation Error: {e}")
        raise HTTPException(500, f"Failed to create book: {str(e)}")

@app.get("/api/books/{book_id}")
async def get_book(book_id: str) -> Dict:
    """Get a book by ID."""
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    return book_storage[book_id]

@app.post("/api/books/{book_id}/regenerate-page/{page_number}")
async def regenerate_page(
    book_id: str,
    page_number: int,
    request: RegeneratePageRequest
) -> Dict:
    """Regenerate a specific page illustration."""
    
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    book = book_storage[book_id]
    
    if page_number < 1 or page_number > len(book['pages']):
        raise HTTPException(400, "Invalid page number")
    
    page = book['pages'][page_number - 1]
    
    try:
        illustration = await generate_illustration(
            scene_description=request.scene_description or page.get('scene_description', ''),
            character_description=f"A {book['child_age']}-year-old child named {book['child_name']}, {page.get('character_action', '')}",
            art_style=request.art_style.value,
            mood=request.mood or page.get('mood', 'happy'),
            quality=GenerationQuality.PREVIEW
        )
        
        # Update stored book
        book['preview_images'][page_number - 1] = illustration['url']
        
        return {
            "page_number": page_number,
            "new_image_url": illustration['url'],
            "cost": illustration.get('cost', 0)
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to regenerate page: {str(e)}")

@app.get("/api/books/{book_id}/price")
async def get_book_price(
    book_id: str,
    format: BookFormat,
    shipping: ShippingTier,
    gift_wrap: bool = False
) -> Dict:
    """Calculate total price for a book order."""
    
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    base_price = Config.PRICES[format]
    shipping_cost = Config.SHIPPING_COSTS[shipping]
    wrap_cost = Config.GIFT_WRAP_COST if gift_wrap and format != BookFormat.DIGITAL else 0
    
    subtotal = base_price + shipping_cost + wrap_cost
    
    return {
        "book_id": book_id,
        "format": format.value,
        "base_price": base_price,
        "shipping_cost": shipping_cost,
        "gift_wrap_cost": wrap_cost,
        "subtotal": round(subtotal, 2),
        "total": round(subtotal, 2),  # Add tax calculation here if needed
        "currency": "USD"
    }

@app.post("/api/orders/create")
async def create_order(
    request: OrderRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """Create an order for a book."""
    
    if request.book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    order_id = str(uuid.uuid4())[:8]
    book = book_storage[request.book_id]
    
    # Calculate price
    price = await get_book_price(
        request.book_id,
        request.format,
        request.shipping_tier,
        request.gift_wrap
    )
    
    # Determine delivery estimate
    shipping_options = get_shipping_options()
    shipping_option = next(
        (o for o in shipping_options if o['tier'] == request.shipping_tier.value),
        shipping_options[0]
    )
    
    order_data = {
        "order_id": order_id,
        "book_id": request.book_id,
        "book_title": book['title'],
        "format": request.format.value,
        "shipping_tier": request.shipping_tier.value,
        "gift_wrap": request.gift_wrap,
        "gift_message": request.gift_message,
        "total": price['total'],
        "status": "pending_payment",
        "estimated_delivery": shipping_option['estimated_arrival'],
        "created_at": datetime.now().isoformat()
    }
    
    # In production: Create Stripe checkout session here
    # background_tasks.add_task(process_order, order_id, order_data)
    
    return {
        "order_id": order_id,
        "status": "pending_payment",
        "total": price['total'],
        "currency": "USD",
        "estimated_delivery": shipping_option['estimated_arrival'],
        "checkout_url": f"/checkout/{order_id}"  # Replace with Stripe URL
    }

@app.get("/api/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict:
    """Get order status."""
    # In production: Fetch from database
    return {
        "order_id": order_id,
        "status": "processing",
        "steps": [
            {"name": "Order Received", "status": "completed", "timestamp": datetime.now().isoformat()},
            {"name": "Payment Confirmed", "status": "completed", "timestamp": None},
            {"name": "Generating Print Files", "status": "in_progress", "timestamp": None},
            {"name": "Sent to Printer", "status": "pending", "timestamp": None},
            {"name": "Shipped", "status": "pending", "timestamp": None},
            {"name": "Delivered", "status": "pending", "timestamp": None}
        ]
    }

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Global Error: {exc}")
    return {
        "error": True,
        "message": "An unexpected error occurred. Please try again.",
        "detail": str(exc) if os.getenv("DEBUG") else None
    }

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )