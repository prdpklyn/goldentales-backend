# app/services/level_assessment_service.py
"""
GoldenTales Level Assessment Service
====================================
Assesses learner's understanding level through self-report and optional quiz.
"""

import json
from typing import Dict, List, Optional, Any, Tuple

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException, ValidationException
from app.utils.json_parser import parse_story_json
from app.models.enums import LearningLevel, TopicCategory

logger = get_logger(__name__)


class LevelAssessmentService:
    """
    Service for assessing learner's proficiency level.
    
    Combines self-reported level with optional quiz results to determine
    the most appropriate content difficulty.
    
    Example:
        service = LevelAssessmentService()
        
        # Generate quiz
        quiz = await service.generate_quiz("reinforcement_learning")
        
        # Calibrate level
        result = await service.calibrate_level(
            topic="reinforcement_learning",
            self_reported=LearningLevel.BEGINNER,
            quiz_answers=[...]
        )
    """
    
    # Quiz difficulty by level
    QUIZ_DIFFICULTY_WEIGHTS = {
        LearningLevel.BEGINNER: {"easy": 4, "medium": 1, "hard": 0},
        LearningLevel.INTERMEDIATE: {"easy": 1, "medium": 3, "hard": 1},
        LearningLevel.ADVANCED: {"easy": 0, "medium": 2, "hard": 3},
        LearningLevel.EXPERT: {"easy": 0, "medium": 1, "hard": 4}
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the level assessment service.
        
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
    
    async def generate_quiz(
        self,
        topic: str,
        topic_category: TopicCategory,
        target_level: Optional[LearningLevel] = None,
        num_questions: int = 5,
        age_band: str = "adult"
    ) -> Dict[str, Any]:
        """
        Generate a quiz to assess learner's level.
        
        Args:
            topic: The topic to quiz about
            topic_category: Category of the topic
            target_level: Target difficulty (None for mixed)
            num_questions: Number of questions (default 5)
            age_band: Target age for appropriate language
            
        Returns:
            Dict with quiz_id, questions, and metadata
        """
        if not self.api_key:
            raise ValidationException("AI service not configured for quiz generation")
        
        # Build quiz generation prompt
        prompt = self._build_quiz_prompt(
            topic=topic,
            topic_category=topic_category,
            target_level=target_level,
            num_questions=num_questions,
            age_band=age_band
        )
        
        try:
            logger.info(f"Generating quiz for topic: {topic}")
            response_text = await self._call_gemini_with_retry(prompt)
            
            # Parse JSON response
            quiz_data = self._parse_quiz_response(response_text)
            
            # Validate quiz structure
            if not quiz_data.get("questions") or len(quiz_data["questions"]) < num_questions:
                raise ValidationException(f"Expected {num_questions} questions, got {len(quiz_data.get('questions', []))}")
            
            quiz_data["topic"] = topic
            quiz_data["topic_category"] = topic_category.value
            quiz_data["num_questions"] = len(quiz_data["questions"])
            
            logger.info(f"Generated quiz with {len(quiz_data['questions'])} questions")
            return quiz_data
            
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            raise ExternalServiceException(
                service_name="Gemini AI",
                message=f"Quiz generation failed: {str(e)}",
                is_transient=False
            )
    
    def _build_quiz_prompt(
        self,
        topic: str,
        topic_category: TopicCategory,
        target_level: Optional[LearningLevel],
        num_questions: int,
        age_band: str
    ) -> str:
        """Build prompt for quiz generation."""
        
        age_language = {
            "child": "simple language suitable for children ages 6-12",
            "teen": "clear language suitable for teenagers ages 13-18",
            "adult": "professional language for adult learners"
        }
        language_level = age_language.get(age_band, age_language["adult"])
        
        level_guidance = ""
        if target_level:
            level_guidance = f"Target difficulty: {target_level.value.upper()}"
        else:
            level_guidance = "Mix of difficulty levels (1-2 easy, 2-3 medium, 1-2 hard)"
        
        return f"""
Generate a {num_questions}-question quiz to assess understanding of: {topic}

TOPIC CATEGORY: {topic_category.value}
LANGUAGE: {language_level}
DIFFICULTY: {level_guidance}

REQUIREMENTS:
1. Questions should assess conceptual understanding, not just memorization
2. Include a mix of:
   - Conceptual questions (what/why)
   - Application questions (how/when)
   - Analysis questions (compare/contrast)
3. Each question should have 4 options with ONLY ONE correct answer
4. Include brief explanations for correct answers

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Clear, concise question",
      "options": [
        {{"id": "A", "text": "Option A text"}},
        {{"id": "B", "text": "Option B text"}},
        {{"id": "C", "text": "Option C text"}},
        {{"id": "D", "text": "Option D text"}}
      ],
      "correct_answer": "B",
      "explanation": "Brief explanation of why B is correct",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}

Generate EXACTLY {num_questions} questions. Return ONLY valid JSON, no markdown, no extra text.
"""
    
    def _parse_quiz_response(self, response_text: str) -> Dict[str, Any]:
        """Parse quiz generation response."""
        try:
            # Use robust JSON parser
            quiz_data = parse_story_json(response_text)
            
            # Validate structure
            if not isinstance(quiz_data, dict):
                raise ValueError("Quiz response must be a JSON object")
            if "questions" not in quiz_data:
                raise ValueError("Quiz must have 'questions' field")
            if not isinstance(quiz_data["questions"], list):
                raise ValueError("Questions must be a list")
            
            # Validate each question
            for q in quiz_data["questions"]:
                required_fields = ["question_number", "question_text", "options", "correct_answer"]
                for field in required_fields:
                    if field not in q:
                        raise ValueError(f"Question missing required field: {field}")
            
            return quiz_data
            
        except Exception as e:
            logger.error(f"Failed to parse quiz response: {e}")
            raise ValidationException(f"Invalid quiz format: {str(e)}")
    
    async def calibrate_level(
        self,
        topic: str,
        topic_category: TopicCategory,
        self_reported_level: LearningLevel,
        quiz_answers: Optional[List[Dict[str, str]]] = None,
        quiz_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calibrate learner's effective level.
        
        Combines self-reported level with quiz performance to determine
        the most appropriate content difficulty.
        
        Args:
            topic: The topic being assessed
            topic_category: Category of the topic
            self_reported_level: Learner's self-assessment
            quiz_answers: Optional list of quiz answers (question_number, selected_answer)
            quiz_data: Optional quiz data for scoring
            
        Returns:
            Dict with calibrated_level, confidence_score, and explanation
        """
        logger.info(f"Calibrating level for {topic}: self-reported={self_reported_level.value}")
        
        # If no quiz, return self-reported with lower confidence
        if not quiz_answers or not quiz_data:
            return {
                "calibrated_level": self_reported_level.value,
                "confidence_score": 0.6,
                "self_reported_level": self_reported_level.value,
                "quiz_taken": False,
                "explanation": "Level based on self-report only. Taking a quiz will improve accuracy."
            }
        
        # Score the quiz
        quiz_result = self._score_quiz(quiz_data, quiz_answers)
        
        # Calibrate based on self-report and quiz
        calibrated = self._calibrate_with_quiz(
            self_reported_level,
            quiz_result
        )
        
        return {
            "calibrated_level": calibrated["level"].value,
            "confidence_score": calibrated["confidence"],
            "self_reported_level": self_reported_level.value,
            "quiz_taken": True,
            "quiz_score": quiz_result["score"],
            "quiz_breakdown": quiz_result["breakdown"],
            "explanation": calibrated["explanation"]
        }
    
    def _score_quiz(
        self,
        quiz_data: Dict[str, Any],
        quiz_answers: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Score quiz answers."""
        
        questions = quiz_data.get("questions", [])
        answers_map = {ans["question_number"]: ans["selected_answer"] for ans in quiz_answers}
        
        total = 0
        correct = 0
        breakdown = {"easy": {"total": 0, "correct": 0}, 
                    "medium": {"total": 0, "correct": 0},
                    "hard": {"total": 0, "correct": 0}}
        
        for q in questions:
            q_num = q["question_number"]
            difficulty = q.get("difficulty", "medium")
            
            total += 1
            breakdown[difficulty]["total"] += 1
            
            if q_num in answers_map:
                if answers_map[q_num] == q["correct_answer"]:
                    correct += 1
                    breakdown[difficulty]["correct"] += 1
        
        score = correct / total if total > 0 else 0.0
        
        return {
            "score": round(score, 2),
            "correct": correct,
            "total": total,
            "breakdown": breakdown
        }
    
    def _calibrate_with_quiz(
        self,
        self_reported: LearningLevel,
        quiz_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calibrate level based on self-report and quiz performance.
        
        Algorithm:
        1. Start with self-reported level
        2. Adjust based on quiz score
        3. Consider performance by difficulty
        4. Calculate confidence score
        """
        score = quiz_result["score"]
        breakdown = quiz_result["breakdown"]
        
        # Map self-reported to numeric scale
        level_scale = {
            LearningLevel.BEGINNER: 1,
            LearningLevel.INTERMEDIATE: 2,
            LearningLevel.ADVANCED: 3,
            LearningLevel.EXPERT: 4
        }
        
        reported_numeric = level_scale[self_reported]
        
        # Adjust based on overall score
        adjustment = 0
        if score >= 0.9:
            adjustment = 1  # Potentially one level higher
        elif score >= 0.7:
            adjustment = 0  # Accurate self-assessment
        elif score >= 0.5:
            adjustment = -1  # Possibly one level lower
        else:
            adjustment = -1  # Likely overestimated
        
        # Fine-tune based on difficulty breakdown
        hard_questions = breakdown.get("hard", {})
        if hard_questions.get("total", 0) > 0:
            hard_rate = hard_questions["correct"] / hard_questions["total"]
            if hard_rate >= 0.7 and adjustment >= 0:
                adjustment = min(adjustment + 1, 1)  # Cap at +1
        
        easy_questions = breakdown.get("easy", {})
        if easy_questions.get("total", 0) > 0:
            easy_rate = easy_questions["correct"] / easy_questions["total"]
            if easy_rate < 0.5 and adjustment <= 0:
                adjustment = max(adjustment - 1, -2)  # Cap at -2
        
        # Calculate final level
        calibrated_numeric = max(1, min(4, reported_numeric + adjustment))
        
        # Map back to enum
        numeric_to_level = {
            1: LearningLevel.BEGINNER,
            2: LearningLevel.INTERMEDIATE,
            3: LearningLevel.ADVANCED,
            4: LearningLevel.EXPERT
        }
        
        calibrated_level = numeric_to_level[calibrated_numeric]
        
        # Calculate confidence score
        # High score = high confidence
        # Agreement between self-report and quiz = high confidence
        agreement_bonus = 0.2 if adjustment == 0 else 0.0
        confidence = min(0.95, score * 0.75 + agreement_bonus + 0.2)
        
        # Generate explanation
        if adjustment == 0:
            explanation = f"Quiz confirms {self_reported.value} level. Strong match between self-assessment and performance."
        elif adjustment > 0:
            explanation = f"Quiz suggests {calibrated_level.value} level. Performance exceeded self-assessment."
        else:
            explanation = f"Quiz suggests {calibrated_level.value} level. Recommend starting at this level for optimal learning."
        
        return {
            "level": calibrated_level,
            "confidence": round(confidence, 2),
            "explanation": explanation
        }
