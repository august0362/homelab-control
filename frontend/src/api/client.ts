// Thin fetch wrapper: same-origin /api, timeout, errors normalized to {code, message}.

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status = 0) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  return new ApiError("unknown_error", err instanceof Error ? err.message : String(err));
}

export async function fetchJson<T>(path: string, opts: { timeoutMs?: number; signal?: AbortSignal } = {}): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, opts.timeoutMs ?? 5000);
  opts.signal?.addEventListener("abort", () => controller.abort(), { once: true });

  try {
    const res = await fetch(path, { signal: controller.signal, headers: { Accept: "application/json" } });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      if (body?.code) throw new ApiError(body.code, body.message ?? res.statusText, res.status);
      // No JSON body means our API never answered (e.g. the dev proxy replies 500/502).
      if (res.status >= 500) {
        throw new ApiError("network_error", `Backend unreachable (HTTP ${res.status}).`, res.status);
      }
      throw new ApiError(`http_${res.status}`, res.statusText, res.status);
    }
    return body as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (timedOut) throw new ApiError("timeout", "Backend did not respond in time.");
    if (controller.signal.aborted) throw new ApiError("aborted", "Request cancelled.");
    throw new ApiError("network_error", "Backend unreachable.");
  } finally {
    clearTimeout(timer);
  }
}
