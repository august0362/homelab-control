// Honest placeholder: a feature that is not built yet says so, never a fake demo.
export function NotConfigured({ title, milestone, detail }: { title: string; milestone: string; detail: string }) {
  return (
    <div className="not-configured" role="status">
      <span className="badge badge-neutral">
        <span className="badge-dot" aria-hidden="true" />
        Not configured ({milestone})
      </span>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
