# tests/test_educational_features.py
"""
Tests for Educational Storybook Features
========================================
Tests level assessment, concept characters, educational story generation, and series management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict

from app.models.enums import LearningLevel, TopicCategory, ConceptCharacterType
from app.services.level_assessment_service import LevelAssessmentService
from app.services.educational_story_generator import EducationalStoryGenerator
from app.services.concept_character_service import ConceptCharacterService
from app.services.series_manager import SeriesManager
from character_system import ConceptCharacter


# ============================================
# LEVEL ASSESSMENT TESTS
# ============================================

@pytest.mark.asyncio
async def test_generate_quiz():
    """Test quiz generation for level assessment."""
    service = LevelAssessmentService(api_key="test_key")
    
    # Mock Gemini response
    mock_quiz_response = """{
        "questions": [
            {
                "question_number": 1,
                "question_text": "What is reinforcement learning?",
                "options": [
                    {"id": "A", "text": "A type of supervised learning"},
                    {"id": "B", "text": "Learning through trial and error"},
                    {"id": "C", "text": "A data preprocessing technique"},
                    {"id": "D", "text": "A neural network architecture"}
                ],
                "correct_answer": "B",
                "explanation": "RL learns through trial and error with rewards",
                "difficulty": "easy"
            },
            {
                "question_number": 2,
                "question_text": "What is an agent in RL?",
                "options": [
                    {"id": "A", "text": "The learning entity"},
                    {"id": "B", "text": "The environment"},
                    {"id": "C", "text": "The reward function"},
                    {"id": "D", "text": "The training data"}
                ],
                "correct_answer": "A",
                "explanation": "The agent is the entity that learns and takes actions",
                "difficulty": "medium"
            }
        ]
    }"""
    
    with patch.object(service, '_call_gemini_with_retry', new=AsyncMock(return_value=mock_quiz_response)):
        quiz = await service.generate_quiz(
            topic="reinforcement_learning",
            topic_category=TopicCategory.STEM,
            num_questions=2,
            age_band="adult"
        )
        
        assert quiz["num_questions"] == 2
        assert len(quiz["questions"]) == 2
        assert quiz["questions"][0]["question_number"] == 1
        assert quiz["questions"][0]["correct_answer"] == "B"
        assert quiz["questions"][1]["difficulty"] == "medium"


@pytest.mark.asyncio
async def test_calibrate_level_without_quiz():
    """Test level calibration with self-report only."""
    service = LevelAssessmentService()
    
    result = await service.calibrate_level(
        topic="reinforcement_learning",
        topic_category=TopicCategory.STEM,
        self_reported_level=LearningLevel.BEGINNER,
        quiz_answers=None
    )
    
    assert result["calibrated_level"] == "beginner"
    assert result["confidence_score"] == 0.6
    assert result["quiz_taken"] is False
    assert "self-report only" in result["explanation"].lower()


@pytest.mark.asyncio
async def test_calibrate_level_with_quiz():
    """Test level calibration with quiz results."""
    service = LevelAssessmentService()
    
    quiz_data = {
        "questions": [
            {"question_number": 1, "correct_answer": "B", "difficulty": "easy"},
            {"question_number": 2, "correct_answer": "A", "difficulty": "medium"},
            {"question_number": 3, "correct_answer": "C", "difficulty": "hard"}
        ]
    }
    
    # User got 2/3 correct (missed the hard one)
    quiz_answers = [
        {"question_number": 1, "selected_answer": "B"},  # Correct
        {"question_number": 2, "selected_answer": "A"},  # Correct
        {"question_number": 3, "selected_answer": "D"}   # Wrong
    ]
    
    result = await service.calibrate_level(
        topic="reinforcement_learning",
        topic_category=TopicCategory.STEM,
        self_reported_level=LearningLevel.INTERMEDIATE,
        quiz_answers=quiz_answers,
        quiz_data=quiz_data
    )
    
    assert result["quiz_taken"] is True
    assert result["quiz_score"] == pytest.approx(0.67, 0.01)
    assert result["calibrated_level"] in ["beginner", "intermediate"]
    assert result["confidence_score"] > 0.5


# ============================================
# CONCEPT CHARACTER TESTS
# ============================================

@pytest.mark.asyncio
async def test_create_concept_character():
    """Test concept character creation."""
    service = ConceptCharacterService(api_key="test_key")
    
    # Mock Gemini response
    mock_response = """NAME: Agent Alpha
