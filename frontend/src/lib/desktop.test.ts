import { describe, expect, it } from "vitest";
import { desktopStatusView, desktopWsUrl, keysymFor } from "./desktop";

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
