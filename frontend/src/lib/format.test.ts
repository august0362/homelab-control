import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { formatBytes, formatDateTime, formatDuration } from "./format";
import { capabilityStatus, connectionStatus } from "./status";

describe("formatBytes", () => {
  it("scales binary units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KiB");
    expect(formatBytes(16825643008)).toBe("15.7 GiB");
  });
  it("handles missing values", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(-1)).toBe("—");
  });
});

describe("formatDuration", () => {
  it("formats days, hours, minutes", () => {
    expect(formatDuration(30_000)).toBe("<1m");
    expect(formatDuration(5 * 60_000)).toBe("5m");
    expect(formatDuration(2 * 3_600_000)).toBe("2h 0m");
    expect(formatDuration(93_784_000)).toBe("1d 2h 3m");
  });
  it("rejects bad input", () => {
    expect(formatDuration(undefined)).toBe("—");
    expect(formatDateTime("not a date")).toBe("—");
  });
});

describe("status views", () => {
  it("derives connection state", () => {
    expect(connectionStatus({ data: null, error: null }).label).toBe("Connecting…");
    expect(connectionStatus({ data: { status: "ok", timestamp: "", version: "" }, error: null }).tone).toBe("good");
    expect(connectionStatus({ data: null, error: new ApiError("network_error", "x") }).label).toBe("Disconnected");
  });
  it("labels capabilities", () => {
    expect(capabilityStatus("not_configured")).toEqual({ tone: "neutral", label: "Not configured" });
    expect(capabilityStatus("supported").tone).toBe("good");
  });
});
