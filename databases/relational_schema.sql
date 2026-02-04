-- Relational schema for HelloBot order tracking.

CREATE TABLE IF NOT EXISTS orders (
    order_id   TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    status     TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed example row aligned with the specification.
INSERT INTO orders (order_id, user_id, status)
VALUES ('id-857591726814891', 'user-123', 'Packed')
ON CONFLICT (order_id) DO NOTHING;

