// Honest placeholder: a feature that is not built (or not set up here) says so, never a fake demo.
export function NotConfigured({ title, milestone, detail }: { title: string; milestone?: string; detail: string }) {
  return (
    <div className="not-configured" role="status">
      <span className="badge badge-neutral">
        <span className="badge-dot" aria-hidden="true" />
        Not configured{milestone && ` (${milestone})`}
      </span>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
