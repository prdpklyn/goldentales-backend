# Lovable.dev Implementation Prompt: Educational Storybooks

## Overview
Implement an educational storybook feature that allows users to learn any topic (like reinforcement learning, history, chemistry) through illustrated stories. The system assesses learner level, creates personalized characters, and generates multi-chapter learning series.

---

## Backend API Endpoints (Already Implemented)

### Level Assessment
- `GET /api/v2/education/topics` - List available topic categories
- `GET /api/v2/education/quiz/{topic}` - Generate assessment quiz
- `POST /api/v2/education/assess` - Submit assessment and get calibrated level

### Series Management
- `POST /api/v2/education/series` - Create new learning series
- `GET /api/v2/education/series/{id}` - Get series details and progress
- `GET /api/v2/education/series/{id}/next` - Get next chapter plan
- `POST /api/v2/education/series/{id}/chapters` - Generate chapter

### Preview
- `POST /api/v2/education/preview` - Quick preview generation

**Note:** All endpoints require `X-API-Key` header.

---

## Database Tables (Run in Supabase)

```sql
-- See migrations/003_educational_tables.sql for full schema
-- Key tables:
-- - educational_topics (browse topics)
-- - learner_profiles (store assessments)
-- - learning_series (multi-chapter series)
-- - series_chapters (individual chapters)
-- - concept_characters (reusable concept characters)
```

---

## Frontend Components to Create

### 1. Topic Browser Component

**Component: `TopicBrowser.tsx`**

```typescript
interface TopicCategory {
  id: 'stem' | 'humanities' | 'languages' | 'arts' | 'business' | 'other';
  name: string;
  icon: string;
  topics: string[];
}

// Features:
// - Display 6 category cards in a grid
// - Each card expands to show available topics
// - Search/filter topics by name
// - Click topic to start learning flow
```

**Design:**
```
┌─────────────────────────────────────────┐
│  What would you like to learn?          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │   🔬     │ │   📚     │ │   🌍     │ │
│  │   STEM   │ │Humanities│ │Languages │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │   🎨     │ │   💼     │ │   ⭐     │ │
│  │   Arts   │ │ Business │ │  Other   │ │
│  └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────┘

When expanded:
┌─────────────────────────────────────────┐
│  STEM Topics                            │
│  ┌──────────────┐ ┌──────────────┐      │
│  │Reinforcement │ │Neural        │      │
│  │Learning      │ │Networks      │      │
│  └──────────────┘ └──────────────┘      │
│  ┌──────────────┐ ┌──────────────┐      │
│  │Photosynthesis│ │Solar System  │      │
│  └──────────────┘ └──────────────┘      │
│                                [Search] │
└─────────────────────────────────────────┘
```

**API Call:**
```typescript
const topics = await fetch('/api/v2/education/topics', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());
```

---

### 2. Level Assessment Component

**Component: `LevelAssessment.tsx`**

```typescript
interface LevelAssessmentProps {
  topic: string;
  topicCategory: string;
  onAssessmentComplete: (level: string, confidence: number) => void;
}

// Features:
// - Step 1: Self-report level (4 buttons)
// - Step 2: Optional quiz (5 questions)
// - Step 3: Show calibrated result
// - Progress indicator
```

**States:**
1. **Self-Report Selection**
```
┌─────────────────────────────────────────┐
│  How familiar are you with              │
│  Reinforcement Learning?                │
│                                          │
│  ┌────────────┐  ┌────────────┐         │
│  │  Beginner  │  │Intermediate│         │
│  │   🌱       │  │    🌿      │         │
│  │ Just       │  │ I know     │         │
│  │ starting   │  │ the basics │         │
│  └────────────┘  └────────────┘         │
│  ┌────────────┐  ┌────────────┐         │
│  │  Advanced  │  │   Expert   │         │
│  │    🌳      │  │    🎓      │         │
│  │ Strong     │  │ Deep       │         │
│  │ foundation │  │ expertise  │         │
│  └────────────┘  └────────────┘         │
│                                          │
│  [ ] Take a quick quiz for more         │
│      accurate assessment (optional)      │
└─────────────────────────────────────────┘
```

