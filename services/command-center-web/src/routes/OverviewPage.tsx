import { useSearchParams } from "react-router-dom";
import type { ReactNode } from "react";

import type {
  AttentionItem,
  FacilityStateResponse,
  LotState,
  ManufacturingOverviewResponse,
  SourceStatus,
} from "../contract/generated";
import {
  useFacilityState,
  type FacilityStateView,
} from "../facilityState/useFacilityState";
import { useOverview, type OverviewState } from "../overview/useOverview";
import { useSession } from "../session/SessionProvider";
import { useShowcase, type ShowcaseState } from "../showcase/useShowcase";

const DEFAULT_WORLD_ID = "DEMO-WORLD";

function shorten(value: string, visible = 16): string {
  return value.length > visible ? `${value.slice(0, visible)}…` : value;
}

function TechnicalValue({ value }: { value: string }) {
  const abbreviated = value.length > 16;
  return (
    <span className="technical-value" title={value}>
      <span aria-hidden={abbreviated}>
        {abbreviated ? shorten(value) : value}
      </span>
      {abbreviated ? <span className="sr-only">{value}</span> : null}
    </span>
  );
}

function StatusBadge({
  value,
  tone,
}: {
  value: string;
  tone?: "good" | "warning" | "neutral" | "critical";
}) {
  const normalized = value.toLowerCase();
  const inferred =
    tone ??
    (normalized === "fresh" || normalized === "active"
      ? "good"
      : normalized === "held" || normalized === "degraded"
        ? "warning"
        : normalized === "stale"
          ? "critical"
          : "neutral");
  return <span className={`status-badge status-${inferred}`}>{value}</span>;
}

function SectionHeading({
  eyebrow,
  title,
  id,
  action,
}: {
  eyebrow?: string;
  title: string;
  id?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2 id={id}>{title}</h2>
      </div>
      {action}
    </div>
  );
}

function SessionSummary() {
  const state = useSession();
  switch (state.status) {
    case "loading":
      return (
        <div className="inline-state" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading session…
        </div>
      );
    case "unauthenticated":
      return <p className="empty-copy">Sign-in required.</p>;
    case "error":
      return <p role="alert">The session could not be loaded.</p>;
    case "authenticated": {
      const { actor, environment_id, expires_at } = state.session;
      return (
        <details className="operator-details">
          <summary>Operator context</summary>
          <dl className="compact-definition-list">
            <dt>Actor</dt>
            <dd>
              <TechnicalValue value={actor.actor_id} />
            </dd>
            <dt>Roles</dt>
            <dd>{actor.roles.length > 0 ? actor.roles.join(", ") : "none"}</dd>
            <dt>Environment</dt>
            <dd>{environment_id}</dd>
            <dt>Session expires</dt>
            <dd>
              <TechnicalValue value={expires_at} />
            </dd>
          </dl>
          <p className="muted-copy">
            Roles are shown for information; the server decides what is allowed.
          </p>
        </details>
      );
    }
  }
}

function WorldForm({
  worldId,
  onSelect,
}: {
  worldId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <form
      className="world-control"
      key={worldId ?? "no-world"}
      onSubmit={(event) => {
        event.preventDefault();
        const value = new FormData(event.currentTarget).get("world_id");
        if (typeof value === "string" && value.trim() !== "")
          onSelect(value.trim());
      }}
    >
      <div>
        <label htmlFor="world-id">World ID</label>
        <span className="control-hint">
          Load a Twin-backed operational view
        </span>
      </div>
      <div className="world-input-row">
        <input
          id="world-id"
          name="world_id"
          defaultValue={worldId ?? DEFAULT_WORLD_ID}
          placeholder="DEMO-WORLD"
          required
        />
        <button className="button button-primary" type="submit">
          Load overview <span aria-hidden="true">→</span>
        </button>
      </div>
    </form>
  );
}

function Freshness({ value }: { value: string }) {
  return <StatusBadge value={value} />;
}

