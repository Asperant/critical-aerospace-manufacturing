import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import type { SessionResponse } from "../contract/generated";
import { fetchSession, type SessionResult } from "./sessionClient";

export type SessionState =
  | { status: "loading" }
  | { status: "authenticated"; session: SessionResponse }
  | { status: "unauthenticated" }
  | { status: "error" };

export type SessionLoader = (signal: AbortSignal) => Promise<SessionResult>;

const SessionContext = createContext<SessionState | null>(null);

const defaultLoader: SessionLoader = (signal) => fetchSession(signal);

/** Loads the session once on mount; state lives in memory only. */
export function SessionProvider({
  children,
  loadSession = defaultLoader,
}: {
  children: ReactNode;
  loadSession?: SessionLoader;
}) {
  const [state, setState] = useState<SessionState>({ status: "loading" });

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

  return (
    <SessionContext.Provider value={state}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionState {
  const state = useContext(SessionContext);
  if (state === null)
    throw new Error("useSession must be used inside SessionProvider");
  return state;
}
