// Mirrors backend responses (docs/SPEC.md §4).

export interface Health {
  status: "ok";
  timestamp: string;
  version: string;
}

export interface Device {
  id: string;
  label: string;
  role: "dev" | "production";
  platform: string;
  device_type: string;
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
