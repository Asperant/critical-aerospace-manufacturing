import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { SessionResponse } from "../contract/generated";
import { fetchSession, signOut, type SessionResult } from "./sessionClient";

export type SessionState =
  | { status: "loading" }
  | { status: "authenticated"; session: SessionResponse }
  | { status: "unauthenticated" }
  | { status: "error" };

export type SessionLoader = (signal: AbortSignal) => Promise<SessionResult>;
export type SignOutRequest = (
  csrfToken: string,
  signal: AbortSignal,
) => Promise<void>;

export interface SessionActions {
  /** Ends the session on the server, then returns the UI to unauthenticated. */
  signOut: () => Promise<void>;
  signOutFailed: boolean;
  /** The server said 401 to some request: the session is gone. */
  expire: () => void;
}

interface SessionContextValue {
  state: SessionState;
  actions: SessionActions;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const defaultLoader: SessionLoader = (signal) => fetchSession(signal);
const defaultSignOut: SignOutRequest = (csrfToken, signal) =>
  signOut(csrfToken, signal);

/** Loads the session once on mount; state lives in memory only. */
export function SessionProvider({
  children,
  loadSession = defaultLoader,
  signOutRequest = defaultSignOut,
}: {
  children: ReactNode;
  loadSession?: SessionLoader;
  signOutRequest?: SignOutRequest;
}) {
  const [state, setState] = useState<SessionState>({ status: "loading" });
  const [signOutFailed, setSignOutFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    loadSession(controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return;
        setState(
          result.status === "authenticated"
            ? { status: "authenticated", session: result.session }
            : { status: "unauthenticated" },
        );
      },
      () => {
        if (!controller.signal.aborted) setState({ status: "error" });
      },
    );
    return () => controller.abort();
  }, [loadSession]);

  const csrfToken =
    state.status === "authenticated" ? state.session.csrf_token : null;

  const doSignOut = useCallback(async () => {
    if (csrfToken === null) return;
    try {
      await signOutRequest(csrfToken, new AbortController().signal);
      setSignOutFailed(false);
      setState({ status: "unauthenticated" });
    } catch {
      setSignOutFailed(true);
    }
  }, [csrfToken, signOutRequest]);

  const expire = useCallback(() => {
    setState({ status: "unauthenticated" });
  }, []);

  const value = useMemo(
    () => ({ state, actions: { signOut: doSignOut, signOutFailed, expire } }),
    [state, doSignOut, signOutFailed, expire],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

function useContextValue(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null)
    throw new Error("useSession must be used inside SessionProvider");
  return value;
}

export function useSession(): SessionState {
  return useContextValue().state;
}

export function useSessionActions(): SessionActions {
  return useContextValue().actions;
}
