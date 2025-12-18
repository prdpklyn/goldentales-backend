# AI Prompts & Character Consistency

**Last Updated**: December 2024

This document outlines the prompt engineering strategies used in GoldenTales to ensure high-quality, consistent story generation and illustration.

## 🧠 Core Strategy: "The Character Bible"

The central mechanism for character consistency is the **Character Bible**. This is a detailed text description generated *before* the story or images are created.

- **Source Code**: `character_system.py` -> `CharacterDescriptionGenerator.generate_full_character_bible`
- **Usage**: This description is **prepended** to every single image generation prompt.

### Bible Structure
The bible is a JSON object containing:
1.  `main_character`: A dense, comma-separated list of visual traits.
2.  `main_character_short`: A concise version for narrative context.
3.  `additional_characters`: Descriptions of side characters (pets, siblings).

**Example Bible Entry:**
> "Emma, a 6-year-old girl named Emma with light skin, brown hair in pigtails style, and blue eyes, wearing small round pink glasses, with freckles, wearing purple clothes"

---

## 📝 Story Generation Prompts

**Service**: `app/services/story_generator.py`
**Model**: Google Gemini 2.0 Flash

### Prompt Template
The system uses a structured prompt instructing Gemini to return strict JSON.

```text
You are creating a 10-page children's storybook. The main character must be described CONSISTENTLY.

=== MAIN CHARACTER (use this EXACT description in scene descriptions) ===
{character_bible}

=== STORY SETTINGS ===
Theme: {theme}
Occasion: {occasion}

=== REQUIREMENTS ===
1. {child_name} is the HERO
2. Each page: 2-3 sentences (25-40 words max)
3. Story arc: Setup (1-3) -> Adventure (4-7) -> Resolution (8-10)
4. CRITICAL: In scene_description, ALWAYS describe the main character using the EXACT details above

=== OUTPUT FORMAT ===
Return ONLY a JSON array:
[
  {
    "page_number": 1,
    "text": "...",
    "scene_description": "MUST include: [character's full appearance description]. Scene: [setting details]",
    "character_action": "...",
    "mood": "..."
  }
]
```

---

## 🎨 Image Generation Prompts

**Service**: `character_system.py` / `app/services/image_generator.py`
**Model**: Fal.ai Flux Pro (Standard/Print), Flux Schnell (Preview)

### Prompt Construction
The prompt is assembled dynamically for every page:

1.  **Character Anchor**: `MAIN CHARACTER (must match exactly): {bible_description}`
2.  **Scene Context**: `SCENE: {scene_description_from_story_gen}`
3.  **Action**: `ACTION: The main character is {action}`
4.  **Style modifiers**: Based on selected art style (e.g., "watercolor", "pixar").
5.  **Quality Boosters**: "Professional children's book illustration, high detail..."

### Style Presets
Defined in `character_system.py`:
- **Watercolor**: "soft watercolor illustration style, gentle flowing colors..."
- **Pixar**: "3D animated style illustration, Pixar-quality, soft lighting..."
- **Storybook**: "classic children's book illustration, warm nostalgic colors..."

---

## 📷 Photo Analysis Prompts (Ultra Tier)

**Service**: `character_system.py` -> `analyze_photo_for_character`
**Model**: Gemini 2.0 Flash (Vision)

When a user uploads a photo, we use Gemini Vision to "reverse engineer" the text description.

**Analysis Prompt:**
> "Analyze this photo of a child and extract visual characteristics for an illustrated character. Provide a JSON response with these fields: gender_presentation, estimated_age, skin_tone, hair_color, hair_style, eye_color, distinctive_features..."

This extracted data allows us to build a `CharacterProfile` that matches the real child's appearance, which then feeds into the standard Character Bible flow.
