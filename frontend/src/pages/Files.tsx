import { Card } from "../components/Card";
import { NotConfigured } from "../components/NotConfigured";

export function Files() {
  return (
    <Card title="Files" accent="s2">
      <NotConfigured
        title="File access is not available yet"
        milestone="M4"
        detail="Scoped file access in M4 (roots pending O-01)."
      />
    </Card>
  );
}
