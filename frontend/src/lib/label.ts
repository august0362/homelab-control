// Mirrors backend validate_label (D-24) so obvious mistakes show before a request.
// The backend stays the authority; its message is shown if it still rejects.
export const LABEL_MAX_LENGTH = 40;

export function validateLabel(raw: string): { label: string } | { error: string } {
  const label = raw.trim();
  if (!label) return { error: "Name cannot be empty." };
  if ([...label].length > LABEL_MAX_LENGTH) return { error: `Name must be at most ${LABEL_MAX_LENGTH} characters.` };
  if (/[\p{Cc}\p{Zl}\p{Zp}]/u.test(label)) return { error: "Name cannot contain control characters or line breaks." };
  return { label };
}
