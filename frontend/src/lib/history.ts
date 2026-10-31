import type { Metrics } from "../api/types";

// Chart history lives only in browser memory (FR-01.4): 10 min at one sample per 2 s.
export const HISTORY_SIZE = 300;

export interface Sample {
  t: number; // client receive time (ms); avoids clock skew between server and viewer
  cpu: number | null;
  mem: number | null;
  rx: number | null;
  tx: number | null;
}

export interface History {
  deviceId: string | null;
  samples: Sample[];
}

export const EMPTY_HISTORY: History = { deviceId: null, samples: [] };

export function toSample(m: Metrics, t: number): Sample {
  return {
    t,
    cpu: m.cpu.data?.usage_percent ?? null,
    mem: m.memory.data?.percent ?? null,
    rx: m.network.data?.rx_bytes_per_sec ?? null,
    tx: m.network.data?.tx_bytes_per_sec ?? null,
  };
}

/** Appends a sample, keeps the newest `size`, and starts over when the device changes. */
export function addSample(h: History, m: Metrics, t: number, size = HISTORY_SIZE): History {
  const kept = h.deviceId === m.device.id ? h.samples : [];
  if (kept.at(-1)?.t === t) return h;
  return { deviceId: m.device.id, samples: [...kept.slice(Math.max(0, kept.length - size + 1)), toSample(m, t)] };
}
