import { type RefObject, useEffect, useRef, useState } from "react";
import type RFB from "@novnc/novnc";
import type { ViewerState } from "../lib/desktop";

/** One requested connection; a new object (even with the same url) reconnects. */
export interface VncLink {
  url: string;
}

/** Runs a noVNC viewer in `target` while `link` is set. noVNC is loaded on first use only. */
export function useVnc(target: RefObject<HTMLDivElement | null>, link: VncLink | null) {
  const [state, setState] = useState<ViewerState>("idle");
  const [error, setError] = useState<string | null>(null);
  const rfbRef = useRef<RFB | null>(null);

  useEffect(() => {
    if (!link) {
      setState("idle");
      return;
    }
    let closed = false;
    let rfb: RFB | null = null;
    setState("connecting");
    setError(null);

    const fail = (message: string) => {
      if (closed) return;
      setError(message);
      rfb?.disconnect();
    };

    import("@novnc/novnc")
      .then(({ default: Rfb }) => {
        if (closed || !target.current) return;
        rfb = new Rfb(target.current, link.url, { wsProtocols: ["binary"] });
        rfb.scaleViewport = true; // fit the container; resizes with it
        rfb.background = "transparent";
        rfb.addEventListener("connect", () => !closed && setState("connected"));
        rfb.addEventListener("disconnect", (e) => {
          rfb = rfbRef.current = null; // already closed: cleanup must not disconnect again
          if (closed) return;
          setState("dropped");
          if (!(e as CustomEvent<{ clean: boolean }>).detail.clean) {
            setError((prev) => prev ?? "Connection to the desktop was lost.");
          }
        });
        rfb.addEventListener("credentialsrequired", () =>
          fail("The VNC server asks for a password; this app expects the Unix-socket setup (D-26)."),
        );
        rfb.addEventListener("securityfailure", (e) => {
          const reason = (e as CustomEvent<{ reason?: string }>).detail.reason;
          fail(`VNC security negotiation failed${reason ? `: ${reason}` : ""}.`);
        });
        rfbRef.current = rfb;
      })
      .catch(() => {
        if (closed) return;
        setState("dropped");
        setError("Could not load the VNC viewer.");
      });

    return () => {
      closed = true;
      rfbRef.current = null;
      rfb?.disconnect();
    };
  }, [link, target]);

  return { state, error, rfb: rfbRef };
}
