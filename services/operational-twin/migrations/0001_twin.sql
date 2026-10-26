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
    source_event_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('FRESH', 'DEGRADED', 'STALE')),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (world_id, branch_id)
);
