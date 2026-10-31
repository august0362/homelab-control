// Page registry: add a page here and it appears in the sidebar and router.
import type { ComponentType } from "react";
import type { Health, SystemInfo } from "./api/types";
import type { IconName } from "./components/Icon";
import type { DesktopDock } from "./hooks/useDesktopDock";
import type { MetricsState } from "./hooks/useMetrics";
import type { PollState } from "./hooks/usePolling";
import { Dashboard } from "./pages/Dashboard";
import { Files } from "./pages/Files";
import { RemoteDesktop } from "./pages/RemoteDesktop";
import { System } from "./pages/System";

export interface PageProps {
  system: PollState<SystemInfo>;
  health: PollState<Health>;
  metrics: MetricsState;
  dock: DesktopDock;
}

export interface PageRoute {
  path: string;
  label: string;
  group: (typeof GROUPS)[number];
  icon: IconName;
  component: ComponentType<PageProps>;
}

export const GROUPS = ["Overview", "Access", "System"] as const;

export const routes: PageRoute[] = [
  { path: "/", label: "Dashboard", group: "Overview", icon: "dashboard", component: Dashboard },
  { path: "/remote-desktop", label: "Remote Desktop", group: "Access", icon: "monitor", component: RemoteDesktop },
  { path: "/files", label: "Files", group: "Access", icon: "folder", component: Files },
  { path: "/system", label: "System", group: "System", icon: "server", component: System },
];

export function findRoute(path: string): PageRoute {
  return routes.find((r) => r.path === path) ?? routes[0];
}
