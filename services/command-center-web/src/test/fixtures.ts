import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { SessionResponse } from "../contract/generated";

/** The operations-bff contract fixture, so tests use the real wire shape. */
export function contractSession(): SessionResponse {
  const path = join(
    import.meta.dirname,
    "../../../operations-bff/contracts/v1/session.normal.json",
  );
  return JSON.parse(readFileSync(path, "utf8")) as SessionResponse;
}
