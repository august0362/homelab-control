import { useCallback, useEffect, useState } from "react";
import { type ApiError, fetchJson, toApiError } from "../api/client";
import type { Session } from "../api/types";

export interface SessionState {
  session: Session | null; // null until the backend first answers
  error: ApiError | null; // the last check failed (e.g. backend unreachable)
  check: () => Promise<void>;
  signOut: () => void; // drop the session locally (after logout or a 401)
}

export function useSession(): SessionState {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const check = useCallback(async () => {
    try {
      setSession(await fetchJson<Session>("/api/auth/session"));
      setError(null);
    } catch (err) {
      setError(toApiError(err));
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  const signOut = useCallback(() => setSession((s) => s && { ...s, authenticated: false, expires_at: null }), []);

  return { session, error, check, signOut };
}
