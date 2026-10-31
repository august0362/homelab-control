import type { PowerStatus } from "../api/types";
import type { StatusView } from "./status";

export function powerStatusView(power: PowerStatus | null): StatusView {
  if (!power) return { tone: "neutral", label: "Checking…" };
  if (!power.available) return { tone: "neutral", label: "Not configured" };
  if (!power.reachable) return { tone: "crit", label: "Unreachable" };
  if (power.sleeping_since) return { tone: "warn", label: "Light sleep" };
  return { tone: "good", label: "Awake" };
}

/** "3 of 14 optional tasks running" */
export function taskSummary(power: PowerStatus): string {
  const running = power.tasks.filter((t) => t.active).length;
  return `${running} of ${power.tasks.length} optional tasks running`;
}
