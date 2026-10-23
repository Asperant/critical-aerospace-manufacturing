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
          <p>
            Signed in as <strong>{actor.display_name}</strong>.
          </p>
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

export function OverviewPage() {
  return (
    <section aria-labelledby="overview-heading">
      <h1 id="overview-heading">Manufacturing Overview</h1>
      <SessionSummary />
      <p>Operational data is not connected yet.</p>
    </section>
  );
}
