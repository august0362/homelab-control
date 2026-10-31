import type { ReactNode } from "react";
import type { Metric } from "../api/types";
import { type Accent, Card } from "../components/Card";
import { DeviceName } from "../components/DeviceName";
import { LineChart } from "../components/LineChart";
import { StatusBadge } from "../components/StatusBadge";
import { METRICS_MS } from "../hooks/useMetrics";
import { formatBytes, formatDuration, formatPercent, formatRate, formatTime } from "../lib/format";
import { HISTORY_SIZE } from "../lib/history";
import { capabilityStatus, connectionStatus, freshness, freshnessStatus } from "../lib/status";
import type { PageProps } from "../routes";

const WINDOW_MS = HISTORY_SIZE * METRICS_MS; // 10 min
const MAX_GAP_MS = METRICS_MS * 3;

export function Dashboard({ system, health, metrics }: PageProps) {
  const info = system.data;
  const m = metrics.data;
  const connection = connectionStatus(health);
  const fresh = freshness(metrics, METRICS_MS);
  const times = metrics.history.map((s) => s.t);

  return (
    <div className="grid">
      <div className="metrics-bar span-full">
        <StatusBadge {...freshnessStatus(fresh, metrics.lastUpdated)} />
        <span className="muted">
          Monitoring <strong className="text">{m?.device.label ?? info?.device.label ?? "—"}</strong>
          {m?.uptime_seconds != null && <> · Uptime {formatDuration(m.uptime_seconds * 1000)}</>}
        </span>
        {fresh === "offline" && metrics.error && <span className="muted">{metrics.error.message}</span>}
      </div>

      <div className={`kpi-row span-full ${fresh === "live" ? "" : "is-stale"}`}>
        <Kpi title="CPU" accent="s1" metric={m?.cpu}>
          {(d) => [formatPercent(d.usage_percent), `${d.logical ?? "?"} threads`]}
        </Kpi>
        <Kpi title="Memory" accent="s2" metric={m?.memory}>
          {(d) => [formatPercent(d.percent), `${formatBytes(d.used_bytes)} / ${formatBytes(d.total_bytes)}`]}
        </Kpi>
        <Kpi title="Disk" accent="s3" metric={m?.disk}>
          {(d) => [formatPercent(d.percent), `${d.path} · ${formatBytes(d.used_bytes)} / ${formatBytes(d.total_bytes)}`]}
        </Kpi>
        <Kpi title="Network" accent="s4" metric={m?.network}>
          {(d) => [`↓ ${formatRate(d.rx_bytes_per_sec)}`, `↑ ${formatRate(d.tx_bytes_per_sec)}`]}
        </Kpi>
      </div>

      <Card title="CPU & memory · last 10 min" accent="s1" className="span-2">
        <LineChart
          label="CPU and memory usage in percent over the last 10 minutes"
          times={times}
          series={[
            { label: "CPU", color: "var(--s1)", values: metrics.history.map((s) => s.cpu) },
            { label: "RAM", color: "var(--s2)", values: metrics.history.map((s) => s.mem) },
          ]}
          windowMs={WINDOW_MS}
          maxGapMs={MAX_GAP_MS}
          yMax={100}
          format={(v) => formatPercent(v)}
        />
      </Card>

      <Card title="Network · last 10 min" accent="s4">
        <LineChart
          label="Network receive and transmit rate over the last 10 minutes"
          times={times}
          series={[
            { label: "↓ In", color: "var(--s4)", values: metrics.history.map((s) => s.rx) },
            { label: "↑ Out", color: "var(--s3)", values: metrics.history.map((s) => s.tx) },
          ]}
          windowMs={WINDOW_MS}
          maxGapMs={MAX_GAP_MS}
          minTop={1024}
          format={formatRate}
          height={180}
        />
      </Card>

      <Card title="Sensors" accent="s3">
        {m ? (
          <dl className="kv sensors">
            <dt>Temperature</dt>
            <dd>
              <Reading metric={m.sensors.temperature}>
                {(d) => {
                  const hot = d.reduce((a, b) => (b.current > a.current ? b : a));
                  return `${hot.current.toFixed(0)} °C · ${hot.label}`;
                }}
              </Reading>
            </dd>
            <dt>Fans</dt>
            <dd>
              <Reading metric={m.sensors.fans}>{(d) => d.map((f) => `${f.rpm} RPM`).join(", ")}</Reading>
            </dd>
            <dt>Battery</dt>
            <dd>
              <Reading metric={m.sensors.battery}>
                {(d) =>
                  `${formatPercent(d.percent)}${d.secs_left != null ? ` · ${formatDuration(d.secs_left * 1000)} left` : ""}`
                }
              </Reading>
            </dd>
            <dt>AC power</dt>
            <dd>
              <Reading metric={m.sensors.ac}>{(d) => (d.online ? "Plugged in" : "On battery")}</Reading>
            </dd>
            <dt>Swap</dt>
            <dd>
              <Reading metric={m.swap}>
                {(d) => `${formatPercent(d.percent)} · ${formatBytes(d.used_bytes)} / ${formatBytes(d.total_bytes)}`}
              </Reading>
            </dd>
          </dl>
        ) : (
          <LoadState error={metrics.error?.message} onRetry={metrics.retry} />
        )}
      </Card>

      <Card title="Device" accent="s1">
        {info ? (
          <dl className="kv">
            <dt>Name</dt>
            <dd>
              <DeviceName
                device={info.device}
                onSaved={() => {
                  system.retry();
                  metrics.retry();
                }}
              />
            </dd>
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
            <dd className="mono">health 5s · metrics 2s</dd>
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
    </div>
  );
}

/** KPI tile: real value + detail when status is ok, otherwise N/A + the backend's reason. */
function Kpi<T>({
  title,
  accent,
  metric,
  children,
}: {
  title: string;
  accent: Accent;
  metric: Metric<T> | undefined;
  children: (data: T) => [string, string];
}) {
  const [value, detail] =
    metric?.status === "ok" && metric.data != null ? children(metric.data) : ["N/A", metric?.message ?? "Waiting for data…"];
  return (
    <Card title={title} accent={accent} className="kpi">
      <p className="kpi-value mono">{value}</p>
      <p className="kpi-detail muted">{detail}</p>
    </Card>
  );
}

/** Sensor value; unsupported/unavailable shows N/A, a failed reading is flagged as a fault. */
function Reading<T>({ metric, children }: { metric: Metric<T>; children: (data: T) => ReactNode }) {
  if (metric.status === "ok" && metric.data != null) return <span className="mono">{children(metric.data)}</span>;
  return (
    <span className="reading-na">
      {metric.status === "error" ? <StatusBadge tone="warn" label="Fault" /> : <span>N/A</span>}
      <span className="muted">{metric.message}</span>
    </span>
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
