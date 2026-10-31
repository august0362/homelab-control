import { useEffect, useRef, useState } from "react";
import { POPOUT_PATH, RETURN_MESSAGE } from "../lib/desktop";

/** The desktop detached into its own browser window. `onReturn` runs when it comes back via its button. */
export function usePopout(onReturn: () => void) {
  const [win, setWin] = useState<Window | null>(null);
  const returnRef = useRef(onReturn);
  returnRef.current = onReturn;

  useEffect(() => {
    if (!win) return;
    const timer = setInterval(() => win.closed && setWin(null), 500); // closed with the window's own X
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== window.location.origin || e.source !== win || e.data !== RETURN_MESSAGE) return;
      setWin(null);
      returnRef.current();
    };
    window.addEventListener("message", onMessage);
    return () => {
      clearInterval(timer);
      window.removeEventListener("message", onMessage);
    };
  }, [win]);

  /** False when the browser blocked the pop-up. */
  const popOut = (): boolean => {
    const { pathname, search } = window.location;
    const w = window.open(`${pathname}${search}#${POPOUT_PATH}`, "hlc-desktop", "popup,width=1296,height=800");
    if (!w) return false;
    w.focus();
    setWin(w);
    return true;
  };

  const bringBack = () => {
    win?.close();
    setWin(null);
    returnRef.current();
  };

  return { detached: win !== null, popOut, focus: () => win?.focus(), bringBack };
}
