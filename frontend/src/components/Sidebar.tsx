import type { SystemInfo } from "../api/types";
import { formatDuration } from "../lib/format";
import type { StatusView } from "../lib/status";
import { GROUPS, routes } from "../routes";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";

interface SidebarProps {
  currentPath: string;
  open: boolean;
  connection: StatusView;
  system: SystemInfo | null;
  onNavigate: () => void;
}

export function Sidebar({ currentPath, open, connection, system, onNavigate }: SidebarProps) {
  const bootTime = system ? Date.parse(system.hardware.boot_time) : NaN;
  const uptime = Number.isNaN(bootTime) ? null : Date.now() - bootTime;

  return (
    <aside id="sidebar" className={`sidebar ${open ? "open" : ""}`}>
      <nav aria-label="Main">
        {GROUPS.map((group) => (
          <div className="nav-group" key={group}>
            <p className="nav-group-title">{group}</p>
            {routes
              .filter((r) => r.group === group)
              .map((r) => (
                <a
                  key={r.path}
                  href={`#${r.path}`}
                  className="nav-link"
                  aria-current={r.path === currentPath ? "page" : undefined}
                  onClick={onNavigate}
                >
                  <Icon name={r.icon} />
                  {r.label}
                </a>
              ))}
          </div>
        ))}
      </nav>

      <div className="health-card">
        <p className="nav-group-title">Backend</p>
        <StatusBadge {...connection} />
        <dl>
          <dt>Uptime</dt>
          <dd className="mono">{formatDuration(uptime)}</dd>
        </dl>
      </div>
    </aside>
  );
}
