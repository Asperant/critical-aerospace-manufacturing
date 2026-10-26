-- WP-CORE-003: immutable command reservation and durable acceptance outcome.
-- Both tables are append-only; no runtime UPDATE or DELETE privilege is needed.
CREATE TABLE core.command_idempotency (
    idempotency_key text PRIMARY KEY CHECK (idempotency_key ~ '\S'),
    command_id uuid NOT NULL UNIQUE,
    command_type text NOT NULL CHECK (command_type ~ '\S'),
    command_version integer NOT NULL CHECK (command_version > 0),
    command_fingerprint text NOT NULL CHECK (command_fingerprint ~ '^[0-9a-f]{64}$'),
    target_type text NOT NULL CHECK (target_type ~ '\S'),
    target_id text NOT NULL CHECK (target_id ~ '\S'),
    world_id text NOT NULL CHECK (world_id ~ '\S'),
    correlation_id text NOT NULL CHECK (correlation_id ~ '\S'),
    causation_id text CHECK (causation_id IS NULL OR causation_id ~ '\S'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.command_outcome (
    outcome_id uuid PRIMARY KEY,
    command_id uuid NOT NULL UNIQUE REFERENCES core.command_idempotency(command_id),
    idempotency_key text NOT NULL UNIQUE REFERENCES core.command_idempotency(idempotency_key),
    command_type text NOT NULL CHECK (command_type ~ '\S'),
    command_version integer NOT NULL CHECK (command_version > 0),
    world_id text NOT NULL CHECK (world_id ~ '\S'),
    correlation_id text NOT NULL CHECK (correlation_id ~ '\S'),
    status text NOT NULL CHECK (status IN ('ACCEPTED', 'REJECTED', 'UNRESOLVED')),
    effect_verification text NOT NULL CHECK (effect_verification = 'NOT_VERIFIED'),
    error_code text CHECK (error_code IS NULL OR error_code ~ '\S'),
    detail text CHECK (detail IS NULL OR detail ~ '\S'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
