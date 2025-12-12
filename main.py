# dreamweaver_backend/main.py
"""
DreamWeaver Backend API - V2 with Character Consistency
=======================================================
Complete implementation with deep character consistency:
- Detailed character profile collection
- Character bible generation for every prompt
- Photo analysis for reference
- Multiple character support
- Consistent prompts across all pages
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import os
import uuid
import json
import re
import hashlib
from dotenv import load_dotenv

# Import character system
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    AdditionalCharacterType, MainCharacter, AdditionalCharacter,
    CharacterProfile, CharacterAccessories, CharacterClothing,
    DistinctiveFeatures, CharacterDescriptionGenerator,
    CreateCharacterRequest, AddCharacterRequest,
    create_character_profile_from_request, analyze_photo_for_character
)

load_dotenv()

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title="DreamWeaver API",
    description="AI-powered personalized storybook generation with character consistency",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ENUMS & MODELS
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
    PREVIEW = "preview"
    STANDARD = "standard"
    PRINT = "print"

# ============================================
# REQUEST MODELS
# ============================================

class CreateBookRequest(BaseModel):
    """Full book creation request with character details."""
    
    # Main character - REQUIRED
    child_name: str = Field(..., min_length=2, max_length=30)
    child_gender: Gender
    child_age: int = Field(..., ge=2, le=12)
    
    # Physical appearance - REQUIRED for consistency
    skin_tone: SkinTone
    hair_color: HairColor
    hair_style: HairStyle
    eye_color: EyeColor = EyeColor.BROWN
    body_type: BodyType = BodyType.AVERAGE
    
    # Optional appearance details
    has_glasses: bool = False
    glasses_type: Optional[str] = None  # "round pink glasses"
    has_freckles: bool = False
    has_dimples: bool = False
    other_features: Optional[str] = None  # "birthmark on cheek"
    favorite_outfit: Optional[str] = None  # "red dress with white dots"
    favorite_color: Optional[str] = None
    
    # Photo reference
    photo_url: Optional[str] = None
    
    # Additional characters
    additional_characters: List[AddCharacterRequest] = []
    
    # Story settings
    theme: Theme
    art_style: ArtStyle
    occasion: Optional[str] = None
    special_details: Optional[str] = None
    
    @validator('child_name')
    def validate_name(cls, v):
        if not re.match(r"^[a-zA-Z\s'\-]+$", v):
            raise ValueError('Name can only contain letters')
        return v.strip()

class RegeneratePageRequest(BaseModel):
    """Request to regenerate a specific page."""
    scene_description: Optional[str] = None
    character_action: Optional[str] = None
    mood: Optional[str] = "happy"
    include_characters: Optional[List[str]] = None  # Names of additional chars

class OrderRequest(BaseModel):
    book_id: str
    format: BookFormat
    shipping_tier: ShippingTier
    gift_wrap: bool = False
    gift_message: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_address: Optional[Dict[str, str]] = None

# ============================================
# CONFIGURATION
# ============================================

class Config:
    FAL_KEY = os.getenv("FAL_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LULU_API_KEY = os.getenv("LULU_API_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    
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
    
    GENERATION_COSTS = {
        GenerationQuality.PREVIEW: 0.02,
        GenerationQuality.STANDARD: 0.05,
        GenerationQuality.PRINT: 0.10,
    }
    
    CHRISTMAS_DATE = datetime(2024, 12, 25)
    STANDARD_SHIPPING_DAYS = 10
    EXPRESS_SHIPPING_DAYS = 4
    
    SAFETY_NEGATIVE_PROMPT = (
        "nsfw, nude, violence, blood, scary, horror, dark, disturbing, "
        "disfigured, deformed, ugly, mutated, bad anatomy, extra limbs, "
        "blurry, low quality, watermark, text, signature"
    )

# ============================================
# STORAGE (Replace with DB)
# ============================================

book_storage: Dict[str, Dict] = {}
character_profiles: Dict[str, CharacterProfile] = {}
character_bibles: Dict[str, Dict[str, str]] = {}

# ============================================
# CHARACTER PROFILE MANAGEMENT
# ============================================

async def create_character_profile(request: CreateBookRequest) -> tuple[CharacterProfile, Dict[str, str]]:
    """
    Create a complete character profile and generate the character bible.
    This bible will be used in EVERY image generation for consistency.
    """
    
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
    if request.has_freckles or request.has_dimples or request.other_features:
        distinctive = DistinctiveFeatures(
            freckles=request.has_freckles,
            dimples=request.has_dimples,
            other=request.other_features
        )
    
    # Build clothing preferences
    clothing = None
    if request.favorite_outfit or request.favorite_color:
        clothing = CharacterClothing(
            specific_outfit=request.favorite_outfit,
            favorite_color=request.favorite_color
        )
    
    # Analyze photo if provided
    photo_description = None
    if request.photo_url and Config.GEMINI_API_KEY:
        try:
            photo_analysis = await analyze_photo_for_character(
                request.photo_url, 
                Config.GEMINI_API_KEY
            )
            photo_description = photo_analysis.get('overall_description')
        except Exception as e:
            print(f"Photo analysis failed: {e}")
    
    # Create main character
    main_character = MainCharacter(
        name=request.child_name,
        gender=request.child_gender,
        age=request.child_age,
        skin_tone=request.skin_tone,
        hair_color=request.hair_color,
        hair_style=request.hair_style,
        eye_color=request.eye_color,
        body_type=request.body_type,
        accessories=accessories,
        distinctive_features=distinctive,
        clothing=clothing,
        photo_url=request.photo_url,
        photo_description=photo_description
    )
    
    # Process additional characters
    additional_chars = []
    for char_req in request.additional_characters:
        additional_chars.append(AdditionalCharacter(
            name=char_req.name,
            character_type=char_req.character_type,
            relationship=char_req.relationship,
            gender=char_req.gender,
            age_description=char_req.age_description,
            skin_tone=char_req.skin_tone,
            hair_color=char_req.hair_color,
            pet_species=char_req.pet_species,
            pet_color=char_req.pet_color,
            distinctive_feature=char_req.distinctive_feature
        ))
    
    # Create profile
    profile = CharacterProfile(
        main_character=main_character,
        additional_characters=additional_chars,
        theme=request.theme.value,
        art_style=request.art_style.value
    )
    
    # Generate character bible
    generator = CharacterDescriptionGenerator()
    bible = generator.generate_full_character_bible(profile)
    
    return profile, bible

# ============================================
# STORY GENERATION
# ============================================

async def generate_story_with_gemini(
    character_bible: Dict[str, str],
    child_name: str,
    age: int,
    theme: str,
    occasion: Optional[str] = None,
    special_details: Optional[str] = None,
    additional_characters: List[AdditionalCharacter] = None
) -> List[Dict]:
    """Generate story with character consistency built in."""
    
    import google.generativeai as genai
    
    if not Config.GEMINI_API_KEY:
        raise HTTPException(500, "Gemini API key not configured")
    
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Build additional characters list for story
    additional_chars_text = ""
    if additional_characters:
        chars = []
        for char in additional_characters:
            chars.append(f"- {char.name} ({char.relationship})")
        additional_chars_text = "\n".join(chars)
    
    # Theme elements
    theme_elements = {
        "christmas": "Christmas magic, Santa, elves, snow, presents, giving",
        "space": "planets, stars, rockets, friendly aliens, exploration",
        "ocean": "underwater, dolphins, mermaids, coral reefs, sea creatures",
        "forest": "magical woods, talking animals, fairies, enchanted trees",
        "dinosaur": "prehistoric world, friendly dinosaurs, adventure",
        "superhero": "superpowers, helping others, saving the day",
        "birthday": "celebration, cake, wishes, friends, surprises",
        "bedtime": "dreams, stars, peaceful night, cozy sleep"
    }
    
    prompt = f"""
