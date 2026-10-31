#!/usr/bin/env bash
# D-27: allow the web app's Light sleep, Clean up and Restart for your user only.
# Run on the Dell as your normal user (NOT root):  bash power-setup.sh
# Safe to run again. Asks for your sudo password once. Installs one file:
#   /etc/polkit-1/rules.d/50-homelab-control.rules
# Undo: sudo rm /etc/polkit-1/rules.d/50-homelab-control.rules
set -euo pipefail
cd "$(dirname "$0")"

if [ "$(id -u)" -eq 0 ]; then
  echo "Run as your normal user, not root (sudo is used only to install the rule)." >&2
  exit 1
fi
case "$USER" in
  *[!A-Za-z0-9._-]*|"") echo "Unexpected user name; stopping." >&2; exit 1 ;;
esac

echo "==> 1/2 Install the polkit rule for user $USER"
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
sed "s/@USER@/$USER/" 50-homelab-control.rules > "$tmp"
sudo install -m 0644 -o root -g root "$tmp" /etc/polkit-1/rules.d/50-homelab-control.rules

echo "==> 2/2 Check (no service is stopped, nothing restarts)"
sleep 1 # polkit reloads rules.d on change
reboot_ok=$(busctl call org.freedesktop.login1 /org/freedesktop/login1 \
  org.freedesktop.login1.Manager CanReboot | awk '{print $2}' | tr -d '"')
echo "CanReboot without password: $reboot_ok (expected: yes)"

echo
echo "Done. The web app can now use Light sleep, Wake up, Clean up and Restart."
