import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_BASE } from "../lib/api";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";

const EVENTS = ["risk.updated", "alert.created", "alert.updated", "report.created", "assignment.updated", "feed.degraded"];

/**
 * SSE bridge. On failure the UI is told to show "LIVE UPDATES PAUSED" and the
 * pages fall back to polling every 60 s (see useFallbackPolling).
 */
export function useLiveUpdates() {
  const token = useSession((s) => s.token);
  const setStatus = useUi((s) => s.setLiveStatus);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;
    let closed = false;
    const source = new EventSource(`${API_BASE}/api/v1/stream?token=${encodeURIComponent(token)}`);
    source.onopen = () => setStatus("live");
    const onChange = () => {
      queryClient.invalidateQueries();
    };
    EVENTS.forEach((event) => source.addEventListener(event, onChange));
    source.onerror = () => {
      if (closed) return;
      setStatus("paused");
      source.close();
      // Reconnect with a fresh EventSource after a delay; the UI stays "paused" until open.
      window.setTimeout(() => {
        if (!closed) {
          setStatus("connecting");
          queryClient.invalidateQueries();
        }
      }, 15000);
    };
    return () => {
      closed = true;
      source.close();
      setStatus("paused");
    };
  }, [token, queryClient, setStatus]);
}

export function useFallbackPolling(enabled: boolean) {
  const status = useUi((s) => s.liveStatus);
  return {
    refetchInterval: enabled && status !== "live" ? 60_000 : false,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  } as const;
}
