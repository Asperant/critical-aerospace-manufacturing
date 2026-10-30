import { NavLink, Outlet } from "react-router-dom";

import { useSession, useSessionActions } from "../session/SessionProvider";
import "../styles.css";

// Plain anchors on purpose: sign-in is a full browser navigation to the BFF,
// which runs the identity-provider redirects; the app never sees a token.
const START_LOGIN_PATH = "/v1/session/login";

function SessionArea() {
  const state = useSession();
  const { signOut, signOutFailed } = useSessionActions();
  switch (state.status) {
    case "loading":
      return <span className="session-state">Checking session…</span>;
    case "unauthenticated":
      return <a href={START_LOGIN_PATH}>Sign in</a>;
    case "error":
      return <span className="session-state">Session unavailable</span>;
    case "authenticated":
      return (
        <div className="session-actions">
          <span className="operator-name">
            <span className="operator-dot" aria-hidden="true" />
            {state.session.actor.display_name}
          </span>
          <button
            className="button button-quiet"
            type="button"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
          {signOutFailed ? (
            <span className="session-error" role="alert">
              Sign-out failed. Try again.
            </span>
          ) : null}
        </div>
      );
  }
}

export function RootLayout() {
  const session = useSession();
  const sessionLabel =
    session.status === "authenticated"
      ? "Session active"
      : session.status === "loading"
        ? "Checking session"
        : "Session required";
  return (
    <div className="app-shell">
      <header className="topbar" role="banner">
        <div className="topbar-inner">
          <NavLink
            className="brand"
            to="/overview"
            aria-label="Command Center home"
          >
            <span className="brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span>
              <strong>Manufacturing Command Center</strong>
              <small>Critical operations visibility</small>
            </span>
          </NavLink>
          <nav aria-label="Primary" className="primary-nav">
            <NavLink to="/overview">OPERATOR VIEW</NavLink>
            <NavLink to="/system">SYSTEM VIEW</NavLink>
          </nav>
          <div className="topbar-right">
            <span className="environment-badge">DEMO</span>
            <span className="live-indicator">
              <span className="live-dot" aria-hidden="true" />
              {sessionLabel}
            </span>
            <div className="session-area" role="group" aria-label="Session">
              <SessionArea />
            </div>
          </div>
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>Operations view</span>
        <span>Read-only Twin projection</span>
      </footer>
    </div>
  );
}
