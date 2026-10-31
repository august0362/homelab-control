import { type FormEvent, type RefObject, useEffect, useRef, useState } from "react";
import type RFB from "@novnc/novnc";
import { KEYSYM, keysymFor } from "../lib/desktop";

const SENTINEL = " "; // keeps Backspace firing on mobile keyboards when nothing was typed

interface Props {
  rfb: RefObject<RFB | null>;
  frame: RefObject<HTMLDivElement | null>;
  connected: boolean;
  focused: boolean; // focus mode: the screen has the keyboard
}

// Keyboard Lock (Chromium, fullscreen only): Alt+Tab, the Windows key, Ctrl+W... go to the desktop.
type KeyboardLock = { lock?: () => Promise<void>; unlock?: () => void };
const keyboardLock = () => (navigator as Navigator & { keyboard?: KeyboardLock }).keyboard;

/** Keys a phone or browser cannot send by itself, fullscreen, and an on-screen keyboard trigger. */
export function VncToolbar({ rfb, frame, connected, focused }: Props) {
  const input = useRef<HTMLTextAreaElement>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const sync = () => {
      const on = document.fullscreenElement === frame.current;
      setFullscreen(on);
      if (!on) keyboardLock()?.unlock?.();
    };
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, [frame]);

  const key = (keysym: number, code: string | null = null) => {
    rfb.current?.sendKey(keysym, code);
    rfb.current?.focus();
  };

  const toggleFullscreen = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else
      frame.current
        ?.requestFullscreen()
        .then(() => keyboardLock()?.lock?.())
        .then(() => rfb.current?.focus())
        .catch(() => {});
  };

  const openKeyboard = () => {
    const el = input.current;
    if (!el) return;
    el.value = SENTINEL;
    el.focus();
  };

  // Mobile keyboards often report key "Unidentified"; the input event carries the real text.
  const onInput = (e: FormEvent<HTMLTextAreaElement>) => {
    const ev = e.nativeEvent as InputEvent;
    if (ev.inputType === "deleteContentBackward") rfb.current?.sendKey(KEYSYM.BackSpace, "Backspace");
    else if (ev.inputType === "insertLineBreak") rfb.current?.sendKey(KEYSYM.Return, "Enter");
    else {
      for (const ch of ev.data ?? "") {
        const keysym = keysymFor(ch);
        if (keysym !== null) rfb.current?.sendKey(keysym, null);
      }
    }
    e.currentTarget.value = SENTINEL;
  };

  return (
    <div className="vnc-toolbar" role="toolbar" aria-label="Remote desktop keys">
      <button className="btn btn-sm" disabled={!connected} onClick={() => rfb.current?.sendCtrlAltDel()}>
        Ctrl+Alt+Del
      </button>
      <button className="btn btn-sm" disabled={!connected} onClick={() => key(KEYSYM.Escape, "Escape")}>
        Esc
      </button>
      <button className="btn btn-sm" disabled={!connected} onClick={() => key(KEYSYM.Tab, "Tab")}>
        Tab
      </button>
      <button className="btn btn-sm" disabled={!connected} onClick={openKeyboard}>
        Keyboard
      </button>
      {document.fullscreenEnabled && (
        <button className="btn btn-sm" onClick={toggleFullscreen}>
          {fullscreen ? "Exit fullscreen" : "Fullscreen"}
        </button>
      )}
      <span className={`focus-hint${focused ? " focus-on" : ""}`} role="status">
        {!connected
          ? ""
          : focused
            ? fullscreen
              ? "Focus mode: every key goes to the desktop · hold Esc to leave fullscreen"
              : "Focus mode: keys go to the desktop · click outside the screen to leave"
            : "Click the screen to control it"}
      </span>
      <textarea
        ref={input}
        className="vnc-keyboard-input"
        aria-label="Type into the remote desktop"
        autoCapitalize="off"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        onInput={onInput}
      />
    </div>
  );
}
