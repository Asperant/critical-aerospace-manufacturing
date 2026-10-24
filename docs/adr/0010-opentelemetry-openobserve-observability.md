# ADR-0010: OpenTelemetry + OpenObserve as the observability stack

- **ADR-ID**: ADR-0010
- **Title**: OpenTelemetry + OpenObserve as the observability stack
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: Telemetry instrumentation and backend (ARCH-OBS-TELEMETRY, ARCH-OBS-STORE)
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge targets this ADR)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The observability stack was left open by earlier items. Item 61 settles it: a vendor-neutral instrumentation standard, a routing collector and a single backend.

## Decision Drivers

A vendor-neutral instrumentation contract that decouples application code from the backend, a unified backend for logs, metrics, traces, search, dashboards and alerting, and a small footprint on the single shared host.

## Constraints/Assumptions

- Services use only the OpenTelemetry contract and never call OpenObserve-specific telemetry APIs directly (`TECH-INV-14` to `TECH-INV-16`).
- Retention is bounded and resource limits are mandatory, so observability cannot starve core services.
- Observability is `DEGRADABLE`, never `REQUIRED`: its failure must not corrupt business truth.

## Considered Options

- OpenTelemetry + OpenTelemetry Collector + OpenObserve (single-node): **selected**.
- OpenObserve HA or distributed mode: rejected.
- Standalone Prometheus server: not mandatory.
- Loki and Tempo: rejected.
- Grafana: rejected as mandatory (OpenObserve supplies the unified UI).

## Decision

OpenTelemetry is the canonical instrumentation API, SDK and protocol for logs, metrics and traces; the OpenTelemetry Collector performs central routing; OpenObserve (single-node) is the unified telemetry backend.

## Rationale

The OpenTelemetry contract keeps the backend replaceable, and a single-node unified backend fits the single-host footprint.

## Positive Consequences

The backend can be swapped behind the Collector without touching application code; one unified backend replaces several components.

## Negative Consequences

No high-availability or distributed backend mode is used; this is an accepted limit of the single-node baseline.

## Risks

An observability outage is explicitly degradable and must not corrupt business truth. Logs may carry PII if not scrubbed.

## Operational Impact

Runtime and standard owner: Yavuz; instrumentation is owned by every service owner. The Collector is a stateless pass-through (it may buffer); OpenObserve is a stateful, bounded-retention telemetry store. "OpenObserve/OTel ownership is not domain metric meaning."

## Security/Authority Impact

Low to Medium: operational and trace metadata, with potential PII in logs if not scrubbed.

## Research/Evidence Impact

None stated in the specification for this decision.

## Migration/Rollback

Reversibility class: `REVERSIBLE` (assigned by this record's author, from the specification's note that the backend is swapped behind the Collector without application changes). A new technology on the mandatory critical path is an ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Implementation exists under WP-OBS-001; this record does not certify it, and validation evidence is attached from that work package's accepted evidence.

## Revisit Triggers

If the single-node backend cannot meet the validated resource envelope, or if the Item 61 promotion and exit policy for OpenObserve is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Observability Architecture; `TECH-INV-14` to `TECH-INV-16`; The Backfill ADR Set.
- [ADR index](README.md)
