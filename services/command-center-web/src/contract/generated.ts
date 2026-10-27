/* GENERATED from services/operations-bff/contracts/v1 by scripts/generate-contract-types.mjs.
 * Do not edit; run `npm run contract:generate`. */

export interface ContractRoot {}
/**
 * Current authenticated BFF session. Session management belongs to the BFF only; it carries no domain facts and no access, refresh or ID tokens. The browser holds only an HttpOnly session cookie.
 *
 * This interface was referenced by `ContractRoot`'s JSON-Schema
 * via the `definition` "SessionResponse".
 */
export interface SessionResponse {
  contract_version: "bff.session.v1";
  actor: SessionActor;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  environment_id: string;
  /**
   * UTC RFC 3339 instant with a literal Z suffix.
   */
  authenticated_at: string;
  /**
   * UTC RFC 3339 instant with a literal Z suffix.
   */
  expires_at: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  csrf_token: string;
}
/**
 * Session-derived actor shown to the user. Read only; no field is accepted from the browser.
 */
export interface SessionActor {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  actor_id: string;
  display_name: string;
  /**
   * Identity-provider role claims for display. Claims are input to backend policy, never an authorization decision, and hiding UI by role is not a security control.
   *
   * Items: Opaque nonblank identifier or revision token. Compared for equality only.
   */
  roles: string[];
  derived_from: "SESSION";
}
/**
 * This interface was referenced by `ContractRoot`'s JSON-Schema
 * via the `definition` "ErrorEnvelope".
 */
export interface ErrorEnvelope {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  error_code: string;
  category:
    | "VALIDATION_ERROR"
    | "NOT_FOUND"
    | "CONFLICT"
    | "STALE_STATE"
    | "UNAUTHORIZED"
    | "FORBIDDEN"
    | "DEPENDENCY_UNAVAILABLE"
    | "TIMEOUT"
    | "RATE_LIMITED"
    | "PARTIAL_RESULT"
    | "INTERNAL_ERROR";
  message: string;
  retryable: boolean;
  details?: {};
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  correlation_id: string;
}
/**
 * QUERY response for the Manufacturing Overview attention-first landing view. Composition only: every item keeps its own epistemic class and source freshness; no overall status exists.
 *
 * This interface was referenced by `ContractRoot`'s JSON-Schema
 * via the `definition` "ManufacturingOverviewResponse".
 */
export interface ManufacturingOverviewResponse {
  contract_version: "bff.overview-query.v1";
  meta: QueryMeta;
  /**
   * @maxItems 100
   */
  needs_attention: AttentionItem[];
  page: CursorPage;
}
export interface QueryMeta {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  revision: string;
  /**
   * UTC RFC 3339 instant with a literal Z suffix.
   */
  as_of: string;
  /**
   * UTC RFC 3339 instant with a literal Z suffix.
   */
  generated_at: string;
  /**
   * Least-fresh freshness among sources; never better than any source.
   */
  freshness: "FRESH" | "DEGRADED" | "STALE";
  world: WorldContext;
  /**
   * @minItems 1
   */
  sources: [SourceStatus, ...SourceStatus[]];
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  correlation_id: string;
}
/**
 * Explicit world binding. There is no implicit current world; the BFF forwards it unchanged.
 */
export interface WorldContext {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  world_id: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  simulation_run_id?: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  branch_id?: string;
}
/**
 * Revision, as_of and freshness exactly as reported by one backend Query API, Snapshot or read model.
 */
export interface SourceStatus {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  source: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  revision: string;
  /**
   * UTC RFC 3339 instant with a literal Z suffix.
   */
  as_of: string;
  /**
   * Staleness Contract classification, ordered FRESH (best), DEGRADED, STALE (worst).
   */
  freshness: "FRESH" | "DEGRADED" | "STALE";
}
/**
 * This interface was referenced by `ManufacturingOverviewResponse`'s JSON-Schema
 * via the `definition` "AttentionItem".
 */
