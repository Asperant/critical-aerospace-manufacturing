import { vi } from "vitest";

import type {
  FacilityStateResponse,
  ManufacturingOverviewResponse,
  SessionResponse,
} from "../contract/generated";
import type { ShowcaseResponse } from "../showcase/showcaseClient";
import {
  contractFacilityState,
  contractOverview,
  contractSession,
} from "./fixtures";

export interface RecordedCall {
  method: string;
  path: string;
  query: URLSearchParams;
  headers: Record<string, string>;
  credentials: RequestCredentials | undefined;
}

export function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function contractShowcase(): ShowcaseResponse {
  return {
    contract_version: "bff.showcase.v1",
    meta: {
      world_id: "W-SYNTHETIC-TEST",
      lot_id: "LOT-SYNTHETIC-001",
      freshness: "FRESH",
      correlation_id: "C-SYNTHETIC-SHOWCASE",
    },
    timeline: [
      {
        id: "event-1",
        kind: "EVENT_PUBLISHED",
        label: "Hold event published",
        status: "PUBLISHED",
        source: "core.outbox → NATS/JetStream",
        event_id: "EV-SYNTHETIC-001",
        outbox_id: "OB-SYNTHETIC-001",
      },
    ],
    dispatch: { status: "REJECTED", error_code: "ACTIVE_HOLD" },
    identities: {
      command_id: "CMD-SYNTHETIC-001",
      event_id: "EV-SYNTHETIC-001",
      outbox_id: "OB-SYNTHETIC-001",
      simulator_event_ref: "SIM-SYNTHETIC-001",
      twin_source_event_id: "EV-SYNTHETIC-001",
      twin_status: "FRESH",
    },
    architecture: [
      {
        id: "simulator",
        label: "Simulator",
        status: "OBSERVED",
        detail: "causation SIM-SYNTHETIC-001",
      },
      {
        id: "core",
        label: "Core",
        status: "REPORTED",
        detail: "command outcome read",
      },
      {
        id: "postgresql",
        label: "PostgreSQL",
        status: "READ",
        detail: "authenticated read completed",
      },
      {
        id: "outbox",
        label: "Transactional Outbox",
        status: "PUBLISHED",
        detail: "event published",
      },
      {
        id: "nats",
        label: "NATS / JetStream",
        status: "CONNECTED",
        detail: "CAP_EVENTS/twin-primary connected",
      },
      {
        id: "twin",
        label: "Digital Twin",
        status: "UPDATED",
        detail: "projection FRESH",
      },
      {
        id: "bff",
        label: "BFF",
        status: "SERVING",
        detail: "read model serving",
      },
      {
        id: "ui",
        label: "UI",
        status: "RENDERED",
        detail: "System View rendered",
      },
    ],
    health: [
      {
        id: "postgresql",
        label: "PostgreSQL",
        status: "UP",
        detail: "authenticated read completed",
      },
      { id: "core", label: "Core", status: "UP", detail: "HTTP 200" },
      {
        id: "nats",
        label: "NATS / JetStream",
        status: "UP",
        detail: "stream connected",
      },
      {
        id: "digital-twin",
        label: "Digital Twin",
        status: "UP",
        detail: "projection FRESH",
      },
      { id: "bff", label: "BFF", status: "UP", detail: "response serving" },
      { id: "keycloak", label: "Keycloak", status: "UP", detail: "HTTP 200" },
    ],
    counters: [
      { id: "commands", label: "Commands observed", value: 2 },
      { id: "published-events", label: "Events published", value: 1 },
      { id: "twin-updates", label: "Twin updates", value: 1 },
      { id: "active-holds", label: "Active holds", value: 1 },
      { id: "jetstream-messages", label: "JetStream messages", value: 1 },
    ],
  };
}

export function envelope(
  category: string,
  message: string,
  details?: Record<string, unknown>,
) {
  return {
    error_code: category,
    category,
    message,
    retryable: false,
    correlation_id: "C-SYNTHETIC",
    ...(details ? { details } : {}),
  };
}

/** A stand-in BFF behind the global fetch: the only thing the browser can reach. */
export class FakeBff {
  calls: RecordedCall[] = [];
  session: SessionResponse | null = contractSession();
  sessionStatus: number | null = null;
  logoutStatus: number | null = null;
  overview: (query: URLSearchParams) => Response = () =>
    jsonResponse(200, contractOverview());
  facilityState: (query: URLSearchParams) => Response = () =>
    jsonResponse(200, contractFacilityState());
  showcase: (query: URLSearchParams) => Response = () => jsonResponse(404);

  install(): this {
    vi.stubGlobal("fetch", this.handle);
    return this;
  }

  withOverview(body: ManufacturingOverviewResponse): this {
    this.overview = () => jsonResponse(200, body);
    return this;
  }

  withFacilityState(body: FacilityStateResponse): this {
    this.facilityState = () => jsonResponse(200, body);
    return this;
  }

  withShowcase(body: ShowcaseResponse): this {
    this.showcase = () => jsonResponse(200, body);
    return this;
  }

  private handle = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url = new URL(String(input), "https://cc.invalid");
    this.calls.push({
      method: init?.method ?? "GET",
      path: url.pathname,
      query: url.searchParams,
      headers: { ...(init?.headers as Record<string, string> | undefined) },
      credentials: init?.credentials,
    });
    const call = this.calls[this.calls.length - 1];
    const method = call?.method ?? "GET";
    if (url.pathname === "/v1/session" && method === "GET") {
      if (this.sessionStatus !== null) return jsonResponse(this.sessionStatus);
      return this.session
        ? jsonResponse(200, this.session)
        : jsonResponse(
            401,
            envelope("UNAUTHORIZED", "Authentication required"),
          );
    }
    if (url.pathname === "/v1/session/logout" && method === "POST") {
      if (this.logoutStatus !== null) return jsonResponse(this.logoutStatus);
      if (!this.session)
        return jsonResponse(
          401,
          envelope("UNAUTHORIZED", "Authentication required"),
        );
      if (call?.headers["X-CSRF-Token"] !== this.session.csrf_token) {
        return jsonResponse(
          403,
          envelope("FORBIDDEN", "CSRF token missing or invalid"),
        );
      }
      this.session = null;
      return new Response(null, { status: 204 });
    }
    if (url.pathname === "/v1/overview" && method === "GET") {
      if (!this.session)
        return jsonResponse(
          401,
          envelope("UNAUTHORIZED", "Authentication required"),
        );
      return this.overview(url.searchParams);
    }
    if (url.pathname === "/v1/facility-state" && method === "GET") {
      if (!this.session)
        return jsonResponse(
          401,
          envelope("UNAUTHORIZED", "Authentication required"),
        );
      return this.facilityState(url.searchParams);
    }
    if (url.pathname === "/v1/showcase" && method === "GET") {
      if (!this.session)
        return jsonResponse(
          401,
          envelope("UNAUTHORIZED", "Authentication required"),
        );
      return this.showcase(url.searchParams);
    }
    return jsonResponse(404);
  };

  paths(): string[] {
    return this.calls.map((call) => `${call.method} ${call.path}`);
  }
}
