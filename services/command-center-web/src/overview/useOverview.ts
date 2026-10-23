import { useCallback, useEffect, useRef, useState } from "react";

import type {
  AttentionItem,
  ManufacturingOverviewResponse,
} from "../contract/generated";
import { useSessionActions } from "../session/SessionProvider";
import { fetchOverview, type OverviewResult } from "./overviewClient";

export type OverviewState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      overview: ManufacturingOverviewResponse;
      items: AttentionItem[];
      nextCursor: string | null;
      more: "idle" | "loading" | "error";
    }
  | { status: "unavailable"; sources: string[] }
  | { status: "stale" }
  | { status: "invalid"; message: string }
  | { status: "error" };

type Settled = Exclude<
  OverviewState,
  { status: "idle" } | { status: "loading" }
>;

/**
 * Loads the overview for one world. Results are kept against the request they
 * answer, so a change of world or a reload shows "loading" without any state
 * being set from inside the effect itself.
 */
export function useOverview(worldId: string | null, enabled: boolean) {
  const { expire } = useSessionActions();
  const [reloads, setReloads] = useState(0);
  const [settled, setSettled] = useState<{
    key: string;
    value: Settled;
  } | null>(null);
  const moreController = useRef<AbortController | null>(null);
  const key = enabled && worldId !== null ? `${worldId}#${reloads}` : null;

  const settle = useCallback(
    (forKey: string, result: OverviewResult): void => {
      switch (result.status) {
        case "ok":
          setSettled({
            key: forKey,
            value: {
              status: "ready",
              overview: result.overview,
              items: result.overview.needs_attention,
              nextCursor: result.overview.page.next_cursor,
              more: "idle",
            },
          });
          return;
        case "unauthenticated":
          expire();
          return;
        case "stale":
          setSettled({ key: forKey, value: { status: "stale" } });
          return;
        case "invalid":
          setSettled({
            key: forKey,
            value: { status: "invalid", message: result.message },
          });
          return;
        case "unavailable":
          setSettled({
            key: forKey,
            value: { status: "unavailable", sources: result.sources },
          });
          return;
      }
    },
    [expire],
  );

  useEffect(() => {
    if (key === null || worldId === null) return;
    const controller = new AbortController();
    fetchOverview({ worldId }, controller.signal).then(
      (result) => {
        if (!controller.signal.aborted) settle(key, result);
      },
      () => {
        if (!controller.signal.aborted)
          setSettled({ key, value: { status: "error" } });
      },
    );
    return () => {
      controller.abort();
      moreController.current?.abort();
    };
  }, [key, worldId, settle]);

  const loadMore = useCallback(() => {
    if (key === null || worldId === null) return;
    const current = settled?.key === key ? settled.value : null;
    if (
      current?.status !== "ready" ||
      current.nextCursor === null ||
      current.more === "loading"
    ) {
      return;
    }
    const cursor = current.nextCursor;
    const controller = new AbortController();
    moreController.current = controller;
    setSettled({ key, value: { ...current, more: "loading" } });
    fetchOverview({ worldId, cursor }, controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return;
        if (result.status !== "ok") {
          settle(key, result);
          return;
        }
        setSettled({
          key,
          value: {
            ...current,
            items: [...current.items, ...result.overview.needs_attention],
            nextCursor: result.overview.page.next_cursor,
            more: "idle",
          },
        });
      },
      () => {
        if (!controller.signal.aborted) {
          setSettled({ key, value: { ...current, more: "error" } });
        }
      },
    );
  }, [key, worldId, settled, settle]);

  const reload = useCallback(() => setReloads((count) => count + 1), []);

  let state: OverviewState = { status: "idle" };
  if (key !== null)
    state = settled?.key === key ? settled.value : { status: "loading" };
  return { state, loadMore, reload };
}
