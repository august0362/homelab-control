import type { CapabilityStatus, Health } from "../api/types";
import type { PollState } from "../hooks/usePolling";
import { formatTime } from "./format";

// Status colors are reserved for state and always rendered with a text label.
export type Tone = "good" | "warn" | "crit" | "neutral";

export interface StatusView {
  tone: Tone;
  label: string;
}

export function connectionStatus(health: Pick<PollState<Health>, "data" | "error">): StatusView {
  if (health.error) return { tone: "crit", label: "Disconnected" };
  if (health.data) return { tone: "good", label: "Connected" };
  return { tone: "neutral", label: "Connecting…" };
}

const CAPABILITY: Record<CapabilityStatus, StatusView> = {
  supported: { tone: "good", label: "Supported" },
  requires_consent: { tone: "warn", label: "Requires consent" },
  not_configured: { tone: "neutral", label: "Not configured" },
  unsupported: { tone: "neutral", label: "Unsupported" },
};

export function capabilityStatus(status: CapabilityStatus): StatusView {
  return CAPABILITY[status] ?? { tone: "neutral", label: status };
}

export type Freshness = "connecting" | "live" | "stale" | "offline";

/** offline = latest request failed; stale = no success for 3 poll intervals (slow backend, throttled tab). */
export function freshness(
  poll: Pick<PollState<unknown>, "error" | "lastUpdated">,
  intervalMs: number,
  now = Date.now(),
): Freshness {
  if (poll.error) return "offline";
  if (!poll.lastUpdated) return "connecting";
  return now - poll.lastUpdated.getTime() > 3 * intervalMs ? "stale" : "live";
}

export function freshnessStatus(state: Freshness, lastUpdated: Date | null): StatusView {
  const since = lastUpdated ? ` · last updated ${formatTime(lastUpdated)}` : "";
  if (state === "live") return { tone: "good", label: "Live" };
  if (state === "stale") return { tone: "warn", label: `Stale${since}` };
  if (state === "offline") return { tone: "crit", label: `Offline${since}` };
  return { tone: "neutral", label: "Connecting…" };
}