VISUAL_FORM: friendly blue robot
COLORS: blue, silver, white
FEATURES: digital display on chest showing learning progress
PERSONALITY: curious, determined, learns from mistakes
ROLE: demonstrates how an RL agent explores and learns"""
    
    with patch.object(service, '_call_gemini_with_retry', new=AsyncMock(return_value=mock_response)):
        character = await service.create_concept_character(
            concept_name="RL Agent",
            topic="reinforcement_learning",
            character_type=ConceptCharacterType.AGENT,
            art_style="cartoon",
            age_band="adult"
        )
        
        assert character.name == "Agent Alpha"
        assert character.character_type == ConceptCharacterType.AGENT
        assert character.concept_name == "RL Agent"
        assert "robot" in character.visual_form.lower()
        assert "blue" in character.primary_colors
        assert character.character_slug is not None


def test_concept_character_slug_generation():
    """Test slug generation for concept characters."""
    service = ConceptCharacterService()
    
    slug = service._generate_character_slug("Reward Signal", "reinforcement_learning")
    assert slug == "reward_signal_reinforcement_learning"
    assert len(slug) <= 100


def test_infer_character_type():
    """Test character type inference from concept name."""
    service = ConceptCharacterService()
    
    assert service._infer_character_type("Learning Agent") == ConceptCharacterType.AGENT
    assert service._infer_character_type("Environment Grid") == ConceptCharacterType.ENVIRONMENT
    assert service._infer_character_type("Backpropagation Process") == ConceptCharacterType.PROCESS
    assert service._infer_character_type("Professor Guide") == ConceptCharacterType.GUIDE
    assert service._infer_character_type("Reward Signal") == ConceptCharacterType.ENTITY


@pytest.mark.asyncio
async def test_create_multiple_concept_characters():
    """Test batch creation of concept characters."""
    service = ConceptCharacterService(api_key="test_key")
    
    # Mock responses
    async def mock_create(concept_name, **kwargs):
        return ConceptCharacter(
            name=f"{concept_name} Character",
            character_type=ConceptCharacterType.ENTITY,
            concept_name=concept_name,
            visual_form="test form",
            primary_colors=["blue", "green"],
            distinctive_features="test features"
        )
    
    with patch.object(service, 'create_concept_character', new=mock_create):
        characters = await service.create_multiple_concept_characters(
            concepts=["agents", "rewards", "policies"],
            topic="reinforcement_learning",
            art_style="cartoon"
        )
        
        assert len(characters) == 3
        assert characters[0].concept_name == "agents"
        assert characters[1].concept_name == "rewards"
        assert characters[2].concept_name == "policies"


# ============================================
# EDUCATIONAL STORY GENERATOR TESTS
# ============================================

@pytest.mark.asyncio
async def test_generate_educational_story():
    """Test educational story generation."""
    generator = EducationalStoryGenerator(api_key="test_key")
    
    # Mock Gemini response
    mock_story = """[
        {
            "page_number": 1,
            "text": "Alex begins their journey into reinforcement learning...",
            "scene_description": "Alex, an eager adult learner, stands at the entrance of a digital world",
            "teaching_focus": "Introduction to RL",
            "concept_characters_in_scene": ["Agent Alpha"],
            "mood": "curious",
            "pedagogical_type": "setup"
        },
        {
            "page_number": 2,
            "text": "Meet Agent Alpha, who will help Alex understand how agents learn...",
            "scene_description": "Agent Alpha, a friendly blue robot, appears before Alex",
            "teaching_focus": "What is an agent",
            "concept_characters_in_scene": ["Agent Alpha"],
            "mood": "excited",
            "pedagogical_type": "concept"
        }
    ]"""
    
    character_bible = {
        "main_character": "Alex, adult learner"
    }
    
    concept_characters = [
        {"name": "Agent Alpha", "description": "friendly blue robot", "concept_name": "RL Agent"}
    ]
    
    with patch.object(generator, '_call_gemini_with_retry', new=AsyncMock(return_value=mock_story)):
        pages = await generator.generate_educational_story(
            topic="Reinforcement Learning",
            topic_category=TopicCategory.STEM,
            concepts=["agents", "environments"],
            learner_name="Alex",
            learner_level=LearningLevel.BEGINNER,
            age_band="adult",
            character_bible=character_bible,
            concept_characters=concept_characters,
            chapter_number=1,
            total_chapters=5
        )
        
        assert len(pages) >= 2
        assert pages[0]["page_number"] == 1
        assert pages[0]["pedagogical_type"] == "setup"
        assert "Agent Alpha" in pages[0]["concept_characters_in_scene"]
        assert "teaching_focus" in pages[0]


def test_pedagogical_structure():
    """Test pedagogical structure definition."""
    generator = EducationalStoryGenerator()
    
    structure = generator.PEDAGOGICAL_STRUCTURE
    
    assert "setup" in structure
    assert "core_concepts" in structure
    assert "application" in structure
    assert "reinforcement" in structure
    assert "summary" in structure
    
    # Verify page ranges
    assert structure["setup"]["pages"] == [1, 2]
    assert structure["core_concepts"]["pages"] == [3, 4, 5, 6]


def test_vocabulary_guidance():
    """Test vocabulary guidance for different age bands."""
    generator = EducationalStoryGenerator()
    
    child_vocab = generator.VOCABULARY_GUIDANCE["child"]
    adult_vocab = generator.VOCABULARY_GUIDANCE["adult"]
    
    assert "simple" in child_vocab["complexity"]
    assert "short" in child_vocab["sentence_length"]
    
    assert "professional" in adult_vocab["complexity"]
    assert "varied" in adult_vocab["sentence_length"]


# ============================================
# SERIES MANAGER TESTS
# ============================================

@pytest.mark.asyncio
async def test_create_series():
    """Test series creation."""
    manager = SeriesManager()
    
    series = await manager.create_series(
        topic="Reinforcement Learning",
        topic_slug="reinforcement_learning",
        topic_category=TopicCategory.STEM,
        learner_name="Alex",
        learner_level=LearningLevel.BEGINNER,
        age_band="adult",
        art_style="cartoon",
        target_chapters=5
    )
    
    assert series["id"] is not None
    assert series["title"] == "Alex's Reinforcement Learning Journey"
    assert series["learner_name"] == "Alex"
    assert series["target_chapters"] == 5
    assert series["current_chapter"] == 0
    assert series["status"] == "active"
    assert len(series["concept_progression"]) == 5


def test_plan_concept_progression():
    """Test concept progression planning."""
    manager = SeriesManager()
    
    # Test with known topic
    progression = manager._plan_concept_progression(
        topic_slug="reinforcement_learning",
        target_chapters=5,
        learner_level=LearningLevel.BEGINNER
    )
    
    assert len(progression) == 5
    assert isinstance(progression[0], list)
    assert len(progression[0]) > 0
    
    # Test with unknown topic (generic)
    generic_progression = manager._plan_concept_progression(
        topic_slug="unknown_topic",
        target_chapters=3,
        learner_level=LearningLevel.BEGINNER
    )
    
    assert len(generic_progression) == 3


@pytest.mark.asyncio
async def test_get_next_chapter_plan():
    """Test getting next chapter plan."""
    manager = SeriesManager()
    
    # Create series
    series = await manager.create_series(
        topic="Neural Networks",
        topic_slug="neural_networks",
        topic_category=TopicCategory.STEM,
        learner_name="Sam",
        learner_level=LearningLevel.INTERMEDIATE,
        age_band="teen",
        art_style="anime",
        target_chapters=5
    )
    
    # Get next chapter plan
    plan = await manager.get_next_chapter_plan(series["id"])
    
    assert plan["chapter_number"] == 1
    assert plan["total_chapters"] == 5
    assert len(plan["concepts_to_cover"]) > 0
    assert plan["previous_concepts"] == []
    assert plan["learner_name"] == "Sam"


@pytest.mark.asyncio
async def test_save_chapter():
    """Test saving a chapter."""
    manager = SeriesManager()
    
    # Create series
    series = await manager.create_series(
        topic="Test Topic",
        topic_slug="test_topic",
        topic_category=TopicCategory.STEM,
        learner_name="Test",
        learner_level=LearningLevel.BEGINNER,
        age_band="adult",
        art_style="cartoon",
        target_chapters=3
    )
    
    # Save chapter
    chapter_data = {
        "chapter_number": 1,
        "title": "Chapter 1: Introduction",
        "concepts_covered": ["basics", "fundamentals"],
        "story_pages": [
            {"page_number": 1, "text": "Test page 1"}
        ],
        "generation_time_ms": 5000
    }
    
    saved_chapter = await manager.save_chapter(series["id"], chapter_data)
    
    assert saved_chapter["id"] is not None
    assert saved_chapter["series_id"] == series["id"]
    assert saved_chapter["chapter_number"] == 1
    assert saved_chapter["concepts_covered"] == ["basics", "fundamentals"]
    
    # Verify series progress updated
    updated_series = await manager.get_series(series["id"])
    assert updated_series["current_chapter"] == 1
    assert len(updated_series["completed_chapters"]) == 1


@pytest.mark.asyncio
async def test_series_completion():
    """Test series completion detection."""
    manager = SeriesManager()
    
    # Create series with 2 chapters
    series = await manager.create_series(
        topic="Short Course",
        topic_slug="short_course",
        topic_category=TopicCategory.STEM,
        learner_name="Test",
        learner_level=LearningLevel.BEGINNER,
        age_band="adult",
        art_style="cartoon",
        target_chapters=2
    )
    
    # Save first chapter
    await manager.save_chapter(series["id"], {
        "chapter_number": 1,
        "concepts_covered": ["concept1"]
    })
    
    # Verify still active
    series_data = await manager.get_series(series["id"])
    assert series_data["status"] == "active"
    
    # Save second chapter
    await manager.save_chapter(series["id"], {
        "chapter_number": 2,
        "concepts_covered": ["concept2"]
    })
    
    # Verify completed
    series_data = await manager.get_series(series["id"])
    assert series_data["status"] == "completed"
    assert series_data["completed_at"] is not None


@pytest.mark.asyncio
async def test_save_character_bible():
    """Test saving character bible for series."""
    manager = SeriesManager()
    
    # Create series
    series = await manager.create_series(
        topic="Test Topic",
        topic_slug="test_topic",
        topic_category=TopicCategory.STEM,
        learner_name="Test",
        learner_level=LearningLevel.BEGINNER,
        age_band="adult",
        art_style="cartoon",
        target_chapters=3
    )
    
    # Save character bible
    bible = await manager.save_character_bible(
        series_id=series["id"],
        character_role="concept",
        character_name="Agent Alpha",
        character_bible="A friendly blue robot that teaches RL concepts",
        first_appearance_chapter=1,
        visual_seed=42
    )
    
    assert bible["id"] is not None
    assert bible["series_id"] == series["id"]
    assert bible["character_name"] == "Agent Alpha"
    assert bible["character_role"] == "concept"
    assert bible["visual_seed"] == 42
    assert 1 in bible["appearances_in_chapters"]


# ============================================
# INTEGRATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_full_educational_workflow():
    """Test complete educational storybook workflow."""
    # This is a high-level integration test
    
    # 1. Assess level
    assessment_service = LevelAssessmentService()
    level_result = await assessment_service.calibrate_level(
        topic="reinforcement_learning",
        topic_category=TopicCategory.STEM,
        self_reported_level=LearningLevel.BEGINNER,
        quiz_answers=None
    )
    
    assert level_result["calibrated_level"] == "beginner"
    
    # 2. Create series
    series_manager = SeriesManager()
    series = await series_manager.create_series(
        topic="Reinforcement Learning",
        topic_slug="reinforcement_learning",
        topic_category=TopicCategory.STEM,
        learner_name="Alex",
        learner_level=LearningLevel(level_result["calibrated_level"]),
        age_band="adult",
        art_style="cartoon",
        target_chapters=3
    )
    
    assert series["status"] == "active"
    
    # 3. Get next chapter plan
    plan = await series_manager.get_next_chapter_plan(series["id"])
    
    assert plan["chapter_number"] == 1
    assert len(plan["concepts_to_cover"]) > 0
    
    # 4. Concept characters would be created (mocked here)
    # 5. Story would be generated (mocked here)
    # 6. Chapter would be saved
    
    chapter_data = {
        "chapter_number": 1,
        "concepts_covered": plan["concepts_to_cover"],
        "story_pages": [{"page_number": 1, "text": "Test"}]
    }
    
    await series_manager.save_chapter(series["id"], chapter_data)
    
    # Verify progress
    updated_series = await series_manager.get_series(series["id"])
    assert updated_series["current_chapter"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
