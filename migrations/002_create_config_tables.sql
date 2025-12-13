-- Migration: 002_create_config_tables
-- Description: Create tables for AI model configs, prompt templates, and feature flags
-- GoldenTales Configuration Management Schema

-- ============================================
-- AI Model Configurations
-- ============================================
CREATE TABLE IF NOT EXISTS ai_model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL,          -- 'fal', 'gemini', 'openai', 'replicate', 'anthropic'
    model_id VARCHAR(200) NOT NULL,         -- Provider-specific model identifier
    quality_tier VARCHAR(20) NOT NULL,      -- 'preview', 'standard', 'print'
    parameters JSONB NOT NULL DEFAULT '{}', -- Model-specific parameters
    cost_per_call DECIMAL(10,4) DEFAULT 0,  -- Estimated cost per API call
    avg_latency_ms INT DEFAULT 0,           -- Average response time in ms
    is_active BOOLEAN DEFAULT true,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for common lookups
CREATE INDEX IF NOT EXISTS idx_ai_configs_tier_active
    ON ai_model_configs(quality_tier, is_active)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_ai_configs_provider
    ON ai_model_configs(provider);

-- Insert default configurations
INSERT INTO ai_model_configs (name, provider, model_id, quality_tier, parameters, cost_per_call, avg_latency_ms)
VALUES
    ('fal_preview', 'fal', 'fal-ai/flux/schnell', 'preview',
     '{"image_size": {"width": 800, "height": 600}, "num_inference_steps": 4, "guidance_scale": 3.5}',
     0.02, 2000),
    ('fal_standard', 'fal', 'fal-ai/flux/dev', 'standard',
     '{"image_size": {"width": 1024, "height": 768}, "num_inference_steps": 28, "guidance_scale": 3.5}',
     0.05, 5000),
    ('fal_print', 'fal', 'fal-ai/flux-pro/v1.1', 'print',
     '{"image_size": {"width": 2400, "height": 1800}, "num_inference_steps": 50, "guidance_scale": 3.5}',
     0.10, 15000),
    ('gemini_story', 'gemini', 'gemini-1.5-flash', 'standard',
     '{"temperature": 0.8, "max_output_tokens": 4096, "top_p": 0.95}',
     0.01, 3000)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- Prompt Templates
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,          -- 'story', 'image', 'character', 'scene', 'system'
    template TEXT NOT NULL,
    variables JSONB NOT NULL DEFAULT '[]',  -- List of required variable names
    description TEXT,
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_prompts_name_active
    ON prompt_templates(name, is_active)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_prompts_category
    ON prompt_templates(category);

-- ============================================
-- Feature Flags
-- ============================================
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_enabled BOOLEAN DEFAULT false,
    rollout_percentage INT DEFAULT 0 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    strategy VARCHAR(20) DEFAULT 'percentage',  -- 'all', 'percentage', 'user_list', 'condition'
    conditions JSONB DEFAULT '{}',              -- Targeting conditions
    metadata JSONB DEFAULT '{}',                -- Extra data (experiment info, etc.)
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default feature flags
INSERT INTO feature_flags (name, description, is_enabled, rollout_percentage, strategy)
VALUES
    ('use_flux_pro', 'Use Flux Pro 1.1 for print-quality images', true, 100, 'all'),
    ('enable_ab_testing', 'Enable A/B testing for story generation prompts', false, 0, 'percentage'),
    ('new_character_system', 'Use enhanced character consistency system', false, 10, 'percentage'),
    ('gemini_flash_2', 'Use Gemini 2.0 Flash for story generation', false, 0, 'percentage'),
    ('parallel_image_generation', 'Generate multiple images in parallel', true, 100, 'all'),
    ('pdf_compression', 'Apply compression to generated PDFs', true, 100, 'all'),
    ('digital_delivery', 'Enable digital-only delivery option', true, 100, 'all'),
    ('gift_wrapping', 'Enable gift wrapping option at checkout', true, 100, 'all')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- API Keys table (for authentication)
-- ============================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 hash of the API key
    name VARCHAR(100) NOT NULL,             -- Human-readable name
    description TEXT,
    tier VARCHAR(20) DEFAULT 'standard',    -- 'free', 'standard', 'premium', 'internal'
    scopes JSONB DEFAULT '["read", "write"]',  -- Allowed operations
    rate_limit_tier VARCHAR(20) DEFAULT 'standard',
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,                   -- Optional expiration
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash
    ON api_keys(key_hash)
    WHERE is_active = true;

-- ============================================
-- Config Change Audit Log
-- ============================================
CREATE TABLE IF NOT EXISTS config_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type VARCHAR(50) NOT NULL,       -- 'ai_model', 'prompt', 'feature_flag'
    config_id UUID NOT NULL,
    config_name VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,            -- 'create', 'update', 'delete'
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(100),                -- User/system that made the change
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_config_type
    ON config_audit_log(config_type, config_name);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
    ON config_audit_log(created_at DESC);

-- ============================================
-- Trigger functions for audit logging
-- ============================================

-- AI Model Config audit trigger
CREATE OR REPLACE FUNCTION audit_ai_model_config()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, new_value)
        VALUES ('ai_model', NEW.id, NEW.name, 'create', to_jsonb(NEW));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, old_value, new_value)
        VALUES ('ai_model', NEW.id, NEW.name, 'update', to_jsonb(OLD), to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, old_value)
        VALUES ('ai_model', OLD.id, OLD.name, 'delete', to_jsonb(OLD));
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ai_model_config_audit ON ai_model_configs;
CREATE TRIGGER ai_model_config_audit
AFTER INSERT OR UPDATE OR DELETE ON ai_model_configs
FOR EACH ROW EXECUTE FUNCTION audit_ai_model_config();

-- Feature Flag audit trigger
CREATE OR REPLACE FUNCTION audit_feature_flag()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, new_value)
        VALUES ('feature_flag', NEW.id, NEW.name, 'create', to_jsonb(NEW));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, old_value, new_value)
        VALUES ('feature_flag', NEW.id, NEW.name, 'update', to_jsonb(OLD), to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO config_audit_log (config_type, config_id, config_name, action, old_value)
        VALUES ('feature_flag', OLD.id, OLD.name, 'delete', to_jsonb(OLD));
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS feature_flag_audit ON feature_flags;
CREATE TRIGGER feature_flag_audit
AFTER INSERT OR UPDATE OR DELETE ON feature_flags
FOR EACH ROW EXECUTE FUNCTION audit_feature_flag();

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE ai_model_configs IS 'AI model configurations for different quality tiers';
COMMENT ON TABLE prompt_templates IS 'Versioned prompt templates with variable substitution';
COMMENT ON TABLE feature_flags IS 'Feature flags with rollout support';
COMMENT ON TABLE api_keys IS 'API keys for authentication';
COMMENT ON TABLE config_audit_log IS 'Audit log for configuration changes';
