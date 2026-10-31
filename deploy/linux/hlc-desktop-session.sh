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
exec dbus-launch --exit-with-session startxfce4
