import { type ReactNode, useEffect, useRef, useState } from "react";
import type { DesktopStatus } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { type VncLink, useVnc } from "../hooks/useVnc";
import { desktopStatusView, desktopWsUrl } from "../lib/desktop";
import { StatusBadge } from "./StatusBadge";
import { VncToolbar } from "./VncToolbar";

const STATUS_MS = 3_000;

interface Props {
  actions?: ReactNode; // extra buttons at the end of the bar
  className?: string;
  setTitle?: boolean; // name the browser window after the desktop (pop-out window)
}

/** A self-connecting desktop: status, keys and the screen. Used by the pop-out window and the floating panel. */
export function LiveDesktop({ actions, className = "", setTitle = false }: Props) {
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
    if (setTitle) document.title = desktop ? `Desktop: ${desktop.label}` : "Desktop";
  }, [desktop, setTitle]);

  return (
    <div className={`live-desktop ${className}`} ref={frame}>
      <div className="popout-bar">
        <StatusBadge {...desktopStatusView(desktop?.status ?? null, vnc.state)} />
        <strong>{desktop?.label ?? "Desktop"}</strong>
        <VncToolbar rfb={vnc.rfb} frame={frame} connected={vnc.state === "connected"} />
        {vnc.state === "dropped" && url && (
          <button className="btn btn-sm" onClick={() => setLink({ url: desktopWsUrl(url) })}>
            Reconnect
          </button>
        )}
        {actions}
      </div>
      {(vnc.error || status.error) && <p className="error-text">{vnc.error ?? status.error?.message}</p>}
      {desktop && desktop.status !== "running" && <p className="muted">{desktop.message}</p>}
      {vnc.state !== "dropped" && <div className="vnc-screen popout-screen" ref={screen} />}
    </div>
  );
}
