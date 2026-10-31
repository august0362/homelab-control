import { useEffect, useState } from "react";
import type { Metrics } from "../api/types";
import { addSample, EMPTY_HISTORY, type Sample } from "../lib/history";
import { type PollState, usePolling } from "./usePolling";

export const METRICS_MS = 2_000;

export interface MetricsState extends PollState<Metrics> {
  history: Sample[];
}

/** Polls /api/metrics and keeps the last 10 minutes in memory. Lives in App so history survives page switches. */
export function useMetrics(): MetricsState {
  const poll = usePolling<Metrics>("/api/metrics", METRICS_MS);
  const [history, setHistory] = useState(EMPTY_HISTORY);
  const { data, lastUpdated } = poll;

  useEffect(() => {
    if (data && lastUpdated) setHistory((h) => addSample(h, data, lastUpdated.getTime()));
  }, [data, lastUpdated]);

  return { ...poll, history: history.samples };
}
