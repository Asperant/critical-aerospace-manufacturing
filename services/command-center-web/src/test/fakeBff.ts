import { vi } from "vitest";

import type {
  ManufacturingOverviewResponse,
  SessionResponse,
} from "../contract/generated";
import { contractOverview, contractSession } from "./fixtures";

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

  install(): this {
    vi.stubGlobal("fetch", this.handle);
    return this;
  }

  withOverview(body: ManufacturingOverviewResponse): this {
    this.overview = () => jsonResponse(200, body);
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
    return jsonResponse(404);
  };

  paths(): string[] {
    return this.calls.map((call) => `${call.method} ${call.path}`);
  }
}
