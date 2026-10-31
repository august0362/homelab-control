import { useState } from "react";
import { sendJson, toApiError } from "../api/client";
import type { PowerStatus } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { formatDateTime } from "../lib/format";
import { powerStatusView, taskSummary } from "../lib/power";
import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

const POWER_MS = 10_000;
const ACTION_TIMEOUT_MS = 70_000; // two systemctl calls over SSH, 30 s each at most

type Action = "sleep" | "wake" | "cleanup" | "reboot";

const CONFIRM: Record<Exclude<Action, "wake">, { ask: string; yes: string }> = {
  sleep: {
    ask: "Stop the optional tasks that are running? The remote desktop and any app open in it close. Wake up starts them again.",
    yes: "Yes, light sleep",
  },
  cleanup: {
    ask: "Stop every optional task and forget them? The remote desktop and any app open in it close.",
    yes: "Yes, clean up",
  },
  reboot: {
    ask: "Restart the server? The web loses it for about a minute while it boots; the remote desktop stays off afterwards.",
    yes: "Yes, restart",
  },
};

const DONE: Record<Action, (n?: number) => string> = {
  sleep: (n) => `Light sleep: stopped ${n} task${n === 1 ? "" : "s"}.`,
  wake: (n) => `Woke up: started ${n} task${n === 1 ? "" : "s"}.`,
  cleanup: (n) => `Cleaned up: stopped ${n} task${n === 1 ? "" : "s"}.`,
  reboot: () => "Restarting… the page reconnects when the server is back.",
};

/** D-27: light sleep / wake up, clean up and restart for the Linux server. No shut down. */
export function PowerCard() {
  const power = usePolling<PowerStatus>("/api/power", POWER_MS);
  const [confirm, setConfirm] = useState<Exclude<Action, "wake"> | null>(null);
  const [busy, setBusy] = useState<Action | null>(null);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const data = power.data;
  const ready = !!data?.available && data.reachable && busy === null;

  const run = async (action: Action) => {
    setConfirm(null);
    setBusy(action);
    setResult(null);
    try {
      const body = action === "reboot" ? { confirm: "reboot" } : {};
      const res = await sendJson<{ stopped?: number; started?: number } | undefined>(
        "POST",
        `/api/power/${action}`,
        body,
        { timeoutMs: ACTION_TIMEOUT_MS },
      );
      setResult({ ok: true, text: DONE[action](res?.stopped ?? res?.started) });
    } catch (err) {
      setResult({ ok: false, text: toApiError(err).message });
    } finally {
      setBusy(null);
      power.retry();
    }
  };

  return (
    <Card
      title={`Power${data ? ` · ${data.label}` : ""}`}
      accent="s4"
      className="span-2"
      actions={<StatusBadge {...powerStatusView(data)} />}
    >
      <div className="stack">
        {data?.message && <p className="muted">{data.message}</p>}
        {data?.reachable && (
          <p className="muted">
            {power.loading ? "Refreshing…" : taskSummary(data)}
            {data.sleeping_since && ` · light sleep since ${formatDateTime(data.sleeping_since)}`}
          </p>
        )}
        <div className="desktop-actions">
          {data?.sleeping_since ? (
            <button className="btn btn-primary" disabled={!ready} onClick={() => run("wake")}>
              {busy === "wake" ? "Waking up…" : "Wake up"}
            </button>
          ) : (
            <button className="btn" disabled={!ready} onClick={() => setConfirm("sleep")}>
              {busy === "sleep" ? "Going to sleep…" : "Light sleep"}
            </button>
          )}
          <button className="btn" disabled={!ready} onClick={() => setConfirm("cleanup")}>
            {busy === "cleanup" ? "Cleaning up…" : "Clean up"}
          </button>
          <button className="btn btn-danger" disabled={!ready} onClick={() => setConfirm("reboot")}>
            {busy === "reboot" ? "Restarting…" : "Restart"}
          </button>
        </div>
        {confirm && (
          <div className="confirm" role="alertdialog" aria-label="Confirm">
            <p>{CONFIRM[confirm].ask}</p>
            <div className="desktop-actions">
              <button className={`btn ${confirm === "reboot" ? "btn-danger" : "btn-primary"}`} onClick={() => run(confirm)}>
                {CONFIRM[confirm].yes}
              </button>
              <button className="btn" onClick={() => setConfirm(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
        {result && <p className={result.ok ? "muted" : "error-text"}>{result.text}</p>}
        {power.error && !data && <p className="error-text">{power.error.message}</p>}
        {data?.reachable && (
          <details className="power-tasks">
            <summary className="muted small">Optional tasks (ssh, Tailscale, network and this app are never stopped)</summary>
            <ul>
              {data.tasks.map((t) => (
                <li key={`${t.scope}:${t.unit}`}>
                  <span className={`badge-dot ${t.active ? "dot-on" : ""}`} aria-hidden="true" />
                  <span className="mono">{t.unit}</span>
                  <span className="muted small">{t.active ? "running" : "stopped"}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </Card>
  );
}
