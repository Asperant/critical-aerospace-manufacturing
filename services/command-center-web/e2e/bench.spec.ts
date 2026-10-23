// BENCH-PERF-UI engineering measurement for NFR-PERF-014. Runs only with BENCH=1.
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { WORLD } from "./helpers";

const WARMUP = Number(process.env["BENCH_WARMUP"] ?? 10);
const SAMPLES = Number(process.env["BENCH_SAMPLES"] ?? 100);
const BUDGET_MS = 3000;

declare global {
  interface Window {
    __actionableAt?: number;
  }
}

function nearestRank(sorted: number[], p: number): number {
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
  );
  return sorted[index] ?? Number.NaN;
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}

test("first route warm start to an actionable overview", async ({
  browser,
  browserName,
  baseURL,
}) => {
  const durations: number[] = [];
  for (let i = 0; i < WARMUP + SAMPLES; i += 1) {
    // A fresh context per sample: empty browser cache, warm server.
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      baseURL: baseURL ?? "",
    });
    const signedIn = await context.request.get("/v1/session/login"); // BFF + scripted IdP redirects
    expect(signedIn.ok()).toBe(true);
    const page = await context.newPage();
    await page.addInitScript(() => {
      const mark = () => {
        if (document.querySelector('[aria-label="Needs attention"]')) {
          window.__actionableAt = performance.now();
          observer.disconnect();
        }
      };
      const observer = new MutationObserver(mark);
      document.addEventListener("DOMContentLoaded", () => {
        observer.observe(document.documentElement, {
          childList: true,
          subtree: true,
        });
        mark();
      });
    });
    await page.goto(`/overview?world_id=${WORLD}`);
    await page.waitForFunction(() => window.__actionableAt !== undefined);
    const at = await page.evaluate(() => window.__actionableAt ?? Number.NaN);
    if (i >= WARMUP) durations.push(at);
    await context.close();
  }

  const sorted = [...durations].sort((a, b) => a - b);
  const result = {
    requirement:
      "NFR-PERF-014: primary route actionable after warm start, p95 <= 3 s",
    kind: "engineering measurement on a development host; not canonical final acceptance",
    boundary:
      "navigation start of GET /overview?world_id=... in a fresh browser context (empty cache, signed-in " +
      "session cookie, warm BFF process) until the populated 'Needs attention' list first exists in the DOM",
    browser: `${browserName} ${browser.version()}`,
    transport:
      "loopback HTTPS to one local process serving the built frontend and the BFF",
    backends:
      "scripted identity provider and fixture-backed Core and Twin readers",
    warmupDiscarded: WARMUP,
    samples: durations.length,
    unit: "ms",
    min: round(sorted[0] ?? Number.NaN),
    p50: round(nearestRank(sorted, 50)),
    p95: round(nearestRank(sorted, 95)),
    p99: round(nearestRank(sorted, 99)),
    max: round(sorted[sorted.length - 1] ?? Number.NaN),
    budgetMs: BUDGET_MS,
    verdict: nearestRank(sorted, 95) <= BUDGET_MS ? "PASS" : "FAIL",
    host: {
      cpu: os.cpus()[0]?.model,
      cores: os.cpus().length,
      memoryGiB: Math.round(os.totalmem() / 2 ** 30),
      node: process.version,
    },
    commit: execFileSync("git", ["rev-parse", "HEAD"], {
      encoding: "utf8",
    }).trim(),
    measuredAt: new Date().toISOString(),
  };
  const out = process.env["BENCH_OUT_DIR"] ?? "test-results";
  mkdirSync(out, { recursive: true });
  writeFileSync(
    path.join(out, `bench-ui-${browserName}.json`),
    `${JSON.stringify(result, null, 2)}\n`,
  );
  console.log(JSON.stringify(result));
  expect(durations.every(Number.isFinite)).toBe(true);
  expect(result.p95).toBeLessThanOrEqual(BUDGET_MS);
});
