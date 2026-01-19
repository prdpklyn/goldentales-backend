# app/services/series_manager.py
"""
GoldenTales Series Manager
==========================
Manages multi-chapter learning series with continuity and progress tracking.
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.utils.logging import get_logger
from app.utils.exceptions import ValidationException
from app.models.enums import LearningLevel, TopicCategory

logger = get_logger(__name__)


class SeriesManager:
    """
    Service for managing educational series with multiple chapters.
    
    Handles:
    - Series creation and metadata
    - Chapter progression tracking
    - Character bible persistence across chapters
    - Concept progression planning
    - Progress tracking and analytics
    
    Example:
        manager = SeriesManager(database_service)
        series = await manager.create_series(
            topic="Reinforcement Learning",
            learner_name="Alex",
            target_chapters=5
        )
        
        # Later, generate next chapter
        chapter = await manager.get_next_chapter_plan(series_id)
    """
    
    # Topic-specific concept progressions
    CONCEPT_PROGRESSIONS = {
        "reinforcement_learning": [
            ["agents", "environments"],
            ["states", "observations"],
            ["actions", "policies"],
            ["rewards", "value functions"],
            ["learning", "exploration vs exploitation"]
        ],
        "neural_networks": [
            ["neurons", "activation functions"],
            ["layers", "forward propagation"],
            ["loss functions", "gradient descent"],
            ["backpropagation", "weight updates"],
            ["training", "overfitting prevention"]
        ],
        "photosynthesis": [
            ["sunlight energy", "chloroplasts"],
            ["water absorption", "carbon dioxide"],
            ["light reactions", "ATP production"],
            ["dark reactions", "glucose creation"],
            ["complete process", "oxygen release"]
        ],
        # Add more as needed
    }
    
    def __init__(self, database_service=None):
        """
        Initialize the series manager.
        
        Args:
            database_service: Optional database service for persistence
        """
        self.db = database_service
        # In-memory storage for when DB is unavailable
        self._memory_storage: Dict[str, Dict[str, Any]] = {}
    
    async def create_series(
        self,
        topic: str,
        topic_slug: str,
        topic_category: TopicCategory,
        learner_name: str,
        learner_level: LearningLevel,
        age_band: str,
        art_style: str,
        target_chapters: int = 5,
        learner_profile_id: Optional[str] = None,
        character_bible: Optional[Dict[str, Any]] = None,
        include_quiz_between_chapters: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new learning series.
        
        Args:
            topic: Topic name (e.g., "Reinforcement Learning")
            topic_slug: URL-safe topic identifier
            topic_category: Category of the topic
            learner_name: Name of the learner
            learner_level: Proficiency level
            age_band: Age group
            art_style: Visual style
            target_chapters: Number of chapters
            learner_profile_id: Optional learner profile reference
            character_bible: Learner character description
            include_quiz_between_chapters: Whether to include quizzes
            
        Returns:
            Series data dictionary
        """
        series_id = str(uuid.uuid4())
        
        # Generate concept progression for this topic
        concept_progression = self._plan_concept_progression(
            topic_slug,
            target_chapters,
            learner_level
        )
        
        # Generate title
        title = f"{learner_name}'s {topic} Journey"
        
        series_data = {
            "id": series_id,
            "title": title,
            "topic_slug": topic_slug,
            "topic_category": topic_category.value,
            "learner_profile_id": learner_profile_id,
            "learner_name": learner_name,
            "learner_level": learner_level.value,
            "age_band": age_band,
            "target_chapters": target_chapters,
            "current_chapter": 0,
            "concept_progression": concept_progression,
            "art_style": art_style,
            "series_character_bible": character_bible or {},
            "include_quiz_between_chapters": include_quiz_between_chapters,
            "completed_chapters": [],
            "quiz_scores": [],
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Store in database if available
        if self.db and self.db.client:
            try:
                result = self.db.client.table("learning_series").insert(series_data).execute()
                if result.data:
                    logger.info(f"Created series in database: {series_id}")
                    return result.data[0]
            except Exception as e:
                logger.warning(f"Failed to store series in database: {e}")
        
        # Fallback to in-memory storage
        self._memory_storage[series_id] = series_data
        logger.info(f"Created series in memory: {series_id}")
        
        return series_data
    
    def _plan_concept_progression(
        self,
        topic_slug: str,
        target_chapters: int,
        learner_level: LearningLevel
    ) -> List[List[str]]:
        """
        Plan the concept progression for a series.
        
        Returns a list where each element is a list of concepts for that chapter.
        """
        # Get predefined progression or create generic one
        if topic_slug in self.CONCEPT_PROGRESSIONS:
            base_progression = self.CONCEPT_PROGRESSIONS[topic_slug]
        else:
            # Generic progression structure
            base_progression = [
                ["introduction", "basics"],
                ["core concept 1", "examples"],
                ["core concept 2", "applications"],
                ["advanced ideas", "practice"],
                ["integration", "summary"]
            ]
        
        # Adjust based on target chapters
        if target_chapters <= len(base_progression):
            return base_progression[:target_chapters]
        else:
            # Expand by splitting concepts
            expanded = base_progression.copy()
            while len(expanded) < target_chapters:
                # Add intermediate chapters
                expanded.append(["review", "deeper exploration"])
            return expanded[:target_chapters]
    
    async def get_series(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Get series by ID."""
        
        # Try database first
        if self.db and self.db.client:
            try:
                result = self.db.client.table("learning_series").select("*").eq("id", series_id).execute()
                if result.data:
                    return result.data[0]
            except Exception as e:
                logger.warning(f"Failed to fetch series from database: {e}")
        
        # Fallback to memory
        return self._memory_storage.get(series_id)
    
    async def get_next_chapter_plan(
        self,
        series_id: str
    ) -> Dict[str, Any]:
        """
        Get the plan for the next chapter in a series.
        
        Args:
            series_id: Series identifier
            
        Returns:
            Dict with chapter_number, concepts, previous_chapters info
        """
        series = await self.get_series(series_id)
        if not series:
            raise ValidationException(f"Series not found: {series_id}")
        
        current_chapter = series.get("current_chapter", 0)
        target_chapters = series.get("target_chapters", 5)
        
        if current_chapter >= target_chapters:
            raise ValidationException("Series already complete")
        
        next_chapter_num = current_chapter + 1
        concept_progression = series.get("concept_progression", [])
        
        # Get concepts for next chapter
        if next_chapter_num <= len(concept_progression):
            next_concepts = concept_progression[next_chapter_num - 1]
        else:
            next_concepts = ["additional concepts"]
        
        # Get previous concepts
        previous_concepts = []
        for i in range(current_chapter):
            if i < len(concept_progression):
                previous_concepts.extend(concept_progression[i])
        
        return {
            "series_id": series_id,
            "chapter_number": next_chapter_num,
            "total_chapters": target_chapters,
            "concepts_to_cover": next_concepts,
            "previous_concepts": previous_concepts,
            "learner_name": series.get("learner_name"),
            "learner_level": series.get("learner_level"),
            "age_band": series.get("age_band"),
            "art_style": series.get("art_style"),
            "character_bible": series.get("series_character_bible", {}),
            "include_quiz": series.get("include_quiz_between_chapters", False)
        }
    
    async def save_chapter(
        self,
        series_id: str,
        chapter_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save a completed chapter to the series.
        
        Args:
            series_id: Series identifier
            chapter_data: Chapter content and metadata
            
        Returns:
            Updated chapter data
        """
        chapter_id = str(uuid.uuid4())
        
        chapter_record = {
            "id": chapter_id,
            "series_id": series_id,
            "chapter_number": chapter_data.get("chapter_number"),
            "title": chapter_data.get("title", f"Chapter {chapter_data.get('chapter_number')}"),
            "concepts_covered": chapter_data.get("concepts_covered", []),
            "story_pages": chapter_data.get("story_pages", []),
            "cover_url": chapter_data.get("cover_url"),
            "page_images": chapter_data.get("page_images", []),
            "characters_used": chapter_data.get("characters_used", {}),
            "quiz_questions": chapter_data.get("quiz_questions", []),
            "generation_time_ms": chapter_data.get("generation_time_ms"),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in database if available
        if self.db and self.db.client:
            try:
                result = self.db.client.table("series_chapters").insert(chapter_record).execute()
                if result.data:
                    chapter_record = result.data[0]
                    logger.info(f"Saved chapter to database: {chapter_id}")
            except Exception as e:
                logger.warning(f"Failed to save chapter to database: {e}")
        
        # Update series progress
        await self._update_series_progress(series_id, chapter_id)
        
        return chapter_record
    
    async def _update_series_progress(
        self,
        series_id: str,
        chapter_id: str
    ) -> None:
        """Update series progress after completing a chapter."""
        
        series = await self.get_series(series_id)
        if not series:
            return
        
        completed_chapters = series.get("completed_chapters", [])
        completed_chapters.append(chapter_id)
        
        current_chapter = series.get("current_chapter", 0)
        new_chapter_num = current_chapter + 1
        
        # Check if series is complete
        target_chapters = series.get("target_chapters", 5)
        status = "completed" if new_chapter_num >= target_chapters else "active"
        
        updates = {
            "current_chapter": new_chapter_num,
            "completed_chapters": completed_chapters,
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == "completed":
            updates["completed_at"] = datetime.utcnow().isoformat()
        
        # Update in database
        if self.db and self.db.client:
            try:
                self.db.client.table("learning_series").update(updates).eq("id", series_id).execute()
                logger.info(f"Updated series progress: {series_id}")
            except Exception as e:
                logger.warning(f"Failed to update series: {e}")
        
        # Update memory storage
        if series_id in self._memory_storage:
            self._memory_storage[series_id].update(updates)
    
    async def get_series_chapters(
        self,
        series_id: str
    ) -> List[Dict[str, Any]]:
        """Get all chapters for a series."""
        
        if self.db and self.db.client:
            try:
                result = (
                    self.db.client.table("series_chapters")
                    .select("*")
                    .eq("series_id", series_id)
                    .order("chapter_number")
                    .execute()
                )
                if result.data:
                    return result.data
            except Exception as e:
                logger.warning(f"Failed to fetch chapters from database: {e}")
        
        return []
    
    async def save_character_bible(
        self,
        series_id: str,
        character_role: str,
        character_name: str,
        character_bible: str,
        first_appearance_chapter: int,
        reference_image_url: Optional[str] = None,
        visual_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save a character bible for series-wide consistency.
        
        Args:
            series_id: Series identifier
            character_role: Role (learner, guide, concept)
            character_name: Character name
            character_bible: Full description
            first_appearance_chapter: Chapter where character first appears
            reference_image_url: Optional reference image
            visual_seed: Optional seed for consistent generation
            
        Returns:
            Character bible record
        """
        bible_id = str(uuid.uuid4())
        
        bible_record = {
            "id": bible_id,
            "series_id": series_id,
            "character_role": character_role,
            "character_name": character_name,
            "character_bible": character_bible,
            "reference_image_url": reference_image_url,
            "visual_seed": visual_seed or (42 + hash(character_name) % 1000),
            "first_appearance_chapter": first_appearance_chapter,
            "appearances_in_chapters": [first_appearance_chapter],
            "created_at": datetime.utcnow().isoformat()
        }
        
        if self.db and self.db.client:
            try:
                result = self.db.client.table("series_character_bibles").insert(bible_record).execute()
                if result.data:
                    logger.info(f"Saved character bible: {character_name}")
                    return result.data[0]
            except Exception as e:
                logger.warning(f"Failed to save character bible: {e}")
        
        return bible_record
    
    async def get_series_character_bibles(
        self,
        series_id: str
    ) -> List[Dict[str, Any]]:
        """Get all character bibles for a series."""
        
        if self.db and self.db.client:
            try:
                result = (
                    self.db.client.table("series_character_bibles")
                    .select("*")
                    .eq("series_id", series_id)
                    .execute()
                )
                if result.data:
                    return result.data
            except Exception as e:
                logger.warning(f"Failed to fetch character bibles: {e}")
        
        return []
