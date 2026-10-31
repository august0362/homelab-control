#!/bin/sh
# Started by hlc-desktop.service (M3, D-26): Xvnc :1 listening ONLY on a Unix socket
# (no VNC TCP port), then an XFCE session on it. Stopping the unit kills the whole
# cgroup: Xvnc, XFCE and every app opened inside the desktop.
set -eu

SOCK="${XDG_RUNTIME_DIR:?not set; run as a systemd --user unit}/hlc-vnc.sock"
rm -f "$SOCK"

# SecurityTypes None is acceptable ONLY because the socket is mode 0600 and owned by
# this user: nobody else on the machine can open it, and the network cannot reach it.
# UseBlacklist=0: every socket client shares one "address", so the backend's status
# probes (connect, read banner, close) would otherwise get real viewers blacklisted.
Xvnc :1 \
  -rfbunixpath "$SOCK" -rfbunixmode 0600 -rfbport -1 -localhost -nolisten tcp \
  -SecurityTypes None -UseBlacklist=0 \
  -geometry 1280x720 -depth 24 -desktop "HomeLab Control" &

i=0
while [ ! -S "$SOCK" ]; do
  i=$((i + 1))
  if [ "$i" -gt 50 ]; then
    echo "Xvnc did not create $SOCK within 10 s" >&2
    exit 1
  fi
  sleep 0.2
done

unset DBUS_SESSION_BUS_ADDRESS # XFCE gets its own session bus
export DISPLAY=:1 XDG_SESSION_TYPE=x11
eval "$(dbus-launch --sh-syntax --exit-with-x11)"

# The Dell's Wi-Fi (BCM4313) uploads slowly, so keep the picture cheap to send: no
# compositor effects (shadows, fades) and a plain background instead of the wallpaper.
# These are the user's XFCE settings; the laptop's own screen runs no desktop.
(
  i=0
  while ! pgrep -u "$(id -u)" -x xfdesktop >/dev/null && [ "$i" -lt 60 ]; do
    i=$((i + 1))
    sleep 0.5
  done
  sleep 2
  xfconf-query -c xfwm4 -p /general/use_compositing -s false
  for p in $(xfconf-query -c xfce4-desktop -l | grep '/image-style$'); do
    xfconf-query -c xfce4-desktop -p "$p" -s 0
  done
) &

exec startxfce4
