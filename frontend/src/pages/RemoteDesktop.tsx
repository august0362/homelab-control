import { useRef, useState } from "react";
import { sendJson, toApiError } from "../api/client";
import type { DesktopStatus } from "../api/types";
import { Card } from "../components/Card";
import { NotConfigured } from "../components/NotConfigured";
import { StatusBadge } from "../components/StatusBadge";
import { VncToolbar } from "../components/VncToolbar";
import { usePolling } from "../hooks/usePolling";
import { type VncLink, useVnc } from "../hooks/useVnc";
import { desktopStatusView, desktopWsUrl } from "../lib/desktop";

const STATUS_MS = 3_000; // polled on this page only
const ACTION_TIMEOUT_MS = 20_000; // systemctl may take up to 15 s

/** FR-02: the server's real GUI session through noVNC. Never a placeholder screen. */
export function RemoteDesktop() {
  const status = usePolling<DesktopStatus>("/api/desktop/status", STATUS_MS);
  const frame = useRef<HTMLDivElement>(null);
  const screen = useRef<HTMLDivElement>(null);
  const [link, setLink] = useState<VncLink | null>(null);
  const vnc = useVnc(screen, link);
  const [busy, setBusy] = useState<"start" | "stop" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const desktop = status.data;
  if (!desktop) {
    return (
      <Card title="Remote Desktop" accent="s1">
        {status.error ? <p className="error-text">{status.error.message}</p> : <p className="muted">Loading…</p>}
      </Card>
    );
  }

  if (desktop.status === "not_configured") {
    return (
      <Card title="Remote Desktop" accent="s1">
        <NotConfigured
          title="No remote desktop on this machine"
          detail={`${desktop.message} The desktop runs on the Dell; to reach it from here, follow README → “Remote desktop (staging)”. Nothing here is simulated.`}
        />
      </Card>
    );
  }

  const run = async (action: "start" | "stop") => {
    setBusy(action);
    setActionError(null);
    if (action === "stop") setLink(null);
    try {
      await sendJson("POST", `/api/desktop/${action}`, {}, { timeoutMs: ACTION_TIMEOUT_MS });
    } catch (err) {
      setActionError(toApiError(err).message);
    } finally {
      setBusy(null);
      status.retry();
    }
  };

  const url = desktop.connection_url;
  const state = desktop.status;
  const live = link !== null && vnc.state !== "dropped"; // a dropped viewer is hidden, never a frozen screen
  const viewers = `${desktop.viewers} viewer${desktop.viewers === 1 ? "" : "s"}`;

  return (
    <Card title="Remote Desktop" accent="s1" actions={<StatusBadge {...desktopStatusView(state, vnc.state)} />}>
      <div className="stack">
        <p>
          Desktop: <strong>{desktop.label}</strong> <span className="muted">· {viewers}</span>
        </p>
        <p className="muted">{desktop.message}</p>
        <div className="desktop-actions">
          <button
            className="btn btn-primary"
            disabled={!desktop.can_control || busy !== null || state === "running" || state === "starting"}
            onClick={() => run("start")}
          >
            {busy === "start" ? "Starting…" : "Start"}
          </button>
          <button
            className="btn"
            disabled={!desktop.can_control || busy !== null || state === "stopped"}
            onClick={() => run("stop")}
          >
            {busy === "stop" ? "Stopping…" : "Stop"}
          </button>
          {live ? (
            <button className="btn" onClick={() => setLink(null)}>
              Disconnect
            </button>
          ) : (
            <button className="btn" disabled={!url} onClick={() => url && setLink({ url: desktopWsUrl(url) })}>
              {vnc.state === "dropped" ? "Reconnect" : "Connect"}
            </button>
          )}
        </div>
        {!desktop.can_control && (
          <p className="muted small">
            Start/stop is managed on the server here (DESKTOP_UNIT not set): run{" "}
            <code>systemctl --user start hlc-desktop</code> over SSH.
          </p>
        )}
        {actionError && <p className="error-text">{actionError}</p>}
        {vnc.error && <p className="error-text">{vnc.error}</p>}
      </div>
      {live && (
        <div className="vnc-frame" ref={frame}>
          <VncToolbar rfb={vnc.rfb} frame={frame} connected={vnc.state === "connected"} />
          <div className="vnc-screen" ref={screen} />
          {vnc.state === "connecting" && <p className="vnc-overlay muted">Connecting…</p>}
        </div>
      )}
    </Card>
  );
}
