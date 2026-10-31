import { type FormEvent, useState } from "react";
import { sendJson, toApiError } from "../api/client";
import { Icon } from "../components/Icon";

const SET_PASSWORD = "On the server, run scripts\\set-password.ps1, then restart the backend.";

// Not in the page registry: App shows it whenever there is no session.
export function Login({
  configured,
  notice,
  onSignedIn,
}: {
  configured: boolean;
  notice?: string; // e.g. backend unreachable while checking the session
  onSignedIn: () => Promise<void>;
}) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await sendJson("POST", "/api/auth/login", { password }, { timeoutMs: 10_000 });
      setPassword("");
      await onSignedIn();
    } catch (err) {
      const apiError = toApiError(err);
      if (apiError.code === "invalid_credentials") setError("Wrong password.");
      else if (apiError.code === "auth_not_configured") setError(`No owner password set yet. ${SET_PASSWORD}`);
      else setError(apiError.message); // too_many_attempts: "… Try again in 60 s."
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="cup" size={20} />
          </span>
          <span className="brand-name">HomeLab Control</span>
        </div>
        <div>
          <h1>Sign in</h1>
          <p className="muted">Owner access only.</p>
        </div>
        {configured ? (
          <>
            {notice && !error && <p className="error-text">{notice}</p>}
            {/* Lets password managers save the entry; there is a single owner, no username. */}
            <input type="text" name="username" autoComplete="username" value="owner" readOnly hidden />
            <label className="field">
              <span>Password</span>
              <input
                className="input"
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={error ? true : undefined}
                required
                autoFocus
              />
            </label>
            {error && (
              <p className="error-text" role="alert">
                {error}
              </p>
            )}
            <button className="btn btn-primary" type="submit" disabled={busy || !password}>
              <Icon name="lock" size={16} />
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </>
        ) : (
          <div className="stack">
            <p className="error-text">No owner password set yet.</p>
            <p className="muted">{SET_PASSWORD}</p>
            <button className="btn" type="button" onClick={() => void onSignedIn()}>
              Check again
            </button>
          </div>
        )}
      </form>
    </main>
  );
}
