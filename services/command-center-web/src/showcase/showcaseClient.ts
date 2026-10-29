export interface ShowcaseTimelineItem {
  id: string;
  kind: string;
  label: string;
  status: string;
  source: string;
  occurred_at?: string | null;
  command_id?: string;
  event_id?: string | null;
  outbox_id?: string | null;
  error_code?: string | null;
  event_ref?: string | null;
}

export interface ShowcaseResponse {
  contract_version: "bff.showcase.v1";
  meta: { world_id: string; lot_id: string; freshness: string; correlation_id: string };
  timeline: ShowcaseTimelineItem[];
  dispatch: { status?: string; error_code?: string; detail?: string } | null;
  identities: {
    command_id: string | null;
    event_id: string | null;
    outbox_id: string | null;
    simulator_event_ref: string | null;
    twin_source_event_id: string | null;
    twin_status: string | null;
  };
}

export type ShowcaseResult =
  | { status: "ok"; showcase: ShowcaseResponse }
  | { status: "unauthenticated" }
  | { status: "unavailable" }
  | { status: "invalid"; message: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "";
}

function isShowcase(value: unknown): value is ShowcaseResponse {
  if (!isRecord(value) || value.contract_version !== "bff.showcase.v1") return false;
  const meta = value.meta;
  const timeline = value.timeline;
  const identities = value.identities;
  return (
    isRecord(meta) && text(meta.world_id) && text(meta.lot_id) && text(meta.freshness) &&
    text(meta.correlation_id) && Array.isArray(timeline) && timeline.every((item) =>
      isRecord(item) && text(item.id) && text(item.kind) && text(item.label) &&
      text(item.status) && text(item.source),
    ) && isRecord(identities)
  );
}

export async function fetchShowcase(
  worldId: string,
  lotId: string,
  signal: AbortSignal,
): Promise<ShowcaseResult> {
  const response = await fetch(
    `/v1/showcase?world_id=${encodeURIComponent(worldId)}&lot_id=${encodeURIComponent(lotId)}`,
    { signal, credentials: "same-origin" },
  );
  if (response.status === 401) return { status: "unauthenticated" };
  if (!response.ok) return { status: "unavailable" };
  const body: unknown = await response.json();
  return isShowcase(body)
    ? { status: "ok", showcase: body }
    : { status: "invalid", message: "showcase response failed validation" };
}
