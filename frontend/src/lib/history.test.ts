import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import type { Metrics } from "../api/types";
import { formatPercent, formatRate } from "./format";
import { addSample, EMPTY_HISTORY } from "./history";
import { freshness, freshnessStatus } from "./status";

const unavailable = { status: "unavailable", data: null, message: "x" } as const;

function metrics(deviceId: string, cpu: number | null): Metrics {
  return {
    timestamp: "",
    device: { id: deviceId, label: "", label_source: "hostname", role: "dev", platform: "windows", device_type: "computer" },
    cpu:
      cpu == null
        ? { status: "error", data: null, message: "boom" }
        : { status: "ok", data: { usage_percent: cpu, per_core: [], logical: 1, load_average: null }, message: null },
    memory: { status: "ok", data: { total_bytes: 4, used_bytes: 2, available_bytes: 2, percent: 50 }, message: null },
    swap: unavailable,
    disk: unavailable,
    network: unavailable,
    uptime_seconds: 1,
    sensors: { temperature: unavailable, fans: unavailable, battery: unavailable, ac: unavailable },
  };
}

describe("history buffer", () => {
  it("keeps only the newest samples", () => {
    let h = EMPTY_HISTORY;
    for (let i = 0; i < 5; i++) h = addSample(h, metrics("a", i), i * 2000, 3);
    expect(h.samples.map((s) => s.cpu)).toEqual([2, 3, 4]);
    expect(h.samples.map((s) => s.t)).toEqual([4000, 6000, 8000]);
  });

  it("keeps missing values as null, never 0", () => {
    const h = addSample(EMPTY_HISTORY, metrics("a", null), 1);
    expect(h.samples[0]).toEqual({ t: 1, cpu: null, mem: 50, rx: null, tx: null });
  });

  it("starts over when the device changes and ignores duplicates", () => {
    let h = addSample(EMPTY_HISTORY, metrics("a", 10), 1);
    h = addSample(h, metrics("a", 11), 1);
    expect(h.samples).toHaveLength(1);
    h = addSample(h, metrics("b", 20), 2);
    expect(h).toEqual({ deviceId: "b", samples: [expect.objectContaining({ cpu: 20 })] });
  });
});

describe("freshness", () => {
  const at = new Date(10_000);

  it("is live, then stale after 3 missed intervals", () => {
    expect(freshness({ error: null, lastUpdated: at }, 2000, 15_000)).toBe("live");
    expect(freshness({ error: null, lastUpdated: at }, 2000, 16_001)).toBe("stale");
  });

  it("is offline on error and connecting before the first answer", () => {
    expect(freshness({ error: new ApiError("network_error", "x"), lastUpdated: at }, 2000, 10_500)).toBe("offline");
    expect(freshness({ error: null, lastUpdated: null }, 2000)).toBe("connecting");
  });

  it("labels stale and offline with the last update time", () => {
    expect(freshnessStatus("stale", at).label).toMatch(/^Stale · last updated /);
    expect(freshnessStatus("offline", null)).toEqual({ tone: "crit", label: "Offline" });
  });
});

describe("rate and percent", () => {
  it("formats", () => {
    expect(formatRate(1536)).toBe("1.5 KiB/s");
    expect(formatRate(null)).toBe("—");
    expect(formatPercent(41.84)).toBe("42%");
    expect(formatPercent(null)).toBe("—");
  });
});
