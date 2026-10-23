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
