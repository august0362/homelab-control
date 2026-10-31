import type { StatusView } from "../lib/status";

export function StatusBadge({ tone, label }: StatusView) {
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" aria-hidden="true" />
      {label}
    </span>
  );
}
