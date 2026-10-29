import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  testMatch: "demo-runtime.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL:
      process.env["CAP_DEMO_UI_URL"] ??
      `http://localhost:${process.env["CAP_UI_PORT"] ?? "29090"}`,
    ...devices["Desktop Chrome"],
  },
});
