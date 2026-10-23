import type {
  AttentionItem,
  ManufacturingOverviewResponse,
} from "../contract/generated";

export type OverviewResult =
  | { status: "ok"; overview: ManufacturingOverviewResponse }
  | { status: "unauthenticated" }
  /** The view moved on since the cursor was issued. */
  | { status: "stale" }
  | { status: "invalid"; message: string }
  /** A backend the overview needs could not answer; there is no partial result. */
  | { status: "unavailable"; sources: string[] };

/** The overview could not be read: network failure or a reply outside the contract. */
export class OverviewError extends Error {}

export interface OverviewQuery {
  worldId: string;
  cursor?: string | undefined;
}

const OVERVIEW_URL = "/v1/overview";

const FRESHNESS = ["FRESH", "DEGRADED", "STALE"];
const KINDS: AttentionItem["kind"][] = [
  "QUALITY_EXCURSION",
  "DEGRADED_EQUIPMENT_RISK",
  "BATCH_TARDINESS",
  "PENDING_APPROVAL",
  "STUCK_WORKFLOW",
  "STALE_TWIN_STATE",
];
const EPISTEMIC: AttentionItem["epistemic_class"][] = [
  "ACTUAL",
  "OBSERVED",
  "INFERRED",
  "PREDICTED",
  "PLANNED",
  "COUNTERFACTUAL",
  "STALE",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "";
}

function isOneOf(value: unknown, allowed: readonly string[]): boolean {
  return typeof value === "string" && allowed.includes(value);
}

function isSource(value: unknown): boolean {
  return (
    isRecord(value) &&
    isText(value["source"]) &&
    isText(value["revision"]) &&
    isText(value["as_of"]) &&
    isOneOf(value["freshness"], FRESHNESS)
  );
}

function isItem(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const subject = value["subject"];
  return (
    isText(value["item_id"]) &&
    isOneOf(value["kind"], KINDS) &&
    isOneOf(value["epistemic_class"], EPISTEMIC) &&
    isRecord(subject) &&
    isText(subject["entity_type"]) &&
    isText(subject["entity_id"]) &&
    isText(value["summary"]) &&
    isText(value["source"]) &&
    isText(value["source_revision"]) &&
    isOneOf(value["freshness"], FRESHNESS)
  );
}

/** Runtime check that a reply is a bff.overview-query.v1 view. */
export function isOverviewResponse(
  value: unknown,
): value is ManufacturingOverviewResponse {
  if (!isRecord(value) || value["contract_version"] !== "bff.overview-query.v1")
    return false;
  const meta = value["meta"];
  const page = value["page"];
  const items = value["needs_attention"];
  return (
    isRecord(meta) &&
    isText(meta["revision"]) &&
    isText(meta["as_of"]) &&
    isText(meta["generated_at"]) &&
    isOneOf(meta["freshness"], FRESHNESS) &&
    isRecord(meta["world"]) &&
    isText(meta["world"]["world_id"]) &&
    Array.isArray(meta["sources"]) &&
    meta["sources"].length >= 1 &&
    meta["sources"].every(isSource) &&
    isText(meta["correlation_id"]) &&
    Array.isArray(items) &&
    items.every(isItem) &&
    isRecord(page) &&
    typeof page["limit"] === "number" &&
    (page["next_cursor"] === null || isText(page["next_cursor"]))
  );
}

function envelope(
  value: unknown,
): { category: string; message: string; sources: string[] } | null {
  if (
    !isRecord(value) ||
    !isText(value["category"]) ||
    !isText(value["message"])
  )
    return null;
  const details = value["details"];
  const listed = isRecord(details) ? details["unavailable_sources"] : undefined;
  const sources = Array.isArray(listed) ? listed.filter(isText) : [];
  return { category: value["category"], message: value["message"], sources };
}

/**
 * Reads one page of the Manufacturing Overview from the BFF. The world is always
 * explicit; the browser never composes sources itself.
 */
export async function fetchOverview(
  query: OverviewQuery,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<OverviewResult> {
  if (query.worldId.trim() === "")
    throw new OverviewError("world_id is required");
  const params = new URLSearchParams({ world_id: query.worldId });
  if (query.cursor) params.set("cursor", query.cursor);
  const url = `${OVERVIEW_URL}?${params.toString()}`;
  let response: Response;
  try {
    response = await fetchImpl(url, {
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new OverviewError("The BFF could not be reached");
  }
  if (response.status === 401) return { status: "unauthenticated" };
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new OverviewError("The BFF reply was not JSON");
  }
  if (response.status === 200) {
    if (!isOverviewResponse(body)) {
      throw new OverviewError(
        "The BFF reply is not a bff.overview-query.v1 view",
      );
    }
    return { status: "ok", overview: body };
  }
  const failure = envelope(body);
  if (failure !== null && response.status === 400) {
    return failure.category === "STALE_STATE"
      ? { status: "stale" }
      : { status: "invalid", message: failure.message };
  }
  if (failure !== null && response.status === 503) {
    return { status: "unavailable", sources: failure.sources };
  }
  throw new OverviewError(`Unexpected BFF status ${response.status}`);
}
