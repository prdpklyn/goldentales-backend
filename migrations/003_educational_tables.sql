-- Educational Feature Tables for Supabase
-- Run this in Supabase SQL Editor
-- =========================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================
-- EDUCATIONAL TOPICS TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS educational_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Topic identification
    topic_name VARCHAR(200) NOT NULL,
    topic_slug VARCHAR(200) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,           -- 'stem', 'humanities', etc.
    
    -- Topic metadata
    description TEXT,
    prerequisites JSONB DEFAULT '[]'::jsonb,  -- List of prerequisite topic slugs
    difficulty_mapping JSONB DEFAULT '{}'::jsonb, -- Maps levels to complexity
    
    -- Content structure
    suggested_chapters INT DEFAULT 5,
    key_concepts JSONB DEFAULT '[]'::jsonb,   -- List of main concepts to cover
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topics_category ON educational_topics(category);
CREATE INDEX IF NOT EXISTS idx_topics_slug ON educational_topics(topic_slug);
CREATE INDEX IF NOT EXISTS idx_topics_active ON educational_topics(is_active);

-- =========================================
-- LEARNER PROFILES TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS learner_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Learner identification
    learner_name VARCHAR(100) NOT NULL,
    age_band VARCHAR(20),                     -- 'child', 'teen', 'adult'
    
    -- Level assessment
    topic_slug VARCHAR(200),
    self_reported_level VARCHAR(50),          -- 'beginner', 'intermediate', etc.
    quiz_results JSONB DEFAULT '{}'::jsonb,   -- Quiz questions and answers
    calibrated_level VARCHAR(50),             -- Final assessed level
    confidence_score DECIMAL(3,2),            -- 0.00 to 1.00
    
    -- Character details (if personalized)
    character_bible JSONB DEFAULT '{}'::jsonb, -- Main learner character description
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learner_topic ON learner_profiles(topic_slug);
CREATE INDEX IF NOT EXISTS idx_learner_level ON learner_profiles(calibrated_level);

-- =========================================
-- LEARNING SERIES TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS learning_series (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Series identification
    title VARCHAR(300) NOT NULL,
    topic_slug VARCHAR(200),
    topic_category VARCHAR(50) NOT NULL,
    
    -- Learner details
    learner_profile_id UUID REFERENCES learner_profiles(id),
    learner_name VARCHAR(100) NOT NULL,
    learner_level VARCHAR(50) NOT NULL,
    age_band VARCHAR(20) NOT NULL,
    
    -- Series structure
    target_chapters INT DEFAULT 5,
    current_chapter INT DEFAULT 0,
    concept_progression JSONB DEFAULT '[]'::jsonb, -- Ordered list of concepts
    
    -- Visual consistency
    art_style VARCHAR(50) NOT NULL,
    series_character_bible JSONB DEFAULT '{}'::jsonb, -- All character descriptions
    
    -- Learning features
    include_quiz_between_chapters BOOLEAN DEFAULT false,
    
    -- Progress tracking
    completed_chapters JSONB DEFAULT '[]'::jsonb, -- List of completed chapter IDs
    quiz_scores JSONB DEFAULT '[]'::jsonb,        -- Chapter quiz results
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',      -- 'active', 'completed', 'abandoned'
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_series_topic ON learning_series(topic_slug);
CREATE INDEX IF NOT EXISTS idx_series_learner ON learning_series(learner_profile_id);
CREATE INDEX IF NOT EXISTS idx_series_status ON learning_series(status);

-- =========================================
-- SERIES CHAPTERS TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS series_chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Chapter identification
    series_id UUID NOT NULL REFERENCES learning_series(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(300) NOT NULL,
    
    -- Chapter content
    concepts_covered JSONB DEFAULT '[]'::jsonb,   -- Concepts taught in this chapter
    story_pages JSONB NOT NULL,                   -- Full story content with scenes
    
    -- Visual content
    cover_url TEXT,
    page_images JSONB DEFAULT '[]'::jsonb,        -- URLs for all page illustrations
    
    -- Character data for this chapter
    characters_used JSONB DEFAULT '{}'::jsonb,    -- Character bibles for this chapter
    
    -- Learning assessment
    quiz_questions JSONB DEFAULT '[]'::jsonb,     -- Optional quiz for this chapter
    quiz_score DECIMAL(3,2),                      -- If quiz was taken
    
    -- Metadata
    generation_time_ms INT,
    custom_focus TEXT,                            -- User-specified custom focus
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Constraints
    UNIQUE(series_id, chapter_number)
);

CREATE INDEX IF NOT EXISTS idx_chapters_series ON series_chapters(series_id);
CREATE INDEX IF NOT EXISTS idx_chapters_number ON series_chapters(series_id, chapter_number);

-- =========================================
-- CONCEPT CHARACTERS TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS concept_characters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Character identification
    character_name VARCHAR(100) NOT NULL,
    character_slug VARCHAR(100) NOT NULL,
    character_type VARCHAR(50) NOT NULL,      -- 'agent', 'environment', 'process', etc.
    
    -- Associated topic/concept
    topic_slug VARCHAR(200),
    concept_name VARCHAR(200) NOT NULL,       -- The concept this character represents
    
    -- Visual description
    character_bible TEXT NOT NULL,            -- Full consistent description
    visual_traits JSONB DEFAULT '{}'::jsonb,  -- Key visual markers
    
    -- Usage tracking
    art_style_variants JSONB DEFAULT '{}'::jsonb, -- Different versions per art style
    reference_images JSONB DEFAULT '[]'::jsonb,   -- URLs to generated reference images
    
    -- Metadata
    is_reusable BOOLEAN DEFAULT true,         -- Can be reused across series
    usage_count INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(character_slug, topic_slug)
);

