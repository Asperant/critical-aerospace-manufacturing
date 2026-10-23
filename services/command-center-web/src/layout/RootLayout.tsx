import { NavLink, Outlet } from "react-router-dom";

import { useSession, useSessionActions } from "../session/SessionProvider";

// Plain anchors on purpose: sign-in is a full browser navigation to the BFF,
// which runs the identity-provider redirects; the app never sees a token.
const START_LOGIN_PATH = "/v1/session/login";

function SessionArea() {
  const state = useSession();
  const { signOut, signOutFailed } = useSessionActions();
  switch (state.status) {
    case "loading":
      return <span>Checking session…</span>;
    case "unauthenticated":
      return <a href={START_LOGIN_PATH}>Sign in</a>;
    case "error":
      return <span>Session unavailable</span>;
    case "authenticated":
      return (
        <>
          <span>{state.session.actor.display_name}</span>{" "}
          <button type="button" onClick={() => void signOut()}>
            Sign out
          </button>
          {signOutFailed ? (
            <span role="alert"> Sign-out failed. Try again.</span>
          ) : null}
        </>
      );
  }
}

export function RootLayout() {
  return (
    <>
      <header>
        <strong>Manufacturing Command Center</strong>
        <nav aria-label="Primary">
          <NavLink to="/overview">Overview</NavLink>
        </nav>
        <div role="group" aria-label="Session">
          <SessionArea />
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
