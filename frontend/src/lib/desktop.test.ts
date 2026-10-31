import { describe, expect, it } from "vitest";
import { clampBox, defaultBox, desktopStatusView, desktopWsUrl, keysymFor } from "./desktop";

describe("desktopStatusView", () => {
  it("maps every server state", () => {
    expect(desktopStatusView("not_configured", "idle").label).toBe("Not configured");
    expect(desktopStatusView("stopped", "idle").label).toBe("Stopped");
    expect(desktopStatusView("starting", "idle")).toEqual({ tone: "warn", label: "Starting…" });
    expect(desktopStatusView("error", "idle").tone).toBe("crit");
    expect(desktopStatusView(null, "idle").label).toBe("Checking…");
  });

  it("is Disconnected only when our viewer dropped while the server runs", () => {
    expect(desktopStatusView("running", "connected")).toEqual({ tone: "good", label: "Running" });
    expect(desktopStatusView("running", "idle").label).toBe("Running");
    expect(desktopStatusView("running", "dropped")).toEqual({ tone: "warn", label: "Disconnected" });
    expect(desktopStatusView("stopped", "dropped").label).toBe("Stopped");
  });
});

describe("desktopWsUrl", () => {
  it("follows the page scheme and host", () => {
    expect(desktopWsUrl("/api/desktop/ws", { protocol: "http:", host: "127.0.0.1:5173" })).toBe(
      "ws://127.0.0.1:5173/api/desktop/ws",
    );
    expect(desktopWsUrl("/api/desktop/ws", { protocol: "https:", host: "dell.example.ts.net" })).toBe(
      "wss://dell.example.ts.net/api/desktop/ws",
    );
  });
});

describe("keysymFor", () => {
  it("maps Latin-1 directly and other characters to Unicode keysyms", () => {
    expect(keysymFor("a")).toBe(0x61);
    expect(keysymFor("é")).toBe(0xe9);
    expect(keysymFor("ệ")).toBe(0x01001ec7);
    expect(keysymFor("😀")).toBe(0x0101f600);
  });

  it("ignores control characters", () => {
    expect(keysymFor("\n")).toBeNull();
    expect(keysymFor("")).toBeNull();
  });
});

describe("floating panel geometry", () => {
  it("starts bottom-right and fits a phone", () => {
    expect(defaultBox(1400, 900)).toEqual({ x: 744, y: 440, w: 640, h: 444 });
    const phone = defaultBox(360, 800);
    expect(phone.w).toBe(344);
    expect(phone.x).toBe(8);
  });

  it("keeps the panel on screen and above its minimum size", () => {
    expect(clampBox({ x: -50, y: -20, w: 100, h: 50 }, 1400, 900)).toEqual({ x: 8, y: 8, w: 280, h: 200 });
    expect(clampBox({ x: 1300, y: 850, w: 640, h: 400 }, 1400, 900)).toEqual({ x: 752, y: 492, w: 640, h: 400 });
    expect(clampBox({ x: 0, y: 0, w: 5000, h: 5000 }, 1400, 900)).toEqual({ x: 8, y: 8, w: 1384, h: 884 });
  });
});
