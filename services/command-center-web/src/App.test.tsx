import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { SessionProvider, type SessionLoader } from "./session/SessionProvider";
import { contractSession } from "./test/fixtures";

const authenticated: SessionLoader = async () => ({
  status: "authenticated",
  session: contractSession(),
});
const anonymous: SessionLoader = async () => ({ status: "unauthenticated" });

async function renderAt(path: string, loadSession: SessionLoader = anonymous) {
  const view = render(
    <MemoryRouter initialEntries={[path]}>
      <SessionProvider loadSession={loadSession}>
        <App />
      </SessionProvider>
    </MemoryRouter>,
  );
  await act(async () => undefined);
  return view;
}

describe("App", () => {
  it("mounts the root layout", async () => {
    await renderAt("/overview");
    expect(screen.getByRole("banner")).toHaveTextContent(
      "Manufacturing Command Center",
    );
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("renders the placeholder overview route", async () => {
    await renderAt("/overview");
    expect(
      screen.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Operational data is not connected yet."),
    ).toBeInTheDocument();
  });

  it("sends the root path to the overview", async () => {
    await renderAt("/");
    expect(
      screen.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeInTheDocument();
  });

  it("shows a not-found page for unknown routes", async () => {
    await renderAt("/nowhere");
    expect(
      screen.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeInTheDocument();
  });
});

describe("session summary on the overview", () => {
  it("shows a loading state while the session is read", () => {
    const never: SessionLoader = () => new Promise(() => undefined);
    render(
      <MemoryRouter initialEntries={["/overview"]}>
        <SessionProvider loadSession={never}>
          <App />
        </SessionProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading session");
  });

  it("renders the server-derived actor", async () => {
    await renderAt("/overview", authenticated);
    const session = contractSession();
    expect(screen.getByText(session.actor.display_name)).toBeInTheDocument();
    expect(screen.getByText(session.actor.actor_id)).toBeInTheDocument();
    expect(
      screen.getByText(session.actor.roles.join(", ")),
    ).toBeInTheDocument();
    expect(screen.getByText(session.environment_id)).toBeInTheDocument();
    expect(screen.queryByText("Sign-in required.")).not.toBeInTheDocument();
  });

  it("shows a neutral sign-in-required state without any sign-in control", async () => {
    await renderAt("/overview", anonymous);
    expect(screen.getByText("Sign-in required.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows an error state when the session cannot be loaded", async () => {
    const failing: SessionLoader = async () => {
      throw new Error("down");
    };
    await renderAt("/overview", failing);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The session could not be loaded.",
    );
  });

  it("keeps credentials in memory only: no storage, no cookie writes, no csrf token shown", async () => {
    await renderAt("/overview", authenticated);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
    expect(document.body.textContent).not.toContain(
      contractSession().csrf_token,
    );
  });
});
