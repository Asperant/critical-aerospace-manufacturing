import { expect, test } from "@playwright/test";

import { control, loadOverview, recordTraffic, signIn, WORLD } from "./helpers";

test.beforeEach(async ({ request }) => {
  await control(request, "reset");
});

test.describe("unauthenticated visitor", () => {
  test("sees a neutral sign-in-required overview and a Sign in action", async ({
    page,
  }) => {
    await page.goto("/overview");
    await expect(
      page.getByRole("heading", { level: 1, name: "Manufacturing Overview" }),
    ).toBeVisible();
    await expect(page.getByText("Sign-in required.")).toBeVisible();
    await expect(
      page.getByRole("banner").getByRole("link", { name: "Sign in" }),
    ).toHaveAttribute("href", "/v1/session/login");
    await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
    await expect(page.getByLabel("World ID")).toHaveCount(0);
  });

  test("gets 401 from the BFF for session and overview", async ({
    request,
  }) => {
    expect((await request.get("/v1/session")).status()).toBe(401);
    expect((await request.get(`/v1/overview?world_id=${WORLD}`)).status()).toBe(
      401,
    );
  });
});

test.describe("sign in through the BFF", () => {
  test("follows the BFF redirect chain and ends signed in with a hardened cookie", async ({
    page,
    context,
  }) => {
    const traffic = recordTraffic(page);
    await signIn(page);
    expect(traffic.redirects).toEqual(
      expect.arrayContaining([
        "/v1/session/login",
        "/__fake-idp/authorize",
        "/v1/session/callback",
      ]),
    );
    expect(new URL(page.url()).pathname).toBe("/overview");

    const cookies = await context.cookies();
    const session = cookies.find((cookie) => cookie.name === "cap_session");
    expect(session).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
      path: "/",
    });
    expect(
      cookies.find((cookie) => cookie.name === "cap_login"),
    ).toBeUndefined();

    await expect(page.getByText("U-E2E-01")).toBeVisible();
    await expect(page.getByText("ops-controller")).toBeVisible();
    await expect(page.getByText("ENV-E2E")).toBeVisible();
    expect(await page.evaluate(() => document.cookie)).toBe("");
  });

  test("keeps no credential in browser storage or on the page", async ({
    page,
    request,
  }) => {
    await signIn(page);
    await loadOverview(page);
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toBeVisible();
    const storage = await page.evaluate(() => ({
      local: localStorage.length,
      session: sessionStorage.length,
    }));
    expect(storage).toEqual({ local: 0, session: 0 });
    const csrf = (
      (await (await page.request.get("/v1/session")).json()) as {
        csrf_token: string;
      }
    ).csrf_token;
    expect(await page.content()).not.toContain(csrf);
    const secrets = (await (
      await request.get("/__control/provider-secrets")
    ).json()) as string[];
    const html = await page.content();
    for (const secret of secrets) expect(html).not.toContain(secret);
  });
});

test.describe("overview", () => {
  test("selects a world and renders items, freshness, sources and metadata", async ({
    page,
  }) => {
    await signIn(page);
    await expect(
      page.getByText("Select a world to load the overview."),
    ).toBeVisible();
    const request = page.waitForRequest(
      (r) => new URL(r.url()).pathname === "/v1/overview",
    );
    await loadOverview(page);
    expect(new URL((await request).url()).searchParams.get("world_id")).toBe(
      WORLD,
    );

    const list = page.getByRole("list", { name: "Needs attention" });
    await expect(list.getByRole("listitem")).toHaveCount(2);
    await expect(list).toContainText(
      "Spindle vibration trend inferred above baseline",
    );
    await expect(list).toContainText("INFERRED");
    await expect(list).toContainText("digital-twin-service @ twin-r118");

    const meta = page.getByRole("region", { name: "Overview metadata" });
    await expect(meta).toContainText(WORLD);
    await expect(meta).toContainText("2026-10-23T09:00:00Z");
    await expect(meta).toContainText("DEGRADED");
    await expect(meta).toContainText(
      "Some data may be out of date (DEGRADED).",
    );
    const sources = meta.getByRole("table", { name: "Sources" });
    await expect(
      sources.getByRole("row", { name: /digital-twin-service/ }),
    ).toContainText("twin-r118");
    await expect(
      sources.getByRole("row", { name: /manufacturing-core/ }),
    ).toContainText("core-r77");
  });

  test("says a source is unavailable on 503 instead of showing nothing", async ({
    page,
    request,
  }) => {
    await signIn(page);
    await control(request, "mode/twin_down");
    await loadOverview(page);
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("The overview is unavailable");
    await expect(alert).toContainText("digital-twin-service");
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toHaveCount(0);
    await expect(page.getByText(/Nothing needs attention/)).toHaveCount(0);

    await control(request, "mode/ok");
    await alert.getByRole("button", { name: "Retry" }).click();
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toBeVisible();
  });

  test("shows stale freshness when a source reports STALE", async ({
    page,
    request,
  }) => {
    await signIn(page);
    await control(request, "mode/twin_stale");
    await loadOverview(page);
    await expect(
      page.getByRole("region", { name: "Overview metadata" }),
    ).toContainText("Some data may be out of date (STALE).");
  });

  test("returns to the signed-out experience when the BFF answers 401", async ({
    page,
    request,
  }) => {
    await signIn(page);
    await loadOverview(page);
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toBeVisible();
    await control(request, "expire-sessions");
    await loadOverview(page, "W-E2E-2");
    await expect(
      page.getByRole("banner").getByRole("link", { name: "Sign in" }),
    ).toBeVisible();
    await expect(page.getByText("Sign-in required.")).toBeVisible();
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toHaveCount(0);
  });
});