2. **Quiz Mode** (if opted in)
```
┌─────────────────────────────────────────┐
│  Question 2 of 5                    🔵🔵⚪⚪⚪│
│                                          │
│  What is an "agent" in reinforcement    │
│  learning?                               │
│                                          │
│  ○ A) A type of supervised learning     │
│  ● B) The learning entity that takes    │ <- Selected
│       actions in an environment         │
│  ○ C) The reward function               │
│  ○ D) The training dataset              │
│                                          │
│                    [Previous] [Next →]   │
└─────────────────────────────────────────┘
```

3. **Results**
```
┌─────────────────────────────────────────┐
│  Your Learning Level: Intermediate      │
│                                          │
│  📊 Confidence: 85%                     │
│                                          │
│  Quiz Score: 4/5 (80%)                  │
│  ├── Easy:   2/2 ✓                      │
│  ├── Medium: 2/2 ✓                      │
│  └── Hard:   0/1 ✗                      │
│                                          │
│  Based on your results, we'll create    │
│  content that builds on your existing   │
│  knowledge of basics.                   │
│                                          │
│          [Start Learning →]              │
└─────────────────────────────────────────┘
```

**API Calls:**
```typescript
// Generate quiz
const quiz = await fetch(
  `/api/v2/education/quiz/${topic}?topic_category=${category}&num_questions=5`,
  { headers: { 'X-API-Key': API_KEY } }
).then(r => r.json());

// Submit assessment
const result = await fetch('/api/v2/education/assess', {
  method: 'POST',
  headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic,
    topic_category: category,
    self_reported_level: 'beginner',
    quiz_answers: [
      { question_number: 1, selected_answer: 'B' },
      // ...
    ]
  })
}).then(r => r.json());
```

---

### 3. Learner Character Creator

**Component: `LearnerCharacterCreator.tsx`**

```typescript
interface LearnerCharacterCreatorProps {
  ageBand: 'child' | 'teen' | 'adult';
  onCharacterCreated: (character: LearnerCharacter) => void;
}

// Features:
// - Name input
// - Age band selection (affects story vocabulary)
// - Optional visual customization
// - Art style selection
```

**Design:**
```
┌─────────────────────────────────────────┐
│  Create Your Learning Character         │
│                                          │
│  Name: [___________________]             │
│                                          │
│  Age Group:                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │  Child  │ │  Teen   │ │  Adult  │    │
│  │  6-12   │ │  13-18  │ │   18+   │    │
│  └─────────┘ └─────────┘ └─────────┘    │
│                                          │
│  (This affects vocabulary and examples)  │
│                                          │
│  Art Style:                              │
│  [Cartoon ▼]                             │
│                                          │
│  ☐ Customize appearance (optional)       │
│                                          │
│               [Continue →]               │
└─────────────────────────────────────────┘
```

---

### 4. Series Creation Component

**Component: `SeriesCreator.tsx`**

```typescript
interface SeriesCreatorProps {
  topic: string;
  topicCategory: string;
  learnerLevel: string;
  character: LearnerCharacter;
  onSeriesCreated: (series: Series) => void;
}

// Features:
// - Show topic and level summary
// - Chapter count selection (3-10)
// - Toggle quiz between chapters
// - Create series button
```

**Design:**
```
┌─────────────────────────────────────────┐
│  Ready to Start Learning!               │
│                                          │
│  📚 Topic: Reinforcement Learning       │
│  📊 Level: Intermediate                 │
│  👤 Learner: Alex (Adult)               │
│  🎨 Style: Cartoon                      │
│                                          │
│  ─────────────────────────────────────  │
│                                          │
│  Number of Chapters:                     │
│  [──────●──────] 5 chapters             │
│                                          │
│  Your learning journey:                  │
│  Ch 1: Agents & Environments            │
│  Ch 2: States & Observations            │
│  Ch 3: Actions & Policies               │
│  Ch 4: Rewards & Value Functions        │
│  Ch 5: Learning & Exploration           │
│                                          │
│  ☑ Include quiz after each chapter      │
│                                          │
│        [Create My Learning Series]       │
└─────────────────────────────────────────┘
```

