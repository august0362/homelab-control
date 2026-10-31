import { LiveDesktop } from "../components/LiveDesktop";
import { RETURN_MESSAGE } from "../lib/desktop";

/** The detached desktop: only the screen and its keys, in a window of its own (move it to another monitor). */
export function DesktopWindow() {
  const returnToPage = () => {
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(RETURN_MESSAGE, window.location.origin);
      setTimeout(() => window.close(), 150); // let the message land first
    } else {
      window.location.hash = "#/remote-desktop"; // opened on its own: become the full app
    }
  };

  return (
    <LiveDesktop
      className="popout"
      setTitle
      actions={
        <button className="btn btn-sm btn-primary popout-return" onClick={returnToPage}>
          Return to page
        </button>
      }
    />
  );
}
