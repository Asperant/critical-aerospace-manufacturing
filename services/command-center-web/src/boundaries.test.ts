import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(import.meta.dirname, "..");
const forbiddenPackages =
  /^(nats|kafkajs|amqplib|mqtt|pg|postgres|mysql2?|redis|ioredis|mongodb|mongoose|sqlite3|better-sqlite3|prisma|@prisma\/.*|typeorm|sequelize|knex|drizzle-orm|keycloak-js|oidc-client(-ts)?|jose|jsonwebtoken|@azure\/msal.*|firebase|socket\.io-client|ws|@aws-sdk\/.*)$/;
// The shell fetches nothing yet and must never hold credentials or reach
// anything but the BFF once it does.
const forbiddenSource =
  /\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|access_token|refresh_token|id_token|Authorization|Bearer/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)
      ? [path]
      : [];
  });
}

describe("browser boundaries", () => {
  it("declares no broker, database or identity-provider client packages", () => {
    const pkg = JSON.parse(
      readFileSync(join(root, "package.json"), "utf8"),
    ) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const names = [
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.devDependencies ?? {}),
    ];
    expect(names.filter((name) => forbiddenPackages.test(name))).toEqual([]);
  });

  it("pins every dependency exactly", () => {
    const pkg = JSON.parse(
      readFileSync(join(root, "package.json"), "utf8"),
    ) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const versions = [
      ...Object.values(pkg.dependencies ?? {}),
      ...Object.values(pkg.devDependencies ?? {}),
    ];
    expect(
      versions.filter((version) => !/^\d+\.\d+\.\d+$/.test(version)),
    ).toEqual([]);
  });

  it("has no network, storage or credential access in application code", () => {
    const offenders = sourceFiles(join(root, "src")).filter((file) =>
      forbiddenSource.test(readFileSync(file, "utf8")),
    );
    expect(offenders).toEqual([]);
  });

  it("loads nothing from outside the application", () => {
    const html = readFileSync(join(root, "index.html"), "utf8");
    expect(html).not.toMatch(/https?:\/\//);
  });
});