**API Call:**
```typescript
const series = await fetch('/api/v2/education/series', {
  method: 'POST',
  headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: 'Reinforcement Learning',
    topic_slug: 'reinforcement_learning',
    topic_category: 'stem',
    learner_name: 'Alex',
    learner_level: 'intermediate',
    age_band: 'adult',
    art_style: 'cartoon',
    target_chapters: 5,
    include_quiz_between_chapters: true
  })
}).then(r => r.json());
```

---

### 5. Series Dashboard

**Component: `SeriesDashboard.tsx`**

```typescript
interface SeriesDashboardProps {
  seriesId: string;
}

// Features:
// - Show series progress (chapters completed)
// - Display chapter list with status
// - Continue reading button
// - Generate next chapter button
```

**Design:**
```
┌─────────────────────────────────────────┐
│  Alex's Reinforcement Learning Journey  │
│                                          │
│  Progress: ███████░░░░░░░ 2/5 chapters  │
│                                          │
│  ┌───────────────────────────────────┐   │
│  │ ✅ Chapter 1: Agents & Environments│   │
│  │    Completed • Score: 80%         │   │
│  │    [Read Again]                   │   │
│  └───────────────────────────────────┘   │
│  ┌───────────────────────────────────┐   │
│  │ ✅ Chapter 2: States & Observations│   │
│  │    Completed • Score: 90%         │   │
│  │    [Read Again]                   │   │
│  └───────────────────────────────────┘   │
│  ┌───────────────────────────────────┐   │
│  │ 🔵 Chapter 3: Actions & Policies  │   │
│  │    Ready to generate              │   │
│  │    [Generate Chapter →]           │   │
│  └───────────────────────────────────┘   │
│  ┌───────────────────────────────────┐   │
│  │ ⚪ Chapter 4: Rewards & Value     │   │
│  │    Locked (complete Ch 3 first)   │   │
│  └───────────────────────────────────┘   │
│  ┌───────────────────────────────────┐   │
│  │ ⚪ Chapter 5: Learning & Exploration│  │
│  │    Locked                          │   │
│  └───────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**API Calls:**
```typescript
// Get series details
const series = await fetch(`/api/v2/education/series/${seriesId}`, {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());

// Get next chapter plan
const plan = await fetch(`/api/v2/education/series/${seriesId}/next`, {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());
```

---

### 6. Chapter Generation View

**Component: `ChapterGenerator.tsx`**

```typescript
interface ChapterGeneratorProps {
  seriesId: string;
  chapterNumber: number;
  conceptsToLearn: string[];
  onChapterReady: (chapter: Chapter) => void;
}

// Features:
// - Show what concepts will be taught
// - Optional custom focus input
// - Generation progress (2-5 minutes)
// - Preview when ready
```

**Design (Generating):**
```
┌─────────────────────────────────────────┐
│  Generating Chapter 3                    │
│  Actions & Policies                      │
│                                          │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │
│  │      🎨 Creating your story...  │    │
│  │                                 │    │
│  │      ███████████░░░░░░░░ 65%   │    │
│  │                                 │    │
│  │      ⏱ Estimated: 2 minutes    │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                          │
│  What we're creating:                    │
│  ✓ Story outline                         │
│  ✓ Concept characters                    │
│  → Page illustrations (6/10)            │
│  ○ Final review                          │
│                                          │
│  💡 Did you know? Agent Alpha was       │
│  created to help you understand...      │
└─────────────────────────────────────────┘
```

**API Call:**
```typescript
const chapter = await fetch(
  `/api/v2/education/series/${seriesId}/chapters`,
  {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      custom_focus: 'Include more real-world examples'
    })
  }
).then(r => r.json());
```

---

### 7. Chapter Reader

**Component: `ChapterReader.tsx`**

```typescript
interface ChapterReaderProps {
  chapter: Chapter;
  onComplete: () => void;
  onTakeQuiz: () => void;
}

