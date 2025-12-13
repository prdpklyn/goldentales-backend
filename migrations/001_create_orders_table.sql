-- Migration: 001_create_orders_table
-- Description: Create orders table for storing order details with PDF references
-- Created: 2024-01-XX (adjust date as needed)
-- GoldenTales Order Database Schema

-- Orders table (comprehensive)
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
    pdf_storage_path VARCHAR(500),         -- Supabase Storage path
    pdf_url VARCHAR(1000),                 -- Public/signed URL
    pdf_generated_at TIMESTAMP,

    -- Fulfillment
    fulfillment_provider VARCHAR(50),      -- 'lulu', 'printful', etc.
    fulfillment_order_id VARCHAR(100),
    tracking_number VARCHAR(100),
    tracking_url VARCHAR(500),
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,

    -- Metadata
    metadata JSONB DEFAULT '{}',           -- Flexible additional data
    notes TEXT,                            -- Internal notes

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_orders_shopify_order_id ON orders(shopify_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_story_id ON orders(story_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders(customer_email);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- Order status history trigger (automatically tracks status changes)
CREATE OR REPLACE FUNCTION update_order_status_history()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        NEW.status_history = COALESCE(NEW.status_history, '[]'::jsonb) || jsonb_build_object(
            'status', NEW.status,
            'previous_status', OLD.status,
            'timestamp', NOW(),
            'note', NULL
        );
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists before creating (for idempotency)
DROP TRIGGER IF EXISTS order_status_change ON orders;

CREATE TRIGGER order_status_change
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_order_status_history();

-- Comments for documentation
COMMENT ON TABLE orders IS 'GoldenTales order records with complete details and PDF storage references';
COMMENT ON COLUMN orders.status_history IS 'JSON array tracking all status changes with timestamps';
COMMENT ON COLUMN orders.pdf_storage_path IS 'Path in Supabase Storage bucket (goldentales-assets)';
COMMENT ON COLUMN orders.shipping_address IS 'JSON object: {street, city, state, postal_code, country, name}';
