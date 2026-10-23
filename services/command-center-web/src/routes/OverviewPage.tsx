import { useSearchParams } from "react-router-dom";

import type {
  AttentionItem,
  ManufacturingOverviewResponse,
} from "../contract/generated";
import { useOverview, type OverviewState } from "../overview/useOverview";
import { useSession } from "../session/SessionProvider";

function SessionSummary() {
  const state = useSession();
  switch (state.status) {
    case "loading":
      return <p role="status">Loading session…</p>;
    case "unauthenticated":
      return <p>Sign-in required.</p>;
    case "error":
      return <p role="alert">The session could not be loaded.</p>;
    case "authenticated": {
      const { actor, environment_id, expires_at } = state.session;
      return (
        <>
          <dl>
            <dt>Actor</dt>
            <dd>{actor.actor_id}</dd>
            <dt>Roles</dt>
            <dd>{actor.roles.length > 0 ? actor.roles.join(", ") : "none"}</dd>
            <dt>Environment</dt>
            <dd>{environment_id}</dd>
            <dt>Session expires</dt>
            <dd>{expires_at}</dd>
          </dl>
          <p>
            Roles are shown for information; the server decides what is allowed.
          </p>
        </>
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
      key={worldId ?? ""}
      onSubmit={(event) => {
        event.preventDefault();
        const value = new FormData(event.currentTarget).get("world_id");
        if (typeof value === "string" && value.trim() !== "")
          onSelect(value.trim());
      }}
    >
      <label>
        World ID <input name="world_id" defaultValue={worldId ?? ""} required />
      </label>{" "}
      <button type="submit">Load overview</button>
    </form>
  );
}

function Freshness({ value }: { value: string }) {
  return <span>{value}</span>;
}

function MetaSummary({
  overview,
}: {
  overview: ManufacturingOverviewResponse;
}) {
  const { meta } = overview;
  const world = meta.world;
  return (
    <section aria-label="Overview metadata">
      <dl>
        <dt>World</dt>
        <dd>
          {world.world_id}
          {world.simulation_run_id ? ` · run ${world.simulation_run_id}` : ""}
          {world.branch_id ? ` · branch ${world.branch_id}` : ""}
        </dd>
        <dt>Revision</dt>
        <dd>{meta.revision}</dd>
        <dt>As of</dt>
        <dd>{meta.as_of}</dd>
        <dt>Generated at</dt>
        <dd>{meta.generated_at}</dd>
        <dt>Freshness</dt>
        <dd>
          <Freshness value={meta.freshness} />
        </dd>
      </dl>
      {meta.freshness !== "FRESH" ? (
        <p role="note">Some data may be out of date ({meta.freshness}).</p>
      ) : null}
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
              <td>
                <Freshness value={source.freshness} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return <p>Nothing needs attention in the reported sources.</p>;
  }
  return (
    <ul aria-label="Needs attention">
      {items.map((item) => (
        <li key={`${item.source}/${item.item_id}`}>
          <strong>{item.summary}</strong>
          <dl>
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
            <dd>
              <Freshness value={item.freshness} />
            </dd>
          </dl>
        </li>
      ))}
    </ul>
  );
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
      return <p>Select a world to load the overview.</p>;
    case "loading":
      return <p role="status">Loading overview…</p>;
    case "unavailable":
      return (
        <div role="alert">
          <p>
            The overview is unavailable: a backend it needs could not be
            reached. Nothing is shown rather than a partial view.
          </p>
          {state.sources.length > 0 ? (
            <p>Unavailable: {state.sources.join(", ")}</p>
          ) : null}
          <button type="button" onClick={reload}>
            Retry
          </button>
        </div>
      );
    case "stale":
      return (
        <div role="alert">
          <p>
            The overview changed while it was being paged. Reload to start
            again.
          </p>
          <button type="button" onClick={reload}>
            Reload
          </button>
        </div>
      );
    case "invalid":
      return (
        <p role="alert">The overview request was rejected: {state.message}</p>
      );
    case "error":
      return (
        <div role="alert">
          <p>The overview could not be loaded.</p>
          <button type="button" onClick={reload}>
            Retry
          </button>
        </div>
      );
    case "ready":
      return (
        <>
          <MetaSummary overview={state.overview} />
          <AttentionList items={state.items} />
          {state.nextCursor !== null ? (
            <p>
              <button
                type="button"
                disabled={state.more === "loading"}
                onClick={loadMore}
              >
                Load more
              </button>
              {state.more === "error" ? (
                <span role="alert"> More items could not be loaded.</span>
              ) : null}
            </p>
          ) : null}
        </>
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
  return (
    <section aria-labelledby="overview-heading">
      <h1 id="overview-heading">Manufacturing Overview</h1>
      <SessionSummary />
      {session.status === "authenticated" ? (
        <>
          <WorldForm
            worldId={worldId}
            onSelect={(id) => setParams({ world_id: id })}
          />
          <OverviewView state={state} loadMore={loadMore} reload={reload} />
        </>
      ) : null}
    </section>
  );
}
