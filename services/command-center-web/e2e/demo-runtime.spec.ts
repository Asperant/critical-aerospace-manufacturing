import { expect, test } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const world = "DEMO-WORLD";
const lot = "DEMO-LOT-001";

function record(result: Record<string, unknown>): void {
  const directory =
    process.env["CAP_DEMO_ARTIFACT_DIR"] ?? "../../evidence/demo-presentation";
  mkdirSync(directory, { recursive: true });
  const filename =
    process.env["CAP_DEMO_BROWSER_STAGE"] === "initial"
      ? "browser-initial-result.json"
      : "browser-result.json";
  writeFileSync(
    join(directory, filename),
    `${JSON.stringify(result, null, 2)}\n`,
    "utf8",
  );
}

test("real Keycloak login and held lot are visible in the demo UI", async ({
  page,
}) => {
  const stage = process.env["CAP_DEMO_BROWSER_STAGE"] ?? "final";
  const stateDirectory =
    process.env["CAP_PLATFORM_STATE_DIR"] ??
    `${process.env["HOME"]}/.local/state/cap-demo`;
  const credentials = readFileSync(
    join(stateDirectory, "credentials.env"),
    "utf8",
  );
  const password = credentials
    .split("\n")
    .find((line) => line.startsWith("CAP_DEMO_USER_PASSWORD="))
    ?.slice("CAP_DEMO_USER_PASSWORD=".length);
  if (!password) throw new Error("CAP_DEMO_USER_PASSWORD is missing");

  await page.goto("/overview");
  await page.getByRole("link", { name: "Sign in" }).click();
  await page.locator("#username").fill("demo.operator");
  await page.locator("#password").fill(password);
  await page.locator("#kc-login").click();
  await expect(page.getByText("Demo Operator")).toBeVisible();
  await page.getByLabel("World ID").fill(world);
  await page.getByRole("button", { name: "Load overview" }).click();

  const session = await page.request.get("/v1/session");
  expect(session.status()).toBe(200);
  const facility = await page.request.get(
    `/v1/facility-state?world_id=${world}`,
  );
  expect(facility.status()).toBe(200);
  const facilityBody = (await facility.json()) as {
    meta?: { freshness?: string; sources?: Array<{ source?: string }> };
  };
  expect(facilityBody.meta?.freshness).toBe("FRESH");
  expect(facilityBody.meta?.sources?.[0]?.source).toBe("digital-twin-service");

  const lots = page.getByRole("table", { name: "Production lots" });
  await expect(lots).toContainText(lot);
  if (stage === "initial") {
    await expect(lots).not.toContainText("HELD");
    await expect(
      page.getByText("Nothing needs attention in the reported sources."),
    ).toBeVisible();
    const directory =
      process.env["CAP_DEMO_ARTIFACT_DIR"] ??
      "../../evidence/demo-presentation";
    const screenshot = join(directory, "browser-initial.png");
    await page.screenshot({ path: screenshot, fullPage: true });
    record({
      status: "PASS",
      stage,
      url: page.url(),
      world_id: world,
      lot_id: lot,
      has_authenticated_actor: true,
      has_lot: true,
      has_healthy_state: true,
      bff_authenticated: true,
      screenshot,
    });
    return;
  }
  await expect(lots).toContainText("HELD");
  await expect(lots).toContainText("ACTIVE");
  const quality = page.getByRole("region", { name: "Quality excursion" });
  await expect(quality).toContainText("QUALITY_EXCURSION");
  await expect(
    quality.getByText(
      "Simulator inspection anomaly — inspection-triggered controlled recovery",
    ),
  ).toBeVisible();
  await expect(page.getByText("freshness FRESH")).toBeVisible();
  const showcase = await page.request.get(
    `/v1/showcase?world_id=${world}&lot_id=${lot}`,
  );
  expect(showcase.status()).toBe(200);
  const showcaseBody = (await showcase.json()) as {
    timeline?: Array<{ kind?: string; status?: string }>;
    dispatch?: { status?: string; error_code?: string };
  };
  expect(showcaseBody.timeline?.map((item) => item.kind)).toEqual(
    expect.arrayContaining([
      "SIMULATOR_TRIGGER",
      "COMMAND_ACCEPTED",
      "EVENT_PUBLISHED",
      "TWIN_UPDATED",
      "DISPATCH_BLOCKED",
    ]),
  );
  expect(showcaseBody.dispatch?.status).toBe("REJECTED");
  expect(showcaseBody.dispatch?.error_code).toBe("ACTIVE_HOLD");
  await expect(
    page.getByRole("region", { name: "Operational timeline" }),
  ).toContainText("Dispatch blocked");

  const directory =
    process.env["CAP_DEMO_ARTIFACT_DIR"] ?? "../../evidence/demo-presentation";
  const screenshot = join(directory, "browser-final.png");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.screenshot({
    path: join(directory, "browser-anomaly.png"),
    fullPage: true,
  });
  record({
    status: "PASS",
    stage,
    url: page.url(),
    world_id: world,
    lot_id: lot,
    has_authenticated_actor: true,
    has_lot: true,
    has_held_state: true,
    has_active_hold: true,
    has_quality_excursion: true,
    has_dispatch_blocked: true,
    bff_authenticated: true,
    showcase_authenticated: true,
    has_timeline: true,
    screenshot,
  });
});

