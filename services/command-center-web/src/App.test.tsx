import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { ManufacturingOverviewResponse } from "./contract/generated";
import { SessionProvider } from "./session/SessionProvider";
import {
  contractShowcase,
  envelope,
  FakeBff,
  jsonResponse,
} from "./test/fakeBff";
import { contractOverview, contractSession } from "./test/fixtures";
import { contractFacilityState } from "./test/fixtures";

async function renderAt(path: string, bff: FakeBff = new FakeBff().install()) {
  const view = render(
    <MemoryRouter initialEntries={[path]}>
      <SessionProvider>
        <App />
      </SessionProvider>
    </MemoryRouter>,
  );
  await act(async () => undefined);
  return { bff, ...view };
}

const banner = () => screen.getByRole("banner");

async function click(element: HTMLElement) {
  await act(async () => {
    fireEvent.click(element);
  });
}

describe("routes and shell", () => {
  it("mounts the root layout with navigation and a session area", async () => {
    await renderAt("/overview");
    expect(banner()).toHaveTextContent("Manufacturing Command Center");
    expect(
      within(banner()).getByRole("navigation", { name: "Primary" }),
    ).toBeInTheDocument();
    expect(
      within(banner()).getByRole("group", { name: "Session" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("sends the root path to the overview", async () => {
    await renderAt("/");
    expect(
      screen.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeInTheDocument();
  });

  it("shows a not-found page with a way back for unknown routes", async () => {
    await renderAt("/nowhere");
    expect(
      screen.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Go to the overview" }),
    ).toHaveAttribute("href", "/overview");
  });
});

describe("sign in", () => {
  it("shows Sign in and the neutral message when the session is gone", async () => {
    const bff = new FakeBff();
    bff.session = null;
    bff.install();
    await renderAt("/overview", bff);
    const link = within(banner()).getByRole("link", { name: "Sign in" });
    expect(link).toHaveAttribute("href", "/v1/session/login");
    expect(screen.getByText("Sign-in required.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sign out" }),
    ).not.toBeInTheDocument();
    expect(bff.paths()).toEqual(["GET /v1/session"]); // sign-in is a navigation, not a request
  });

  it("shows an error state when the session cannot be loaded", async () => {
    const bff = new FakeBff();
    bff.sessionStatus = 503;
    bff.install();
    await renderAt("/overview", bff);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The session could not be loaded.",
    );
    expect(
      within(banner()).getByText("Session unavailable"),
    ).toBeInTheDocument();
  });
});

describe("authenticated shell", () => {
  it("renders the server-derived actor in the header and the session details", async () => {
    await renderAt("/overview");
    const session = contractSession();
    expect(
      within(banner()).getByText(session.actor.display_name),
    ).toBeInTheDocument();
    expect(screen.getByText(session.actor.actor_id)).toBeInTheDocument();
    expect(
      screen.getByText(session.actor.roles.join(", ")),
    ).toBeInTheDocument();
    expect(screen.getByText(session.environment_id)).toBeInTheDocument();
    expect(
      within(banner()).queryByRole("link", { name: "Sign in" }),
    ).not.toBeInTheDocument();
  });

  it("signs out with the session's CSRF value and returns to the unauthenticated state", async () => {
    const { bff } = await renderAt("/overview");
    await click(within(banner()).getByRole("button", { name: "Sign out" }));
    await waitFor(() =>
      expect(
        within(banner()).getByRole("link", { name: "Sign in" }),
      ).toBeInTheDocument(),
    );
    const logout = bff.calls.find((call) => call.path === "/v1/session/logout");
    expect(logout?.method).toBe("POST");
    expect(logout?.headers["X-CSRF-Token"]).toBe(contractSession().csrf_token);
    expect(logout?.credentials).toBe("include");
    expect(screen.getByText("Sign-in required.")).toBeInTheDocument();
    expect(
      screen.queryByText(contractSession().actor.actor_id),
    ).not.toBeInTheDocument();
    expect(bff.session).toBeNull(); // the server ended it
  });

  it("stays signed in and says so when sign-out is refused", async () => {
    const bff = new FakeBff();
    bff.logoutStatus = 403;
    bff.install();
    await renderAt("/overview", bff);
    await click(within(banner()).getByRole("button", { name: "Sign out" }));
    expect(await within(banner()).findByRole("alert")).toHaveTextContent(
      "Sign-out failed",
    );
    expect(
      within(banner()).getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("keeps credentials in memory only", async () => {
    await renderAt("/overview?world_id=W-SYNTHETIC-TEST");
    await screen.findByRole("list", { name: "Needs attention" });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
    expect(document.body.textContent).not.toContain(
      contractSession().csrf_token,
    );
  });
});

describe("overview", () => {
  it("renders Twin-backed equipment and lot state for the selected world", async () => {
    const { bff } = await renderAt("/overview?world_id=W-SYNTHETIC-TEST");
    const state = contractFacilityState();
    const equipment = state.facility.equipment[0];
    const lot = state.facility.lots[0];
    if (!equipment || !lot) throw new Error("facility fixture is empty");
    expect(
      await screen.findByRole("heading", { level: 2, name: "Facility state" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Facility equipment" }),
    ).toHaveTextContent(equipment.equipment_id);
    expect(
      screen.getByRole("table", { name: "Production lots" }),
    ).toHaveTextContent(lot.lifecycle_state);
    const stateCall = bff.calls.find(
      (call) => call.path === "/v1/facility-state",
    );
    expect(stateCall?.query.get("world_id")).toBe("W-SYNTHETIC-TEST");
  });

  it("keeps facility-state unavailability separate from the overview alert", async () => {
    const bff = new FakeBff();
    bff.facilityState = () =>
      jsonResponse(
        503,
        envelope("DEPENDENCY_UNAVAILABLE", "Twin is unavailable", {
          unavailable_sources: ["digital-twin-service"],
        }),
      );
    bff.install();
    await renderAt("/overview?world_id=W-SYNTHETIC-TEST", bff);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "digital-twin-service",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("polls the BFF for the same world at a bounded cadence", async () => {
    vi.useFakeTimers();
    try {
      const bff = new FakeBff();
      let revision = 0;
      bff.facilityState = () => {
        const body = structuredClone(contractFacilityState());
        body.meta.revision = `state-poll-${revision++}`;
        return jsonResponse(200, body);
      };
      bff.install();
      await renderAt("/overview?world_id=W-SYNTHETIC-TEST", bff);
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(
        bff.calls.filter((call) => call.path === "/v1/facility-state"),
      ).toHaveLength(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("asks for a world before fetching anything", async () => {
    const { bff } = await renderAt("/overview");
    expect(
      screen.getByText("Select a world to load the overview."),
    ).toBeInTheDocument();
    expect(bff.paths()).toEqual(["GET /v1/session"]);
  });

  it("selects a world through the URL and requests it from the BFF", async () => {
    const { bff } = await renderAt("/overview");
    fireEvent.change(screen.getByLabelText("World ID"), {
      target: { value: "W-SYNTHETIC-TEST" },
    });
    await click(screen.getByRole("button", { name: "Load overview" }));
    await screen.findByRole("list", { name: "Needs attention" });
    const call = bff.calls.find((c) => c.path === "/v1/overview");
    expect(call?.query.get("world_id")).toBe("W-SYNTHETIC-TEST");
    expect(call?.credentials).toBe("include");
  });

  it("renders the attention items with their class, source and freshness", async () => {
    await renderAt("/overview?world_id=W-SYNTHETIC-TEST");
    const list = await screen.findByRole("list", { name: "Needs attention" });
    const items = within(list).getAllByRole("listitem");
    const expected = contractOverview().needs_attention;
    expect(items).toHaveLength(expected.length);
    for (const [index, item] of expected.entries()) {
      const rendered = items[index];
      expect(rendered).toHaveTextContent(item.summary);
      expect(rendered).toHaveTextContent(item.kind);
      expect(rendered).toHaveTextContent(item.epistemic_class);
      expect(rendered).toHaveTextContent(
        `${item.source} @ ${item.source_revision}`,
      );
      expect(rendered).toHaveTextContent(item.freshness);
    }
  });

  it("preserves revision, as_of, freshness, world and sources", async () => {
    await renderAt("/overview?world_id=W-SYNTHETIC-TEST");
    const meta = await screen.findByRole("region", {
      name: "Overview metadata",
    });
    const { meta: expected } = contractOverview();
    expect(meta).toHaveTextContent(expected.revision);
    expect(meta).toHaveTextContent(expected.as_of);
    expect(meta).toHaveTextContent(expected.generated_at);
    expect(meta).toHaveTextContent(expected.world.world_id);
    expect(meta).toHaveTextContent(expected.freshness);
    expect(meta).toHaveTextContent("Some data may be out of date (DEGRADED).");
    const sources = within(meta).getByRole("table", { name: "Sources" });
    for (const source of expected.sources) {
      const row = within(sources).getByRole("row", {
        name: new RegExp(source.source),
      });
      expect(row).toHaveTextContent(source.revision);
      expect(row).toHaveTextContent(source.as_of);
      expect(row).toHaveTextContent(source.freshness);
    }
  });

  it("says nothing needs attention only when every source answered", async () => {
    const empty: ManufacturingOverviewResponse = {
      ...contractOverview(),
      needs_attention: [],
    };
    const bff = new FakeBff().withOverview(empty).install();
    await renderAt("/overview?world_id=W", bff);
    expect(
      await screen.findByText(
        "Nothing needs attention in the reported sources.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Sources" })).toBeInTheDocument();
  });

  it("returns to the unauthenticated experience on 401", async () => {
    const bff = new FakeBff();
    bff.overview = () =>
      jsonResponse(401, envelope("UNAUTHORIZED", "Authentication required"));
    bff.install();
    await renderAt("/overview?world_id=W", bff);
    await within(banner()).findByRole("link", { name: "Sign in" });
    expect(screen.getByText("Sign-in required.")).toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "Needs attention" }),
    ).not.toBeInTheDocument();
  });

  it("shows an explicit unavailable state on 503, never an empty overview", async () => {
    const bff = new FakeBff();
    bff.overview = () =>
      jsonResponse(
        503,
        envelope("DEPENDENCY_UNAVAILABLE", "unavailable", {
          unavailable_sources: ["digital-twin-service"],
          required: false,
        }),
      );
    bff.install();
    await renderAt("/overview?world_id=W", bff);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The overview is unavailable");
    expect(alert).toHaveTextContent("digital-twin-service");
    expect(
      screen.queryByText(/Nothing needs attention/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "Needs attention" }),
    ).not.toBeInTheDocument();
    bff.overview = () => jsonResponse(200, contractOverview());
    await click(within(alert).getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("list", { name: "Needs attention" }),
    ).toBeInTheDocument();
  });

  it("shows a rejected request and a malformed reply visibly", async () => {
    const rejected = new FakeBff();
    rejected.overview = () =>
      jsonResponse(400, envelope("VALIDATION_ERROR", "world_id is not valid"));
    rejected.install();
    const first = await renderAt("/overview?world_id=W", rejected);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "world_id is not valid",
    );
    first.unmount();

    const malformed = new FakeBff();
    malformed.overview = () =>
      jsonResponse(200, { contract_version: "bff.overview-query.v1" });
    malformed.install();
    await renderAt("/overview?world_id=W", malformed);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The overview could not be loaded.",
    );
  });

  function pagedBff() {
    const base = contractOverview();
    const template = base.needs_attention[0];
    if (!template) throw new Error("fixture has no items");
    const first: ManufacturingOverviewResponse = {
      ...base,
      page: { limit: 2, next_cursor: "CUR-1" },
    };
    const second: ManufacturingOverviewResponse = {
      ...base,
      needs_attention: [
        { ...template, item_id: "A-003", summary: "Second page item" },
      ],
      page: { limit: 2, next_cursor: null },
    };
    return { first, second };
  }

  it("pages with the cursor and appends the next page", async () => {
    const { first, second } = pagedBff();
    const bff = new FakeBff();
    bff.overview = (query) =>
      jsonResponse(200, query.get("cursor") === "CUR-1" ? second : first);
    bff.install();
    await renderAt("/overview?world_id=W", bff);
    await click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Second page item")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(
      screen.queryByRole("button", { name: "Load more" }),
    ).not.toBeInTheDocument();
    const cursors = bff.calls
      .filter((c) => c.path === "/v1/overview")
      .map((c) => c.query.get("cursor"));
    expect(cursors).toEqual([null, "CUR-1"]);
  });

  it("restarts from the first page when the view moved on", async () => {
    const { first } = pagedBff();
    const bff = new FakeBff();
    bff.overview = (query) =>
      query.get("cursor") === "CUR-1"
        ? jsonResponse(400, envelope("STALE_STATE", "The overview changed"))
        : jsonResponse(200, first);
    bff.install();
    await renderAt("/overview?world_id=W", bff);
    await click(await screen.findByRole("button", { name: "Load more" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "The overview changed while it was being paged.",
    );
    await click(within(alert).getByRole("button", { name: "Reload" }));
    expect(
      await screen.findByRole("button", { name: "Load more" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(
      first.needs_attention.length,
    );
  });
});

describe("system view", () => {
  it("renders the runtime flow, health readout and persisted identities from the BFF", async () => {
    const bff = new FakeBff().withShowcase(contractShowcase()).install();
    await renderAt(
      "/system?world_id=W-SYNTHETIC-TEST&lot_id=LOT-SYNTHETIC-001",
      bff,
    );
    expect(
      await screen.findByRole("heading", { level: 2, name: "System flow" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Simulator")).toBeInTheDocument();
    expect(screen.getAllByText("NATS / JetStream")).not.toHaveLength(0);
    expect(
      screen.getByRole("heading", { level: 2, name: "System health" }),
    ).toBeInTheDocument();
    expect(screen.getByText("CMD-SYNTHETIC-001")).toBeInTheDocument();
    expect(screen.getAllByText("reported by runtime")).not.toHaveLength(0);
    const call = bff.calls.find((item) => item.path === "/v1/showcase");
    expect(call?.query.get("world_id")).toBe("W-SYNTHETIC-TEST");
    expect(call?.query.get("lot_id")).toBe("LOT-SYNTHETIC-001");
  });

  it("does not invent a healthy state when the BFF read model is unavailable", async () => {
    const bff = new FakeBff();
    bff.showcase = () => jsonResponse(503);
    bff.install();
    await renderAt("/system", bff);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Runtime evidence is unavailable.",
    );
    expect(screen.queryByText("PASS")).not.toBeInTheDocument();
  });
});

describe("browser to BFF only", () => {
  it("sends every request to a /v1 BFF path", async () => {
    const { bff } = await renderAt("/overview?world_id=W");
    await screen.findByRole("list", { name: "Needs attention" });
    await click(within(banner()).getByRole("button", { name: "Sign out" }));
    await waitFor(() =>
      expect(bff.paths()).toContain("POST /v1/session/logout"),
    );
    expect(bff.calls.every((call) => call.path.startsWith("/v1/"))).toBe(true);
    expect(bff.calls.every((call) => !("Authorization" in call.headers))).toBe(
      true,
    );
  });
});
