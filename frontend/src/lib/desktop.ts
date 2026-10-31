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

/** Floating desktop panel geometry (px, viewport coordinates). */
export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

const MARGIN = 8;
const MIN_W = 280;
const MIN_H = 200;
const BARS_H = 84; // title bar + key bar above the 16:9 screen

/** Bottom-right corner, 640 px wide (or the screen width minus margins on a phone). */
export function defaultBox(vw: number, vh: number): Box {
  const w = Math.min(640, vw - 2 * MARGIN);
  const h = Math.round((w * 9) / 16) + BARS_H;
  return clampBox({ x: vw - w - 2 * MARGIN, y: vh - h - 2 * MARGIN, w, h }, vw, vh);
}

/** Keep the panel at least MIN size and fully on screen, so its title bar can always be grabbed. */
export function clampBox(box: Box, vw: number, vh: number): Box {
  const w = Math.min(Math.max(box.w, MIN_W), vw - 2 * MARGIN);
  const h = Math.min(Math.max(box.h, MIN_H), vh - 2 * MARGIN);
  const x = Math.min(Math.max(box.x, MARGIN), Math.max(MARGIN, vw - w - MARGIN));
  const y = Math.min(Math.max(box.y, MARGIN), Math.max(MARGIN, vh - h - MARGIN));
  return { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) };
}
