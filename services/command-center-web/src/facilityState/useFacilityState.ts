import { useCallback, useEffect, useState } from "react";

import { useSessionActions } from "../session/SessionProvider";
import {
  fetchFacilityState,
  type FacilityStateResult,
} from "./facilityStateClient";
import type { FacilityStateResponse } from "../contract/generated";

export type FacilityStateView =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; state: FacilityStateResponse }
  | { status: "unavailable"; sources: string[] }
  | { status: "invalid"; message: string }
  | { status: "error" };

const DEFAULT_POLL_INTERVAL_MS = 3000;

/** Initial snapshot followed by bounded polling through the BFF only. */
export function useFacilityState(
  worldId: string | null,
  enabled: boolean,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
) {
  const { expire } = useSessionActions();
  const [reloads, setReloads] = useState(0);
  const [state, setState] = useState<FacilityStateView>({ status: "idle" });
  const [settledKey, setSettledKey] = useState<string | null>(null);
  const key = enabled && worldId !== null ? `${worldId}#${reloads}` : null;

  const settle = useCallback(
    (result: FacilityStateResult): boolean => {
      switch (result.status) {
        case "ok":
          setState({ status: "ready", state: result.state });
          return true;
        case "unauthenticated":
          expire();
          return false;
        case "invalid":
          setState({ status: "invalid", message: result.message });
          return true;
        case "unavailable":
          setState({ status: "unavailable", sources: result.sources });
          return true;
      }
    },
    [expire],
  );

  useEffect(() => {
    if (key === null || worldId === null) {
      return;
    }
    let stopped = false;
    let timer: number | undefined;
    let controller: AbortController | null = null;

    const poll = async () => {
      if (stopped) return;
      controller = new AbortController();
      setSettledKey(key);
      setState((current) =>
        current.status === "ready" ? current : { status: "loading" },
      );
      try {
        const result = await fetchFacilityState({ worldId }, controller.signal);
        if (!stopped && result.status !== "unauthenticated") settle(result);
        if (!stopped && result.status !== "unauthenticated")
          timer = window.setTimeout(poll, pollIntervalMs);
      } catch {
        if (!stopped && !controller.signal.aborted) {
          setState({ status: "error" });
          timer = window.setTimeout(poll, pollIntervalMs);
        }
      }
    };
    void poll();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
      controller?.abort();
    };
  }, [key, pollIntervalMs, settle, worldId]);

  const reload = useCallback(() => setReloads((count) => count + 1), []);
  return {
    state:
      key === null
        ? ({ status: "idle" } as const)
        : settledKey === key
          ? state
          : ({ status: "loading" } as const),
    reload,
  };
}