// Features:
// - Page-by-page navigation
// - Full-page illustrations
// - Text overlay with teaching content
// - Progress bar
// - "Take Quiz" button at end
```

**Design:**
```
┌─────────────────────────────────────────┐
│  Chapter 3: Actions & Policies     ≡    │
│  Page 5 of 10                           │
│                                          │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │
│  │     [Illustration]              │    │
│  │     Alex and Agent Alpha        │    │
│  │     exploring the action space  │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                          │
│  "Agent Alpha looked at the choices     │
│  before them. 'Each action has          │
│  consequences,' Alpha explained.        │
│  'That's why we need a policy - a       │
│  strategy for choosing the best         │
│  action in each situation.'"            │
│                                          │
│  📚 Concept: Policies are strategies    │
│  that map states to actions.            │
│                                          │
│  [← Previous]  ●●●●●○○○○○  [Next →]     │
└─────────────────────────────────────────┘
```

---

### 8. Chapter Quiz Component

**Component: `ChapterQuiz.tsx`**

```typescript
interface ChapterQuizProps {
  seriesId: string;
  chapterNumber: number;
  questions: QuizQuestion[];
  onComplete: (score: number) => void;
}

// Features:
// - Questions based on chapter content
// - Immediate feedback after each answer
// - Final score with celebration
// - Unlock next chapter on completion
```

---

### 9. Concept Character Card

**Component: `ConceptCharacterCard.tsx`**

```typescript
interface ConceptCharacterCardProps {
  character: ConceptCharacter;
  onClick?: () => void;
}

// Features:
// - Display character visual
// - Show concept it represents
// - Personality traits
// - Expandable details
```

**Design:**
```
┌─────────────────────────────────────────┐
│  Meet the Characters                    │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │  🤖      │  │  🌍      │             │
│  │  Agent   │  │  World   │             │
│  │  Alpha   │  │  Grid    │             │
│  └──────────┘  └──────────┘             │
│  Represents:   Represents:              │
│  RL Agent      Environment              │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │  ⭐      │  │  🎓      │             │
│  │  Rewardy │  │  Prof.   │             │
│  │          │  │  Pi      │             │
│  └──────────┘  └──────────┘             │
│  Represents:   Represents:              │
│  Reward Signal Guide/Mentor             │
└─────────────────────────────────────────┘
```

---

## Page Updates Needed

### Home Page
- Add "Learn Any Topic" section
- Feature educational storybooks alongside children's books
- Show popular learning topics

### Navigation
- Add "Learn" menu item linking to topic browser
- Add "My Learning" for viewing user's series

### New Pages
- `/learn` - Topic browser
- `/learn/assess` - Level assessment
- `/learn/create` - Series creation
- `/learn/series/{id}` - Series dashboard
- `/learn/series/{id}/chapter/{num}` - Chapter reader

---

## State Management

### Learning Context

```typescript
interface LearningState {
  // Topic selection
  selectedTopic: string | null;
  topicCategory: string | null;
  
  // Assessment
  selfReportedLevel: string | null;
  calibratedLevel: string | null;
  quizResults: QuizResult | null;
  
  // Character
  learnerName: string;
  ageBand: 'child' | 'teen' | 'adult';
  artStyle: string;
  
  // Series
  currentSeriesId: string | null;
  currentChapter: number;
  
  // Progress
  completedChapters: string[];
  quizScores: Record<number, number>;
}

