# Lovable.dev Implementation Prompt: Premium & Ultra Tiers

## Overview
Implement Premium and Ultra tier book creation with photo-to-character transformation and tier selection UI.

---

## Backend API Endpoints (Already Implemented)

### Photo Character
- `POST /api/v2/photo/validate` - Validate photo for character transformation
- `POST /api/v2/photo/preview` - Generate character preview
- `POST /api/v2/photo/approve/{preview_id}` - Approve character preview

### Books V2
- `POST /api/v2/books/create` - Create book with tier selection
- `GET /api/v2/books/{book_id}` - Get book details
- `POST /api/v2/books/{book_id}/regenerate-page/{page_number}` - Regenerate page

**Note:** Pricing is handled by Shopify. The backend focuses on story, character, and print generation.

---

## Database Migration

### Add `tier` Column to Stories Table

```sql
-- Add tier column to stories table
ALTER TABLE stories 
ADD COLUMN tier VARCHAR(20) DEFAULT 'basic' CHECK (tier IN ('basic', 'premium', 'ultra'));

-- Add character_reference_url for Ultra tier
ALTER TABLE stories
ADD COLUMN character_reference_url TEXT;

-- Add is_photo_based flag
ALTER TABLE stories
ADD COLUMN is_photo_based BOOLEAN DEFAULT false;

-- Create index for tier queries
CREATE INDEX idx_stories_tier ON stories(tier);

-- Update existing records to 'basic' tier
UPDATE stories SET tier = 'basic' WHERE tier IS NULL;

COMMENT ON COLUMN stories.tier IS 'Book pricing tier: basic, premium, or ultra';
COMMENT ON COLUMN stories.character_reference_url IS 'URL of transformed character image (Ultra tier only)';
COMMENT ON COLUMN stories.is_photo_based IS 'Whether the book uses photo-to-character transformation';
```

---

## Frontend Components to Create

### 1. Tier Selection Component

**Component: `TierSelector.tsx`**

```typescript
interface Tier {
  id: 'basic' | 'premium' | 'ultra';
  name: string;
  badge?: string;  // "POPULAR" | "NEW"
  description: string;
  features: string[];
  prices: {
    digital: number;
    softcover: number;
    hardcover: number;
  };
}

// Features:
// - Display 3 tier cards side by side (mobile: stack)
// - Highlight selected tier with border/shadow
// - Show badge (POPULAR for Premium, NEW for Ultra)
// - Display price based on selected format
// - Click to select tier
```

**Design:**
- Basic: Simple card, white background
- Premium: Highlighted card, gradient border, "POPULAR" badge (top-right)
- Ultra: Premium styling + gradient background, "NEW" badge

**Note:** Tier pricing should be managed in Shopify products, not fetched from backend.

---

### 2. Photo Upload Component (Ultra Tier)

**Component: `PhotoUploader.tsx`**

```typescript
interface PhotoUploaderProps {
  onPhotoValidated: (photoUrl: string) => void;
  onValidationError: (error: string) => void;
}

// Features:
// - Drag-and-drop or click to upload
// - Preview uploaded image
// - Call validation API: POST /api/v2/photo/validate
// - Show validation result (face detected, quality check)
// - Display issues if validation fails
// - Progress indicator during upload/validation
```

**States:**
1. Empty: Show upload zone with icon
2. Uploading: Progress bar
3. Validating: Spinner with "Detecting face..."
4. Valid: Green checkmark + "Photo validated!"
5. Invalid: Red X + error messages

**API Calls:**
```typescript
// 1. Upload to storage (Supabase Storage)
const { data: { publicUrl } } = await supabase.storage
  .from('photos')
  .upload(`${userId}/${filename}`, file);

// 2. Validate
const validation = await fetch('/api/v2/photo/validate', {
  method: 'POST',
  body: JSON.stringify({ photo_url: publicUrl })
});
```

---

### 3. Character Preview Component

**Component: `CharacterPreview.tsx`**

