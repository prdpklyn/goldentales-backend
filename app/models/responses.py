# app/models/responses.py
"""
GoldenTales Response Models
===========================
Pydantic models for API response serialization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.models.enums import OrderStatus, BookTier


class PageResponse(BaseModel):
    """Single story page response."""
    page_number: int
    text: str
    scene_description: str
    character_action: Optional[str] = None
    mood: str = "happy"
    image_url: Optional[str] = None
    characters_in_scene: List[str] = []


class BookResponse(BaseModel):
    """Full book response."""
    book_id: str
    title: str
    child_name: str
    child_age: int
    theme: str
    art_style: str
    pages: List[PageResponse]
    preview_images: List[str]
    page_count: int
    character_bible: Optional[Dict[str, Any]] = None
    created_at: str
    status: str = "preview"


class PriceResponse(BaseModel):
    """Price calculation response."""
    book_id: str
    format: str
    base_price: float
    shipping_cost: float
    gift_wrap_cost: float
    total: float
    currency: str = "USD"


class OrderResponse(BaseModel):
    """Order creation response."""
    order_id: str
    book_id: str
    book_title: str
    total: float
    status: str
    estimated_delivery: str
    checkout_url: str


class OrderStatusResponse(BaseModel):
    """Order status response."""
    order_id: str
    status: OrderStatus
    steps: List[Dict[str, str]]


class ShippingOptionResponse(BaseModel):
    """Shipping option details."""
    tier: str
    name: str
    description: str
    available: bool
    deadline: Optional[str] = None
    estimated_arrival: str
    days_until_deadline: int = 0


class CountdownResponse(BaseModel):
    """Christmas countdown response."""
    expired: bool
    days: int
    hours: int
    minutes: int
    urgency: str
    deadline: Optional[str] = None


class ConfigResponse(BaseModel):
    """Public configuration response."""
    themes: List[str]
    art_styles: List[str]
    prices: Dict[str, float]
    shipping_options: List[ShippingOptionResponse]
    countdown: CountdownResponse
    character_options: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    checks: Dict[str, bool]
    timestamp: str


# ============================================
# V2 API RESPONSE MODELS (Premium/Ultra Tiers)
# ============================================

class PhotoValidationResponse(BaseModel):
    """Photo validation result."""
    valid: bool
    face_detected: bool
    confidence: float
    message: str
    issues: List[str] = []


class CharacterPreviewResponse(BaseModel):
    """Character preview generation result."""
    preview_id: str
    original_photo_url: str
    character_image_url: str
    art_style: str
    message: str
    expires_at: Optional[str] = None  # Preview expiration time


class ApprovalResponse(BaseModel):
    """Character approval result."""
    approved: bool
    character_reference_url: str
    message: str


class BookResponseV2(BaseModel):
    """V2 book response with tier information."""
    book_id: str
    title: str
    tier: BookTier
    child_name: str
    child_age: int
    theme: str
    art_style: str
    is_photo_based: bool = False
    character_reference_url: Optional[str] = None
    pages: List[PageResponse]
    preview_images: List[str]
    page_count: int
    character_bible: Optional[Dict[str, Any]] = None
    created_at: str
    status: str = "preview"


# ============================================
# PREVIEW API RESPONSE MODELS (Kids Flow)
# ============================================

class CoverImageResponse(BaseModel):
    """Cover image with metadata."""
    image_url: str
    prompt_used: str


class HeroPortraitResponse(BaseModel):
    """Hero portrait with placeholder indicator."""
    image_url: str
    is_placeholder: bool


class PreviewSpreadResponse(BaseModel):
    """Single preview spread (page)."""
    page_number: int
    image_url: str
    text: str


class PreviewMetadataResponse(BaseModel):
    """Preview generation metadata."""
    generation_time_ms: int
    model_version: str = "v2.1"
    art_style: str


class QuickPreviewResponse(BaseModel):
    """Quick preview generation result."""
    preview_id: str
    title: str
    cover: CoverImageResponse
    hero_portrait: HeroPortraitResponse
    spreads: List[PreviewSpreadResponse]
    metadata: PreviewMetadataResponse


class StyleAttributesResponse(BaseModel):
    """Style characteristics for a variant."""
    warmth: str
    detail: str
    expressiveness: str


class LikenessVariantResponse(BaseModel):
    """Single likeness variant."""
    id: str
    image_url: str
    likeness_score: int
    style_label: str
    description: str
    style_attributes: StyleAttributesResponse


class PhotoAnalysisResponse(BaseModel):
    """Source photo analysis result."""
    face_detected: bool
    quality_score: int
    lighting: str
    angle: str


class LikenessVariantsResponse(BaseModel):
    """Likeness variants generation result."""
    variants: List[LikenessVariantResponse]
    processing_time_ms: int
    source_photo_analysis: PhotoAnalysisResponse


class RegenerateTweaksResponse(BaseModel):
    """Applied tweaks for regeneration."""
    tone: Optional[str] = None
    art_modifier: Optional[str] = None
    sidekick: Optional[str] = None


class RegenerateMetadataResponse(BaseModel):
    """Regeneration metadata."""
    regeneration_time_ms: int
    tweaks_applied: RegenerateTweaksResponse


class RegenerateSpreadResponse(BaseModel):
    """Regenerated preview spread."""
    page_number: int
    image_url: str
    text: str
    updated: bool


class PreviewRegenerateResponse(BaseModel):
    """Preview regeneration result."""
    preview_id: str
    hero_portrait: HeroPortraitResponse
    spreads: List[RegenerateSpreadResponse]
    metadata: RegenerateMetadataResponse


class BookPageResponse(BaseModel):
    """A single page in the full book."""
    page_number: int
    text: str
    image_url: str
    scene_description: str
    character_action: str
    mood: str


class ExtendPreviewResponse(BaseModel):
    """Response from extending a preview to a full book."""
    preview_id: str
    book_id: str
    title: str
    child_name: str
    theme: str
    cover_url: str
    hero_portrait_url: str
    pages: List[BookPageResponse]
    total_pages: int
    character_bible: Dict[str, Any]
    art_style: str
    generation_time_ms: int
    was_continued: bool  # True if story was continued from preview, False if regenerated


# ============================================
# EDUCATIONAL STORYBOOK RESPONSE MODELS
# ============================================

class QuizQuestionOption(BaseModel):
    """Quiz question option."""
    id: str  # "A", "B", "C", "D"
    text: str


class QuizQuestion(BaseModel):
    """A single quiz question."""
    question_number: int
    question_text: str
    options: List[QuizQuestionOption]
    correct_answer: Optional[str] = None  # Only included in results
    explanation: Optional[str] = None
    difficulty: str  # "easy", "medium", "hard"


class QuizResponse(BaseModel):
    """Quiz generation response."""
    quiz_id: str
    topic: str
    topic_category: str
    questions: List[QuizQuestion]
    num_questions: int


class QuizBreakdown(BaseModel):
    """Quiz score breakdown by difficulty."""
    easy: Dict[str, int]
    medium: Dict[str, int]
    hard: Dict[str, int]


class LevelAssessmentResponse(BaseModel):
    """Level assessment result."""
    calibrated_level: str
    confidence_score: float
    self_reported_level: str
    quiz_taken: bool
    quiz_score: Optional[float] = None
    quiz_breakdown: Optional[QuizBreakdown] = None
    explanation: str


class ConceptCharacterResponse(BaseModel):
    """Concept character description."""
    name: str
    character_type: str
    concept_name: str
    visual_form: str
    primary_colors: List[str]
    distinctive_features: str
    personality_traits: Optional[str] = None
    role_in_story: Optional[str] = None


class SeriesResponse(BaseModel):
    """Educational series response."""
    series_id: str
    title: str
    topic: str
    topic_category: str
    learner_name: str
    learner_level: str
    age_band: str
    art_style: str
    target_chapters: int
    current_chapter: int
    concept_progression: List[List[str]]
    completed_chapters: List[str]
    status: str
    created_at: str


class ChapterPageResponse(BaseModel):
    """A single page in an educational chapter."""
    page_number: int
    text: str
    image_url: Optional[str] = None
    scene_description: str
    teaching_focus: str
    concept_characters_in_scene: List[str] = []
    mood: str
    pedagogical_type: str  # "setup", "concept", "application", etc.


class ChapterResponse(BaseModel):
    """Educational chapter response."""
    chapter_id: str
    series_id: str
    chapter_number: int
    title: str
    concepts_covered: List[str]
    cover_url: Optional[str] = None
    pages: List[ChapterPageResponse]
    total_pages: int
    quiz_questions: Optional[List[QuizQuestion]] = None
    generation_time_ms: int
    created_at: str


class NextChapterPlanResponse(BaseModel):
    """Next chapter planning information."""
    series_id: str
    chapter_number: int
    total_chapters: int
    concepts_to_cover: List[str]
    previous_concepts: List[str]
    ready_to_generate: bool


class EducationalPreviewResponse(BaseModel):
    """Quick educational preview response."""
    preview_id: str
    topic: str
    title: str
    cover: CoverImageResponse
    concept_characters: List[ConceptCharacterResponse]
    sample_pages: List[ChapterPageResponse]
    metadata: Dict[str, Any]


class TopicInfoResponse(BaseModel):
    """Topic information response."""
    topic_name: str
    topic_slug: str
    topic_category: str
    description: str
    suggested_chapters: int
    key_concepts: List[str]
    difficulty_range: List[str]  # ["beginner", "intermediate", "advanced"]