function TwinSource({ sources }: { sources: SourceStatus[] }) {
  const twin =
    sources.find((source) => source.source.includes("twin")) ?? sources[0];
  if (!twin) return null;
  return (
    <div className="twin-source">
      <span className="source-icon" aria-hidden="true">
        ◈
      </span>
      <div>
        <span className="field-label">Twin source</span>
        <strong>{twin.source}</strong>
      </div>
      <Freshness value={twin.freshness} />
    </div>
  );
}

function MetaSummary({
  overview,
  facility,
}: {
  overview: ManufacturingOverviewResponse | null;
  facility: FacilityStateResponse | null;
}) {
  const meta = overview?.meta ?? facility?.meta;
  if (!meta) return null;
  return (
    <section className="card twin-card" aria-label="Overview metadata">
      <SectionHeading eyebrow="Data confidence" title="Twin state freshness" />
      <TwinSource sources={meta.sources} />
      <div className="twin-grid">
        <div>
          <span className="field-label">World</span>
          <strong>{meta.world.world_id}</strong>
        </div>
        <div>
          <span className="field-label">Freshness</span>
          <strong>
            <Freshness value={meta.freshness} />
          </strong>
        </div>
        <div className="twin-confidence-copy">
          <span className="field-label">Operator guidance</span>
          <strong>Live operational state</strong>
          <span className="detail-value">
            Technical lineage is available below.
          </span>
        </div>
      </div>
      {meta.freshness !== "FRESH" ? (
        <p className="notice notice-warning" role="note">
          Some data may be out of date ({meta.freshness}). Twin data is{" "}
          {meta.freshness.toLowerCase()}. Review before acting.
        </p>
      ) : null}
      <details className="technical-details">
        <summary>Technical provenance</summary>
        <dl className="compact-definition-list">
          <dt>World ID</dt>
          <dd>{meta.world.world_id}</dd>
          {meta.world.simulation_run_id ? (
            <>
              <dt>Simulation run</dt>
              <dd>{meta.world.simulation_run_id}</dd>
            </>
          ) : null}
          {meta.world.branch_id ? (
            <>
              <dt>Branch</dt>
              <dd>{meta.world.branch_id}</dd>
            </>
          ) : null}
          <dt>Revision</dt>
          <dd>{meta.revision}</dd>
          <dt>As of</dt>
          <dd>{meta.as_of}</dd>
          <dt>Generated at</dt>
          <dd>{meta.generated_at}</dd>
          <dt>Freshness</dt>
          <dd>{meta.freshness}</dd>
        </dl>
        <table aria-label="Sources">
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col">Revision</th>
              <th scope="col">As of</th>
              <th scope="col">Freshness</th>
            </tr>
          </thead>
          <tbody>
            {meta.sources.map((source) => (
              <tr key={source.source}>
                <th scope="row">{source.source}</th>
                <td>{source.revision}</td>
                <td>{source.as_of}</td>
                <td>{source.freshness}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

function SummaryCards({
  worldId,
  lot,
  freshness,
}: {
  worldId: string;
  lot: LotState | null;
  freshness: string;
}) {
  return (
    <div className="summary-grid" aria-label="Operational summary">
      <article className="summary-card">
        <span className="summary-icon icon-blue" aria-hidden="true">
          ◎
        </span>
        <div>
          <span className="field-label">Facility / world</span>
          <strong>{worldId}</strong>
          <span className="summary-caption">Twin-scoped view</span>
        </div>
      </article>
      <article className="summary-card summary-card-accent">
        <span className="summary-icon icon-cyan" aria-hidden="true">
          ◫
        </span>
        <div>
          <span className="field-label">Active lot</span>
          <strong>{lot?.lot_id ?? "No lot reported"}</strong>
          <span className="summary-caption">
            {lot?.route_position.operation_class_id ?? "Awaiting state"}
          </span>
        </div>
      </article>
      <article className="summary-card">
        <span className="summary-icon icon-amber" aria-hidden="true">
          !
        </span>
        <div>
          <span className="field-label">Production state</span>
          <strong>
            {lot ? <StatusBadge value={lot.lifecycle_state} /> : "—"}
          </strong>
          <span className="summary-caption">
            {lot ? "Lot lifecycle" : "No active lot"}
          </span>
        </div>
      </article>
      <article className="summary-card">
        <span className="summary-icon icon-green" aria-hidden="true">
          ◌
        </span>
        <div>
          <span className="field-label">Data freshness</span>
          <strong>
            <Freshness value={freshness} />
          </strong>
          <span className="summary-caption">Reported by Twin</span>
        </div>
      </article>
    </div>
  );
}

function LotCard({ lot }: { lot: LotState }) {
  const holdActive = lot.hold_state !== "NONE" && lot.hold_state !== "CLEAR";
  return (
    <article className={`lot-card ${holdActive ? "lot-card-held" : ""}`}>
      <div className="lot-card-heading">
        <div>
          <p className="eyebrow">Serialized production lot</p>
          <h3>{lot.lot_id}</h3>
        </div>
        <Freshness value={lot.freshness} />
      </div>
      <div className="lot-status-row" aria-label={`${lot.lot_id} state`}>
        <div>
          <span className="field-label">Lot lifecycle</span>
          <StatusBadge value={lot.lifecycle_state} />
        </div>
        <div>
          <span className="field-label">Execution state</span>
          <StatusBadge value={lot.execution_state} />
        </div>
        <div>
          <span className="field-label">Hold state</span>
          <StatusBadge
            value={lot.hold_state}
            tone={holdActive ? "warning" : "neutral"}
          />
        </div>
      </div>
      <p className="state-legend">
        Production state describes the lot lifecycle. Execution state describes
        whether work is running or waiting. Hold state describes a quality or
        material restriction.
      </p>
      {holdActive ? (
        <div className="hold-alert" role="note">
          <span className="hold-alert-icon" aria-hidden="true">
            !
          </span>
          <div>
            <strong>Active quality hold</strong>
            <p>
              This lot is held while the reported quality event is reviewed.
              Release authority remains outside this view.
            </p>
          </div>
        </div>
      ) : null}
      <div className="route-strip">
        <div>
          <span className="field-label">Route</span>
          <strong>{lot.route_position.route_id}</strong>
        </div>
        <div>
          <span className="field-label">Current visit</span>
          <strong>{lot.route_position.visit_id}</strong>
        </div>
        <div>
          <span className="field-label">Operation</span>
          <strong>{lot.route_position.operation_class_id}</strong>
        </div>
        <div>
          <span className="field-label">Position</span>
          <strong>{lot.route_position.position}</strong>
        </div>
      </div>
      <details className="technical-details lot-technical-details">
        <summary>Lot traceability</summary>
        <dl className="compact-definition-list">
          <dt>Revision</dt>
          <dd>{lot.revision}</dd>
          <dt>Epistemic class</dt>
          <dd>{lot.epistemic_class}</dd>
        </dl>
      </details>
    </article>
  );
}

function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0)
    return (
      <p className="empty-copy">
        Nothing needs attention in the reported sources.
      </p>
    );
  return (
    <ul className="attention-list" aria-label="Needs attention">
      {items.map((item) => {
        const quality = item.kind === "QUALITY_EXCURSION";
        return (
          <li
            className={`attention-card ${quality ? "attention-quality" : ""}`}
            key={`${item.source}/${item.item_id}`}
          >
            <div className="attention-card-heading">
              <span className="event-icon" aria-hidden="true">
                {quality ? "!" : "•"}
              </span>
              <div>
                <span className="eyebrow">
                  {quality ? "Quality event" : "Attention item"}
                </span>
                <strong>{item.summary}</strong>
              </div>
              <Freshness value={item.freshness} />
            </div>
            <div className="attention-fields">
              <div>
                <span className="field-label">Type</span>
                <strong>{item.kind}</strong>
              </div>
              <div>
                <span className="field-label">Observation state</span>
                <strong>{item.epistemic_class}</strong>
              </div>
              <div>
                <span className="field-label">Affected subject</span>
                <strong>
                  {item.subject.entity_type} {item.subject.entity_id}
                </strong>
              </div>
              <div>
                <span className="field-label">Source</span>
                <strong>{item.source}</strong>
                <span className="detail-value">
                  Revision <TechnicalValue value={item.source_revision} />
                </span>
              </div>
            </div>
            <dl className="attention-technical sr-only">
              <dt>Kind</dt>
              <dd>{item.kind}</dd>
              <dt>Epistemic class</dt>
              <dd>{item.epistemic_class}</dd>
              <dt>Subject</dt>
              <dd>
                {item.subject.entity_type} {item.subject.entity_id}
              </dd>
              <dt>Source</dt>
              <dd>
                {item.source} @ {item.source_revision}
              </dd>
              <dt>Freshness</dt>
              <dd>{item.freshness}</dd>
            </dl>
          </li>
        );
      })}
    </ul>
  );
}

function QualityExcursion({ items }: { items: AttentionItem[] }) {
  const item = items.find(
    (candidate) => candidate.kind === "QUALITY_EXCURSION",
  );
  if (!item) return null;
  return (
    <section className="card quality-panel" aria-labelledby="quality-heading">
      <SectionHeading
        eyebrow="Action required"
        title="Quality excursion"
        id="quality-heading"
      />
      <div className="quality-event">
        <div className="quality-event-mark" aria-hidden="true">
          !
        </div>
        <div>
          <strong>{item.summary}</strong>
          <p>
            The affected lot is on hold because of this reported quality event.
          </p>
        </div>
        <StatusBadge value={item.freshness} />
      </div>
      <div className="quality-fields">
        <div>
          <span className="field-label">Type</span>
          <strong>{item.kind}</strong>
        </div>
        <div>
          <span className="field-label">Affected lot</span>
          <strong>{item.subject.entity_id}</strong>
        </div>
        <div>
          <span className="field-label">Observation state</span>
          <strong>{item.epistemic_class}</strong>
        </div>
        <div>
          <span className="field-label">Source</span>
          <strong>{item.source}</strong>
        </div>
      </div>
    </section>
  );
}

function ShowcaseTimeline({ state }: { state: ShowcaseState }) {
  if (state.status === "idle" || state.status === "loading") return null;
  if (state.status !== "ready") return null;
  const { timeline, dispatch } = state.showcase;
  if (timeline.length === 0) {
    return (
      <section
        className="card timeline-panel"
        aria-label="Operational timeline"
      >
        <SectionHeading eyebrow="Live evidence" title="Operational timeline" />
        <p className="empty-copy">
          No persisted showcase events have reached this lot yet.
        </p>
      </section>
    );
  }
  return (
    <section className="card timeline-panel" aria-label="Operational timeline">
      <SectionHeading eyebrow="Live evidence" title="Operational timeline" />
      <ol className="timeline-list">
        {timeline.map((item) => (
          <li className="timeline-item" key={item.id}>
            <span className="timeline-marker" aria-hidden="true" />
            <div>
              <strong>{item.label}</strong>
              <span className="timeline-detail">
                {item.source} · {item.status}
                {item.error_code ? ` · ${item.error_code}` : ""}
              </span>
            </div>
          </li>
        ))}
      </ol>
      {dispatch?.status === "REJECTED" &&
      dispatch.error_code === "ACTIVE_HOLD" ? (
        <p className="dispatch-blocked" role="status">
          Dispatch blocked — active quality hold{" "}
          <span>{dispatch.error_code}</span>
        </p>
      ) : null}
    </section>
  );
}

function EquipmentTables({ state }: { state: FacilityStateResponse }) {
  const { facility } = state;
  return (
    <>
      {facility.equipment.length > 0 ? (
        <details className="equipment-details" open>
          <summary>Equipment state ({facility.equipment.length})</summary>
          <div className="table-scroll">
            <table aria-label="Facility equipment">
              <caption>Equipment</caption>
              <thead>
                <tr>
                  <th scope="col">Equipment</th>
                  <th scope="col">Equipment state</th>
                  <th scope="col">Maintenance</th>
                  <th scope="col">Freshness</th>
                </tr>
              </thead>
              <tbody>
                {facility.equipment.map((item) => (
                  <tr key={item.equipment_id}>
                    <th scope="row">{item.equipment_id}</th>
                    <td>{item.equipment_state}</td>
                    <td>{item.maintenance_state}</td>
                    <td>{item.freshness}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
      <details className="equipment-details" open>
        <summary>Production lots ({facility.lots.length})</summary>
        <div className="table-scroll">
          <table aria-label="Production lots">
            <caption>Lots</caption>
            <thead>
              <tr>
                <th scope="col">Lot</th>
                <th scope="col">Lifecycle</th>
                <th scope="col">Execution</th>
                <th scope="col">Hold</th>
                <th scope="col">Route visit</th>
                <th scope="col">Freshness</th>
              </tr>
            </thead>
            <tbody>
              {facility.lots.map((item) => (
                <tr key={item.lot_id}>
                  <th scope="row">{item.lot_id}</th>
                  <td>{item.lifecycle_state}</td>
                  <td>{item.execution_state}</td>
                  <td>{item.hold_state}</td>
                  <td>
                    {item.route_position.visit_id} ·{" "}
                    {item.route_position.operation_class_id}
                  </td>
                  <td>{item.freshness}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

function FacilityStateViewPanel({
  state,
  reload,
  overview,
  showcase,
}: {
  state: FacilityStateView;
  reload: () => void;
  overview: OverviewState;
  showcase: ShowcaseState;
}) {
  switch (state.status) {
    case "idle":
      return (
        <div className="empty-panel">
          <span className="empty-panel-icon" aria-hidden="true">
            ◎
          </span>
          <div>
            <strong>Select a world to load the overview.</strong>
            <p>
              Choose a world scope above to retrieve live Twin-backed state.
            </p>
          </div>
        </div>
      );
    case "loading":
      return (
        <div className="loading-panel" role="status">
          <span className="spinner" aria-hidden="true" />
          <div>
            <strong>Loading operational state</strong>
            <p>Requesting the latest Twin projection…</p>
          </div>
        </div>
      );
    case "unavailable":
      return (
        <div className="state-panel state-error" role="status">
          <strong>The Twin facility state is unavailable.</strong>
          {state.sources.length > 0 ? (
            <p>Unavailable: {state.sources.join(", ")}</p>
          ) : null}
          <button
            className="button button-secondary"
            type="button"
            onClick={reload}
          >
            Retry facility state
          </button>
        </div>
      );
    case "invalid":
      return (
        <div className="state-panel state-error" role="status">
          Facility state request rejected: {state.message}
        </div>
      );
    case "error":
      return (
        <div className="state-panel state-error" role="status">
          <strong>The facility state could not be loaded.</strong>
          <button
            className="button button-secondary"
            type="button"
            onClick={reload}
          >
            Retry facility state
          </button>
        </div>
      );
    case "ready": {
      const { meta, facility } = state.state;
      const overviewValue =
        overview.status === "ready" ? overview.overview : null;
      return (
        <>
          <SummaryCards
            worldId={meta.world.world_id}
            lot={facility.lots[0] ?? null}
            freshness={meta.freshness}
          />
          <section
            className="section-block"
            aria-labelledby="facility-state-heading"
          >
            <SectionHeading
              eyebrow="Live operational state"
              title="Facility state"
              id="facility-state-heading"
              action={
                <span className="section-status">
                  <span className="live-dot" aria-hidden="true" />
                  Polling Twin
                </span>
              }
            />
            <p className="state-context">
              World {meta.world.world_id} · freshness {meta.freshness}
            </p>
            {facility.lots.length > 0 ? (
              <div className="lot-grid">
                {facility.lots.map((lot) => (
                  <LotCard key={lot.lot_id} lot={lot} />
                ))}
              </div>
            ) : (
              <div className="empty-panel">
                <strong>No production lots reported.</strong>
                <p>The Twin returned an empty lot collection for this world.</p>
              </div>
            )}
            <EquipmentTables state={state.state} />
          </section>
          <QualityExcursion items={overviewValue?.needs_attention ?? []} />
          <ShowcaseTimeline state={showcase} />
          <MetaSummary overview={overviewValue} facility={state.state} />
        </>
      );
    }
  }
}

function OverviewView({
  state,
  loadMore,
  reload,
}: {
  state: OverviewState;
  loadMore: () => void;
  reload: () => void;
}) {
  switch (state.status) {
    case "idle":
    case "loading":
      return null;
    case "unavailable":
      return (
        <div className="state-panel state-error" role="alert">
          <strong>The overview is unavailable.</strong>
          <p>
            A backend it needs could not be reached. Nothing is shown rather
            than a partial view.
          </p>
          {state.sources.length > 0 ? (
            <p>Unavailable: {state.sources.join(", ")}</p>
          ) : null}
          <button
            className="button button-secondary"
            type="button"
            onClick={reload}
          >
            Retry
          </button>
        </div>
      );
    case "stale":
      return (
        <div className="state-panel state-error" role="alert">
          <strong>The overview changed while it was being paged.</strong>
          <p>Reload to start with a consistent view.</p>
          <button
            className="button button-secondary"
            type="button"
            onClick={reload}
          >
            Reload
          </button>
        </div>
      );
    case "invalid":
      return (
        <p className="state-panel state-error" role="alert">
          The overview request was rejected: {state.message}
        </p>
      );
    case "error":
      return (
        <div className="state-panel state-error" role="alert">
          <strong>The overview could not be loaded.</strong>
          <button
            className="button button-secondary"
            type="button"
            onClick={reload}
          >
            Retry
          </button>
        </div>
      );
    case "ready":
      return (
        <section
          className="card attention-panel"
          aria-labelledby="attention-heading"
        >
          <SectionHeading
            eyebrow="Operational awareness"
            title="Needs attention"
            id="attention-heading"
          />
          <AttentionList items={state.items} />
          {state.nextCursor !== null ? (
            <button
              className="button button-secondary"
              disabled={state.more === "loading"}
              type="button"
              onClick={loadMore}
            >
              {state.more === "loading" ? "Loading…" : "Load more"}
            </button>
          ) : null}
          {state.more === "error" ? (
            <span role="alert"> More items could not be loaded.</span>
          ) : null}
        </section>
      );
  }
}

export function OverviewPage() {
  const session = useSession();
  const [params, setParams] = useSearchParams();
  const worldId = params.get("world_id")?.trim() || null;
  const { state, loadMore, reload } = useOverview(
    worldId,
    session.status === "authenticated",
  );
  const facility = useFacilityState(
    worldId,
    session.status === "authenticated",
  );
  const showcaseLotId =
    facility.state.status === "ready"
      ? (facility.state.state.facility.lots[0]?.lot_id ?? "DEMO-LOT-001")
      : "DEMO-LOT-001";
  const showcase = useShowcase(
    worldId,
    showcaseLotId,
    session.status === "authenticated",
  );
  return (
    <section className="overview-page" aria-labelledby="overview-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Aerospace manufacturing operations</p>
          <h1 id="overview-heading">Manufacturing Overview</h1>
          <p className="page-subtitle">
            One clear view of the active world, production state, and quality
            signals.
          </p>
        </div>
        <SessionSummary />
      </div>
      {session.status === "authenticated" ? (
        <>
          <WorldForm
            worldId={worldId}
            onSelect={(id) => setParams({ world_id: id })}
          />
          <FacilityStateViewPanel
            state={worldId ? facility.state : { status: "idle" }}
            reload={facility.reload}
            overview={state}
            showcase={showcase.state}
          />
          {facility.state.status !== "ready" ? (
            <OverviewView state={state} loadMore={loadMore} reload={reload} />
          ) : null}
          {facility.state.status === "ready" ? (
            <OverviewView state={state} loadMore={loadMore} reload={reload} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
