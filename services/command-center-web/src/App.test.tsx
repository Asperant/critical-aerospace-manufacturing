import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("mounts the root layout", () => {
    renderAt("/overview");
    expect(screen.getByRole("banner")).toHaveTextContent(
      "Manufacturing Command Center",
    );
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("renders the placeholder overview route", () => {
    renderAt("/overview");
    expect(
      screen.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Operational data is not connected yet."),
    ).toBeInTheDocument();
  });

  it("sends the root path to the overview", () => {
    renderAt("/");
    expect(
      screen.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeInTheDocument();
  });

  it("shows a not-found page for unknown routes", () => {
    renderAt("/nowhere");
    expect(
      screen.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeInTheDocument();
  });
});
