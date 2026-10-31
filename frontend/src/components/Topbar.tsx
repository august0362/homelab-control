import type { SystemInfo } from "../api/types";
import { Icon } from "./Icon";

interface TopbarProps {
  system: SystemInfo | null;
  menuOpen: boolean;
  onToggleMenu: () => void;
}

export function Topbar({ system, menuOpen, onToggleMenu }: TopbarProps) {
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
      </div>
    </header>
  );
}
