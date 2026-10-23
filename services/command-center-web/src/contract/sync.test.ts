import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { expect, it } from "vitest";

it("generated contract types are in sync with the BFF schemas", () => {
  const output = execFileSync(
    process.execPath,
    ["scripts/generate-contract-types.mjs", "--check"],
    { cwd: join(import.meta.dirname, "../.."), encoding: "utf8" },
  );
  expect(output).toContain("contract types are up to date");
});
