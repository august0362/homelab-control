import { useEffect, useRef, useState } from "react";
import type { DesktopStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { VncToolbar } from "../components/VncToolbar";
import { usePolling } from "../hooks/usePolling";
import { type VncLink, useVnc } from "../hooks/useVnc";
import { RETURN_MESSAGE, desktopStatusView, desktopWsUrl } from "../lib/desktop";

const STATUS_MS = 3_000;

/** The detached desktop: only the screen and its keys, in a window of its own (move it to another monitor). */
export function DesktopWindow() {
  const status = usePolling<DesktopStatus>("/api/desktop/status", STATUS_MS);
  const frame = useRef<HTMLDivElement>(null);
  const screen = useRef<HTMLDivElement>(null);
  const [link, setLink] = useState<VncLink | null>(null);
  const vnc = useVnc(screen, link);
  const desktop = status.data;
  const url = desktop?.connection_url ?? null;

  // Connect as soon as the desktop runs; after a drop the owner reconnects by hand.
  useEffect(() => {
    if (url && !link) setLink({ url: desktopWsUrl(url) });
  }, [url, link]);

  useEffect(() => {
    document.title = desktop ? `Desktop: ${desktop.label}` : "Desktop";
  }, [desktop]);

  const returnToPage = () => {
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(RETURN_MESSAGE, window.location.origin);
      setTimeout(() => window.close(), 150); // let the message land first
    } else {
      window.location.hash = "#/remote-desktop"; // opened on its own: become the full app
    }
  };

  return (
    <div className="popout" ref={frame}>
      <div className="popout-bar">
        <StatusBadge {...desktopStatusView(desktop?.status ?? null, vnc.state)} />
        <strong>{desktop?.label ?? "Desktop"}</strong>
        <VncToolbar rfb={vnc.rfb} frame={frame} connected={vnc.state === "connected"} />
        {vnc.state === "dropped" && url && (
          <button className="btn btn-sm" onClick={() => setLink({ url: desktopWsUrl(url) })}>
            Reconnect
          </button>
        )}
        <button className="btn btn-sm btn-primary popout-return" onClick={returnToPage}>
          Return to page
        </button>
      </div>
      {(vnc.error || status.error) && <p className="error-text">{vnc.error ?? status.error?.message}</p>}
      {desktop && desktop.status !== "running" && <p className="muted">{desktop.message}</p>}
      {vnc.state !== "dropped" && <div className="vnc-screen popout-screen" ref={screen} />}
    </div>
  );
}
