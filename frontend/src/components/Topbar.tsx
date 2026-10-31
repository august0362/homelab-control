import type { SystemInfo } from "../api/types";
import { Icon } from "./Icon";

interface TopbarProps {
  system: SystemInfo | null;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onLogout?: () => void; // omitted when no login is needed (dev on this machine)
}

export function Topbar({ system, menuOpen, onToggleMenu, onLogout }: TopbarProps) {
  const device = system?.device;
  return (
    <header className="topbar">
      <button
        className="icon-btn menu-btn"
        onClick={onToggleMenu}
        aria-expanded={menuOpen}
        aria-controls="sidebar"
        aria-label="Toggle navigation"
      >
        <Icon name="menu" />
      </button>
      <div className="brand">
        <span className="brand-mark">
          <Icon name="cup" size={20} />
        </span>
        <span className="brand-name">HomeLab Control</span>
        {system && <span className="brand-version mono">v{system.app.version}</span>}
      </div>
      <div className="topbar-device">
        {device ? (
          <>
            <span className="topbar-label">
              Monitoring <strong>{device.label}</strong>
            </span>
            <span className={`role role-${device.role}`}>{device.role}</span>
          </>
        ) : (
          <span className="topbar-label muted">No device info</span>
        )}
        {onLogout && (
          <button className="btn logout-btn" onClick={onLogout} aria-label="Log out" title="Log out">
            <Icon name="logout" size={16} />
            <span className="logout-text">Log out</span>
          </button>
        )}
      </div>
    </header>
  );
}
