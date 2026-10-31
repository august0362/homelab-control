import { useCallback, useEffect, useState } from "react";

const KEY = "hlc.desktopFloating"; // per-browser preference; storage may be unavailable

export interface DesktopDock {
  floating: boolean; // the desktop floats over the app instead of sitting in the Remote Desktop page
  resumeInPage: boolean; // just docked: the page should reconnect on its own
  float: () => void;
  dock: () => void;
  resumed: () => void;
}

/** Docked (in the Remote Desktop page) or floating (a panel over every page). Lives in the Shell. */
export function useDesktopDock(): DesktopDock {
  const [floating, setFloating] = useState(() => {
    try {
      return localStorage.getItem(KEY) === "1";
    } catch {
      return false;
    }
  });
  const [resumeInPage, setResumeInPage] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, floating ? "1" : "0");
    } catch {
      // private window: the choice just lasts until reload
    }
  }, [floating]);

  const float = useCallback(() => setFloating(true), []);
  const dock = useCallback(() => {
    setFloating(false);
    setResumeInPage(true);
    window.location.hash = "#/remote-desktop";
  }, []);
  const resumed = useCallback(() => setResumeInPage(false), []);

  return { floating, resumeInPage, float, dock, resumed };
}
