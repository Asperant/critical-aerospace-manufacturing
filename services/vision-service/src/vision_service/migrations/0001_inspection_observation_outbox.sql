CREATE TABLE vision.inspection_observation_outbox (
    source_event_id text PRIMARY KEY CHECK (source_event_id !~ '^[[:space:]]*$'),
    event_id text NOT NULL UNIQUE CHECK (event_id !~ '^[[:space:]]*$'),
    subject text NOT NULL CHECK (subject !~ '^[[:space:]]*$'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    published_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    claim_token uuid,
    claimed_until timestamptz,
    CHECK ((claim_token IS NULL) = (claimed_until IS NULL))
);
CREATE INDEX inspection_observation_outbox_pending
    ON vision.inspection_observation_outbox (created_at, event_id)
    WHERE published_at IS NULL;
CREATE TABLE vision.schema_migration (
    version text PRIMARY KEY,
    sha256 text NOT NULL,
    runtime_role text NOT NULL
);
