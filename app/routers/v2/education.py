# app/routers/v2/education.py
"""
GoldenTales V2 Education Router
================================
API endpoints for educational storybooks and learning series.

These endpoints support creating educational content for any topic at any level.
"""

import time
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header

from app.models.requests import (
    LevelAssessmentRequest, CreateEducationalSeriesRequest,
    GenerateChapterRequest, EducationalPreviewRequest
)
from app.models.responses import (
    QuizResponse, LevelAssessmentResponse, SeriesResponse,
    ChapterResponse, NextChapterPlanResponse, EducationalPreviewResponse,
    TopicInfoResponse, ConceptCharacterResponse
)
from app.models.enums import LearningLevel, TopicCategory, ConceptCharacterType
from app.services.level_assessment_service import LevelAssessmentService
from app.services.educational_story_generator import EducationalStoryGenerator
from app.services.concept_character_service import ConceptCharacterService
from app.services.series_manager import SeriesManager
from app.services.image_generator import ImageGenerator
from app.middleware.auth import APIKeyData, get_api_key_validator
from app.utils.logging import get_logger
from app.utils.exceptions import ValidationException, ExternalServiceException
from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType

logger = get_logger(__name__)

router = APIRouter(prefix="/education", tags=["Education"])


async def require_api_key(x_api_key: Optional[str] = Header(None)) -> APIKeyData:
    """
    Dependency to validate API key from X-API-Key header.
    
    Educational endpoints require API key authentication.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    validator = get_api_key_validator()
    api_key_data = await validator.validate(x_api_key)
    
    if not api_key_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return api_key_data


@router.get("/topics")
async def list_topics(
    category: Optional[str] = None,
    api_key: APIKeyData = Depends(require_api_key)
) -> Dict[str, List[str]]:
    """
    List available topic categories.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        category: Optional filter by category
        api_key: Validated API key data
        
    Returns:
        Dict with topic categories and example topics
    """
    categories = {
        "stem": ["Reinforcement Learning", "Neural Networks", "Photosynthesis", "Solar System"],
        "humanities": ["Ancient Rome", "Renaissance Art", "World War II", "Philosophy Basics"],
        "languages": ["Spanish Grammar", "Japanese Hiragana", "French Vocabulary", "English Idioms"],
        "arts": ["Music Theory", "Color Theory", "Drawing Fundamentals", "Dance Basics"],
        "business": ["Marketing Basics", "Financial Planning", "Entrepreneurship", "Leadership Skills"],
        "other": ["Cooking Techniques", "Gardening", "Public Speaking", "Time Management"]
    }
    
    if category:
        if category not in categories:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        return {category: categories[category]}
    
    return categories


@router.get("/quiz/{topic}")
async def get_quiz(
    topic: str,
    topic_category: str,
    num_questions: int = 5,
    target_level: Optional[str] = None,
    age_band: str = "adult",
    api_key: APIKeyData = Depends(require_api_key)
) -> QuizResponse:
    """
    Generate a quiz to assess learner's level on a topic.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        topic: Topic to quiz about
        topic_category: Category of the topic
        num_questions: Number of questions (1-10, default 5)
        target_level: Optional target difficulty
        age_band: Age group (child/teen/adult)
        api_key: Validated API key data
        
    Returns:
        QuizResponse with questions
    """
    logger.info(f"Generating quiz for topic: {topic}")
    
    try:
        # Validate parameters
        try:
            category = TopicCategory(topic_category)
        except ValueError:
            raise ValidationException(f"Invalid topic_category: {topic_category}")
        
        level = None
        if target_level:
            try:
                level = LearningLevel(target_level)
            except ValueError:
                raise ValidationException(f"Invalid target_level: {target_level}")
        
        if not 1 <= num_questions <= 10:
            raise ValidationException("num_questions must be between 1 and 10")
        
        # Generate quiz
        service = LevelAssessmentService()
        quiz_data = await service.generate_quiz(
            topic=topic,
            topic_category=category,
            target_level=level,
            num_questions=num_questions,
            age_band=age_band
        )
        
        # Add quiz ID
        import uuid
        quiz_data["quiz_id"] = str(uuid.uuid4())[:8]
        
        return QuizResponse(**quiz_data)
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error generating quiz: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.post("/assess")
async def assess_level(
    request: LevelAssessmentRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> LevelAssessmentResponse:
    """
    Assess learner's level through self-report and optional quiz.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        request: Level assessment request with quiz answers
        api_key: Validated API key data
        
    Returns:
        LevelAssessmentResponse with calibrated level
    """
    logger.info(f"Assessing level for topic: {request.topic}")
    
    try:
        # Parse enums
        try:
            category = TopicCategory(request.topic_category)
            level = LearningLevel(request.self_reported_level)
        except ValueError as e:
            raise ValidationException(str(e))
        
        # Calibrate level
        service = LevelAssessmentService()
        
        # Convert quiz answers if provided
        quiz_answers = None
        if request.quiz_answers:
            quiz_answers = [
                {"question_number": ans.question_number, "selected_answer": ans.selected_answer}
                for ans in request.quiz_answers
            ]
        
        result = await service.calibrate_level(
            topic=request.topic,
            topic_category=category,
            self_reported_level=level,
            quiz_answers=quiz_answers
        )
        
        return LevelAssessmentResponse(**result)
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error assessing level: {e}")
        raise HTTPException(status_code=500, detail="Failed to assess level")


@router.post("/series", response_model=SeriesResponse)
async def create_series(
    request: CreateEducationalSeriesRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> SeriesResponse:
    """
    Create a new educational learning series.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        request: Series creation request
        api_key: Validated API key data
        
    Returns:
        SeriesResponse with series metadata
    """
    logger.info(f"Creating series for topic: {request.topic}")
    
    try:
        # Parse enums
        try:
            category = TopicCategory(request.topic_category)
            level = LearningLevel(request.learner_level)
        except ValueError as e:
            raise ValidationException(str(e))
        
        # Build character bible if details provided
        character_bible = {}
        if request.learner_gender:
            try:
                gender = Gender(request.learner_gender)
                character_bible = {
                    "main_character": f"{request.learner_name}, {request.age_band} learner",
                    "gender": request.learner_gender,
                    "skin_tone": request.skin_tone or "medium",
                    "hair_color": request.hair_color or "brown",
                    "hair_style": request.hair_style or "neat"
                }
            except ValueError:
                pass  # Skip if invalid, use defaults
        
        # Create series
        manager = SeriesManager()
        series_data = await manager.create_series(
            topic=request.topic,
            topic_slug=request.topic_slug,
            topic_category=category,
            learner_name=request.learner_name,
            learner_level=level,
            age_band=request.age_band,
            art_style=request.art_style,
            target_chapters=request.target_chapters,
            learner_profile_id=request.learner_profile_id,
            character_bible=character_bible,
            include_quiz_between_chapters=request.include_quiz_between_chapters
        )
        
        return SeriesResponse(
            series_id=series_data["id"],
            title=series_data["title"],
            topic=request.topic,
            topic_category=series_data["topic_category"],
            learner_name=series_data["learner_name"],
            learner_level=series_data["learner_level"],
            age_band=series_data["age_band"],
            art_style=series_data["art_style"],
            target_chapters=series_data["target_chapters"],
            current_chapter=series_data["current_chapter"],
            concept_progression=series_data["concept_progression"],
            completed_chapters=series_data["completed_chapters"],
            status=series_data["status"],
            created_at=series_data["created_at"]
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating series: {e}")
        raise HTTPException(status_code=500, detail="Failed to create series")


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: str,
    api_key: APIKeyData = Depends(require_api_key)
) -> SeriesResponse:
    """
    Get series details and progress.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        series_id: Series identifier
        api_key: Validated API key data
        
    Returns:
        SeriesResponse with series data
    """
    logger.info(f"Fetching series: {series_id}")
    
    try:
        manager = SeriesManager()
        series_data = await manager.get_series(series_id)
        
        if not series_data:
            raise HTTPException(status_code=404, detail="Series not found")
        
        return SeriesResponse(
            series_id=series_data["id"],
            title=series_data["title"],
            topic=series_data.get("topic_slug", "unknown"),
            topic_category=series_data["topic_category"],
            learner_name=series_data["learner_name"],
            learner_level=series_data["learner_level"],
            age_band=series_data["age_band"],
            art_style=series_data["art_style"],
            target_chapters=series_data["target_chapters"],
            current_chapter=series_data["current_chapter"],
            concept_progression=series_data["concept_progression"],
            completed_chapters=series_data["completed_chapters"],
            status=series_data["status"],
            created_at=series_data["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching series: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch series")


@router.get("/series/{series_id}/next", response_model=NextChapterPlanResponse)
async def get_next_chapter_plan(
    series_id: str,
    api_key: APIKeyData = Depends(require_api_key)
) -> NextChapterPlanResponse:
    """
    Get plan for the next chapter in a series.
    
    **Authentication**: Requires X-API-Key header
    
    Args:
        series_id: Series identifier
        api_key: Validated API key data
        
    Returns:
        NextChapterPlanResponse with chapter planning info
    """
    logger.info(f"Getting next chapter plan for series: {series_id}")
    
    try:
        manager = SeriesManager()
        plan = await manager.get_next_chapter_plan(series_id)
        
        return NextChapterPlanResponse(
            series_id=plan["series_id"],
            chapter_number=plan["chapter_number"],
            total_chapters=plan["total_chapters"],
            concepts_to_cover=plan["concepts_to_cover"],
            previous_concepts=plan["previous_concepts"],
            ready_to_generate=True
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting next chapter plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chapter plan")


@router.post("/series/{series_id}/chapters", response_model=ChapterResponse)
async def generate_chapter(
    series_id: str,
    request: GenerateChapterRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> ChapterResponse:
    """
    Generate the next chapter in a series.
    
    **Authentication**: Requires X-API-Key header
    
    **Performance**: May take 2-5 minutes for full generation
    
    Args:
        series_id: Series identifier
        request: Chapter generation request
        api_key: Validated API key data
        
    Returns:
        ChapterResponse with generated chapter
    """
    start_time = time.time()
    logger.info(f"Generating chapter for series: {series_id}")
    
    try:
        # Get chapter plan
        manager = SeriesManager()
        plan = await manager.get_next_chapter_plan(series_id)
        
        # Create concept characters
        concept_service = ConceptCharacterService()
        concept_characters = await concept_service.create_multiple_concept_characters(
            concepts=plan["concepts_to_cover"],
            topic=series_id,  # Use series_id as topic context
            art_style=plan["art_style"],
            age_band=plan["age_band"]
        )
        
        # Convert to dict format for story generator
        concept_chars_dict = [
            {
                "name": char.name,
                "description": f"{char.visual_form} in {' and '.join(char.primary_colors)} with {char.distinctive_features}",
                "concept_name": char.concept_name
            }
            for char in concept_characters
        ]
        
        # Generate educational story
        story_gen = EducationalStoryGenerator()
        story_pages = await story_gen.generate_educational_story(
            topic=series_id,
            topic_category=TopicCategory.STEM,  # TODO: Get from series
            concepts=plan["concepts_to_cover"],
            learner_name=plan["learner_name"],
            learner_level=LearningLevel(plan["learner_level"]),
            age_band=plan["age_band"],
            character_bible=plan["character_bible"],
            concept_characters=concept_chars_dict,
            chapter_number=plan["chapter_number"],
            total_chapters=plan["total_chapters"],
            previous_concepts=plan["previous_concepts"],
            art_style=plan["art_style"],
            custom_focus=request.custom_focus
        )
        
        # Save chapter
        chapter_data = {
            "chapter_number": plan["chapter_number"],
            "title": f"Chapter {plan['chapter_number']}: {', '.join(plan['concepts_to_cover'])}",
            "concepts_covered": plan["concepts_to_cover"],
            "story_pages": story_pages,
            "characters_used": {
                "learner": plan["character_bible"],
                "concept_characters": concept_chars_dict
            },
            "generation_time_ms": int((time.time() - start_time) * 1000)
        }
        
        saved_chapter = await manager.save_chapter(series_id, chapter_data)
        
        # Build response
        from app.models.responses import ChapterPageResponse
        pages = [
            ChapterPageResponse(
                page_number=page["page_number"],
                text=page["text"],
                scene_description=page["scene_description"],
                teaching_focus=page.get("teaching_focus", ""),
                concept_characters_in_scene=page.get("concept_characters_in_scene", []),
                mood=page.get("mood", "curious"),
                pedagogical_type=page.get("pedagogical_type", "concept")
            )
            for page in story_pages
        ]
        
        return ChapterResponse(
            chapter_id=saved_chapter["id"],
            series_id=series_id,
            chapter_number=saved_chapter["chapter_number"],
            title=saved_chapter["title"],
            concepts_covered=saved_chapter["concepts_covered"],
            pages=pages,
            total_pages=len(pages),
            generation_time_ms=saved_chapter["generation_time_ms"],
            created_at=saved_chapter["created_at"]
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error generating chapter: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate chapter")


@router.post("/preview", response_model=EducationalPreviewResponse)
async def educational_preview(
    request: EducationalPreviewRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> EducationalPreviewResponse:
    """
    Generate a quick educational preview (2-3 sample pages).
    
    **Authentication**: Requires X-API-Key header
    
    **Performance**: Should complete in under 60 seconds
    
    Args:
        request: Preview request
        api_key: Validated API key data
        
    Returns:
        EducationalPreviewResponse with preview content
    """
    start_time = time.time()
    logger.info(f"Generating educational preview for: {request.topic}")
    
    try:
        # This is a simplified preview - just generate 2 concept characters and 2 pages
        concept_service = ConceptCharacterService()
        sample_concepts = ["introduction", "basics"]
        
        concept_characters = await concept_service.create_multiple_concept_characters(
            concepts=sample_concepts,
            topic=request.topic,
            art_style=request.art_style,
            age_band=request.age_band
        )
        
        # Build simple character bible
        character_bible = {
            "main_character": f"{request.learner_name}, {request.age_band} learner"
        }
        
        # Build response
        import uuid
        preview_id = str(uuid.uuid4())[:8]
        
        return EducationalPreviewResponse(
            preview_id=preview_id,
            topic=request.topic,
            title=f"{request.learner_name}'s {request.topic} Journey",
            cover={
                "image_url": "https://placehold.co/1024x1024/blue/white?text=Educational+Preview",
                "prompt_used": f"Educational book cover for {request.topic}"
            },
            concept_characters=[
                ConceptCharacterResponse(
                    name=char.name,
                    character_type=char.character_type.value,
                    concept_name=char.concept_name,
                    visual_form=char.visual_form,
                    primary_colors=char.primary_colors,
                    distinctive_features=char.distinctive_features,
                    personality_traits=char.personality_traits,
                    role_in_story=char.role_in_story
                )
                for char in concept_characters
            ],
            sample_pages=[],
            metadata={
                "generation_time_ms": int((time.time() - start_time) * 1000),
                "preview_mode": True
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating educational preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")
