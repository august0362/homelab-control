import { type PointerEvent, useEffect, useRef, useState } from "react";
import { type Box, clampBox, defaultBox } from "../lib/desktop";
import { LiveDesktop } from "./LiveDesktop";

const KEY = "hlc.floatingBox";

function savedBox(): Box {
  const { innerWidth: vw, innerHeight: vh } = window;
  try {
    const box = JSON.parse(localStorage.getItem(KEY) ?? "null") as Box | null;
    if (box && [box.x, box.y, box.w, box.h].every(Number.isFinite)) return clampBox(box, vw, vh);
  } catch {
    // no storage or a broken value: start from the default
  }
  return defaultBox(vw, vh);
}

/** The desktop lifted out of the page: drag the title bar to move, the corner to resize; stays over every page. */
export function FloatingDesktop({ onDock }: { onDock: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState(savedBox);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(box));
    } catch {
      // keep it for this page load only
    }
  }, [box]);

  // Corner resize is native CSS; mirror the new size into state. Window resize re-clamps.
  useEffect(() => {
    const el = panel.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      setBox((b) => (b.w === w && b.h === h ? b : clampBox({ ...b, w, h }, window.innerWidth, window.innerHeight)));
    });
    observer.observe(el);
    const onWindow = () => setBox((b) => clampBox(b, window.innerWidth, window.innerHeight));
    window.addEventListener("resize", onWindow);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", onWindow);
    };
  }, []);

  const startDrag = (e: PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button, input, label")) return;
    const handle = e.currentTarget;
    const start = { px: e.clientX, py: e.clientY, x: box.x, y: box.y };
    handle.setPointerCapture(e.pointerId);
    const move = (ev: globalThis.PointerEvent) =>
      setBox((b) =>
        clampBox(
          { ...b, x: start.x + ev.clientX - start.px, y: start.y + ev.clientY - start.py },
          window.innerWidth,
          window.innerHeight,
        ),
      );
    const stop = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", stop);
      handle.removeEventListener("pointercancel", stop);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", stop);
    handle.addEventListener("pointercancel", stop);
  };

  return (
    <div
      className="floating-desktop"
      ref={panel}
      role="dialog"
      aria-label="Floating remote desktop"
      style={{ left: box.x, top: box.y, width: box.w, height: box.h }}
    >
      <div className="floating-head" onPointerDown={startDrag}>
        <span className="floating-grip" aria-hidden="true">
          ⠿
        </span>
        <span className="muted small">Remote desktop</span>
        <label className="dock-toggle">
          <input type="checkbox" checked={false} onChange={onDock} />
          Docked in page
        </label>
      </div>
      <div className="floating-body">
        <LiveDesktop />
      </div>
    </div>
  );
}