test.describe("sign out", () => {
  test("posts the session's CSRF value, ends the session and signs out the UI", async ({
    page,
  }) => {
    await signIn(page);
    const logout = page.waitForRequest(
      (r) => new URL(r.url()).pathname === "/v1/session/logout",
    );
    await page.getByRole("button", { name: "Sign out" }).click();
    const sent = await logout;
    expect(sent.method()).toBe("POST");
    expect((await sent.allHeaders())["x-csrf-token"]).toBeTruthy();
    expect((await sent.response())?.status()).toBe(204);
    await expect(
      page.getByRole("banner").getByRole("link", { name: "Sign in" }),
    ).toBeVisible();
    expect((await page.request.get("/v1/session")).status()).toBe(401);
  });

  test("a logout without the CSRF value is refused and changes nothing", async ({
    page,
  }) => {
    await signIn(page);
    const refused = await page.request.post("/v1/session/logout");
    expect(refused.status()).toBe(403);
    expect((await refused.json()) as { category: string }).toMatchObject({
      category: "FORBIDDEN",
    });
    expect((await page.request.get("/v1/session")).status()).toBe(200);
  });
});

test.describe("navigation", () => {
  test("redirects the root to the overview", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/overview$/);
    await expect(
      page.getByRole("navigation", { name: "Primary" }),
    ).toBeVisible();
  });

  test("shows not-found and links back to the overview", async ({ page }) => {
    await page.goto("/nowhere");
    await expect(
      page.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Go to the overview" }).click();
    await expect(page).toHaveURL(/\/overview$/);
  });
});

test.describe("browser boundaries", () => {
  test("talks to the BFF origin only, with no socket and no token in any reply", async ({
    page,
    request,
  }) => {
    const traffic = recordTraffic(page);
    await signIn(page);
    await loadOverview(page);
    await expect(
      page.getByRole("list", { name: "Needs attention" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();

    const origin = new URL(page.url()).origin;
    expect(traffic.urls.length).toBeGreaterThan(5);
    for (const url of traffic.urls) {
      const parsed = new URL(url);
      expect(parsed.origin, url).toBe(origin);
      expect(parsed.pathname, url).toMatch(
        /^\/($|overview|assets\/|v1\/|__fake-idp\/)/,
      );
    }
    expect(traffic.websockets).toBe(0);
    const secrets = (await (
      await request.get("/__control/provider-secrets")
    ).json()) as string[];
    const everything = traffic.bodies.join("\n");
    for (const secret of secrets) expect(everything).not.toContain(secret);
    expect(everything).not.toMatch(/access_token|refresh_token|id_token/);
  });

  test("every response carries a correlation id and the health surface answers", async ({
    request,
  }) => {
    const health = await request.get("/healthz");
    expect(health.status()).toBe(200);
    expect(await health.json()).toMatchObject({
      service: "operations-bff",
      status: "ok",
    });
    expect(health.headers()["x-correlation-id"]).toMatch(/^[0-9a-f]{32}$/);
    const denied = await request.get("/v1/session");
    expect(
      ((await denied.json()) as { correlation_id: string }).correlation_id,
    ).toBe(denied.headers()["x-correlation-id"]);
  });
});
