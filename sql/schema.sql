-- =============================================================================
-- Suruthi Order Service – Database Schema
-- Run this script against your `order_service_db` database
-- =============================================================================

-- Enable UUID generation (built into PostgreSQL 13+, else install pgcrypto)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- ENUMS
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE order_status_enum AS ENUM (
        'pending',
        'confirmed',
        'processing',
        'shipped',
        'delivered',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;


-- =============================================================================
-- TABLE: orders
-- Stores one row per customer order
-- =============================================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id    UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID            NOT NULL,
    total_price NUMERIC(12, 2)  NOT NULL CHECK (total_price >= 0),
    status      order_status_enum NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Index for fast user-specific order history queries
CREATE INDEX IF NOT EXISTS idx_orders_user_id    ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);


-- =============================================================================
-- TABLE: order_items
-- Stores individual product lines within each order
-- =============================================================================

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id      UUID            NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id    UUID            NOT NULL,
    quantity      INTEGER         NOT NULL CHECK (quantity > 0),
    price         NUMERIC(12, 2)  NOT NULL CHECK (price > 0)
);

-- Index for fast item lookup by order
CREATE INDEX IF NOT EXISTS idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);


-- =============================================================================
-- STORED PROCEDURE: sp_create_order
-- =============================================================================
--
-- WHY a stored procedure here?
-- ─────────────────────────────
-- Creating an order requires TWO inserts: one into `orders`, then multiple
-- into `order_items`. If anything fails midway (e.g. network drop after the
-- first insert), we'd have a ghost order with no items.
--
-- By wrapping both inserts in a PROCEDURE, PostgreSQL executes them in a
-- single atomic transaction inside the database engine itself.
-- No partial writes. No orphaned rows.
--
-- HOW it's called:
--   CALL sp_create_order(
--       '...uuid...',           -- order_id
--       '...uuid...',           -- user_id
--       299.99,                 -- total_price
--       ARRAY['uuid1','uuid2'], -- product_ids
--       ARRAY[2, 1],            -- quantities
--       ARRAY[99.99, 100.01]    -- prices per unit
--   );
-- =============================================================================

CREATE OR REPLACE PROCEDURE sp_create_order(
    p_order_id    UUID,
    p_user_id     UUID,
    p_total_price NUMERIC(12, 2),
    p_product_ids UUID[],
    p_quantities  INTEGER[],
    p_prices      NUMERIC(12, 2)[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_idx INTEGER;
BEGIN
    -- ── Validation ───────────────────────────────────────────────────────────
    IF p_total_price < 0 THEN
        RAISE EXCEPTION 'total_price cannot be negative: %', p_total_price;
    END IF;

    IF array_length(p_product_ids, 1) IS NULL OR array_length(p_product_ids, 1) = 0 THEN
        RAISE EXCEPTION 'Order must contain at least one item';
    END IF;

    IF array_length(p_product_ids, 1) <> array_length(p_quantities, 1)
    OR array_length(p_product_ids, 1) <> array_length(p_prices, 1) THEN
        RAISE EXCEPTION 'product_ids, quantities, and prices arrays must have the same length';
    END IF;

    -- ── INSERT into orders ───────────────────────────────────────────────────
    INSERT INTO orders (order_id, user_id, total_price, status, created_at)
    VALUES (p_order_id, p_user_id, p_total_price, 'pending', NOW());

    -- ── INSERT each item into order_items ────────────────────────────────────
    FOR v_idx IN 1 .. array_length(p_product_ids, 1) LOOP

        IF p_quantities[v_idx] <= 0 THEN
            RAISE EXCEPTION 'Quantity must be positive for product %', p_product_ids[v_idx];
        END IF;

        IF p_prices[v_idx] <= 0 THEN
            RAISE EXCEPTION 'Price must be positive for product %', p_product_ids[v_idx];
        END IF;

        INSERT INTO order_items (order_item_id, order_id, product_id, quantity, price)
        VALUES (
            gen_random_uuid(),
            p_order_id,
            p_product_ids[v_idx],
            p_quantities[v_idx],
            p_prices[v_idx]
        );
    END LOOP;

    -- Both inserts committed atomically when the CALL transaction commits.
END;
$$;


-- =============================================================================
-- STORED PROCEDURE: sp_update_order_status
-- =============================================================================
--
-- WHY a stored procedure here?
-- ─────────────────────────────
-- Order status follows a strict lifecycle (state machine). We don't want
-- anyone — not even a direct SQL query — to jump an order from DELIVERED
-- back to PENDING. By putting the transition validation inside the DB procedure,
-- the rule is enforced at the database level, not just the application level.
--
-- This means even if someone bypasses the API and runs SQL directly, the
-- invalid transition is still blocked.
--
-- HOW it's called:
--   CALL sp_update_order_status('...uuid...', 'shipped');
-- =============================================================================

CREATE OR REPLACE PROCEDURE sp_update_order_status(
    p_order_id   UUID,
    p_new_status order_status_enum
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status order_status_enum;
BEGIN
    -- ── Fetch current status (lock row to prevent concurrent updates) ─────────
    SELECT status INTO v_current_status
    FROM orders
    WHERE order_id = p_order_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order % not found', p_order_id;
    END IF;

    -- ── Enforce state-machine transitions ─────────────────────────────────────
    IF v_current_status = 'delivered' OR v_current_status = 'cancelled' THEN
        RAISE EXCEPTION 'Order % is in terminal state ''%'' and cannot be updated',
            p_order_id, v_current_status;
    END IF;

    IF v_current_status = 'pending' AND p_new_status NOT IN ('confirmed', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition: % → % (allowed: confirmed, cancelled)',
            v_current_status, p_new_status;
    END IF;

    IF v_current_status = 'confirmed' AND p_new_status NOT IN ('processing', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition: % → % (allowed: processing, cancelled)',
            v_current_status, p_new_status;
    END IF;

    IF v_current_status = 'processing' AND p_new_status NOT IN ('shipped', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition: % → % (allowed: shipped, cancelled)',
            v_current_status, p_new_status;
    END IF;

    IF v_current_status = 'shipped' AND p_new_status <> 'delivered' THEN
        RAISE EXCEPTION 'Invalid transition: % → % (allowed: delivered)',
            v_current_status, p_new_status;
    END IF;

    -- ── Apply the update ──────────────────────────────────────────────────────
    UPDATE orders
    SET status = p_new_status
    WHERE order_id = p_order_id;

END;
$$;


-- =============================================================================
-- SAMPLE DATA (optional – for testing)
-- Uncomment to insert test records.
-- =============================================================================

/*
-- Test order
INSERT INTO orders (order_id, user_id, total_price, status)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    499.98,
    'pending'
);

INSERT INTO order_items (order_id, product_id, quantity, price)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 2, 149.99),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 1, 200.00);
*/
