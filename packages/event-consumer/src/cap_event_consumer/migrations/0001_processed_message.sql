-- WP-EVT-003: installed separately in each consumer's private schema.
CREATE TABLE {schema}.processed_message (
    consumer_scope text NOT NULL CHECK (consumer_scope ~ '\S'),
    event_id text NOT NULL CHECK (event_id ~ '\S'),
    processed_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    PRIMARY KEY (consumer_scope, event_id)
);
CREATE TABLE {schema}.consumer_schema_migration (
    version text PRIMARY KEY,
    sha256 text NOT NULL,
    runtime_role text NOT NULL
);