CREATE INDEX IF NOT EXISTS idx_concept_chars_topic ON concept_characters(topic_slug);
CREATE INDEX IF NOT EXISTS idx_concept_chars_concept ON concept_characters(concept_name);
CREATE INDEX IF NOT EXISTS idx_concept_chars_type ON concept_characters(character_type);
CREATE INDEX IF NOT EXISTS idx_concept_chars_reusable ON concept_characters(is_reusable);

-- =========================================
-- SERIES CHARACTER BIBLES TABLE
-- =========================================
CREATE TABLE IF NOT EXISTS series_character_bibles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Series reference
    series_id UUID NOT NULL REFERENCES learning_series(id) ON DELETE CASCADE,
    
    -- Character data
    character_role VARCHAR(50) NOT NULL,      -- 'learner', 'guide', 'concept'
    character_name VARCHAR(100) NOT NULL,
    character_bible TEXT NOT NULL,            -- Full description for consistency
    
    -- Visual reference
    reference_image_url TEXT,
    visual_seed INT,                          -- Seed for consistent generation
    
    -- Usage tracking
    first_appearance_chapter INT,
    appearances_in_chapters JSONB DEFAULT '[]'::jsonb, -- List of chapter numbers
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(series_id, character_name)
);

CREATE INDEX IF NOT EXISTS idx_series_bibles_series ON series_character_bibles(series_id);
CREATE INDEX IF NOT EXISTS idx_series_bibles_role ON series_character_bibles(character_role);

-- =========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =========================================

-- Enable RLS on all tables
ALTER TABLE educational_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE series_chapters ENABLE ROW LEVEL SECURITY;
ALTER TABLE concept_characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE series_character_bibles ENABLE ROW LEVEL SECURITY;

-- Public read access for topics (anyone can browse topics)
CREATE POLICY "Topics are viewable by everyone"
    ON educational_topics FOR SELECT
    USING (is_active = true);

-- Concept characters can be viewed by everyone (for reuse)
CREATE POLICY "Concept characters are viewable by everyone"
    ON concept_characters FOR SELECT
    USING (is_reusable = true);

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role has full access to educational_topics"
    ON educational_topics FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role has full access to learner_profiles"
    ON learner_profiles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role has full access to learning_series"
    ON learning_series FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role has full access to series_chapters"
    ON series_chapters FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role has full access to concept_characters"
    ON concept_characters FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role has full access to series_character_bibles"
    ON series_character_bibles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- =========================================
-- TRIGGERS FOR UPDATED_AT
-- =========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER update_educational_topics_updated_at
    BEFORE UPDATE ON educational_topics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learner_profiles_updated_at
    BEFORE UPDATE ON learner_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learning_series_updated_at
    BEFORE UPDATE ON learning_series
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_concept_characters_updated_at
    BEFORE UPDATE ON concept_characters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_series_character_bibles_updated_at
    BEFORE UPDATE ON series_character_bibles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- SEED DATA (Optional)
-- =========================================

-- Insert some common topics
INSERT INTO educational_topics (topic_name, topic_slug, category, description, suggested_chapters, key_concepts, is_active)
VALUES 
    ('Reinforcement Learning', 'reinforcement_learning', 'stem', 'Learn the fundamentals of reinforcement learning through interactive stories', 5, '["agents", "environments", "rewards", "policies", "learning"]'::jsonb, true),
    ('Neural Networks', 'neural_networks', 'stem', 'Understand how neural networks work and learn', 5, '["neurons", "layers", "backpropagation", "training", "applications"]'::jsonb, true),
    ('Photosynthesis', 'photosynthesis', 'stem', 'Discover how plants convert sunlight into energy', 4, '["chloroplasts", "light reactions", "carbon dioxide", "glucose production"]'::jsonb, true)
ON CONFLICT (topic_slug) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Educational feature tables created successfully!';
    RAISE NOTICE 'Total tables created: 6';
    RAISE NOTICE '- educational_topics';
    RAISE NOTICE '- learner_profiles'; 
    RAISE NOTICE '- learning_series';
    RAISE NOTICE '- series_chapters';
    RAISE NOTICE '- concept_characters';
    RAISE NOTICE '- series_character_bibles';
END $$;
