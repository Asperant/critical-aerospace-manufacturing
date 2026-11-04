import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

async function login(page: Page) {
  await page.goto("/demo-lab");
  await page.getByRole("link", { name: "Sign in" }).click();
  const credentials = readFileSync(
    join(process.env["CAP_PLATFORM_STATE_DIR"] ?? "/state", "credentials.env"),
    "utf8",
  );
  const password = credentials
    .split("\n")
    .find((line) => line.startsWith("CAP_DEMO_USER_PASSWORD="))
    ?.slice("CAP_DEMO_USER_PASSWORD=".length);
  if (!password) throw new Error("CAP_DEMO_USER_PASSWORD is missing");
  await page.locator("#username").fill("demo.operator");
  await page.locator("#password").fill(password);
  await page.locator("#kc-login").click();
  await expect(page.getByText("Demo Operator")).toBeVisible();
  await page.goto("/overview?world_id=DEMO-WORLD");
  await expect(page.getByRole("heading", { name: "Manufacturing Overview" })).toBeVisible();
  await page.goto("/demo-lab");
}

test("Demo Lab runs real available experiments through the BFF", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Demo Lab" })).toBeVisible();

  await page.getByRole("button", { name: "Simülasyonu başlat" }).click({ force: true });
  const simulation = page.locator(".demo-panel").nth(1);
  await expect(simulation.getByText("İşlenen olay", { exact: true })).toBeVisible();
  await expect(simulation.getByText("Son durum", { exact: true })).toBeVisible();
  await expect(simulation.getByText("Gerçek olaylardan makine / lot Gantt", { exact: true })).toBeVisible();
  await expect(simulation.locator(".simulation-gantt-bar").first()).toBeVisible();
  await expect(simulation.getByText("Lot ve makine ilerleyişi", { exact: true })).toBeVisible();
  const firstTimeline = await simulation.locator(".simulation-timeline").innerText();
  await simulation.locator(".demo-controls input").nth(2).fill("5");
  await expect(simulation.locator(".demo-controls input").nth(2)).toHaveValue("5");
  const secondRun = page.waitForResponse((response) => response.url().includes("/v1/demo-lab/simulation/runs") && response.request().method() === "POST");
  await simulation.getByRole("button", { name: "Simülasyonu başlat" }).click({ force: true });
  await secondRun;
  await expect(simulation.getByText("İşlenen olay", { exact: true })).toBeVisible();
  const secondTimeline = await simulation.locator(".simulation-timeline").innerText();
  expect(secondTimeline).not.toBe(firstTimeline);
  await simulation.locator(".demo-controls input").nth(4).fill("5");
  const failureRun = page.waitForResponse((response) => response.url().includes("/v1/demo-lab/simulation/runs") && response.request().method() === "POST");
  await simulation.getByRole("button", { name: "Simülasyonu başlat" }).click({ force: true });
  await failureRun;
  await expect(simulation.locator(".simulation-gantt")).toBeVisible();
  await expect(page.getByText("GERÇEK KERNEL", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Karşılaştır" }).click({ force: true });
  await expect(page.getByText("Karar anındaki gerçek adaylar", { exact: true })).toBeVisible();
  for (const name of ["FIFO", "EDD", "CR", "SPT", "SRPT"]) {
    await expect(page.locator(".schedule-algorithm-heading strong").filter({ hasText: name })).toBeVisible();
  }

  const traceResponse = await page.request.get(
    "/v1/demo-lab/event-trace?world_id=DEMO-WORLD&lot_id=DEMO-LOT-001",
  );
  expect(traceResponse.status()).toBe(200);

  const cleanImagePath = "/work/evidence/demo-presentation/browser-initial.png";
  await page.getByLabel("Temiz görüntü PNG").setInputFiles(cleanImagePath);
  await page.locator(".vision-card").nth(0).getByRole("button", { name: /çalıştır/ }).click({ force: true });
  await expect(page.locator(".vision-card").nth(0).locator(".vision-result")).toContainText(/Anomali adayı|Değerlendirilemedi/);
  const imagePath = "/tmp/cap-demo-lab-evidence/browser-final.png";
  await page.getByLabel("Kusurlu görüntü PNG").setInputFiles(imagePath);
  await page.locator(".vision-card").nth(1).getByRole("button", { name: /çalıştır/ }).click({ force: true });
  await expect(page.getByText("Anomali adayı bulundu", { exact: true })).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "Kalite hatasını tetikle" }).click({ force: true });
  await expect(page.getByText("Senaryo lotu", { exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("REJECTED", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("ACTIVE", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Gerçek olay kanıt zinciri", { exact: true })).toBeVisible();
  await expect(page.getByText("PostgreSQL core.outbox", { exact: false })).toBeVisible();

  const quality = page.locator(".demo-panel").nth(3);
  const firstLot = await quality.locator(".demo-result-grid strong").first().innerText();
  const repeatRun = page.waitForResponse((response) => response.url().includes("/v1/demo-lab/quality-excursion") && response.request().method() === "POST");
  await quality.getByRole("button", { name: "Kalite hatasını tetikle" }).click({ force: true });
  await repeatRun;
  await expect(quality.getByText("Senaryo lotu", { exact: true })).toBeVisible({ timeout: 30_000 });
  const secondLot = await quality.locator(".demo-result-grid strong").first().innerText();
  expect(secondLot).not.toBe(firstLot);
  await expect(quality.getByText("ACTIVE_HOLD", { exact: true })).toBeVisible();

  await page.goto("/overview?world_id=DEMO-WORLD");
  await expect(page.getByRole("heading", { name: "Manufacturing Overview" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dikkat gerektiren kayıtlar" })).toBeVisible();
  await expect(page.getByLabel("Dikkat kayıtları filtresi")).toBeVisible();
  await expect(page.locator('a[href^="/demo-lab?lot_id=DEMO-LAB-"]').first()).toBeVisible({ timeout: 30_000 });
  await page.locator(".attention-toolbar select").selectOption("demo");
  await expect(page.getByText(/Demo kayıtları/).first()).toBeVisible();
  await page.goto(`/demo-lab?lot_id=${encodeURIComponent(secondLot)}`);
  await expect(page.getByText("Gerçek olay kanıt zinciri", { exact: true })).toBeVisible();
  await expect(page.getByText("ACTIVE", { exact: true }).first()).toBeVisible();
});