```typescript
interface CharacterPreviewProps {
  photoUrl: string;
  artStyle: string;
  onApproved: (characterReferenceUrl: string) => void;
  onRegenerate: () => void;
}

// Features:
// - Show original photo and transformed character side-by-side
// - Arrow between images
// - "Is this your child?" heading
// - "Yes, looks great! 👍" button (primary)
// - "Try again 🔄" button (secondary)
// - Loading state during transformation (30-60 seconds)
// - Show art style used
```

**Layout:**
```
┌─────────────────────────────────────────┐
│  Is this your child?                     │
│                                          │
│  ┌────────┐    ➡️    ┌────────┐        │
│  │ Photo  │         │Cartoon │         │
│  │        │         │Version │         │
│  └────────┘         └────────┘         │
│   Original        Watercolor Style      │
│                                          │
│  [Yes, looks great! 👍] [Try again 🔄] │
└─────────────────────────────────────────┘
```

**API Calls:**
```typescript
// 1. Generate preview
const preview = await fetch('/api/v2/photo/preview', {
  method: 'POST',
  body: JSON.stringify({
    photo_url: photoUrl,
    art_style: artStyle,
    preserve_likeness: 0.8
  })
});

// 2. Approve
const approval = await fetch(`/api/v2/photo/approve/${preview.preview_id}`, {
  method: 'POST'
});
```

---

### 4. Book Creation Flow (Updated)

**Component: `CreateBookFlow.tsx`**

Update existing flow to support tiers:

```typescript
// Step 1: Tier Selection
<TierSelector 
  selectedTier={tier}
  onSelectTier={setTier}
  selectedFormat={format}
/>

// Step 2: Character Details (existing)
<CharacterDetailsForm {...} />

// Step 2.5: Photo Upload (if Ultra tier selected)
{tier === 'ultra' && (
  <>
    <PhotoUploader 
      onPhotoValidated={setPhotoUrl}
      onValidationError={handleError}
    />
    {photoUrl && (
      <CharacterPreview
        photoUrl={photoUrl}
        artStyle={artStyle}
        onApproved={setCharacterReferenceUrl}
        onRegenerate={handleRegenerate}
      />
    )}
  </>
)}

// Step 3: Story Settings (existing)
<StorySettingsForm {...} />

// Step 4: Review & Create
<BookSummary 
  tier={tier}
  prices={prices}
  isPhotoBased={tier === 'ultra'}
/>
```

---

### 5. Pricing Display Component

**Component: `PricingCard.tsx`**

Display pricing based on tier selection:

```typescript
interface PricingCardProps {
  tier: 'basic' | 'premium' | 'ultra';
  format: 'digital' | 'softcover' | 'hardcover';
  price: number;
}

// Features:
// - Show format icon
// - Display price prominently
// - Show savings compared to Basic (for Premium/Ultra)
// - "Best Value" badge for Premium Hardcover
```

---

### 6. Feature Comparison Modal

**Component: `TierComparisonModal.tsx`**

Help users choose the right tier:

```typescript
// API Call:
const comparison = await fetch('/api/v2/pricing/compare');

// Display table:
// Feature                 | Basic | Premium | Ultra
// -------------------------|-------|---------|-------
// AI Character            |   ✓   |    ✓    |   
// Photo-to-Character      |       |         |   ✓
// Full-Page Illustrations |       |    ✓    |   ✓
// Text Overlays           |       |    ✓    |   ✓
// Speech Bubbles          |       |    ✓    |   ✓
// Enhanced Typography     |       |    ✓    |   ✓
```

---

## Page Updates Needed

### Home Page
- Add tier selection section
- Highlight Premium tier as most popular
- Add "Transform Your Child's Photo" CTA for Ultra tier

### Book Creation Page
- Replace single-tier flow with tier selector
- Conditionally show photo upload for Ultra tier
- Update pricing display to show tier-based prices

### Pricing Page (if exists)
- Update with 3-tier pricing
- Add feature comparison table
- Add FAQs about photo requirements (Ultra tier)

