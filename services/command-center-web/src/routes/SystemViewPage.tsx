import { useSearchParams } from "react-router-dom";
import { Fragment } from "react";

import { useSession } from "../session/SessionProvider";
import { useShowcase, type ShowcaseState } from "../showcase/useShowcase";
import type {
  ShowcaseCounter,
  ShowcaseSystemItem,
} from "../showcase/showcaseClient";

const DEFAULT_WORLD_ID = "DEMO-WORLD";
const DEFAULT_LOT_ID = "DEMO-LOT-001";

function TechnicalValue({ value }: { value: string }) {
  return (
    <span className="technical-value" title={value}>
      {value.length > 20 ? `${value.slice(0, 20)}…` : value}
    </span>
  );
}

function statusClass(status: string): string {
  const value = status.toLowerCase();
  if (
    [
      "up",
      "updated",
      "published",
      "connected",
      "read",
      "serving",
      "rendered",
      "observed",
      "reported",
    ].includes(value)
  ) {
    return "status-good";
  }
  if (["degraded", "pending", "no_event"].includes(value))
    return "status-warning";
  if (["down", "unavailable"].includes(value)) return "status-critical";
  return "status-neutral";
}

function RuntimeStatus({ value }: { value: string }) {
  return <span className={`status-badge ${statusClass(value)}`}>{value}</span>;
}

function WorldForm({ worldId, lotId }: { worldId: string; lotId: string }) {
  const [, setParams] = useSearchParams();
  return (
    <form
      className="world-control system-world-control"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const nextWorld = String(form.get("world_id") ?? "").trim();
        const nextLot = String(form.get("lot_id") ?? "").trim();
        if (nextWorld && nextLot)
          setParams({ world_id: nextWorld, lot_id: nextLot });
      }}
    >
      <div>
        <label htmlFor="system-world-id">World and lot</label>
        <span className="control-hint">Read-only runtime evidence scope</span>
      </div>
      <div className="world-input-row system-world-input-row">
        <input
          id="system-world-id"
          name="world_id"
          defaultValue={worldId}
          required
        />
        <input
          aria-label="Lot ID"
          name="lot_id"
          defaultValue={lotId}
          required
        />
        <button className="button button-primary" type="submit">
          Load system view <span aria-hidden="true">→</span>
        </button>
      </div>
    </form>
  );
}

