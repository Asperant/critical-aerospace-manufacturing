-- WP-CORE-002: first-class retained material holds.
-- A released row remains immutable history; the partial unique index permits
-- at most one active hold per lot without mutating lot lifecycle/execution.
CREATE TABLE core.material_hold (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    lot_id text NOT NULL REFERENCES core.lot(id),
    reason text NOT NULL CHECK (reason ~ '\S'),
    status text NOT NULL CHECK (status IN ('ACTIVE', 'RELEASED')),
    placed_at timestamptz NOT NULL,
    released_at timestamptz,
    release_reason text CHECK (release_reason IS NULL OR release_reason ~ '\S'),
    placed_command_id uuid NOT NULL REFERENCES core.command_idempotency(command_id),
    released_command_id uuid REFERENCES core.command_idempotency(command_id),
    CONSTRAINT material_hold_status_fields CHECK (
        (status = 'ACTIVE' AND released_at IS NULL AND release_reason IS NULL
            AND released_command_id IS NULL)
        OR
        (status = 'RELEASED' AND released_at IS NOT NULL
            AND release_reason IS NOT NULL AND released_command_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX material_hold_one_active_per_lot
    ON core.material_hold(lot_id) WHERE status = 'ACTIVE';

CREATE INDEX material_hold_lot_history ON core.material_hold(lot_id, placed_at);
