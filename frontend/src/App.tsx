import { useSession } from "./hooks/useSession";
import { Login } from "./pages/Login";
import { Shell } from "./Shell";

/** Session gate (D-23): Login until the backend confirms a session (or says none is needed, D-25), then the app shell. */
export function App() {
  const { session, error, check, signOut } = useSession();
  if (session?.authenticated) return <Shell onSignedOut={signOut} canLogout={session.login_required} />;
  if (!session && !error) return <p className="splash muted">Loading…</p>;
  return <Login configured={session?.configured ?? true} notice={error?.message} onSignedIn={check} />;
}
