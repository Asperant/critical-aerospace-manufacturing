import type {
  EquipmentState,
  FacilityStateResponse,
  LotState,
} from "../contract/generated";

export type FacilityStateResult =
  | { status: "ok"; state: FacilityStateResponse }
  | { status: "unauthenticated" }
  | { status: "invalid"; message: string }
  | { status: "unavailable"; sources: string[] };

export class FacilityStateError extends Error {}

export interface FacilityStateQuery {
  worldId: string;
  simulationRunId?: string;
  branchId?: string;
  asOf?: string;
}

const STATE_URL = "/v1/facility-state";
const FRESHNESS = ["FRESH", "DEGRADED", "STALE"] as const;
const EPISTEMIC = [
  "ACTUAL",
  "OBSERVED",
  "INFERRED",
  "PREDICTED",
  "PLANNED",
  "COUNTERFACTUAL",
  "STALE",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "";
}

function isOneOf<T extends string>(
  value: unknown,
  allowed: readonly T[],
): value is T {
  return typeof value === "string" && allowed.includes(value as T);
}

function isEquipment(value: unknown): value is EquipmentState {
  return (
    isRecord(value) &&
    isText(value["equipment_id"]) &&
    isText(value["revision"]) &&
    isText(value["equipment_state"]) &&
    isText(value["maintenance_state"]) &&
    isOneOf(value["epistemic_class"], EPISTEMIC) &&
    isOneOf(value["freshness"], FRESHNESS)
  );
}

function isLot(value: unknown): value is LotState {
  if (!isRecord(value)) return false;
  const route = value["route_position"];
  return (
    isText(value["lot_id"]) &&
    isText(value["revision"]) &&
    isText(value["lifecycle_state"]) &&
    isText(value["execution_state"]) &&
    isText(value["hold_state"]) &&
    isRecord(route) &&
    isText(route["route_id"]) &&
    isText(route["visit_id"]) &&
    typeof route["position"] === "number" &&
    Number.isInteger(route["position"]) &&
    route["position"] >= 0 &&
    isText(route["operation_class_id"]) &&
    isOneOf(value["epistemic_class"], EPISTEMIC) &&
    isOneOf(value["freshness"], FRESHNESS)
  );
}

function isMeta(value: unknown): value is FacilityStateResponse["meta"] {
  if (!isRecord(value)) return false;
  const world = value["world"];
  const sources = value["sources"];
  return (
    isText(value["revision"]) &&
    isText(value["as_of"]) &&
    isText(value["generated_at"]) &&
    isOneOf(value["freshness"], FRESHNESS) &&
    isRecord(world) &&
    isText(world["world_id"]) &&
    Array.isArray(sources) &&
    sources.length > 0 &&
    sources.every(
      (source) =>
        isRecord(source) &&
        isText(source["source"]) &&
        isText(source["revision"]) &&
        isText(source["as_of"]) &&
        isOneOf(source["freshness"], FRESHNESS),
    ) &&
    isText(value["correlation_id"])
  );
}

export function isFacilityStateResponse(
  value: unknown,
): value is FacilityStateResponse {
  if (!isRecord(value) || value["contract_version"] !== "bff.facility-state.v1")
    return false;
  const facility = value["facility"];
  return (
    isMeta(value["meta"]) &&
    isRecord(facility) &&
    Array.isArray(facility["equipment"]) &&
    facility["equipment"].every(isEquipment) &&
    Array.isArray(facility["lots"]) &&
    facility["lots"].every(isLot)
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

export async function fetchFacilityState(
  query: FacilityStateQuery,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<FacilityStateResult> {
  if (query.worldId.trim() === "")
    throw new FacilityStateError("world_id is required");
  const params = new URLSearchParams({ world_id: query.worldId });
  if (query.simulationRunId)
    params.set("simulation_run_id", query.simulationRunId);
  if (query.branchId) params.set("branch_id", query.branchId);
  if (query.asOf) params.set("as_of", query.asOf);
  const url = `${STATE_URL}?${params.toString()}`;
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
    throw new FacilityStateError("The BFF could not be reached");
  }
  if (response.status === 401) return { status: "unauthenticated" };
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new FacilityStateError("The BFF reply was not JSON");
  }
  if (response.status === 200) {
    if (!isFacilityStateResponse(body))
      throw new FacilityStateError(
        "The BFF reply is not a facility-state view",
      );
    return { status: "ok", state: body };
  }
  const failure = envelope(body);
  if (failure !== null && response.status === 400)
    return { status: "invalid", message: failure.message };
  if (failure !== null && response.status === 503)
    return { status: "unavailable", sources: failure.sources };
  throw new FacilityStateError(`Unexpected BFF status ${response.status}`);
}
