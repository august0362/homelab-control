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

interface RequestOpts {
  timeoutMs?: number;
  signal?: AbortSignal;
}

export function fetchJson<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  return request<T>(path, { headers: { Accept: "application/json" } }, opts);
}

/** JSON write (POST/PATCH). The backend rejects writes without this Content-Type (CSRF guard). */
export function sendJson<T = void>(method: "POST" | "PATCH", path: string, body: unknown = {}, opts: RequestOpts = {}): Promise<T> {
  return request<T>(
    path,
    { method, headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify(body) },
    opts,
  );
}

async function request<T>(path: string, init: RequestInit, opts: RequestOpts): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, opts.timeoutMs ?? 5000);
  opts.signal?.addEventListener("abort", () => controller.abort(), { once: true });

  try {
    const res = await fetch(path, { ...init, signal: controller.signal });
    if (res.status === 204) return undefined as T;
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      if (body?.code) throw new ApiError(body.code, body.message ?? res.statusText, res.status);
      // No JSON body means our API never answered (e.g. the dev proxy replies 500/502).
      if (res.status >= 500) {
        throw new ApiError("network_error", `Backend unreachable (HTTP ${res.status}).`, res.status);
      }
      if (res.status === 401) throw new ApiError("unauthorized", "Sign in to continue.", 401);
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
