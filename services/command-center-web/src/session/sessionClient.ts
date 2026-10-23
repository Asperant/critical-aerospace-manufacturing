import type { ErrorEnvelope, SessionResponse } from "../contract/generated";

/** Outcome of asking the BFF who the current session belongs to. */
export type SessionResult =
  | { status: "authenticated"; session: SessionResponse }
  | { status: "unauthenticated" };

/** The session could not be determined or ended: network failure or unexpected reply. */
export class SessionError extends Error {}

const SESSION_URL = "/v1/session";
const LOGOUT_URL = "/v1/session/logout";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "";
}

/** Runtime check that a reply really is a bff.session.v1 session. */
export function isSessionResponse(value: unknown): value is SessionResponse {
  if (!isRecord(value) || value["contract_version"] !== "bff.session.v1")
    return false;
  const actor = value["actor"];
  return (
    isRecord(actor) &&
    actor["derived_from"] === "SESSION" &&
    isText(actor["actor_id"]) &&
    isText(actor["display_name"]) &&
    Array.isArray(actor["roles"]) &&
    actor["roles"].every(isText) &&
    isText(value["environment_id"]) &&
    isText(value["authenticated_at"]) &&
    isText(value["expires_at"]) &&
    isText(value["csrf_token"])
  );
}

export function isUnauthorized(value: unknown): value is ErrorEnvelope {
  return isRecord(value) && value["category"] === "UNAUTHORIZED";
}

/**
 * Reads the current session from the BFF. The browser holds only the HttpOnly
 * session cookie, which `credentials: "include"` sends; identity comes from the
 * server's reply and nothing is sent that could assert one.
 */
export async function fetchSession(
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<SessionResult> {
  let response: Response;
  try {
    response = await fetchImpl(SESSION_URL, {
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new SessionError("The BFF could not be reached");
  }
  if (response.status === 401) return { status: "unauthenticated" };
  if (response.status !== 200) {
    throw new SessionError(`Unexpected BFF status ${response.status}`);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new SessionError("The BFF reply was not JSON");
  }
  if (!isSessionResponse(body)) {
    throw new SessionError("The BFF reply is not a bff.session.v1 session");
  }
  return { status: "authenticated", session: body };
}

/**
 * Ends the session on the server. The CSRF value is the one the BFF itself gave
 * this session; it is a request-forgery guard and carries no authority. A 401
 * means the session was already gone, which is the state the caller wants.
 */
export async function signOut(
  csrfToken: string,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  let response: Response;
  try {
    response = await fetchImpl(LOGOUT_URL, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json", "X-CSRF-Token": csrfToken },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new SessionError("The BFF could not be reached");
  }
  if (response.status === 204 || response.status === 401) return;
  throw new SessionError(`Sign-out was refused with status ${response.status}`);
}
