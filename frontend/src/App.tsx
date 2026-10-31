import { useEffect, useState } from "react";
import type { Health, SystemInfo } from "./api/types";
import { Icon } from "./components/Icon";
import { Sidebar } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";
import { Topbar } from "./components/Topbar";
import { useHashPath } from "./hooks/useHashPath";
import { usePolling } from "./hooks/usePolling";
import { connectionStatus } from "./lib/status";
import { findRoute } from "./routes";

const HEALTH_MS = 5_000;
const SYSTEM_MS = 60_000; // static info; refreshed rarely

export function App() {
  const path = useHashPath();
  const [menuOpen, setMenuOpen] = useState(false);
  const health = usePolling<Health>("/api/health", HEALTH_MS);
  const system = usePolling<SystemInfo>("/api/system", SYSTEM_MS);

  // Backend came back: reload device info now instead of waiting for the slow poll.
  const { retry: retrySystem, error: systemError } = system;
  useEffect(() => {
    if (health.data && systemError) retrySystem();
  }, [health.data, systemError, retrySystem]);

  const route = findRoute(path);
  const Page = route.component;
  const connection = connectionStatus(health);
  const info = system.data;
  const online = health.error ? "offline" : health.data ? "online" : "connecting";

  const refresh = () => {
    health.retry();
    system.retry();
  };

  return (
    <div className="app">
      <Topbar system={info} menuOpen={menuOpen} onToggleMenu={() => setMenuOpen((o) => !o)} />
      <Sidebar
        currentPath={route.path}
        open={menuOpen}
        connection={connection}
        system={info}
        onNavigate={() => setMenuOpen(false)}
      />
      <main className="main">
        <header className="page-head">
          <div>
            <h1>{route.label}</h1>
            <p className="page-sub">
              {info ? `${info.hardware.hostname} · ${info.os.pretty_name}` : "Unknown device"}
              {" · "}
              <span className={`online-${online}`}>{online}</span>
            </p>
          </div>
          <div className="page-actions">
            <StatusBadge {...connection} />
            <button className="btn" onClick={refresh}>
              <Icon name="refresh" size={16} />
              Refresh
            </button>
          </div>
        </header>
        <Page system={system} health={health} />
      </main>
    </div>
  );
}
