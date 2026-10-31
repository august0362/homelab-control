// Mirrors backend responses (docs/SPEC.md §4).

export interface Health {
  status: "ok";
  timestamp: string;
  version: string;
}

export interface Device {
  id: string;
  label: string;
  label_source: "custom" | "env" | "hostname"; // "custom" = renamed on the UI
  role: "dev" | "production";
  platform: string;
  device_type: string;
}

export interface Session {
  authenticated: boolean;
  configured: boolean; // false = no owner password set yet
  expires_at: string | null;
}

export type CapabilityStatus = "supported" | "unsupported" | "not_configured" | "requires_consent";

export interface Capability {
  status: CapabilityStatus;
  message: string | null;
}

export interface SystemInfo {
  timestamp: string;
  device: Device;
  os: { system: string; release: string; version: string; pretty_name: string; [key: string]: string | null };
  hardware: {
    hostname: string;
    architecture: string;
    cpu_model: string | null;
    cpu_logical: number | null;
    cpu_physical: number | null;
    memory_total_bytes: number;
    boot_time: string;
  };
  app: { name: string; version: string; python: string };
  capabilities: Record<string, Capability>;
}

// Every metric group says whether its data is real; data is null unless status is "ok".
export type MetricStatus = "ok" | "unsupported" | "unavailable" | "error";

export interface Metric<T> {
  status: MetricStatus;
  data: T | null;
  message: string | null;
}

export interface Metrics {
  timestamp: string;
  device: Device;
  cpu: Metric<{ usage_percent: number; per_core: number[]; logical: number | null; load_average: number[] | null }>;
  memory: Metric<{ total_bytes: number; used_bytes: number; available_bytes: number; percent: number }>;
  swap: Metric<{ total_bytes: number; used_bytes: number; free_bytes: number; percent: number }>;
  disk: Metric<{ path: string; total_bytes: number; used_bytes: number; free_bytes: number; percent: number }>;
  network: Metric<{ rx_bytes_per_sec: number; tx_bytes_per_sec: number }>;
  uptime_seconds: number | null;
  sensors: {
    temperature: Metric<{ sensor: string; label: string; current: number; high: number | null; critical: number | null }[]>;
    fans: Metric<{ sensor: string; label: string; rpm: number }[]>;
    battery: Metric<{ percent: number; secs_left: number | null }>;
    ac: Metric<{ online: boolean }>;
  };
}