---

## State Management

### Book Creation Context

```typescript
interface BookCreationState {
  // Tier selection
  tier: 'basic' | 'premium' | 'ultra';
  
  // Photo (Ultra tier)
  photoUrl?: string;
  photoValidated: boolean;
  characterPreviewId?: string;
  characterReferenceUrl?: string;
  
  // Existing fields
  childName: string;
  childAge: number;
  theme: string;
  artStyle: string;
  // ... other fields
}
```

---

## UI/UX Guidelines

### Colors
- **Basic Tier**: `#3B82F6` (blue)
- **Premium Tier**: `#8B5CF6` (purple) - Gradient border
- **Ultra Tier**: `#EC4899` (pink) - Gradient background

### Badges
- **POPULAR**: Orange badge, top-right of Premium card
- **NEW**: Green badge with sparkle emoji, top-right of Ultra card

### Loading States
- **Photo Upload**: Progress bar with percentage
- **Validation**: Spinner with "Detecting face..." message
- **Character Transform**: Skeleton + "Creating your character... (30-60s)" message
- **Book Generation**: Progress bar showing: "Generating story... (1/3)"

### Error Handling
- **Photo Validation Failed**: Show specific issues (e.g., "No face detected", "Photo too blurry")
- **Character Transform Failed**: "Try again" button with different photo
- **API Error**: Toast notification with retry option

---

## Testing Checklist

### Basic Tier
- [ ] Can create book with AI character
- [ ] Pricing displays correctly
- [ ] No photo upload shown

### Premium Tier
- [ ] Can create book with full-page layout
- [ ] Pricing displays correctly
- [ ] "POPULAR" badge shown

### Ultra Tier
- [ ] Photo upload appears
- [ ] Photo validation works
- [ ] Character preview generates
- [ ] Can approve/regenerate character
- [ ] Character reference passed to book creation
- [ ] "NEW" badge shown
- [ ] Pricing displays correctly

### Edge Cases
- [ ] Photo upload fails gracefully
- [ ] Face not detected - shows clear error
- [ ] User cancels during character preview
- [ ] Preview expires after 1 hour
- [ ] Can switch tiers mid-flow
- [ ] Tier selection persists on page reload

---

## API Integration Notes

### Base URL
All V2 endpoints use: `{API_BASE_URL}/api/v2`

### Request Example (Create Ultra Book)

```typescript
const response = await fetch('/api/v2/books/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    tier: 'ultra',
    child_name: 'Emma',
    child_age: 6,
    child_gender: 'girl',
    skin_tone: 'light skin',
    hair_color: 'brown hair',
    hair_style: 'pigtails',
    eye_color: 'blue eyes',
    body_type: 'average',
    theme: 'christmas',
    art_style: 'watercolor',
    character_reference_url: 'https://...', // From approved preview
    has_glasses: false,
    has_freckles: true,
    has_dimples: true,
    additional_characters: []
  })
});

const book = await response.json();
// book.tier === 'ultra'
// book.is_photo_based === true
// book.prices === { digital: 19.99, softcover: 49.99, hardcover: 69.99 }
```

---

## Environment Variables

Add to `.env`:

```bash
# Supabase Storage (for photo uploads)
VITE_SUPABASE_STORAGE_BUCKET=photos
```

---

## Success Metrics

After implementation, track:
- Tier selection distribution (Basic vs Premium vs Ultra)
- Photo upload success rate (Ultra tier)
- Character preview approval rate
- Conversion rate by tier
- Average order value by tier

---

## Support & Documentation

### Photo Requirements (Ultra Tier)
Document for users:
- Clear, front-facing photo
- Good lighting
- Single person in frame
- Face clearly visible (no sunglasses/masks)
- Minimum resolution: 512x512px
- Supported formats: JPEG, PNG

### FAQ Additions
- "What's the difference between tiers?"
- "How does photo-to-character work?"
- "Can I change tiers after creation?"
- "What if my photo doesn't work?"