You are creating a 10-page children's storybook. The main character must be described CONSISTENTLY.

=== MAIN CHARACTER (use this EXACT description in scene descriptions) ===
{character_bible['main_character']}

=== ADDITIONAL CHARACTERS ===
{additional_chars_text or "None"}

=== STORY SETTINGS ===
Theme: {theme.upper()} - {theme_elements.get(theme, '')}
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
    "characters_in_scene": ["{child_name}"] // list names of characters appearing
  }}
]

IMPORTANT: scene_description MUST start with the character's appearance every time!
"""
    
    try:
        response = await model.generate_content_async(prompt)
        response_text = response.text.strip()
        
        # Clean markdown
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        story_pages = json.loads(response_text)
        
        # Ensure character description is in every scene
        for page in story_pages:
            if 'scene_description' in page:
                desc = page['scene_description']
                # If character description isn't prominent, prepend it
                if character_bible['main_character_short'] not in desc:
                    page['scene_description'] = f"{character_bible['main_character']}. {desc}"
        
        return story_pages[:10]
        
    except Exception as e:
        print(f"Story Generation Error: {e}")
        raise HTTPException(500, f"Story generation failed: {str(e)}")

# ============================================
# IMAGE GENERATION WITH CHARACTER CONSISTENCY
# ============================================

async def generate_illustration_with_character(
    character_bible: Dict[str, str],
    scene_description: str,
    character_action: str,
    mood: str,
    art_style: str,
    page_number: int,
    characters_in_scene: List[str] = None,
    quality: GenerationQuality = GenerationQuality.PREVIEW
) -> Dict[str, Any]:
    """
    Generate illustration with full character consistency.
    The character bible is included in EVERY prompt.
    """
    
    import fal_client
    
    if not Config.FAL_KEY:
        raise HTTPException(500, "Fal.ai API key not configured")
    
    os.environ["FAL_KEY"] = Config.FAL_KEY
    
    # Build the complete prompt using the character description generator
    generator = CharacterDescriptionGenerator()
    
    full_prompt = generator.build_page_prompt(
        character_bible=character_bible,
        scene_description=scene_description,
        character_action=character_action,
        mood=mood,
        art_style=art_style,
        page_number=page_number,
        include_additional_characters=characters_in_scene
    )
    
    # Add quality and consistency instructions
    full_prompt += """

