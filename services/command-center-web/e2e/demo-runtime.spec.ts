import { expect, test } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const world = "DEMO-WORLD";
const lot = "DEMO-LOT-001";

function record(result: Record<string, unknown>): void {
  const directory =
    process.env["CAP_DEMO_ARTIFACT_DIR"] ?? "../../evidence/demo-presentation";
  mkdirSync(directory, { recursive: true });
  writeFileSync(
    join(directory, "browser-result.json"),
    `${JSON.stringify(result, null, 2)}\n`,
    "utf8",
  );
}

test("real Keycloak login and held lot are visible in the demo UI", async ({
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
  await expect(lots).toContainText("HELD");
  await expect(lots).toContainText("ACTIVE");
  await expect(page.getByText("QUALITY_EXCURSION")).toBeVisible();
  await expect(
    page.getByText("inspection-triggered controlled recovery acceptance slice"),
  ).toBeVisible();
  await expect(page.getByText("freshness FRESH")).toBeVisible();

  const directory =
    process.env["CAP_DEMO_ARTIFACT_DIR"] ?? "../../evidence/demo-presentation";
  const screenshot = join(directory, "browser-final.png");
  await page.screenshot({ path: screenshot, fullPage: true });
  record({
    status: "PASS",
    url: page.url(),
    world_id: world,
    lot_id: lot,
    has_authenticated_actor: true,
    has_lot: true,
    has_held_state: true,
    has_active_hold: true,
    has_quality_excursion: true,
    bff_authenticated: true,
    screenshot,
  });
});
