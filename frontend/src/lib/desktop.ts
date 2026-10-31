import type { DesktopState } from "../api/types";
import type { StatusView } from "./status";

/** This browser's own VNC connection, independent of the server-side desktop state. */
export type ViewerState = "idle" | "connecting" | "connected" | "dropped";

/** FR-02.4 badge. "Disconnected" = our viewer dropped while the server says running. */
export function desktopStatusView(status: DesktopState | null, viewer: ViewerState): StatusView {
  switch (status) {
    case "running":
      return viewer === "dropped" ? { tone: "warn", label: "Disconnected" } : { tone: "good", label: "Running" };
    case "starting":
      return { tone: "warn", label: "Starting…" };
    case "stopped":
      return { tone: "neutral", label: "Stopped" };
    case "error":
      return { tone: "crit", label: "Error" };
    case "not_configured":
      return { tone: "neutral", label: "Not configured" };
    default:
      return { tone: "neutral", label: "Checking…" };
  }
}

/** Same host as the page, so the session cookie and the Origin check both apply. */
export function desktopWsUrl(path: string, loc: Pick<Location, "protocol" | "host"> = window.location): string {
  return `${loc.protocol === "https:" ? "wss:" : "ws:"}//${loc.host}${path}`;
}

export const KEYSYM = { BackSpace: 0xff08, Tab: 0xff09, Return: 0xff0d, Escape: 0xff1b } as const;

/** X11 keysym for one typed character: Latin-1 maps 1:1, everything else is 0x01000000 + code point. */
export function keysymFor(ch: string): number | null {
  const cp = ch.codePointAt(0);
  if (cp === undefined || cp < 0x20 || (cp >= 0x7f && cp < 0xa0)) return null;
  return cp < 0x100 ? cp : 0x01000000 + cp;
}

/** The detached desktop window (hash route outside the app shell) and its "back to the page" message. */
export const POPOUT_PATH = "/desktop-window";
export const RETURN_MESSAGE = "hlc-desktop:return";
