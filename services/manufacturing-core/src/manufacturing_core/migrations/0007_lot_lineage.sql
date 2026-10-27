-- Internal immutable history closures; never current lot membership updates.
CREATE TABLE core.lineage_history (
    world_id text PRIMARY KEY CHECK (world_id ~ '\S')
);
CREATE TABLE core.lineage_event (
    world_id text NOT NULL REFERENCES core.lineage_history(world_id),
    id text NOT NULL CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    position integer NOT NULL CHECK (position >= 0),
    kind text NOT NULL CHECK (kind IN ('SPLIT', 'MERGE')),
    source_event_id text NOT NULL CHECK (source_event_id ~ '\S'),
    reason text NOT NULL CHECK (reason ~ '\S'),
    occurred_at timestamptz NOT NULL,
    effective_from timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL,
    PRIMARY KEY (world_id, id),
    UNIQUE (world_id, position),
    UNIQUE (world_id, source_event_id)
);
CREATE TABLE core.lineage_lot (
    world_id text NOT NULL REFERENCES core.lineage_history(world_id),
    lot_id text NOT NULL REFERENCES core.lot(id),
    root_position integer CHECK (root_position >= 0),
    producer_id text,
    child_position integer CHECK (child_position >= 0),
    PRIMARY KEY (world_id, lot_id),
    UNIQUE (world_id, root_position),
    UNIQUE (world_id, producer_id, child_position),
    FOREIGN KEY (world_id, producer_id) REFERENCES core.lineage_event(world_id, id),
    CHECK ((root_position IS NOT NULL AND producer_id IS NULL AND child_position IS NULL)
        OR (root_position IS NULL AND producer_id IS NOT NULL AND child_position IS NOT NULL))
);
CREATE TABLE core.lineage_membership (
    world_id text NOT NULL,
    lot_id text NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    component_id text NOT NULL REFERENCES core.serialized_component(id),
    PRIMARY KEY (world_id, lot_id, position),
    UNIQUE (world_id, lot_id, component_id),
    FOREIGN KEY (world_id, lot_id) REFERENCES core.lineage_lot(world_id, lot_id)
);
CREATE TABLE core.lineage_parent (
    world_id text NOT NULL,
    event_id text NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    lot_id text NOT NULL,
    PRIMARY KEY (world_id, event_id, position),
    UNIQUE (world_id, lot_id),
    FOREIGN KEY (world_id, event_id) REFERENCES core.lineage_event(world_id, id),
    FOREIGN KEY (world_id, lot_id) REFERENCES core.lineage_lot(world_id, lot_id)
);
