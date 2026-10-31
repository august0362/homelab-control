import type { CapabilityStatus, Health } from "../api/types";
import type { PollState } from "../hooks/usePolling";

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
