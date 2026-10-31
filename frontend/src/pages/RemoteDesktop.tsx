import { Card } from "../components/Card";
import { NotConfigured } from "../components/NotConfigured";

export function RemoteDesktop() {
  return (
    <Card title="Remote Desktop" accent="s1">
      <NotConfigured
        title="Remote desktop is not available yet"
        milestone="M3"
        detail="noVNC integration in M3 — requires the Dell. Nothing here is simulated."
      />
    </Card>
  );
}