// Actions
type LearningAction =
  | { type: 'SELECT_TOPIC'; topic: string; category: string }
  | { type: 'SET_LEVEL'; level: string; confidence: number }
  | { type: 'SET_CHARACTER'; name: string; ageBand: string }
  | { type: 'CREATE_SERIES'; seriesId: string }
  | { type: 'COMPLETE_CHAPTER'; chapterNum: number; score: number }
  | { type: 'RESET' };
```

---

## UI/UX Guidelines

### Colors
- **STEM**: `#3B82F6` (blue)
- **Humanities**: `#8B5CF6` (purple)
- **Languages**: `#10B981` (green)
- **Arts**: `#F59E0B` (amber)
- **Business**: `#6366F1` (indigo)
- **Other**: `#EC4899` (pink)

### Level Badges
- **Beginner**: 🌱 Green badge
- **Intermediate**: 🌿 Blue badge
- **Advanced**: 🌳 Purple badge
- **Expert**: 🎓 Gold badge

### Progress Indicators
- **Chapter Completed**: ✅ Green check
- **In Progress**: 🔵 Blue dot
- **Locked**: ⚪ Gray, disabled

### Loading States
- **Quiz Loading**: Shimmer animation on question cards
- **Assessment**: Progress bar with "Calibrating..."
- **Chapter Generation**: Multi-step progress with time estimate
- **Page Turn**: Smooth slide animation

### Concept Characters
- Always show character name and what they represent
- Use consistent colors for same concept across chapters
- Animate entrance when character first appears in story

---

## Testing Checklist

### Topic Selection
- [ ] Can browse all 6 categories
- [ ] Topics display correctly
- [ ] Search/filter works
- [ ] Selecting topic advances flow

### Level Assessment
- [ ] Self-report buttons work
- [ ] Quiz questions display correctly
- [ ] Can skip quiz
- [ ] Results show correctly
- [ ] Calibrated level makes sense

### Series Creation
- [ ] All fields validate
- [ ] Chapter slider works (3-10)
- [ ] Concept progression displays
- [ ] Series creates successfully

### Chapter Generation
- [ ] Progress updates in real-time
- [ ] Handles long generation (2-5 min)
- [ ] Error handling works
- [ ] Can cancel and retry

### Chapter Reading
- [ ] Pages navigate correctly
- [ ] Images load
- [ ] Text is readable
- [ ] Concept highlights work
- [ ] Quiz unlocks at end

### Cross-Chapter Consistency
- [ ] Same characters appear consistently
- [ ] References to previous chapters work
- [ ] Progress saves correctly
- [ ] Can resume mid-chapter

---

## API Integration Notes

### Base URL
All education endpoints use: `{API_BASE_URL}/api/v2/education`

### Request Example (Create Series)

```typescript
const response = await fetch('/api/v2/education/series', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    topic: 'Reinforcement Learning',
    topic_slug: 'reinforcement_learning',
    topic_category: 'stem',
    learner_name: 'Alex',
    learner_level: 'intermediate',
    age_band: 'adult',
    art_style: 'cartoon',
    target_chapters: 5,
    include_quiz_between_chapters: true
  })
});

const series = await response.json();
// series.series_id - use for subsequent calls
// series.concept_progression - chapters outline
```

### Error Handling

```typescript
try {
  const result = await generateChapter(seriesId);
} catch (error) {
  if (error.status === 503) {
    // AI service busy - show retry with timer
    toast.error('Our AI is busy. Please try again in a moment.');
  } else if (error.status === 404) {
    // Series not found
    router.push('/learn');
  } else {
    toast.error('Something went wrong. Please try again.');
  }
}
```

---

## Success Metrics

After implementation, track:
- Topics selected (popularity)
- Assessment completion rate
- Quiz opt-in rate
- Series creation rate
- Chapters completed per series
- Quiz scores over time
- Return rate (users starting second series)

---

## FAQ for Users

Add to help section:
- "How does level assessment work?"
- "Can I change my level after starting?"
- "What are concept characters?"
- "How long does chapter generation take?"
- "Can I learn multiple topics at once?"
- "Will my character look the same in every chapter?"
