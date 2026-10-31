import { describe, expect, it } from "vitest";
import type { PowerStatus } from "../api/types";
import { powerStatusView, taskSummary } from "./power";

const base: PowerStatus = {
  available: true,
  reachable: true,
  label: "Dell",
  sleeping_since: null,
  tasks: [
    { unit: "docker.service", scope: "system", active: true },
    { unit: "cups.service", scope: "system", active: false },
  ],
  message: null,
};

describe("powerStatusView", () => {
  it("names each state", () => {
    expect(powerStatusView(null).label).toBe("Checking…");
    expect(powerStatusView({ ...base, available: false }).label).toBe("Not configured");
    expect(powerStatusView({ ...base, reachable: false })).toEqual({ tone: "crit", label: "Unreachable" });
    expect(powerStatusView({ ...base, sleeping_since: "2026-10-31T08:00:00+00:00" }).label).toBe("Light sleep");
    expect(powerStatusView(base)).toEqual({ tone: "good", label: "Awake" });
  });

  it("counts running tasks", () => {
    expect(taskSummary(base)).toBe("1 of 2 optional tasks running");
  });
});
