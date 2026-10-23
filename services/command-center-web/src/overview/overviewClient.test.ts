import { describe, expect, it, vi } from "vitest";

import { contractOverview } from "../test/fixtures";
import { envelope, jsonResponse } from "../test/fakeBff";
import {
  fetchOverview,
  isOverviewResponse,
  OverviewError,
} from "./overviewClient";

function replying(status: number, body?: unknown) {
  return vi.fn<typeof fetch>(async () => jsonResponse(status, body));
}

const signal = () => new AbortController().signal;

describe("fetchOverview", () => {
  it("sends the explicit world, the cookie and nothing that asserts identity", async () => {
    const fetchMock = replying(200, contractOverview());
    await fetchOverview({ worldId: "W SYNTHETIC/1" }, signal(), fetchMock);
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/v1/overview?world_id=W+SYNTHETIC%2F1");
    expect(init?.credentials).toBe("include");
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.body ?? null).toBeNull();
    expect(init?.headers).toEqual({ Accept: "application/json" });
  });

  it("passes the cursor through when paging", async () => {
    const fetchMock = replying(200, contractOverview());
    await fetchOverview(
      { worldId: "W-1", cursor: "CUR-1" },
      signal(),
      fetchMock,
    );
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/v1/overview?world_id=W-1&cursor=CUR-1",
    );
  });

  it("refuses to ask without a world", async () => {
    const fetchMock = replying(200, contractOverview());
    await expect(
      fetchOverview({ worldId: "  " }, signal(), fetchMock),
    ).rejects.toBeInstanceOf(OverviewError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns the view exactly as the contract fixture describes it", async () => {
    const overview = contractOverview();
    const result = await fetchOverview(
      { worldId: "W" },
      signal(),
      replying(200, overview),
    );
    expect(result).toEqual({ status: "ok", overview });
  });

  it("maps 401 to unauthenticated", async () => {
    const result = await fetchOverview(
      { worldId: "W" },
      signal(),
      replying(401, envelope("UNAUTHORIZED", "Authentication required")),
    );
    expect(result).toEqual({ status: "unauthenticated" });
  });

  it("maps a moved view to stale and other 400s to invalid", async () => {
    expect(
      await fetchOverview(
        { worldId: "W" },
        signal(),
        replying(400, envelope("STALE_STATE", "moved")),
      ),
    ).toEqual({ status: "stale" });
    expect(
      await fetchOverview(
        { worldId: "W" },
        signal(),
        replying(400, envelope("VALIDATION_ERROR", "Cursor is not valid")),
      ),
    ).toEqual({ status: "invalid", message: "Cursor is not valid" });
  });

  it("maps 503 to unavailable and names the sources, never to a view", async () => {
    const down = envelope("DEPENDENCY_UNAVAILABLE", "unavailable", {
      unavailable_sources: ["digital-twin-service"],
      required: false,
    });
    const result = await fetchOverview(
      { worldId: "W" },
      signal(),
      replying(503, down),
    );
    expect(result).toEqual({
      status: "unavailable",
      sources: ["digital-twin-service"],
    });
  });

  it.each([403, 404, 500, 502])(
    "treats status %i as an error",
    async (status) => {
      await expect(
        fetchOverview(
          { worldId: "W" },
          signal(),
          replying(status, envelope("INTERNAL_ERROR", "x")),
        ),
      ).rejects.toBeInstanceOf(OverviewError);
    },
  );

  it("treats a network failure and a non-JSON reply as errors", async () => {
    const failing = vi.fn<typeof fetch>(async () => {
      throw new TypeError("down");
    });
    await expect(
      fetchOverview({ worldId: "W" }, signal(), failing),
    ).rejects.toBeInstanceOf(OverviewError);
    const html = vi.fn<typeof fetch>(
      async () => new Response("<html>", { status: 200 }),
    );
    await expect(
      fetchOverview({ worldId: "W" }, signal(), html),
    ).rejects.toBeInstanceOf(OverviewError);
  });

  it("rejects a 200 that is outside the contract", async () => {
    const broken = {
      ...contractOverview(),
      meta: { ...contractOverview().meta, freshness: "PRISTINE" },
    };
    await expect(
      fetchOverview({ worldId: "W" }, signal(), replying(200, broken)),
    ).rejects.toBeInstanceOf(OverviewError);
  });
});

describe("isOverviewResponse", () => {
  it("accepts the contract fixture", () => {
    expect(isOverviewResponse(contractOverview())).toBe(true);
  });

  it.each([
    "revision",
    "as_of",
    "generated_at",
    "freshness",
    "world",
    "sources",
    "correlation_id",
  ])("refuses a view whose meta lacks %s", (field) => {
    const view = contractOverview();
    const meta: Record<string, unknown> = { ...view.meta };
    delete meta[field];
    expect(isOverviewResponse({ ...view, meta })).toBe(false);
  });

  it("refuses unknown kinds, classes and freshness values and bad paging", () => {
    const view = contractOverview();
    const item = view.needs_attention[0];
    expect(
      isOverviewResponse({
        ...view,
        needs_attention: [{ ...item, kind: "OTHER" }],
      }),
    ).toBe(false);
    expect(
      isOverviewResponse({
        ...view,
        needs_attention: [{ ...item, epistemic_class: "TRUE" }],
      }),
    ).toBe(false);
    expect(
      isOverviewResponse({
        ...view,
        needs_attention: [{ ...item, freshness: "?" }],
      }),
    ).toBe(false);
    expect(
      isOverviewResponse({ ...view, page: { limit: "50", next_cursor: null } }),
    ).toBe(false);
    expect(
      isOverviewResponse({ ...view, meta: { ...view.meta, sources: [] } }),
    ).toBe(false);
  });
});
