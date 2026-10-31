import { Card } from "../components/Card";
import { formatBytes, formatDateTime } from "../lib/format";
import type { PageProps } from "../routes";

type Row = [label: string, value: string | number | null | undefined, mono?: boolean];

export function System({ system }: PageProps) {
  const info = system.data;
  if (!info) {
    return (
      <Card title="System">
        {system.error ? (
          <div className="stack">
            <p className="error-text">{system.error.message}</p>
            <button className="btn" onClick={system.retry}>
              Retry
            </button>
          </div>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </Card>
    );
  }

  const { os, hardware, app, device } = info;
  return (
    <div className="grid">
      <InfoTable
        title="Operating system"
        accent="s1"
        rows={[
          ["Name", os.pretty_name],
          ["System", os.system],
          ["Release", os.release],
          ["Version", os.version, true],
        ]}
      />
      <InfoTable
        title="Hardware"
        accent="s2"
        rows={[
          ["Hostname", hardware.hostname, true],
          ["Architecture", hardware.architecture, true],
          ["CPU", hardware.cpu_model],
          ["Cores (physical / logical)", `${hardware.cpu_physical ?? "—"} / ${hardware.cpu_logical ?? "—"}`, true],
          ["Memory", formatBytes(hardware.memory_total_bytes), true],
          ["Boot time", formatDateTime(hardware.boot_time), true],
        ]}
      />
      <InfoTable
        title="Device"
        accent="s3"
        rows={[
          ["Label", device.label],
          ["Role", device.role],
          ["Platform", device.platform],
          ["Type", device.device_type],
          ["ID", device.id, true],
        ]}
      />
      <InfoTable
        title="Application"
        accent="s4"
        rows={[
          ["Name", app.name],
          ["Version", app.version, true],
          ["Python", app.python, true],
          ["Fetched", formatDateTime(info.timestamp), true],
        ]}
      />
    </div>
  );
}

function InfoTable({ title, accent, rows }: { title: string; accent: "s1" | "s2" | "s3" | "s4"; rows: Row[] }) {
  return (
    <Card title={title} accent={accent}>
      <table className="info-table">
        <tbody>
          {rows.map(([label, value, mono]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td className={mono ? "mono" : undefined}>{value ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
