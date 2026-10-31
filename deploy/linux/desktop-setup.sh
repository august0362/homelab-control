#!/usr/bin/env bash
# M3: on-demand virtual desktop for HomeLab Control (D-26).
# Run on the Dell as your normal user (NOT root), from anywhere:
#   bash desktop-setup.sh
# Safe to run again. Asks for your sudo password at most twice (apt, linger).
# Changes: installs TigerVNC (plus any missing XFCE piece; Mint XFCE already has them),
# copies two files into your home, turns on linger. Does not reboot, touch SSH/Tailscale, the firewall or the boot target.
set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\n==> %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
  echo "Run as your normal user, not root (sudo is used only where needed)." >&2
  exit 1
fi

# The XFCE pieces the session needs; on Mint XFCE only TigerVNC is missing.
PKGS=(xfce4-session xfwm4 xfce4-panel xfdesktop4 xfce4-terminal dbus-x11 tigervnc-standalone-server)
step "1/5 Packages: ${PKGS[*]}"
missing=()
for p in "${PKGS[@]}"; do
  dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || missing+=("$p")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "Installing ${missing[*]} (no recommended extras, needs sudo)"
  sudo apt-get install -y --no-install-recommends "${missing[@]}"
else
  echo "Already installed."
fi

step "2/5 Xvnc must support a Unix socket (-rfbunixpath)"
help=$(Xvnc -help 2>&1 || true)
case "$help" in
  *rfbunixpath*) echo "OK" ;;
  *)
    echo "This Xvnc has no -rfbunixpath option. Stop here; see deploy/linux/README.md." >&2
    exit 1
    ;;
esac

step "3/5 Session script -> ~/.local/libexec/hlc-desktop-session"
install -D -m 0755 hlc-desktop-session.sh "$HOME/.local/libexec/hlc-desktop-session"

step "4/5 User unit -> ~/.config/systemd/user/hlc-desktop.service (never enabled at boot)"
install -D -m 0644 hlc-desktop.service "$HOME/.config/systemd/user/hlc-desktop.service"
systemctl --user daemon-reload

step "5/5 Linger: keep your systemd --user manager running without a login (needs sudo)"
if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" = "yes" ]; then
  echo "Already on."
else
  sudo loginctl enable-linger "$USER"
fi

printf '\nDone. Nothing is running yet.\n'
echo "Start: systemctl --user start hlc-desktop"
echo "Stop:  systemctl --user stop hlc-desktop"
