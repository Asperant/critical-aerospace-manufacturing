// Generates src/contract/generated.ts from the operations-bff JSON Schemas so the
// browser never hand-duplicates contract types. `--check` fails on drift.
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { compile } from "json-schema-to-typescript";

const here = import.meta.dirname;
const contracts = path.resolve(here, "../../operations-bff/contracts/v1");
const target = path.resolve(here, "../src/contract/generated.ts");
const base = "https://contracts.cap.invalid/operations-bff/v1/";

const root = {
  $id: `${base}frontend-types.schema.json`,
  title: "ContractRoot",
  type: "object",
  additionalProperties: false,
  properties: {},
  $defs: {
    SessionResponse: { $ref: "session.schema.json" },
    ErrorEnvelope: { $ref: "common.schema.json#/$defs/ErrorEnvelope" },
    ManufacturingOverviewResponse: { $ref: "overview-query.schema.json" },
    FacilityStateResponse: { $ref: "facility-state.schema.json" },
  },
};

// The contract $ids point at a reserved .invalid host; resolve them from disk.
const local = {
  order: 1,
  canRead: (file) => file.url.startsWith(base),
  read: (file) =>
    readFileSync(
      path.join(contracts, path.basename(new URL(file.url).pathname)),
      "utf8",
    ),
};

const output = await compile(root, "ContractRoot", {
  cwd: contracts,
  unreachableDefinitions: true,
  additionalProperties: false,
  declareExternallyReferenced: true,
  bannerComment:
    "/* GENERATED from services/operations-bff/contracts/v1 by scripts/generate-contract-types.mjs.\n * Do not edit; run `npm run contract:generate`. */",
  $refOptions: { resolve: { http: false, local } },
});

if (process.argv.includes("--check")) {
  if (readFileSync(target, "utf8") !== output) {
    console.error(
      "src/contract/generated.ts is out of date; run `npm run contract:generate`.",
    );
    process.exit(1);
  }
  console.log("contract types are up to date");
} else {
  writeFileSync(target, output);
  console.log(`wrote ${path.relative(process.cwd(), target)}`);
}
