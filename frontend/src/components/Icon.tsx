// Inline stroke icons (24px grid) — no icon library needed.
const PATHS = {
  dashboard: "M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z",
  monitor: "M3 4h18v12H3zM8 20h8M12 16v4",
  folder: "M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z",
  server: "M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  menu: "M4 6h16M4 12h16M4 18h16",
  cup: "M4 9h12v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5zM16 11h2a3 3 0 0 1 0 6h-2M8 3v3M12 3v3",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