export interface AttentionItem {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  item_id: string;
  /**
   * This interface was referenced by `ManufacturingOverviewResponse`'s JSON-Schema
   * via the `definition` "AttentionKind".
   */
  kind:
    | "QUALITY_EXCURSION"
    | "DEGRADED_EQUIPMENT_RISK"
    | "BATCH_TARDINESS"
    | "PENDING_APPROVAL"
    | "STUCK_WORKFLOW"
    | "STALE_TWIN_STATE";
  /**
   * Facility-wide epistemic vocabulary. Classes are never flattened into one status.
   */
  epistemic_class: "ACTUAL" | "OBSERVED" | "INFERRED" | "PREDICTED" | "PLANNED" | "COUNTERFACTUAL" | "STALE";
  subject: EntityRef;
  summary: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  source: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  source_revision: string;
  /**
   * Staleness Contract classification, ordered FRESH (best), DEGRADED, STALE (worst).
   */
  freshness: "FRESH" | "DEGRADED" | "STALE";
}
export interface EntityRef {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  entity_type: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  entity_id: string;
}
/**
 * This interface was referenced by `ManufacturingOverviewResponse`'s JSON-Schema
 * via the `definition` "CursorPage".
 */
export interface CursorPage {
  limit: number;
  /**
   * Opaque server cursor; null when no further window exists.
   */
  next_cursor: string | null;
}
/**
 * Read-only Twin-backed facility state for one explicit world. Lifecycle, execution and hold dimensions remain separate; freshness and epistemic class are preserved from the Twin.
 *
 * This interface was referenced by `ContractRoot`'s JSON-Schema
 * via the `definition` "FacilityStateResponse".
 */
export interface FacilityStateResponse {
  contract_version: "bff.facility-state.v1";
  meta: QueryMeta;
  facility: FacilityState;
}
/**
 * This interface was referenced by `FacilityStateResponse`'s JSON-Schema
 * via the `definition` "FacilityState".
 */
export interface FacilityState {
  equipment: EquipmentState[];
  lots: LotState[];
}
/**
 * This interface was referenced by `FacilityStateResponse`'s JSON-Schema
 * via the `definition` "EquipmentState".
 */
export interface EquipmentState {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  equipment_id: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  revision: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  equipment_state: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  maintenance_state: string;
  /**
   * Facility-wide epistemic vocabulary. Classes are never flattened into one status.
   */
  epistemic_class: "ACTUAL" | "OBSERVED" | "INFERRED" | "PREDICTED" | "PLANNED" | "COUNTERFACTUAL" | "STALE";
  /**
   * Staleness Contract classification, ordered FRESH (best), DEGRADED, STALE (worst).
   */
  freshness: "FRESH" | "DEGRADED" | "STALE";
}
/**
 * This interface was referenced by `FacilityStateResponse`'s JSON-Schema
 * via the `definition` "LotState".
 */
export interface LotState {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  lot_id: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  revision: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  lifecycle_state: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  execution_state: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  hold_state: string;
  route_position: RoutePosition;
  /**
   * Facility-wide epistemic vocabulary. Classes are never flattened into one status.
   */
  epistemic_class: "ACTUAL" | "OBSERVED" | "INFERRED" | "PREDICTED" | "PLANNED" | "COUNTERFACTUAL" | "STALE";
  /**
   * Staleness Contract classification, ordered FRESH (best), DEGRADED, STALE (worst).
   */
  freshness: "FRESH" | "DEGRADED" | "STALE";
}
/**
 * This interface was referenced by `FacilityStateResponse`'s JSON-Schema
 * via the `definition` "RoutePosition".
 */
export interface RoutePosition {
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  route_id: string;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  visit_id: string;
  position: number;
  /**
   * Opaque nonblank identifier or revision token. Compared for equality only.
   */
  operation_class_id: string;
}
