-- WP-CORE-004 slice 2: immutable relational snapshots, never route state.
CREATE TABLE core.rework_history (
    component_id text PRIMARY KEY REFERENCES core.serialized_component(id)
);

CREATE TABLE core.rework_directive (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    component_id text NOT NULL REFERENCES core.rework_history(component_id),
    reason text NOT NULL CHECK (reason ~ '\S'),
    originating_inspection_id text NOT NULL CHECK (originating_inspection_id ~ '\S'),
    origin_execution_id text NOT NULL,
    return_visit_id text NOT NULL CHECK (return_visit_id ~ '\S'),
    rework_route_id text NOT NULL CHECK (rework_route_id ~ '\S'),
    rework_route_revision text NOT NULL CHECK (rework_route_revision ~ '\S'),
    related_defect_id text CHECK (related_defect_id ~ '\S'),
    related_incident_id text CHECK (related_incident_id ~ '\S'),
    current_rework_count numeric NOT NULL CHECK (
        current_rework_count >= 0 AND current_rework_count < 'Infinity'::numeric
        AND current_rework_count = trunc(current_rework_count)
    ),
    approval_state text NOT NULL CHECK (approval_state ~ '\S'),
    policy_state text NOT NULL CHECK (policy_state ~ '\S'),
    UNIQUE (id, component_id),
    UNIQUE (id, rework_route_id, rework_route_revision)
);

CREATE TABLE core.rework_segment (
    component_id text NOT NULL REFERENCES core.rework_history(component_id),
    position integer NOT NULL CHECK (position >= 0),
    route_id text NOT NULL CHECK (route_id ~ '\S'),
    route_revision text NOT NULL CHECK (route_revision ~ '\S'),
    directive_id text UNIQUE,
    PRIMARY KEY (component_id, position),
    FOREIGN KEY (directive_id, component_id) REFERENCES core.rework_directive(id, component_id),
    FOREIGN KEY (directive_id, route_id, route_revision)
        REFERENCES core.rework_directive(id, rework_route_id, rework_route_revision),
    CHECK ((position = 0 AND directive_id IS NULL) OR (position > 0 AND directive_id IS NOT NULL))
);

CREATE TABLE core.rework_route_visit (
    component_id text NOT NULL,
    segment_position integer NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    id text NOT NULL CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    operation_class_id text NOT NULL CHECK (operation_class_id ~ '\S'),
    equipment_id text NOT NULL REFERENCES core.equipment(id),
    PRIMARY KEY (component_id, segment_position, position),
    UNIQUE (component_id, segment_position, id),
    FOREIGN KEY (component_id, segment_position) REFERENCES core.rework_segment(component_id, position)
);

CREATE TABLE core.rework_execution (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    component_id text NOT NULL,
    segment_position integer NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    lot_id text NOT NULL REFERENCES core.lot(id),
    route_visit_id text NOT NULL,
    equipment_id text NOT NULL REFERENCES core.equipment(id),
    started_at timestamptz NOT NULL,
    ended_at timestamptz NOT NULL CHECK (ended_at >= started_at),
    UNIQUE (id, component_id),
    UNIQUE (component_id, segment_position, position),
    FOREIGN KEY (component_id, segment_position) REFERENCES core.rework_segment(component_id, position),
    FOREIGN KEY (component_id, segment_position, route_visit_id)
        REFERENCES core.rework_route_visit(component_id, segment_position, id)
);

ALTER TABLE core.rework_directive ADD FOREIGN KEY (origin_execution_id, component_id)
    REFERENCES core.rework_execution(id, component_id);

-- Separate ledger preserves the unchanged single-initial-migration runner.
CREATE TABLE core.rework_schema_migration (
    version text PRIMARY KEY,
    sha256 text NOT NULL,
    runtime_role text NOT NULL
);
