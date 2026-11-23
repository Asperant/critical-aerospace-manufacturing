CREATE SCHEMA IF NOT EXISTS twin;

CREATE TABLE IF NOT EXISTS twin.projection_entity (
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    world_id text NOT NULL,
    branch_id text NOT NULL,
    aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
    state jsonb NOT NULL,
    source_event_id text NOT NULL,
    source_revision text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (world_id, branch_id, aggregate_type, aggregate_id)
);
CREATE TABLE IF NOT EXISTS twin.applied_event (
    consumer_scope text NOT NULL,
    event_id text NOT NULL,
    world_id text NOT NULL,
    branch_id text NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    aggregate_version bigint NOT NULL CHECK (aggregate_version > 0),
    applied_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_scope, event_id)
);

CREATE TABLE IF NOT EXISTS twin.projection_revision (
    world_id text NOT NULL,
    branch_id text NOT NULL,
    source_event_id text,
    status text NOT NULL CHECK (status IN ('FRESH', 'DEGRADED', 'STALE')),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (world_id, branch_id)
);

-- A gap can be known before this world has accepted any source event. Keep its
-- stale marker without inventing an applied source revision.
ALTER TABLE twin.projection_revision ALTER COLUMN source_event_id DROP NOT NULL;

CREATE TABLE IF NOT EXISTS twin.projection_gap (
    consumer_scope text NOT NULL,
    world_id text NOT NULL,
    branch_id text NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    required_version bigint NOT NULL CHECK (required_version > 0),
    detected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_scope, world_id, branch_id, aggregate_type, aggregate_id)
);
