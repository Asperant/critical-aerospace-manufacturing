# operations-bff v1 contract (DN-UI-BFFCON, slice 1)

| Registry field | Declaration |
|---|---|
| Contract ID / version | `bff.operations-bff.v1` / v1 |
| Type / semantics | QUERY and COMMAND over HTTP described by OpenAPI 3.1; STREAMING messages as JSON Schema only |
| Semantic owner / producer | Asrın Dündar / operations-bff (no runtime yet) |
| Intended consumers | Command Center web application, contract tests, UI fixtures |
| OpenAPI | `operations-bff.openapi.yaml` |
| Schemas | `common`, `overview-query`, `command`, `stream-message` (`*.schema.json`) |
| Fixture | `overview-query.normal.json` (SYNTHETIC TEST) |
| Authority | Presentation composition only; no MaterialHold, scheduling, approval or lifecycle authority |
| Status / dependency | Initial v1 draft; not a merged CONTRACT_READY declaration |
| Security | No credentials, Oracle labels or private schemas; authentication scheme deferred |
| Deprecation | None; initial version |

## Surface

| Class | Operation | Notes |
|---|---|---|
| QUERY | `GET /v1/overview` (`getManufacturingOverview`) | Manufacturing Overview "Needs Attention"; cursor pagination, `world_id` required, optional `as_of` |
| COMMAND | `POST /v1/commands` (`submitCommand`) | Intent only; receipt is `ACCEPTED`, `REJECTED`, `CONFLICT` or `STALE`, never completion |
| STREAMING | `StreamMessage` (`x-bff-streaming`) | `DELTA` and `RESYNC_REQUIRED` after the snapshot query; no path |

Every Query response carries `meta` with `revision`, `as_of`, `generated_at`,
`freshness`, `world` and per-source `sources`. `meta.freshness` is the
least-fresh source and `meta.as_of` the oldest source `as_of` (JSON Schema
cannot express this; `check_composition` in the tests does). Each attention
item keeps its own epistemic class and source freshness. There is no overall
status field. `meta.revision` is an opaque equality-only token of the composed
view, not a domain revision; the stream chains `from_revision` to it.

## Boundaries

- Browser to BFF only. No path, parameter or property names a broker, database,
  or private service API, and the OpenAPI document declares no servers.
- The stream transport (WebSocket or SSE) is an open architecture decision and
  is not pinned. The browser never reaches the event backbone.
- Actor identity, role and permissions are never request fields; the BFF takes
  them from the authenticated session and forwards them unchanged.
- Command `command_type` and `parameters` are backend-owned and forwarded
  unmodified; the BFF interprets none of them.
- Out of this slice: runtime, authentication scheme, routes of the web app,
  broker consumers, database access, further views, the artifact access API.
