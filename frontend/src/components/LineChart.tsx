// Hand-written SVG time-series chart: one y-axis, 2px lines, gaps for missing data,
// legend + direct labels, hover crosshair with tooltip. Only what the dashboard needs.
import { type PointerEvent, useEffect, useRef, useState } from "react";

export interface Series {
  label: string;
  color: string; // a series token, e.g. "var(--s1)"
  values: (number | null)[];
}

interface LineChartProps {
  label: string; // accessible name
  times: number[]; // ms, ascending, same length as every series
  series: Series[];
  windowMs: number;
  maxGapMs: number; // longer gaps (offline) break the line instead of bridging it
  format: (v: number) => string;
  yMax?: number; // fixed top (percent); otherwise the next power of two above the data
  minTop?: number;
  height?: number;
}

const PAD = { top: 10, bottom: 24 };
const CHAR_W = 7; // mono 11–12px; margins grow with the longest label
const NARROW = 480; // below this the legend alone identifies series

const clock = (t: number) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

export function LineChart({ label, times, series, windowMs, maxGapMs, format, yMax, minTop = 1, height = 220 }: LineChartProps) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState<number | null>(null);

  const end = times.at(-1) ?? 0;
  const start = end - windowMs;
  const dataMax = Math.max(minTop, ...series.flatMap((s) => s.values.filter((v): v is number => v != null)));
  const top = yMax ?? 2 ** Math.ceil(Math.log2(dataMax));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * top);
  const lastOf = (s: Series) => s.values.at(-1);
  const direct = width >= NARROW;
  const longest = (texts: string[]) => Math.max(0, ...texts.map((t) => t.length)) * CHAR_W;
  const pad = {
    ...PAD,
    left: longest(ticks.map(format)) + 12,
    right: direct
      ? longest(series.map((s) => (lastOf(s) == null ? "" : `${s.label} ${format(lastOf(s)!)}`))) + 20
      : 12,
  };
  const iw = Math.max(0, width - pad.left - pad.right);
  const ih = height - pad.top - pad.bottom;
  const x = (t: number) => pad.left + ((t - start) / windowMs) * iw;
  const y = (v: number) => pad.top + ih - (Math.min(v, top) / top) * ih;

  const path = (values: (number | null)[]) => {
    let d = "";
    let prev: number | null = null;
    values.forEach((v, i) => {
      const t = times[i];
      if (v == null || t < start) {
        prev = null;
        return;
      }
      d += `${prev != null && t - prev <= maxGapMs ? "L" : "M"}${x(t).toFixed(1)},${y(v).toFixed(1)}`;
      prev = t;
    });
    return d;
  };

  // Direct labels at each series' latest value, nudged apart so they never overlap.
  const ends = series
    .map((s) => ({ s, v: lastOf(s) }))
    .filter((e): e is { s: Series; v: number } => e.v != null)
    .map((e) => ({ ...e, y: y(e.v) }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 15);

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const px = e.clientX - e.currentTarget.getBoundingClientRect().left;
    let best = -1;
    for (let i = 0; i < times.length; i++) {
      if (times[i] >= start && (best < 0 || Math.abs(x(times[i]) - px) < Math.abs(x(times[best]) - px))) best = i;
    }
    setHover(best < 0 ? null : best);
  };

  const hx = hover != null ? x(times[hover]) : 0;

  return (
    <div className="chart">
      <ul className="legend">
        {series.map((s) => (
          <li key={s.label}>
            <span className="swatch" style={{ background: s.color }} />
            {s.label}
          </li>
        ))}
      </ul>
      <div className="chart-plot" ref={ref} style={{ height }}>
        {times.length === 0 ? (
          <p className="chart-empty muted">Waiting for the first samples…</p>
        ) : (
          width > 0 && (
            <svg
              width={width}
              height={height}
              role="img"
              aria-label={label}
              onPointerMove={onMove}
              onPointerLeave={() => setHover(null)}
            >
              {ticks.map((v) => (
                <g key={v}>
                  <line className="chart-grid" x1={pad.left} x2={pad.left + iw} y1={y(v)} y2={y(v)} />
                  <text className="chart-axis" x={pad.left - 8} y={y(v)} dy="0.32em" textAnchor="end">
                    {format(v)}
                  </text>
                </g>
              ))}
              {[start, start + windowMs / 2, end].map((t, i) => (
                <text
                  key={i}
                  className="chart-axis"
                  x={x(t)}
                  y={height - 6}
                  textAnchor={(["start", "middle", "end"] as const)[i]}
                >
                  {clock(t)}
                </text>
              ))}
              {series.map((s) => (
                <path key={s.label} d={path(s.values)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" />
              ))}
              {ends.map(({ s, v, y: ly }) => (
                <g key={s.label}>
                  <circle className="chart-dot" cx={x(end)} cy={y(v)} r={4} fill={s.color} />
                  {direct && (
                    <text className="chart-label" x={pad.left + iw + 10} y={ly} dy="0.32em">
                      {s.label} {format(v)}
                    </text>
                  )}
                </g>
              ))}
              {hover != null && (
                <g>
                  <line className="chart-crosshair" x1={hx} x2={hx} y1={pad.top} y2={pad.top + ih} />
                  {series.map((s) => {
                    const v = s.values[hover];
                    return v == null ? null : (
                      <circle key={s.label} className="chart-dot" cx={hx} cy={y(v)} r={4} fill={s.color} />
                    );
                  })}
                </g>
              )}
            </svg>
          )
        )}
        {hover != null && (
          <div
            className="chart-tip"
            style={hx > width / 2 ? { right: width - hx + 12 } : { left: hx + 12 }}
          >
            <p className="mono">{new Date(times[hover]).toLocaleTimeString()}</p>
            {series.map((s) => (
              <p key={s.label}>
                <span className="swatch" style={{ background: s.color }} />
                {s.label} <strong className="mono">{s.values[hover] == null ? "N/A" : format(s.values[hover]!)}</strong>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
