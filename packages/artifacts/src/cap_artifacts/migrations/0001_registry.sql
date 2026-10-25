-- WP-OBJ-001: artifact metadata registry (02 Large Artifact Policy: metadata and
-- provenance live in the relational layer; bytes live in object storage).
-- One row per artifact version. The primary key makes a version write-once even
-- under concurrent writers; the trigger makes identity and content immutable and
-- allows only the 02 lifecycle transitions. Rows are never deleted by the
-- runtime: DELETED keeps a tombstone.
CREATE SCHEMA IF NOT EXISTS artifact AUTHORIZATION CURRENT_USER;
REVOKE ALL ON SCHEMA artifact FROM PUBLIC;

CREATE TABLE artifact.schema_migration (
    version text PRIMARY KEY,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    runtime_role text NOT NULL
);

CREATE TABLE artifact.artifact_version (
    artifact_id uuid NOT NULL,
    version integer NOT NULL CHECK (version >= 1),
    artifact_type text NOT NULL CHECK (artifact_type ~ '^[a-z][a-z0-9_]{1,63}$'),
    retention_class text NOT NULL CHECK (retention_class IN ('RC-B', 'RC-C', 'RC-D')),
    bucket text NOT NULL CHECK (bucket IN ('cap-artifacts-rc-b', 'cap-artifacts-rc-c', 'cap-artifacts-rc-d')),
    object_key text NOT NULL UNIQUE CHECK (object_key ~ '^v1/[a-z][a-z0-9_]{1,63}/[0-9a-f]{2}/'),
    object_id uuid NOT NULL UNIQUE,
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    checksum_algorithm text NOT NULL CHECK (checksum_algorithm = 'sha256'),
    checksum_value text NOT NULL CHECK (checksum_value ~ '^[0-9a-f]{64}$'),
    lifecycle_status text NOT NULL CHECK (lifecycle_status IN (
        'RESERVED', 'UPLOADING', 'VALIDATING', 'AVAILABLE', 'FAILED', 'QUARANTINED',
        'ABORTED', 'RETIRED', 'DELETE_ELIGIBLE', 'PENDING_DELETE', 'DELETED')),
    reference jsonb NOT NULL CHECK (reference ->> 'schema' = 'cap.artifact-ref/v1'),
    reserved_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (artifact_id, version),
    CHECK (reference ->> 'lifecycle_status' = lifecycle_status),
    CHECK (reference ->> 'artifact_id' = artifact_id::text),
    CHECK ((reference ->> 'version')::integer = version)
);
CREATE INDEX artifact_version_status ON artifact.artifact_version (lifecycle_status, updated_at);

CREATE TABLE artifact.lifecycle_transition (
    source text NOT NULL,
    target text NOT NULL,
    PRIMARY KEY (source, target)
);
INSERT INTO artifact.lifecycle_transition (source, target) VALUES
    ('RESERVED', 'UPLOADING'), ('RESERVED', 'ABORTED'),
    ('UPLOADING', 'VALIDATING'), ('UPLOADING', 'FAILED'), ('UPLOADING', 'ABORTED'),
    ('VALIDATING', 'AVAILABLE'), ('VALIDATING', 'FAILED'), ('VALIDATING', 'QUARANTINED'),
    ('AVAILABLE', 'QUARANTINED'), ('AVAILABLE', 'RETIRED'), ('AVAILABLE', 'DELETE_ELIGIBLE'),
    ('QUARANTINED', 'DELETE_ELIGIBLE'), ('FAILED', 'DELETE_ELIGIBLE'),
    ('ABORTED', 'DELETE_ELIGIBLE'), ('RETIRED', 'DELETE_ELIGIBLE'),
    ('DELETE_ELIGIBLE', 'PENDING_DELETE'), ('PENDING_DELETE', 'DELETED');

CREATE FUNCTION artifact.guard_version() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.lifecycle_status <> 'RESERVED' THEN
            RAISE EXCEPTION 'a new artifact version starts RESERVED' USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF (NEW.artifact_id, NEW.version, NEW.artifact_type, NEW.retention_class, NEW.bucket,
        NEW.object_key, NEW.object_id, NEW.size_bytes, NEW.checksum_algorithm,
        NEW.checksum_value, NEW.reserved_at)
       IS DISTINCT FROM
       (OLD.artifact_id, OLD.version, OLD.artifact_type, OLD.retention_class, OLD.bucket,
        OLD.object_key, OLD.object_id, OLD.size_bytes, OLD.checksum_algorithm,
        OLD.checksum_value, OLD.reserved_at)
       OR (NEW.reference - 'lifecycle_status') IS DISTINCT FROM (OLD.reference - 'lifecycle_status') THEN
        RAISE EXCEPTION 'artifact identity and content are immutable' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.lifecycle_status IS DISTINCT FROM OLD.lifecycle_status AND NOT EXISTS (
        SELECT 1 FROM artifact.lifecycle_transition t
        WHERE t.source = OLD.lifecycle_status AND t.target = NEW.lifecycle_status) THEN
        RAISE EXCEPTION 'lifecycle transition % -> % is not allowed', OLD.lifecycle_status, NEW.lifecycle_status
            USING ERRCODE = 'check_violation';
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END
$$;

CREATE TRIGGER artifact_version_guard
    BEFORE INSERT OR UPDATE ON artifact.artifact_version
    FOR EACH ROW EXECUTE FUNCTION artifact.guard_version();
