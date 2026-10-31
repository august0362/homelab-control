import { Card } from "../components/Card";
import { NotConfigured } from "../components/NotConfigured";
import { StatusBadge } from "../components/StatusBadge";
import { formatTime } from "../lib/format";
import { capabilityStatus, connectionStatus } from "../lib/status";
import type { PageProps } from "../routes";

export function Dashboard({ system, health }: PageProps) {
  const info = system.data;
  const connection = connectionStatus(health);

  return (
    <div className="grid">
      <Card title="Device" accent="s1">
        {info ? (
          <dl className="kv">
            <dt>Label</dt>
            <dd>{info.device.label}</dd>
            <dt>Hostname</dt>
            <dd className="mono">{info.hardware.hostname}</dd>
            <dt>OS</dt>
            <dd>{info.os.pretty_name}</dd>
            <dt>Platform</dt>
            <dd>{info.device.platform}</dd>
            <dt>Role</dt>
            <dd>{info.device.role}</dd>
            <dt>Device ID</dt>
            <dd className="mono truncate" title={info.device.id}>
              {info.device.id}
            </dd>
          </dl>
        ) : (
          <LoadState error={system.error?.message} onRetry={system.retry} />
        )}
      </Card>

      <Card title="Connection" accent="s2">
        <div className="stack">
          <StatusBadge {...connection} />
          <dl className="kv">
            <dt>Last check</dt>
            <dd className="mono">{formatTime(health.lastUpdated)}</dd>
            <dt>Backend</dt>
            <dd className="mono">{health.data ? `v${health.data.version}` : "—"}</dd>
            <dt>Poll</dt>
            <dd className="mono">every 5s</dd>
          </dl>
          {health.error && (
            <>
              <p className="error-text">{health.error.message}</p>
              <button className="btn" onClick={health.retry}>
                Retry now
              </button>
            </>
          )}
        </div>
      </Card>

      <Card title="Capabilities" accent="s3" className="span-2">
        {info ? (
          <ul className="cap-list">
            {Object.entries(info.capabilities).map(([name, cap]) => (
              <li key={name}>
                <span className="cap-name">{name}</span>
                <StatusBadge {...capabilityStatus(cap.status)} />
                <span className="muted cap-msg">{cap.message ?? ""}</span>
              </li>
            ))}
          </ul>
        ) : (
          <LoadState error={system.error?.message} onRetry={system.retry} />
        )}
      </Card>

      <Card title="Real-time metrics" accent="s4" className="span-2">
        <NotConfigured
          title="CPU, RAM, disk, network, uptime, sensors"
          milestone="M2"
          detail="Real-time metrics in M2. No placeholder numbers are shown until real readings exist."
        />
      </Card>
    </div>
  );
}

function LoadState({ error, onRetry }: { error?: string; onRetry: () => void }) {
  if (!error) return <p className="muted">Loading…</p>;
  return (
    <div className="stack">
      <p className="error-text">{error}</p>
      <button className="btn" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
