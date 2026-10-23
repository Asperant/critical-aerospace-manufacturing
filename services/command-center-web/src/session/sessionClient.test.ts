import { describe, expect, it, vi } from "vitest";

import { contractSession } from "../test/fixtures";
import {
  fetchSession,
  isSessionResponse,
  SessionError,
  signOut,
} from "./sessionClient";

function replying(status: number, body?: unknown) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
}

const unauthorized = {
  error_code: "SESSION_REQUIRED",
  category: "UNAUTHORIZED",
  message: "Authentication required",
  retryable: false,
  correlation_id: "C-1",
};

describe("fetchSession", () => {
  it("returns the server-derived session for a 200", async () => {
    const session = contractSession();
    const result = await fetchSession(
      new AbortController().signal,
      replying(200, session),
    );
    expect(result).toEqual({ status: "authenticated", session });
  });

  it("asks the BFF only, with the cookie and nothing that asserts identity", async () => {
    const fetchMock = replying(200, contractSession());
    const controller = new AbortController();
    await fetchSession(controller.signal, fetchMock);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/v1/session");
    expect(init?.credentials).toBe("include");
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.body ?? null).toBeNull();
    expect(init?.headers).toEqual({ Accept: "application/json" });
    expect(init?.signal).toBe(controller.signal);
  });

  it("treats 401 as unauthenticated", async () => {
    const result = await fetchSession(
      new AbortController().signal,
      replying(401, unauthorized),
    );
    expect(result).toEqual({ status: "unauthenticated" });
  });

  it.each([403, 500, 503])(
    "treats status %i as an error, not as a session",
    async (status) => {
      await expect(
        fetchSession(
          new AbortController().signal,
          replying(status, unauthorized),
        ),
      ).rejects.toBeInstanceOf(SessionError);
    },
  );

  it("treats a network failure as an error", async () => {
    const failing = vi.fn<typeof fetch>(async () => {
      throw new TypeError("network down");
    });
    await expect(
      fetchSession(new AbortController().signal, failing),
    ).rejects.toBeInstanceOf(SessionError);
  });

  it("lets an aborted request surface as an abort, not a session error", async () => {
    const controller = new AbortController();
    controller.abort();
    const aborted = vi.fn<typeof fetch>(async () => {
      throw new DOMException("aborted", "AbortError");
    });
    await expect(
      fetchSession(controller.signal, aborted),
    ).rejects.not.toBeInstanceOf(SessionError);
  });

  it("rejects replies that are not JSON", async () => {
    const html = vi.fn<typeof fetch>(
      async () => new Response("<html></html>", { status: 200 }),
    );
    await expect(
      fetchSession(new AbortController().signal, html),
    ).rejects.toBeInstanceOf(SessionError);
  });
});

describe("isSessionResponse", () => {
  it("accepts the contract fixture", () => {
    expect(isSessionResponse(contractSession())).toBe(true);
  });

  it("refuses an actor that is not derived from the session", () => {
    const forged = {
      ...contractSession(),
      actor: { ...contractSession().actor, derived_from: "CLIENT" },
    };
    expect(isSessionResponse(forged)).toBe(false);
  });

  it.each([
    "actor",
    "environment_id",
    "expires_at",
    "csrf_token",
    "contract_version",
  ])("refuses a reply without %s", (field) => {
    const partial: Record<string, unknown> = { ...contractSession() };
    delete partial[field];
    expect(isSessionResponse(partial)).toBe(false);
  });

  it.each([null, "session", 42, [], {}])("refuses %j", (value) => {
    expect(isSessionResponse(value)).toBe(false);
  });
});

describe("signOut", () => {
  const signal = () => new AbortController().signal;

  it("posts to the BFF with the cookie and the session's CSRF value only", async () => {
    const fetchMock = replying(204);
    await signOut("CSRF-1", signal(), fetchMock);
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/v1/session/logout");
    expect(init?.method).toBe("POST");
    expect(init?.credentials).toBe("include");
    expect(init?.body ?? null).toBeNull();
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "X-CSRF-Token": "CSRF-1",
    });
  });

  it("treats an already-ended session (401) as signed out", async () => {
    await expect(
      signOut("CSRF-1", signal(), replying(401, unauthorized)),
    ).resolves.toBeUndefined();
  });

  it.each([403, 500])("reports status %i as a failure", async (status) => {
    await expect(
      signOut("CSRF-1", signal(), replying(status)),
    ).rejects.toBeInstanceOf(SessionError);
  });

  it("reports a network failure", async () => {
    const failing = vi.fn<typeof fetch>(async () => {
      throw new TypeError("down");
    });
    await expect(signOut("CSRF-1", signal(), failing)).rejects.toBeInstanceOf(
      SessionError,
    );
  });
});
