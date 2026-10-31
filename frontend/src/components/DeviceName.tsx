import { type FormEvent, useState } from "react";
import { sendJson, toApiError } from "../api/client";
import type { Device } from "../api/types";
import { LABEL_MAX_LENGTH, validateLabel } from "../lib/label";
import { Icon } from "./Icon";

const SOURCE: Record<Device["label_source"], string> = {
  custom: "Renamed on this page",
  env: "Default from DEVICE_LABEL",
  hostname: "Default: hostname",
};

/** Device name with inline rename (D-24). onSaved refreshes everything that shows the name. */
export function DeviceName({ device, onSaved }: { device: Device; onSaved: () => void }) {
  const [draft, setDraft] = useState<string | null>(null); // null = not editing
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (label: string | null) => {
    setError(null);
    if (label !== null) {
      const checked = validateLabel(label);
      if ("error" in checked) return setError(checked.error);
      label = checked.label;
    }
    setBusy(true);
    try {
      await sendJson<Device>("PATCH", "/api/device", { label });
      setDraft(null);
      onSaved();
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void save(draft ?? "");
  };

  if (draft === null) {
    return (
      <span className="device-name">
        <span className="truncate" title={SOURCE[device.label_source]}>
          {device.label}
        </span>
        <button
          className="icon-btn icon-btn-sm"
          type="button"
          aria-label="Rename device"
          title="Rename"
          onClick={() => {
            setDraft(device.label);
            setError(null);
          }}
        >
          <Icon name="pencil" size={14} />
        </button>
      </span>
    );
  }

  return (
    <form className="rename" onSubmit={submit}>
      <input
        className="input"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && setDraft(null)}
        aria-label="Device name"
        aria-invalid={error ? true : undefined}
        autoFocus
      />
      <div className="rename-actions">
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </button>
        <button className="btn" type="button" disabled={busy} onClick={() => setDraft(null)}>
          Cancel
        </button>
        {device.label_source === "custom" && (
          <button className="btn" type="button" disabled={busy} onClick={() => void save(null)}>
            Reset to default
          </button>
        )}
      </div>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      <p className="muted rename-hint">1–{LABEL_MAX_LENGTH} characters. Shown in the top bar and on the dashboard.</p>
    </form>
  );
}
