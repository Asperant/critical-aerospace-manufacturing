import { useCallback, useEffect, useState } from "react";

import { useSessionActions } from "../session/SessionProvider";
import { fetchShowcase, type ShowcaseResponse, type ShowcaseResult } from "./showcaseClient";

export type ShowcaseState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; showcase: ShowcaseResponse }
  | { status: "unavailable" }
  | { status: "invalid"; message: string };

export function useShowcase(worldId: string | null, lotId: string | null, enabled: boolean) {
  const { expire } = useSessionActions();
  const [reloads, setReloads] = useState(0);
  const [state, setState] = useState<ShowcaseState>({ status: "idle" });
  const key = enabled && worldId && lotId ? `${worldId}/${lotId}#${reloads}` : null;

  const settle = useCallback((result: ShowcaseResult) => {
    if (result.status === "unauthenticated") {
      expire();
    } else if (result.status === "ok") {
      setState({ status: "ready", showcase: result.showcase });
    } else if (result.status === "invalid") {
      setState({ status: "invalid", message: result.message });
    } else if (result.status === "unavailable") {
      setState({ status: "unavailable" });
    }
  }, [expire]);

  useEffect(() => {
    if (key === null || worldId === null || lotId === null) {
      setState({ status: "idle" });
      return;
    }
    let stopped = false;
    let timer: number | undefined;
    const controller = new AbortController();
    const poll = async () => {
      if (stopped) return;
      setState((current) => current.status === "ready" ? current : { status: "loading" });
      try {
        const result = await fetchShowcase(worldId, lotId, controller.signal);
        if (!stopped && result.status !== "unauthenticated") settle(result);
        if (!stopped && result.status !== "unauthenticated") timer = window.setTimeout(poll, 3000);
      } catch {
        if (!stopped) {
          setState({ status: "unavailable" });
          timer = window.setTimeout(poll, 3000);
        }
      }
    };
    void poll();
    return () => {
      stopped = true;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [key, lotId, settle, worldId]);

  return { state, reload: useCallback(() => setReloads((count) => count + 1), []) };
}
