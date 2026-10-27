-- WP-CORE-009: state representation only. Transition legality remains in
-- WP-CORE-002 and is intentionally not encoded by this migration.
CREATE TABLE core.production_order_state (
    id text PRIMARY KEY REFERENCES core.production_order(id),
    revision text NOT NULL CHECK (revision ~ '\S'),
    lifecycle_state text NOT NULL DEFAULT 'CREATED' CHECK (
        lifecycle_state IN ('CREATED', 'VALIDATED', 'RELEASED', 'IN_PROGRESS',
                            'COMPLETED', 'CANCELLED', 'SUSPENDED')
    )
);

CREATE TABLE core.lot_state (
    id text PRIMARY KEY REFERENCES core.lot(id),
    revision text NOT NULL CHECK (revision ~ '\S'),
    lifecycle_state text NOT NULL DEFAULT 'CREATED' CHECK (
        lifecycle_state IN ('CREATED', 'RELEASED', 'IN_PRODUCTION', 'COMPLETED',
                            'SCRAPPED', 'CANCELLED')
    ),
    execution_state text NOT NULL DEFAULT 'READY' CHECK (
        execution_state IN ('READY', 'QUEUED', 'RESERVED', 'DISPATCHED',
                            'PROCESSING', 'STEP_COMPLETED')
    )
);

CREATE TABLE core.serialized_component_state (
    id text PRIMARY KEY REFERENCES core.serialized_component(id),
    revision text NOT NULL CHECK (revision ~ '\S'),
    lifecycle_state text NOT NULL DEFAULT 'CREATED' CHECK (
        lifecycle_state IN ('CREATED', 'IN_PRODUCTION', 'COMPLETED', 'SCRAPPED')
    ),
    execution_state text NOT NULL DEFAULT 'READY' CHECK (
        execution_state IN ('READY', 'QUEUED', 'RESERVED', 'DISPATCHED',
                            'PROCESSING', 'STEP_COMPLETED')
    )
);
