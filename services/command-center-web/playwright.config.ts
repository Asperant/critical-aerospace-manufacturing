import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env["E2E_PORT"] ?? 18443);
const baseURL = `https://127.0.0.1:${port}`;
// The benchmark is an engineering measurement, not a gate: it only runs on request.
const bench = process.env["BENCH"] === "1";
const python =
  process.env["E2E_PYTHON"] ?? "uv run --project ../../ci --locked python";

export default defineConfig({
  testDir: "e2e",
  testMatch: bench
    ? /bench\.spec\.ts$/
    : /^(?!.*bench)(?!.*demo-runtime).*\.spec\.ts$/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  timeout: bench ? 120_000 : 30_000,
  use: { baseURL, ignoreHTTPSErrors: true, trace: "retain-on-failure" },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
  ],
  webServer: {
    command: `${python} ../operations-bff/e2e/harness.py --port ${port} --dist dist`,
    url: `${baseURL}/healthz`,
    ignoreHTTPSErrors: true,
    reuseExistingServer: false,
    timeout: 60_000,
    stdout: "ignore",
    stderr: "pipe",
    env: {
      ...(process.env as Record<string, string>),
      PYTHONPATH: "../operations-bff/src",
    },
  },
});