test("authenticated System View exposes the live runtime path", async ({
  page,
}) => {
  const stateDirectory =
    process.env["CAP_PLATFORM_STATE_DIR"] ??
    `${process.env["HOME"]}/.local/state/cap-demo`;
  const credentials = readFileSync(
    join(stateDirectory, "credentials.env"),
    "utf8",
  );
  const password = credentials
    .split("\n")
    .find((line) => line.startsWith("CAP_DEMO_USER_PASSWORD="))
    ?.slice("CAP_DEMO_USER_PASSWORD=".length);
  if (!password) throw new Error("CAP_DEMO_USER_PASSWORD is missing");

  await page.goto("/system");
  await page.getByRole("link", { name: "Sign in" }).click();
  await page.locator("#username").fill("demo.operator");
  await page.locator("#password").fill(password);
  await page.locator("#kc-login").click();
  await expect(page.getByText("Demo Operator")).toBeVisible();
  await page.getByLabel("World and lot").fill(`${world} ${lot}`);
  await page.getByRole("button", { name: "Load system view" }).click();

  await expect(
    page.getByRole("heading", { name: "System View" }),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "System flow" })).toContainText(
    "Simulator",
  );
  await expect(page.getByRole("region", { name: "System flow" })).toContainText(
    "NATS / JetStream",
  );
  await expect(
    page.getByRole("region", { name: "System health" }),
  ).toContainText("Core API");
  await expect(page.getByRole("region", { name: "Event trace" })).toContainText(
    "Event ID",
  );
  await expect(page.getByText("RENDERED", { exact: true })).toBeVisible();

  const showcase = await page.request.get(
    `/v1/showcase?world_id=${world}&lot_id=${lot}`,
  );
  expect(showcase.status()).toBe(200);
  const body = (await showcase.json()) as {
    architecture?: Array<{ id?: string }>;
    health?: Array<{ id?: string }>;
    counters?: Array<{ id?: string }>;
  };
  expect(body.architecture?.map((item) => item.id)).toEqual(
    expect.arrayContaining([
      "simulator",
      "core",
      "postgres",
      "outbox",
      "nats",
      "twin",
      "bff",
      "ui",
    ]),
  );
  expect(body.health?.map((item) => item.id)).toEqual(
    expect.arrayContaining([
      "core",
      "postgres",
      "nats",
      "twin",
      "keycloak",
      "bff",
    ]),
  );
  expect(body.counters?.map((item) => item.id)).toEqual(
    expect.arrayContaining(["commands", "published-events", "twin-updates"]),
  );
});
