import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const WORLD = "W-E2E";

/** Puts the harness's scripted boundaries into a known state. */
export async function control(
  request: APIRequestContext,
  path: string,
): Promise<void> {
  const response = await request.post(`/__control/${path}`);
  expect(response.ok(), `control ${path}`).toBe(true);
}

export interface Traffic {
  urls: string[];
  redirects: string[];
  bodies: string[];
  websockets: number;
}

/** Records everything the page does on the network, to assert on boundaries. */
export function recordTraffic(page: Page): Traffic {
  const traffic: Traffic = {
    urls: [],
    redirects: [],
    bodies: [],
    websockets: 0,
  };
  page.on("request", (request) => traffic.urls.push(request.url()));
  page.on("websocket", () => (traffic.websockets += 1));
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (response.status() >= 300 && response.status() < 400)
      traffic.redirects.push(path);
    else
      response.text().then(
        (text) => traffic.bodies.push(text),
        () => undefined,
      );
  });
  return traffic;
}

export async function signIn(page: Page): Promise<void> {
  await page.goto("/overview");
  await page.getByRole("link", { name: "Sign in" }).click();
  await expect(
    page.getByRole("banner").getByText("E2E Operator"),
  ).toBeVisible();
}

export async function loadOverview(
  page: Page,
  world: string = WORLD,
): Promise<void> {
  await page.getByLabel("World ID").fill(world);
  await page.getByRole("button", { name: "Load overview" }).click();
}
