import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { contractSession } from "../test/fixtures";
import {
  SessionProvider,
  useSession,
  type SessionLoader,
} from "./SessionProvider";
import type { SessionResult } from "./sessionClient";

function Probe() {
  return <p data-testid="state">{useSession().status}</p>;
}

function deferred() {
  let resolve: (result: SessionResult) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<SessionResult>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("SessionProvider", () => {
  it("starts loading and then shows the authenticated state", async () => {
    const pending = deferred();
    render(
      <SessionProvider loadSession={() => pending.promise}>
        <Probe />
      </SessionProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("loading");
    await act(async () =>
      pending.resolve({ status: "authenticated", session: contractSession() }),
    );
    expect(screen.getByTestId("state")).toHaveTextContent("authenticated");
  });

  it("shows the unauthenticated state", async () => {
    const pending = deferred();
    render(
      <SessionProvider loadSession={() => pending.promise}>
        <Probe />
      </SessionProvider>,
    );
    await act(async () => pending.resolve({ status: "unauthenticated" }));
    expect(screen.getByTestId("state")).toHaveTextContent("unauthenticated");
  });

  it("shows an error state when the session cannot be determined", async () => {
    const pending = deferred();
    render(
      <SessionProvider loadSession={() => pending.promise}>
        <Probe />
      </SessionProvider>,
    );
    await act(async () => pending.reject(new Error("down")));
    expect(screen.getByTestId("state")).toHaveTextContent("error");
  });

  it("aborts the request on unmount and ignores a late answer", async () => {
    const pending = deferred();
    let seen: AbortSignal | undefined;
    const loader: SessionLoader = (signal) => {
      seen = signal;
      return pending.promise;
    };
    const view = render(
      <SessionProvider loadSession={loader}>
        <Probe />
      </SessionProvider>,
    );
    view.unmount();
    expect(seen?.aborted).toBe(true);
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    await act(async () => pending.resolve({ status: "unauthenticated" }));
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("refuses to be used outside its provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Probe />)).toThrow(
      "useSession must be used inside SessionProvider",
    );
    spy.mockRestore();
  });
});