CRITICAL CONSISTENCY RULES:
- Character's face, hair, skin tone, and features must match the description EXACTLY
- Same character design as all other pages in this book
- Maintain exact hair color, style, and length
- Keep any accessories (glasses, bows, etc.) consistent
- Same clothing style/colors throughout

OUTPUT: High-quality children's book illustration, professional, vibrant, safe for all ages.
"""
    
    # Select model based on quality
    if quality == GenerationQuality.PREVIEW:
        model = "fal-ai/flux/schnell"
        params = {
            "prompt": full_prompt,
            "image_size": "landscape_4_3",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
            "seed": 42 + page_number,  # Consistent seed per page
        }
    elif quality == GenerationQuality.STANDARD:
        model = "fal-ai/flux-pro"
        params = {
            "prompt": full_prompt,
            "negative_prompt": Config.SAFETY_NEGATIVE_PROMPT,
            "image_size": "landscape_4_3",
            "num_images": 1,
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
            "seed": 42 + page_number,
        }
    else:  # PRINT
        model = "fal-ai/flux-pro/v1.1"
        params = {
            "prompt": full_prompt,
            "negative_prompt": Config.SAFETY_NEGATIVE_PROMPT,
            "image_size": {"width": 2400, "height": 1800},
            "num_images": 1,
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
            "seed": 42 + page_number,
        }
    
    try:
        handler = await fal_client.submit_async(model, arguments=params)
        result = await handler.get()
        
        return {
            "url": result['images'][0]['url'],
            "quality": quality.value,
            "page_number": page_number,
            "cost": Config.GENERATION_COSTS[quality]
        }
        
    except Exception as e:
        print(f"Image Generation Error (page {page_number}): {e}")
        raise HTTPException(500, f"Image generation failed: {str(e)}")

async def generate_all_illustrations(
    character_bible: Dict[str, str],
    story_pages: List[Dict],
    art_style: str,
    quality: GenerationQuality = GenerationQuality.PREVIEW
) -> List[Dict]:
    """Generate all illustrations with character consistency."""
    
    illustrations = []
    batch_size = 3
    
    for i in range(0, len(story_pages), batch_size):
        batch = story_pages[i:i + batch_size]
        
        tasks = [
            generate_illustration_with_character(
                character_bible=character_bible,
                scene_description=page.get('scene_description', ''),
                character_action=page.get('character_action', ''),
                mood=page.get('mood', 'happy'),
                art_style=art_style,
                page_number=page.get('page_number', i + idx + 1),
                characters_in_scene=page.get('characters_in_scene', []),
                quality=quality
            )
            for idx, page in enumerate(batch)
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                illustrations.append({
                    "url": "https://placehold.co/800x600/amber/white?text=Regenerate",
                    "error": str(result)
                })
            else:
                illustrations.append(result)
        
        if i + batch_size < len(story_pages):
            await asyncio.sleep(0.5)
    
    return illustrations

# ============================================
# TIMELINE
# ============================================

def get_shipping_options() -> List[Dict]:
    today = datetime.now()
    christmas = Config.CHRISTMAS_DATE
    
    options = []
    
    options.append({
        "tier": "digital",
        "name": "Digital PDF",
        "price": 0,
        "description": "Instant download",
        "available": True,
        "estimated_arrival": "Instant"
    })
    
    standard_deadline = christmas - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    standard_available = today < standard_deadline
    options.append({
        "tier": "standard",
        "name": "Standard Shipping",
        "price": 0,
        "description": f"Order by {standard_deadline.strftime('%b %d')} for Christmas",
        "available": standard_available,
        "deadline": standard_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=Config.STANDARD_SHIPPING_DAYS)).strftime('%b %d'),
        "days_until_deadline": max(0, (standard_deadline - today).days)
    })
    
    express_deadline = christmas - timedelta(days=Config.EXPRESS_SHIPPING_DAYS)
    express_available = today < express_deadline
    options.append({
        "tier": "express",
        "name": "Express Shipping",
        "price": 12,
        "description": "Fast delivery",
        "available": express_available,
        "deadline": express_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=Config.EXPRESS_SHIPPING_DAYS)).strftime('%b %d'),
        "days_until_deadline": max(0, (express_deadline - today).days)
    })
    
    return options

def get_countdown() -> Dict:
    today = datetime.now()
    deadline = Config.CHRISTMAS_DATE - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    diff = deadline - today
    
    if diff.total_seconds() < 0:
        return {"expired": True, "days": 0, "hours": 0, "minutes": 0, "urgency": "expired"}
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    urgency = "normal"
    if days <= 2: urgency = "critical"
    elif days <= 5: urgency = "urgent"
    elif days <= 10: urgency = "warning"
    
    return {
        "expired": False,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "urgency": urgency,
        "deadline": deadline.strftime('%B %d')
    }

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {"service": "DreamWeaver API", "version": "2.1.0", "status": "healthy"}

@app.get("/api/config")
async def get_config():
    """Get all configuration options for the frontend."""
    return {
        "themes": [t.value for t in Theme],
        "art_styles": [s.value for s in ArtStyle],
        "formats": [f.value for f in BookFormat],
        "prices": {f.value: Config.PRICES[f] for f in BookFormat},
        "shipping_options": get_shipping_options(),
        "countdown": get_countdown(),
        # Character options for the form
        "character_options": {
            "genders": [g.value for g in Gender],
            "skin_tones": [{"value": s.value, "label": s.value} for s in SkinTone],
            "hair_colors": [{"value": h.value, "label": h.value} for h in HairColor],
            "hair_styles": [{"value": h.value, "label": h.value} for h in HairStyle],
            "eye_colors": [{"value": e.value, "label": e.value} for e in EyeColor],
            "body_types": [{"value": b.value, "label": b.value} for b in BodyType],
            "additional_character_types": [t.value for t in AdditionalCharacterType]
        }
    }

@app.get("/api/shipping-options")
async def shipping_options():
    return {"options": get_shipping_options(), "countdown": get_countdown()}

@app.post("/api/books/create")
async def create_book(request: CreateBookRequest) -> Dict:
    """Create a new book with full character consistency."""
    
    book_id = str(uuid.uuid4())[:8]
    
    try:
        # 1. Create character profile and bible
        profile, bible = await create_character_profile(request)
        character_profiles[book_id] = profile
        character_bibles[book_id] = bible
        
        # 2. Generate story with character awareness
        story_pages = await generate_story_with_gemini(
            character_bible=bible,
            child_name=request.child_name,
            age=request.child_age,
            theme=request.theme.value,
            occasion=request.occasion,
            special_details=request.special_details,
            additional_characters=profile.additional_characters
        )
        
        # 3. Generate illustrations with character consistency
        illustrations = await generate_all_illustrations(
            character_bible=bible,
            story_pages=story_pages,
            art_style=request.art_style.value,
            quality=GenerationQuality.PREVIEW
        )
        
        # 4. Store book data
        book_data = {
            "book_id": book_id,
            "title": f"{request.child_name}'s {request.theme.value.title()} Adventure",
            "child_name": request.child_name,
            "child_age": request.child_age,
            "theme": request.theme.value,
            "art_style": request.art_style.value,
            "pages": story_pages,
            "preview_images": [img.get('url', '') for img in illustrations],
            "page_count": len(story_pages),
            "character_bible": bible,  # Store for regeneration
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
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    return book_storage[book_id]

@app.post("/api/books/{book_id}/regenerate-page/{page_number}")
async def regenerate_page(
    book_id: str,
    page_number: int,
    request: RegeneratePageRequest
) -> Dict:
    """Regenerate a page using the stored character bible."""
    
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    book = book_storage[book_id]
    bible = book.get('character_bible') or character_bibles.get(book_id)
    
    if not bible:
        raise HTTPException(400, "Character profile not found")
    
    if page_number < 1 or page_number > len(book['pages']):
        raise HTTPException(400, "Invalid page number")
    
    page = book['pages'][page_number - 1]
    
    try:
        illustration = await generate_illustration_with_character(
            character_bible=bible,
            scene_description=request.scene_description or page.get('scene_description', ''),
            character_action=request.character_action or page.get('character_action', ''),
            mood=request.mood or page.get('mood', 'happy'),
            art_style=book['art_style'],
            page_number=page_number,
            characters_in_scene=request.include_characters or page.get('characters_in_scene', []),
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
        raise HTTPException(500, f"Failed to regenerate: {str(e)}")

@app.get("/api/books/{book_id}/price")
async def get_book_price(
    book_id: str,
    format: BookFormat,
    shipping: ShippingTier,
    gift_wrap: bool = False
) -> Dict:
    if book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    base_price = Config.PRICES[format]
    shipping_cost = Config.SHIPPING_COSTS[shipping]
    wrap_cost = Config.GIFT_WRAP_COST if gift_wrap and format != BookFormat.DIGITAL else 0
    
    return {
        "book_id": book_id,
        "format": format.value,
        "base_price": base_price,
        "shipping_cost": shipping_cost,
        "gift_wrap_cost": wrap_cost,
        "total": round(base_price + shipping_cost + wrap_cost, 2),
        "currency": "USD"
    }

@app.post("/api/orders/create")
async def create_order(request: OrderRequest, background_tasks: BackgroundTasks) -> Dict:
    if request.book_id not in book_storage:
        raise HTTPException(404, "Book not found")
    
    order_id = str(uuid.uuid4())[:8]
    book = book_storage[request.book_id]
    
    price = await get_book_price(
        request.book_id, request.format, request.shipping_tier, request.gift_wrap
    )
    
    shipping_options = get_shipping_options()
    shipping_option = next(
        (o for o in shipping_options if o['tier'] == request.shipping_tier.value),
        shipping_options[0]
    )
    
    return {
        "order_id": order_id,
        "book_id": request.book_id,
        "book_title": book['title'],
        "format": request.format.value,
        "total": price['total'],
        "status": "pending_payment",
        "estimated_delivery": shipping_option['estimated_arrival'],
        "checkout_url": f"/checkout/{order_id}"
    }

@app.get("/api/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict:
    return {
        "order_id": order_id,
        "status": "processing",
        "steps": [
            {"name": "Order Received", "status": "completed"},
            {"name": "Payment Confirmed", "status": "completed"},
            {"name": "Generating Print Files", "status": "in_progress"},
            {"name": "Sent to Printer", "status": "pending"},
            {"name": "Shipped", "status": "pending"},
            {"name": "Delivered", "status": "pending"}
        ]
    }

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)