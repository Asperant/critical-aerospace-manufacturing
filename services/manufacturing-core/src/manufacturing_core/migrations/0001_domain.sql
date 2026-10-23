-- WP-CORE-001: initial Core-owned domain storage. No platform role provisioning.
CREATE SCHEMA IF NOT EXISTS core AUTHORIZATION CURRENT_USER;
REVOKE ALL ON SCHEMA core FROM PUBLIC;

CREATE TABLE core.equipment (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S')
);
CREATE TABLE core.manufacturing_route (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S')
);
CREATE TABLE core.route_visit (
    route_id text NOT NULL REFERENCES core.manufacturing_route(id),
    id text NOT NULL CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    position integer NOT NULL CHECK (position >= 0),
    operation_class_id text NOT NULL CHECK (operation_class_id ~ '\S'),
    equipment_id text NOT NULL REFERENCES core.equipment(id),
    PRIMARY KEY (route_id, id),
    UNIQUE (route_id, position)
);
CREATE TABLE core.production_order (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    route_id text NOT NULL REFERENCES core.manufacturing_route(id)
);
CREATE TABLE core.lot (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    order_id text NOT NULL REFERENCES core.production_order(id)
);
CREATE TABLE core.serialized_component (
    id text PRIMARY KEY CHECK (id ~ '\S'),
    revision text NOT NULL CHECK (revision ~ '\S'),
    lot_id text NOT NULL REFERENCES core.lot(id)
);
CREATE TABLE core.schema_migration (
    version text PRIMARY KEY,
    sha256 text NOT NULL,
    runtime_role text NOT NULL
);
