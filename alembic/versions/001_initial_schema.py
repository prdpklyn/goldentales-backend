"""Initial schema: orders and config tables

Revision ID: 001
Revises: 
Create Date: 2024-12-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create orders and configuration tables."""
    
    # ========================================
    # ORDERS TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- External references
            shopify_order_id VARCHAR(100) UNIQUE,
            shopify_order_number VARCHAR(50),

            -- Book reference
            story_id UUID NOT NULL REFERENCES stories(id),

            -- Order details
            format VARCHAR(20) NOT NULL,           -- 'digital', 'softcover', 'hardcover'
            book_size VARCHAR(20) DEFAULT '8x8',   -- '8x8', '8.5x8.5', '10x8'
            quantity INT DEFAULT 1,

            -- Pricing (stored at time of order for audit trail)
            base_price DECIMAL(10,2) NOT NULL DEFAULT 0,
            shipping_cost DECIMAL(10,2) DEFAULT 0,
            gift_wrap_cost DECIMAL(10,2) DEFAULT 0,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            tax_amount DECIMAL(10,2) DEFAULT 0,
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            currency VARCHAR(3) DEFAULT 'USD',

            -- Shipping
            shipping_tier VARCHAR(20),             -- 'standard', 'express', 'digital'
            shipping_address JSONB,                -- Full address object

            -- Gift options
            is_gift BOOLEAN DEFAULT false,
            gift_message TEXT,
            gift_wrap BOOLEAN DEFAULT false,
            recipient_email VARCHAR(255),

            -- Customer info
            customer_email VARCHAR(255),
            customer_name VARCHAR(200),
            customer_phone VARCHAR(50),

            -- Status tracking
            status VARCHAR(30) NOT NULL DEFAULT 'pending_payment',
            status_history JSONB DEFAULT '[]',     -- Array of {status, timestamp, note}

            -- Print production
            print_job_id VARCHAR(100),
            pdf_storage_path TEXT,                 -- Supabase storage path
            pdf_url TEXT,                          -- Public URL if available
            print_provider VARCHAR(50),            -- 'lulu', 'printful', etc.
            print_provider_order_id VARCHAR(100),

            -- Shipping tracking
            tracking_number VARCHAR(100),
            tracking_url TEXT,
            carrier VARCHAR(50),
            shipped_at TIMESTAMP,
            delivered_at TIMESTAMP,
            estimated_delivery_date DATE,

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            cancelled_at TIMESTAMP,

            -- Metadata
            metadata JSONB DEFAULT '{}',           -- Flexible storage for additional data
            internal_notes TEXT                    -- For internal use

        );

        -- Indexes for orders table
        CREATE INDEX idx_orders_shopify_order_id ON orders(shopify_order_id);
        CREATE INDEX idx_orders_story_id ON orders(story_id);
        CREATE INDEX idx_orders_status ON orders(status);
        CREATE INDEX idx_orders_customer_email ON orders(customer_email);
        CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

        -- Function to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        -- Trigger for orders
        CREATE TRIGGER update_orders_updated_at
            BEFORE UPDATE ON orders
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # ========================================
    # AI MODEL CONFIGS TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_model_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Model identification
            quality_tier VARCHAR(50) NOT NULL UNIQUE,  -- 'preview', 'standard', 'print', 'story'
            model_name VARCHAR(200) NOT NULL,          -- e.g., 'fal-ai/flux/schnell'
            provider VARCHAR(50) NOT NULL,             -- 'fal', 'gemini', 'openai'

            -- Configuration
            config JSONB NOT NULL,                     -- Model-specific settings
            cost_per_call DECIMAL(10,4) DEFAULT 0,
            avg_latency_ms INT DEFAULT 0,

            -- Status
            is_active BOOLEAN DEFAULT true,
            is_default BOOLEAN DEFAULT false,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            notes TEXT
        );

        CREATE INDEX idx_ai_models_quality_tier ON ai_model_configs(quality_tier);
        CREATE INDEX idx_ai_models_is_active ON ai_model_configs(is_active);

        CREATE TRIGGER update_ai_models_updated_at
            BEFORE UPDATE ON ai_model_configs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # ========================================
    # PROMPT TEMPLATES TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Template identification
            name VARCHAR(200) NOT NULL UNIQUE,
            category VARCHAR(50) NOT NULL,            -- 'story', 'character', 'scene', etc.
            version INT DEFAULT 1,

            -- Template content
            template_text TEXT NOT NULL,
            variables JSONB DEFAULT '[]',              -- List of required variables
            example_output TEXT,

            -- Status
            is_active BOOLEAN DEFAULT true,
            is_default BOOLEAN DEFAULT false,

            -- A/B testing
            ab_test_variant VARCHAR(50),               -- 'control', 'variant_a', 'variant_b'
            performance_score DECIMAL(5,2),            -- User satisfaction score

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            usage_count INT DEFAULT 0,
            notes TEXT
        );

        CREATE INDEX idx_prompts_category ON prompt_templates(category);
        CREATE INDEX idx_prompts_is_active ON prompt_templates(is_active);
        CREATE INDEX idx_prompts_ab_variant ON prompt_templates(ab_test_variant);

        CREATE TRIGGER update_prompts_updated_at
            BEFORE UPDATE ON prompt_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # ========================================
    # FEATURE FLAGS TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Flag identification
            flag_key VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            category VARCHAR(50),                      -- 'ai', 'ui', 'payment', etc.

            -- Status
            is_enabled BOOLEAN DEFAULT false,

            -- Rollout strategy
            rollout_strategy VARCHAR(50) DEFAULT 'all', -- 'all', 'percentage', 'user_list', 'condition'
            rollout_percentage INT DEFAULT 0,           -- 0-100 for percentage rollout
            rollout_users JSONB DEFAULT '[]',           -- List of user IDs for user_list strategy
            rollout_conditions JSONB DEFAULT '{}',      -- Conditions for conditional rollout

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            notes TEXT,

            -- Analytics
            usage_count INT DEFAULT 0,
            last_evaluated_at TIMESTAMP
        );

        CREATE INDEX idx_flags_key ON feature_flags(flag_key);
        CREATE INDEX idx_flags_is_enabled ON feature_flags(is_enabled);
        CREATE INDEX idx_flags_category ON feature_flags(category);

        CREATE TRIGGER update_flags_updated_at
            BEFORE UPDATE ON feature_flags
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # ========================================
    # API KEYS TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Key information
            key_hash VARCHAR(64) NOT NULL UNIQUE,      -- SHA-256 hash of the key
            key_prefix VARCHAR(10) NOT NULL,           -- First 8 chars for identification
            name VARCHAR(200) NOT NULL,
            tier VARCHAR(50) NOT NULL DEFAULT 'free',  -- 'free', 'standard', 'premium', 'internal'

            -- Rate limits
            rate_limit_per_minute INT DEFAULT 10,
            rate_limit_per_day INT DEFAULT 100,

            -- Status
            is_active BOOLEAN DEFAULT true,
            is_revoked BOOLEAN DEFAULT false,

            -- Usage tracking
            last_used_at TIMESTAMP,
            total_requests INT DEFAULT 0,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            created_by VARCHAR(100),
            notes TEXT
        );

        CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
        CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
        CREATE INDEX idx_api_keys_tier ON api_keys(tier);
    """)
    
    # ========================================
    # CONFIG AUDIT LOG TABLE
    # ========================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS config_audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Event information
            table_name VARCHAR(100) NOT NULL,
            record_id UUID NOT NULL,
            action VARCHAR(20) NOT NULL,               -- 'create', 'update', 'delete'

            -- Changes
            old_values JSONB,
            new_values JSONB,

            -- Actor
            changed_by VARCHAR(100),
            change_reason TEXT,

            -- Timestamp
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_audit_table ON config_audit_log(table_name);
        CREATE INDEX idx_audit_record ON config_audit_log(record_id);
        CREATE INDEX idx_audit_changed_at ON config_audit_log(changed_at DESC);
    """)


def downgrade() -> None:
    """Drop all tables created in upgrade."""
    
    # Drop audit log first (no dependencies)
    op.execute("DROP TABLE IF EXISTS config_audit_log CASCADE;")
    
    # Drop config tables
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS feature_flags CASCADE;")
    op.execute("DROP TABLE IF EXISTS prompt_templates CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_model_configs CASCADE;")
    
    # Drop orders table
    op.execute("DROP TABLE IF EXISTS orders CASCADE;")
    
    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;")

