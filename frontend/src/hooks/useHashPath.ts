import { useEffect, useState } from "react";

// Hash routing ("#/files") needs no server-side fallback on any host.
const read = () => window.location.hash.replace(/^#/, "") || "/";

export function useHashPath(): string {
  const [path, setPath] = useState(read);
  useEffect(() => {
    const onChange = () => setPath(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return path;
}
