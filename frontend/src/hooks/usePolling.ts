import { useCallback, useEffect, useState } from "react";
import { ApiError, fetchJson, toApiError } from "../api/client";

export interface PollState<T> {
  data: T | null; // last good response, kept while errors happen
  error: ApiError | null;
  loading: boolean;
  lastUpdated: Date | null;
  retry: () => void;
}

/** Polls `path` with a setTimeout chain: the next request starts only after the previous one ends. */
export function usePolling<T>(path: string, intervalMs: number): PollState<T> {
  const [state, setState] = useState<Omit<PollState<T>, "retry">>({
    data: null,
    error: null,
    loading: true,
    lastUpdated: null,
  });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;

    const run = async () => {
      controller = new AbortController();
      try {
        const data = await fetchJson<T>(path, { signal: controller.signal });
        if (!stopped) setState({ data, error: null, loading: false, lastUpdated: new Date() });
      } catch (err) {
        if (!stopped) setState((s) => ({ ...s, error: toApiError(err), loading: false }));
      }
      if (!stopped) timer = setTimeout(run, intervalMs);
    };
    run();

    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
    };
  }, [path, intervalMs, attempt]);

  const retry = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    setAttempt((n) => n + 1);
  }, []);

  return { ...state, retry };
}
