import { useEffect, useRef, useState } from "react";
import { sendJson, toApiError } from "../api/client";
import type { DesktopStatus } from "../api/types";
import { Card } from "../components/Card";
import { DeviceName } from "../components/DeviceName";
import { NotConfigured } from "../components/NotConfigured";
import { StatusBadge } from "../components/StatusBadge";
import { VncToolbar } from "../components/VncToolbar";
import { usePolling } from "../hooks/usePolling";
import { usePopout } from "../hooks/usePopout";
import { type VncLink, useVnc } from "../hooks/useVnc";
import { desktopStatusView, desktopWsUrl } from "../lib/desktop";
import type { PageProps } from "../routes";

const STATUS_MS = 3_000; // polled on this page only
const ACTION_TIMEOUT_MS = 20_000; // systemctl may take up to 15 s

/** FR-02: the server's real GUI session through noVNC. Never a placeholder screen. */
export function RemoteDesktop({ dock }: PageProps) {
  const status = usePolling<DesktopStatus>("/api/desktop/status", STATUS_MS);
  const frame = useRef<HTMLDivElement>(null);
  const screen = useRef<HTMLDivElement>(null);
  const [link, setLink] = useState<VncLink | null>(null);
  const vnc = useVnc(screen, link);
  const [busy, setBusy] = useState<"start" | "stop" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const popout = usePopout(() => {
    const url = status.data?.connection_url; // back from the window: show it here again
    if (url) setLink({ url: desktopWsUrl(url) });
  });

  // Just docked from the floating panel: show it here right away.
  const runningUrl = status.data?.connection_url ?? null;
  const { resumeInPage, resumed } = dock;
  useEffect(() => {
    if (!resumeInPage || !runningUrl) return;
    resumed();
    setLink({ url: desktopWsUrl(runningUrl) });
  }, [resumeInPage, runningUrl, resumed]);

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

  const popOut = () => {
    setActionError(null);
    if (popout.popOut()) setLink(null); // one viewer at a time: the window takes over
    else setActionError("The browser blocked the pop-up window. Allow pop-ups for this site and try again.");
  };

  const floatOut = () => {
    setLink(null); // one viewer at a time: the floating panel takes over
    dock.float();
  };
  const viewers = `${desktop.viewers} viewer${desktop.viewers === 1 ? "" : "s"}`;

  return (
    <Card title="Remote Desktop" accent="s1" actions={<StatusBadge {...desktopStatusView(state, vnc.state)} />}>
      <div className="stack">
        <div className="desktop-name">
          <span>Desktop:</span>
          <strong>
            <DeviceName
              label={desktop.label}
              source={desktop.label_source}
              endpoint="/api/server"
              hint="The server's name on Remote Desktop and the Power card."
              onSaved={status.retry}
            />
          </strong>
          <span className="muted">· {viewers}</span>
        </div>
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
          {dock.floating ? null : popout.detached ? (
            <>
              <button className="btn" onClick={popout.focus}>
                Show window
              </button>
              <button className="btn" onClick={popout.bringBack}>
                Return to page
              </button>
            </>
          ) : (
            <>
              {live ? (
                <button className="btn" onClick={() => setLink(null)}>
                  Disconnect
                </button>
              ) : (
                <button className="btn" disabled={!url} onClick={() => url && setLink({ url: desktopWsUrl(url) })}>
                  {vnc.state === "dropped" ? "Reconnect" : "Connect"}
                </button>
              )}
              <button className="btn" disabled={!url} onClick={popOut} title="Open the desktop in its own window">
                Pop out
              </button>
            </>
          )}
        </div>
        <label className="dock-toggle">
          <input
            type="checkbox"
            checked={!dock.floating}
            disabled={popout.detached}
            onChange={(e) => (e.target.checked ? dock.dock() : floatOut())}
          />
          Docked in page <span className="muted small">(untick to float it over the app)</span>
        </label>
        {dock.floating && <p className="muted">The desktop floats over the app. Tick “Docked in page” to bring it back.</p>}
        {popout.detached && <p className="muted">The desktop is open in a separate window.</p>}
        {!desktop.can_control && (
          <p className="muted small">
            Start/stop is managed on the server here (DESKTOP_UNIT not set): run{" "}
            <code>systemctl --user start hlc-desktop</code> over SSH.
          </p>
        )}
        {actionError && <p className="error-text">{actionError}</p>}
        {vnc.error && <p className="error-text">{vnc.error}</p>}
      </div>
      {live && !dock.floating && (
        <div className={`vnc-frame${vnc.focused ? " vnc-focused" : ""}`} ref={frame}>
          <VncToolbar rfb={vnc.rfb} frame={frame} connected={vnc.state === "connected"} focused={vnc.focused} />
          <div className="vnc-screen" ref={screen} />
          {vnc.state === "connecting" && <p className="vnc-overlay muted">Connecting…</p>}
        </div>
      )}
    </Card>
  );
}
