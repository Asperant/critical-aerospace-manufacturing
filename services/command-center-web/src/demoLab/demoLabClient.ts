export interface VisionDefect {
  defect_id: string;
  anomaly_score: number;
  area_fraction: number;
  localization: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  open_set_decision: string;
}

export interface VisionResponse {
  contract_version: string;
  observation: {
    outcome: string;
    review_required: boolean;
    data_quality: { status: string; flags: string[] };
    defects: VisionDefect[];
    image_anomaly_score: number | null;
    confidence_calibration: string;
    pipeline_identity: {
      preprocessing_version: string;
      threshold_policy_version: string;
      output_schema_version: string;
    };
    inference: { latency_ms: number };
  };
}

export interface SimulationResponse {
  contract_version: string;
  run: {
    provenance: string;
    scenario: Record<string, unknown>;
    result: {
      termination: string;
      processed_events: number;
      simulation_time: number;
      queue_depth: number;
      event_sequence_digest: string;
      final_state_digest: string;
    };
    state: {
      initial: SimulationState;
      final: SimulationState;
    };
    records: Array<{
      sequence: number;
      time: number;
      kind: string;
      event_id: string;
      outcome: unknown;
    }>;
    operational_events: Array<{
      kind: string;
      time: number;
      attributes: unknown;
    }>;
    timeline: Array<{
      sequence: number;
      time: number;
      kind: string;
      lane: string;
      lot_id: string | null;
      machine_id: string | null;
      route_step: string | null;
      attributes: Record<string, unknown>;
    }>;
    gantt: Array<{
      lot_id: string;
      machine_id: string;
      route_step: string;
      start_time: number;
      end_time: number | null;
      status: string;
      failure_events: Array<{
        sequence: number;
        time: number;
        machine_id: string;
      }>;
    }>;
  };
}

export interface SimulationState {
  world_id: string;
  state_revision: string;
  simulation_time: number;
  lots: Array<{
    lot_id: string;
    revision: string;
    lifecycle: string;
    execution_state: string;
    held: boolean;
    current_visit: string | null;
    rework_count: number;
    execution_count: number;
  }>;
  machines: Array<{
    machine_id: string;
    state: string;
    health: string;
    usage: number;
    lot_id: string | null;
  }>;
  provenance: string;
}

export interface SchedulingResponse {
  contract_version: string;
  provenance: string;
  instance: SchedulingInstance;
  results: Array<{
    baseline_id: string;
    name: string;
    version: string;
    status: string;
    selected_job_id: string | null;
    rule_description: string;
    selection_reason: string;
    selected_job: SchedulingJob | null;
    ranking: Array<{
      rank: number;
      job_id: string;
      key: unknown;
      priority_value: unknown;
      priority_display: string;
    }>;
  }>;
}

export interface SchedulingJob {
  job_id: string;
  queue_entry_tick: number;
  due_tick: number;
  operation_ticks: number;
  remaining_route_ticks: number;
  tick_unit: string;
  state: string;
  dispatchable: boolean;
}

export interface SchedulingInstance {
  instance_id: string;
  seed: number;
  generator_version: string;
  config_sha256: string;
  decision_tick: number;
  jobs: SchedulingJob[];
}

export interface QualityResponse {
  contract_version: string;
  world_id: string;
  lot_id: string;
  correlation_id: string;
  simulator: {
    event_type: string;
    event_ref: string;
    seed: number;
    processed_events: number;
    event_sequence_digest: string;
    final_state_digest: string;
  };
  core: {
    before: { held: boolean; revision: string };
    hold: {
      status: string;
      command_id: string;
      event_id: string;
      outcome_id: string;
    };
    after: { held: boolean; revision: string };
    dispatch: { status: string; error_code: string | null; command_id: string };
  };
  transport: {
    outbox: {
      outbox_id: string;
      event_id: string;
      publication_status: string;
      causation_id: string;
    };
    nats: {
      stream: string;
      consumer: string;
      num_ack_pending: number;
      num_redelivered: number;
    };
  };
  twin: {
    twin_projection: {
      source_event_id: string;
      state: Record<string, unknown>;
    };
    twin_revision: { source_event_id: string; status: string } | null;
  };
}

export interface TraceResponse {
  contract_version: string;
  core_state: {
    held: boolean;
    revision: string;
    lifecycle_state: string;
    execution_state: string;
  } | null;
  core_showcase: {
    timeline: Array<{
      kind: string;
      label: string;
      status: string;
      source: string;
      identity?: string;
    }>;
  };
  twin: {
    latest_applied_event: { event_id: string; applied_at: string } | null;
    revision: { source_event_id: string; status: string } | null;
  };
  nats: {
    stream?: string;
    consumer?: string;
    num_ack_pending?: number;
    num_redelivered?: number;
    status?: string;
  };
  identities: Record<string, string | null>;
}

export type DemoLabResult<T> =
  | { status: "ok"; value: T }
  | { status: "unauthenticated" }
  | { status: "error"; message: string };

async function requestJson<T>(
  url: string,
  init: RequestInit,
  csrfToken: string | null,
  fetchImpl: typeof fetch = fetch,
): Promise<DemoLabResult<T>> {
  try {
    const response = await fetchImpl(url, {
      ...init,
      credentials: "include",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
        ...init.headers,
      },
    });
    if (response.status === 401) return { status: "unauthenticated" };
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      return {
        status: "error",
        message: body?.detail ?? `Request failed (${response.status})`,
      };
    }
    return { status: "ok", value: (await response.json()) as T };
  } catch {
    return { status: "error", message: "Demo Lab backend is unavailable" };
  }
}

export function runVision(
  file: File,
  params: {
    worldId: string;
    lotId: string;
    zThreshold: number;
    minArea: number;
  },
  csrfToken: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({
    world_id: params.worldId,
    lot_id: params.lotId,
    z_threshold: String(params.zThreshold),
    min_area_px: String(params.minArea),
  });
  return requestJson<VisionResponse>(
    `/v1/demo-lab/vision/inspect?${query}`,
    {
      method: "POST",
      body: file,
      signal,
      headers: {
        "Content-Type":
          file.type ||
          (/[.]jpe?g$/i.test(file.name) ? "image/jpeg" : "image/png"),
      },
    },
    csrfToken,
  );
}

export function runSimulation(
  body: Record<string, unknown>,
  csrfToken: string,
  signal: AbortSignal,
) {
  return requestJson<SimulationResponse>(
    "/v1/demo-lab/simulation/runs",
    {
      method: "POST",
      body: JSON.stringify(body),
      signal,
      headers: { "Content-Type": "application/json" },
    },
    csrfToken,
  );
}

export function compareScheduling(
  body: Record<string, unknown>,
  csrfToken: string,
  signal: AbortSignal,
) {
  return requestJson<SchedulingResponse>(
    "/v1/demo-lab/scheduling/compare",
    {
      method: "POST",
      body: JSON.stringify(body),
      signal,
      headers: { "Content-Type": "application/json" },
    },
    csrfToken,
  );
}

export function runQualityExcursion(
  worldId: string,
  csrfToken: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({ world_id: worldId });
  return requestJson<QualityResponse>(
    `/v1/demo-lab/quality-excursion?${query}`,
    {
      method: "POST",
      signal,
    },
    csrfToken,
  );
}

export function fetchTrace(
  worldId: string,
  lotId: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({ world_id: worldId, lot_id: lotId });
  return requestJson<TraceResponse>(
    `/v1/demo-lab/event-trace?${query}`,
    { signal },
    null,
  );
}
