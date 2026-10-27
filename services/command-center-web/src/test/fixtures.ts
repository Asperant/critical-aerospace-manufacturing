import { readFileSync } from "node:fs";
import { join } from "node:path";

import type {
  FacilityStateResponse,
  ManufacturingOverviewResponse,
  SessionResponse,
} from "../contract/generated";

const contracts = join(
  import.meta.dirname,
  "../../../operations-bff/contracts/v1",
);

function load<T>(name: string): T {
  return JSON.parse(readFileSync(join(contracts, name), "utf8")) as T;
}

/** The operations-bff contract fixtures, so tests use the real wire shapes. */
export function contractSession(): SessionResponse {
  return load<SessionResponse>("session.normal.json");
}

export function contractOverview(): ManufacturingOverviewResponse {
  return load<ManufacturingOverviewResponse>("overview-query.normal.json");
}

export function contractFacilityState(): FacilityStateResponse {
  return load<FacilityStateResponse>("facility-state.normal.json");
}

export function contractOpenApi(): string {
  return readFileSync(join(contracts, "operations-bff.openapi.yaml"), "utf8");
}
