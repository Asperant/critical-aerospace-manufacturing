import { describe, expect, it, vi } from "vitest";

import { contractFacilityState } from "../test/fixtures";
import { envelope, jsonResponse } from "../test/fakeBff";
import {
  fetchFacilityState,
  FacilityStateError,
  isFacilityStateResponse,
} from "./facilityStateClient";

function replying(status: number, body?: unknown) {
  return vi.fn<typeof fetch>(async () => jsonResponse(status, body));
}

const signal = () => new AbortController().signal;

describe("fetchFacilityState", () => {
  it("sends the explicit world and optional scope through the BFF", async () => {
    const fetchMock = replying(200, contractFacilityState());
    await fetchFacilityState(
      {
        worldId: "W SYNTHETIC/1",
        simulationRunId: "RUN-1",
        branchId: "PRIMARY",
        asOf: "2026-10-23T09:00:00Z",
      },
      signal(),
      fetchMock,
    );
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe(
      "/v1/facility-state?world_id=W+SYNTHETIC%2F1&simulation_run_id=RUN-1&branch_id=PRIMARY&as_of=2026-10-23T09%3A00%3A00Z",
    );
    expect(init?.credentials).toBe("include");
    expect(init?.headers).toEqual({ Accept: "application/json" });
    expect(init?.body ?? null).toBeNull();
  });

  it("refuses an empty world before making a request", async () => {
    const fetchMock = replying(200, contractFacilityState());
    await expect(
      fetchFacilityState({ worldId: "  " }, signal(), fetchMock),
    ).rejects.toBeInstanceOf(FacilityStateError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps lifecycle, execution and hold dimensions in the response", async () => {
    const state = contractFacilityState();
    const result = await fetchFacilityState(
      { worldId: "W-1" },
      signal(),
      replying(200, state),
    );
    expect(result).toEqual({ status: "ok", state });
    expect(state.facility.lots[0]).toEqual(
      expect.objectContaining({
        lifecycle_state: expect.any(String),
        execution_state: expect.any(String),
        hold_state: expect.any(String),
      }),
    );
  });

  it("maps authentication and dependency failures without fabricating a view", async () => {
    expect(
      await fetchFacilityState(
        { worldId: "W-1" },
        signal(),
        replying(401, envelope("UNAUTHORIZED", "Authentication required")),
      ),
    ).toEqual({ status: "unauthenticated" });
    expect(
      await fetchFacilityState(
        { worldId: "W-1" },
        signal(),
        replying(
          503,
          envelope("DEPENDENCY_UNAVAILABLE", "unavailable", {
            unavailable_sources: ["digital-twin-service"],
          }),
        ),
      ),
    ).toEqual({
      status: "unavailable",
      sources: ["digital-twin-service"],
    });
  });

  it("rejects malformed success replies and unknown statuses", async () => {
    await expect(
      fetchFacilityState(
        { worldId: "W-1" },
        signal(),
        replying(200, { contract_version: "bff.facility-state.v1" }),
      ),
    ).rejects.toBeInstanceOf(FacilityStateError);
    await expect(
      fetchFacilityState(
        { worldId: "W-1" },
        signal(),
        replying(500, envelope("INTERNAL_ERROR", "x")),
      ),
    ).rejects.toBeInstanceOf(FacilityStateError);
  });
});

describe("isFacilityStateResponse", () => {
  it("accepts the contract fixture and rejects missing dimensions", () => {
    const state = contractFacilityState();
    expect(isFacilityStateResponse(state)).toBe(true);
    const broken = structuredClone(state);
    delete (
      broken.facility.lots[0] as Partial<(typeof broken.facility.lots)[number]>
    ).hold_state;
    expect(isFacilityStateResponse(broken)).toBe(false);
  });
});
