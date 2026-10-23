import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(import.meta.dirname, "..");
const forbiddenPackages =
  /^(nats|kafkajs|amqplib|mqtt|pg|postgres|mysql2?|redis|ioredis|mongodb|mongoose|sqlite3|better-sqlite3|prisma|@prisma\/.*|typeorm|sequelize|knex|drizzle-orm|keycloak-js|oidc-client(-ts)?|jose|jsonwebtoken|@azure\/msal.*|firebase|socket\.io-client|ws|@aws-sdk\/.*)$/;
// Nothing in the browser may open a socket, keep credentials or read cookies.
const forbiddenSource =
  /XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|access_token|refresh_token|id_token|Authorization|Bearer/;
const networkModule = "src/session/sessionClient.ts";

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
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)
      ? [path]
      : [];
  });
}

const applicationCode = sourceFiles(join(root, "src")).map((file) => ({
  name: relative(root, file),
  text: readFileSync(file, "utf8"),
}));

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

  it("reaches the network only from the session client, and only the BFF", () => {
    const users = applicationCode.filter((file) => /\bfetch\b/.test(file.text));
    expect(users.map((file) => file.name)).toEqual([networkModule]);
    const client =
      applicationCode.find((file) => file.name === networkModule)?.text ?? "";
    const urls = [
      ...client.matchAll(/fetchImpl\(\s*([A-Za-z_]+|"[^"]*")/g),
    ].map((m) => m[1]);
    expect(urls).toEqual(["SESSION_URL"]);
    expect(client).toMatch(/const SESSION_URL = "\/v1\/session";/);
    expect(client).toMatch(/credentials:\s*"include"/);
    expect(
      applicationCode.filter((file) => /https?:\/\//.test(file.text)),
    ).toEqual([]);
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
  });
});