function Flow({ items }: { items: ShowcaseSystemItem[] }) {
  const withUi: ShowcaseSystemItem[] = [
    ...items.filter((item) => item.id !== "ui"),
    {
      id: "ui",
      label: "UI",
      status: "RENDERED",
      detail: "System View rendered this response",
    },
  ];
  return (
    <section
      className="card system-flow-panel"
      aria-labelledby="system-flow-heading"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Live runtime path</p>
          <h2 id="system-flow-heading">System flow</h2>
        </div>
        <span className="section-status">
          <span className="live-dot" aria-hidden="true" />
          BFF read model
        </span>
      </div>
      <div
        className="system-flow"
        aria-label="Simulator to UI architecture flow"
      >
        {withUi.map((item, index) => (
          <div className="system-flow-step" key={item.id}>
            <article className="system-stage">
              <span className="system-stage-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <strong>{item.label}</strong>
              <RuntimeStatus value={item.status} />
              <span className="system-stage-detail">{item.detail}</span>
              {typeof item.command_id === "string" ? (
                <TechnicalValue value={item.command_id} />
              ) : null}
              {typeof item.event_id === "string" ? (
                <TechnicalValue value={item.event_id} />
              ) : null}
            </article>
            {index < withUi.length - 1 ? (
              <span className="system-flow-arrow" aria-hidden="true">
                →
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function Health({ items }: { items: ShowcaseSystemItem[] }) {
  const health = [
    ...items,
    {
      id: "ui",
      label: "UI",
      status: "RENDERED",
      detail: "System View rendered",
    },
  ];
  return (
    <section
      className="card system-health-panel"
      aria-labelledby="system-health-heading"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dependency readout</p>
          <h2 id="system-health-heading">System health</h2>
        </div>
      </div>
      <div className="system-health-grid">
        {health.map((item) => (
          <article className="system-health-item" key={item.id}>
            <div>
              <strong>{item.label}</strong>
              <RuntimeStatus value={item.status} />
            </div>
            <span>{item.detail}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function Counters({ items }: { items: ShowcaseCounter[] }) {
  return (
    <section className="system-counters" aria-label="Runtime counters">
      {items.map((item) => (
        <article className="system-counter" key={item.id}>
          <span className="field-label">{item.label}</span>
          <strong>{item.value === null ? "UNKNOWN" : item.value}</strong>
          <span className="summary-caption">reported by runtime</span>
        </article>
      ))}
    </section>
  );
}

function Evidence({
  state,
}: {
  state: Extract<ShowcaseState, { status: "ready" }>;
}) {
  const { showcase } = state;
  return (
    <>
      <Flow items={showcase.architecture} />
      <div className="system-two-column">
        <Health items={showcase.health} />
        <section
          className="card system-identities"
          aria-labelledby="system-identities-heading"
        >
          <div className="section-heading">
            <div>
              <p className="eyebrow">Correlation and lineage</p>
              <h2 id="system-identities-heading">Event trace</h2>
            </div>
          </div>
          <dl className="compact-definition-list">
            <dt>World / lot</dt>
            <dd>
              {showcase.meta.world_id} / {showcase.meta.lot_id}
            </dd>
            <dt>Correlation</dt>
            <dd>
              <TechnicalValue value={showcase.meta.correlation_id} />
            </dd>
            {Object.entries(showcase.identities).map(([key, value]) =>
              value ? (
                <Fragment key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>
                    <TechnicalValue value={String(value)} />
                  </dd>
                </Fragment>
              ) : null,
            )}
          </dl>
        </section>
      </div>
      <Counters items={showcase.counters} />
      <section
        className="card timeline-panel system-trace-panel"
        aria-labelledby="system-trace-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Persisted evidence</p>
            <h2 id="system-trace-heading">Event timeline</h2>
          </div>
          <RuntimeStatus value={showcase.meta.freshness} />
        </div>
        {showcase.timeline.length === 0 ? (
          <p className="empty-copy">
            No persisted events were reported for this scope.
          </p>
        ) : (
          <ol className="timeline-list">
            {showcase.timeline.map((item) => (
              <li className="timeline-item" key={item.id}>
                <span className="timeline-marker" aria-hidden="true" />
                <div>
                  <strong>{item.label}</strong>
                  <span className="timeline-detail">
                    {item.source} · {item.status}
                    {item.event_id ? ` · ${item.event_id}` : ""}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}

function ShowcaseState({ state }: { state: ShowcaseState }) {
  switch (state.status) {
    case "idle":
      return (
        <div className="empty-panel">
          <strong>Select a runtime scope.</strong>
          <p>System View reads the authenticated demo BFF evidence endpoint.</p>
        </div>
      );
    case "loading":
      return (
        <div className="loading-panel" role="status">
          <span className="spinner" aria-hidden="true" />
          <div>
            <strong>Loading runtime evidence</strong>
            <p>Reading the current Core, outbox, JetStream and Twin state…</p>
          </div>
        </div>
      );
    case "unavailable":
      return (
        <div className="state-panel state-error" role="alert">
          <strong>Runtime evidence is unavailable.</strong>
          <p>
            No status is inferred while the BFF read model cannot be reached.
          </p>
        </div>
      );
    case "invalid":
      return (
        <div className="state-panel state-error" role="alert">
          Runtime evidence was rejected: {state.message}
        </div>
      );
    case "ready":
      return <Evidence state={state} />;
  }
}

export function SystemViewPage() {
  const session = useSession();
  const [params] = useSearchParams();
  const worldId = params.get("world_id")?.trim() || DEFAULT_WORLD_ID;
  const lotId = params.get("lot_id")?.trim() || DEFAULT_LOT_ID;
  const showcase = useShowcase(
    worldId,
    lotId,
    session.status === "authenticated",
  );
  return (
    <section
      className="overview-page system-view-page"
      aria-labelledby="system-view-heading"
    >
      <div className="page-heading">
        <div>
          <p className="eyebrow">Runtime observability</p>
          <h1 id="system-view-heading">System View</h1>
          <p className="page-subtitle">
            Trace the real demo path from simulator observation to the rendered
            operational view.
          </p>
        </div>
      </div>
      {session.status === "authenticated" ? (
        <>
          <WorldForm worldId={worldId} lotId={lotId} />
          <ShowcaseState state={showcase.state} />
        </>
      ) : (
        <p className="empty-copy">Sign-in required.</p>
      )}
    </section>
  );
}
