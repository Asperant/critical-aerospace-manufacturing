# Plane operations and bounded recovery (CTRL-PM-014)

Plane is host management infrastructure, not the product SUT. The repository and offline projectctl commands work independently of its availability. Stop Plane during controlled product benchmark campaigns if its host load would contaminate measurements; record that operating decision and restart/verify it afterward. Do not launch the product stack for projectctl tests.

## Deployment and persistence

Compose deployment: `/srv/ailab/plane/plane-app/docker-compose.yaml`; private configuration: adjacent `plane.env`. Current project is `plane-app`. Database has 10 raw state rows: nine canonical API states plus Plane’s internal `Triage` (`group=triage`). Backup preserves that row; no state is removed or reinterpreted. All twelve observed Plane containers use restart policy `always`. The observed host boot was 2026-10-11 20:06:17 local time; current API container started at 2026-10-11T18:23:35Z with restart count 1. These are observations, not a controlled reboot test. Database persistence is `plane-app_pgdata`; MinIO uses `plane-app_uploads` at `/export` plus its observed anonymous `/data` volume. Valkey, RabbitMQ, proxy and worker logs have separate volumes. Do not remove volumes or run compose down with `-v`. Docker-host reboot/daemon restart has not been induced; restart policies alone do not prove a reboot test.

## Backup

Run `python tools/operations/plane_backup.py backup`. It verifies the running database/object-store deployment identity and persistence mounts, checks free disk, creates a private unique directory under `/srv/ailab/backups`, takes a PostgreSQL custom MVCC dump, copies both actual MinIO persistence directories through Docker archive-copy, and privately copies compose/configuration. SHA-256 inventory verifies every copied artifact. Output contains paths, counts and results only. Database credentials expand inside the container and are never printed. Backups contain secrets and personal/project data: keep directory mode 0700 and files 0600; never commit or upload them as repository evidence.

Failed attempts remain for diagnosis; no automated deletion. The first attempt in this run failed from SQL quoting before any database dump; the corrected script passes SQL as a positional argument. Concurrent Plane writes should be paused by operators for a disaster-recovery checkpoint. This backup uses a transaction-consistent database dump and live object copy, not a globally atomic cross-store snapshot. Broker/Valkey queues, worker logs and PostgreSQL global roles are excluded. Restoring production requires configuration/roles reconstruction and reconciliation of pending jobs before workers start; this is a bounded recoverability test, not a complete disaster-recovery certification.

## Verify safely

Run `python tools/operations/plane_backup.py verify --backup <recorded-direct-child-path>` for checksums. `verify-isolated --backup <path>` creates a unique PostgreSQL 15.7 container using the backup-recorded database image ID with `--pull never`, network none, no published ports and tmpfs database storage. It verifies no live mounts are attached, restores with exit-on-error/no-owner/no-privileges, compares restored counts with the original observation, rehashes object files and stops the isolated container. The stopped container is retained; deleting it requires approval. This proves PostgreSQL restore usability and object-file integrity; a running restored MinIO/complete Plane deployment is not asserted.

## Human-owned live recovery gate

Never point restore commands at live containers/volumes. A live disaster recovery requires explicit approval, verified target paths and identities, an operator-selected maintenance window, stopped writers, independently preserved original storage, compatible pinned images, role/config reconstruction, object-service restore and application smoke checks. Do not rename/overwrite mounts, restore live, reformat disks, modify partitions or change persistent mounts unattended. A full isolated application restore may be planned separately; this script cannot perform live restore.

## Restart check

After the backup and read-only audit, a bounded API-container restart is safe for this setup window: record its container identity/restart policy and database/object-store mount identities before/after, wait for authenticated API reads to succeed, and verify project identity/inventory unchanged. It temporarily interrupts API service; it does not restart or modify persistence containers. Full host reboot and destructive failure injection remain human-owned. Evidence records what was actually executed.

Actual restart result: one API-container restart, followed by an initially failed five-attempt discovery probe. Later authentication and fresh full discovery succeeded without another restart or configuration change; all compared API inventory was identical. Database/object-store mounts match the backup observation and their startup timestamps predate the backup. Treat startup/recovery availability as something to observe explicitly, not as guaranteed by `always`. The failed probe is preserved in operational evidence.
