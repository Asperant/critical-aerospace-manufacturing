import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

import { contractOpenApi } from "./test/fixtures";

const root = join(import.meta.dirname, "..");
const forbiddenPackages =
  /^(nats|kafkajs|amqplib|mqtt|pg|postgres|mysql2?|redis|ioredis|mongodb|mongoose|sqlite3|better-sqlite3|prisma|@prisma\/.*|typeorm|sequelize|knex|drizzle-orm|keycloak-js|oidc-client(-ts)?|jose|jsonwebtoken|@azure\/msal.*|firebase|socket\.io-client|ws|@aws-sdk\/.*)$/;
// Nothing in the browser may open a socket, keep credentials or read cookies.
const forbiddenSource =
  /XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|access_token|refresh_token|id_token|Authorization|Bearer/;
const networkModules = [
  "src/overview/overviewClient.ts",
  "src/session/sessionClient.ts",
];
const bffPaths = {
  SESSION_URL: "/v1/session",
  LOGOUT_URL: "/v1/session/logout",
  OVERVIEW_URL: "/v1/overview",
};

interface Manifest {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}

function manifest(): Manifest {
  return JSON.parse(
    readFileSync(join(root, "package.json"), "utf8"),
  ) as Manifest;
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory())
      return entry.name === "test" ? [] : sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)
      ? [path]
      : [];
  });
}

const applicationCode = sourceFiles(join(root, "src")).map((file) => ({
  name: relative(root, file).replaceAll("\\", "/"),
  text: readFileSync(file, "utf8"),
}));

function text(name: string): string {
  return applicationCode.find((file) => file.name === name)?.text ?? "";
}

describe("browser boundaries", () => {
  it("declares no broker, database or identity-provider client packages", () => {
    const pkg = manifest();
    const names = [
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.devDependencies ?? {}),
    ];
    expect(names.filter((name) => forbiddenPackages.test(name))).toEqual([]);
  });

  it("pins every dependency exactly", () => {
    const pkg = manifest();
    const versions = [
      ...Object.values(pkg.dependencies ?? {}),
      ...Object.values(pkg.devDependencies ?? {}),
    ];
    expect(
      versions.filter((version) => !/^\d+\.\d+\.\d+$/.test(version)),
    ).toEqual([]);
  });

  it("has no socket, storage, cookie or credential access in application code", () => {
    const offenders = applicationCode.filter((file) =>
      forbiddenSource.test(file.text),
    );
    expect(offenders.map((file) => file.name)).toEqual([]);
  });

  it("reaches the network only from the two BFF clients", () => {
    const users = applicationCode.filter((file) => /\bfetch\b/.test(file.text));
    expect(users.map((file) => file.name).sort()).toEqual(networkModules);
    expect(
      applicationCode.filter((file) => /https?:\/\//.test(file.text)),
    ).toEqual([]);
  });

  it("sends only to the BFF paths, always with the session cookie", () => {
    const constants: Record<string, string> = {};
    for (const name of networkModules) {
      for (const match of text(name).matchAll(
        /const (\w+_URL) = "([^"]*)";/g,
      )) {
        constants[match[1] ?? ""] = match[2] ?? "";
      }
      const body = text(name);
      const calls = [...body.matchAll(/fetchImpl\(\s*(\w+)/g)].map((m) => m[1]);
      const requests = (body.match(/fetchImpl\(/g) ?? []).length;
      expect(requests).toBeGreaterThan(0);
      expect(calls).toHaveLength(requests);
      expect(
        (body.match(/^\s+credentials:\s*"include",$/gm) ?? []).length,
      ).toBe(requests);
      for (const call of calls)
        expect(["SESSION_URL", "LOGOUT_URL", "url"]).toContain(call);
    }
    expect(constants).toEqual(bffPaths);
    expect(text("src/overview/overviewClient.ts")).toContain(
      "`${OVERVIEW_URL}?${params.toString()}`",
    );
  });

  it("uses the operations and paths declared in the BFF OpenAPI contract", () => {
    const openapi = contractOpenApi();
    const operations: [string, string, string][] = [
      ["/v1/session", "get", "getSession"],
      ["/v1/session/login", "get", "startLogin"],
      ["/v1/session/logout", "post", "logout"],
      ["/v1/overview", "get", "getManufacturingOverview"],
    ];
    for (const [path, method, id] of operations) {
      expect(openapi).toMatch(
        new RegExp(
          `^  ${path}:\\n    ${method}:\\n      operationId: ${id}$`,
          "m",
        ),
      );
    }
    expect(text("src/layout/RootLayout.tsx")).toContain(
      'const START_LOGIN_PATH = "/v1/session/login";',
    );
    expect(text("src/layout/RootLayout.tsx")).toMatch(
      /<a href=\{START_LOGIN_PATH\}>/,
    );
  });

  it("loads nothing from outside the application", () => {
    const html = readFileSync(join(root, "index.html"), "utf8");
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("keeps contract types generated, not hand-written", () => {
    const generated = readFileSync(
      join(root, "src/contract/generated.ts"),
      "utf8",
    );
    expect(generated).toMatch(
      /^\/\* GENERATED from services\/operations-bff\/contracts\/v1/,
    );
    for (const name of [
      "SessionResponse",
      "ErrorEnvelope",
      "ManufacturingOverviewResponse",
    ]) {
      expect(generated).toContain(`export interface ${name}`);
    }
    const handWritten = applicationCode.filter(
      (file) =>
        file.name !== "src/contract/generated.ts" &&
        /interface (SessionResponse|ErrorEnvelope|ManufacturingOverviewResponse|QueryMeta)\b/.test(
          file.text,
        ),
    );
    expect(handWritten).toEqual([]);
  });
});
