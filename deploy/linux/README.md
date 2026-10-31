# deploy/linux — Dell (Linux Mint)

Full deployment (backend service, Tailscale Serve) arrives in M6 — see docs/ARCHITECTURE.md §3, §8.
This folder holds the **remote desktop** setup from M3 (D-26) and the **power** permission (D-27).

## Remote desktop (M3)

A separate XFCE session in TigerVNC Xvnc (`:1`, 1280x720), started only on demand. It does not
use the laptop's own screen, and the Dell keeps booting to text mode (`multi-user.target`).

| File | Installed to | Role |
|---|---|---|
| `desktop-setup.sh` | — (run it once) | Installs TigerVNC (+ any missing XFCE piece), copies the two files below, turns on linger |
| `hlc-desktop-session.sh` | `~/.local/libexec/hlc-desktop-session` | Starts Xvnc on a Unix socket, then XFCE |
| `hlc-desktop.service` | `~/.config/systemd/user/` | The on/off switch (`systemctl --user`), no `[Install]`: never starts at boot |

Security model: Xvnc listens **only** on `/run/user/<uid>/hlc-vnc.sock` (mode 0600, owned by the
user), with `-rfbport -1` (no TCP port) and `-nolisten tcp` (no X11 TCP port). `SecurityTypes None`
is acceptable only because of that: nobody else on the machine can open the socket and the network
cannot reach it. The web app reaches it through its authenticated WebSocket bridge (M6: the backend
must run as the same user). `UseBlacklist=0`: all socket clients share one "address", so the
backend's status probes would otherwise get real viewers blacklisted.

### Install (owner, on the Dell)

```bash
# copy this folder to the Dell first, e.g. scp deploy/linux/* <dell>:hlc-deploy/
bash ~/hlc-deploy/desktop-setup.sh     # asks for the sudo password at most twice
```

Safe to run again. It does not reboot, touch SSH/Tailscale, the firewall or the boot target.

### Use

```bash
systemctl --user start hlc-desktop     # on
systemctl --user stop hlc-desktop      # off: closes XFCE and every app opened in it
systemctl --user status hlc-desktop
```

Staging from the ASUS (before M6): see the main README, "Remote desktop (staging)" — an SSH tunnel
`-L 127.0.0.1:5901:/run/user/<uid>/hlc-vnc.sock` plus `DESKTOP_VNC=tcp:127.0.0.1:5901`.

First start only: Mint shows its Welcome window and may ask "Authentication is required to create a
color managed device". Close the first, press **Cancel** on the second (it is the color daemon, not
needed here).

### Slow Wi-Fi (why the picture lags)

The Dell's Wi-Fi card is a Broadcom BCM4313 (`brcmsmac` driver). Measured 2026-10-31 it uploads only
~20–120 KB/s (downloads ~650 KB/s, ~3000 retries), over Tailscale or the plain LAN alike, and its
power saving is already off. The screen travels Dell → browser, so that upload is the limit.
`hlc-desktop-session.sh` keeps the picture cheap (no compositor, plain background: first picture
469 → 336 KiB, a menu settles in ~4 s instead of ~9 s) and noVNC uses compression level 6. The real
fix is a LAN cable (Intel 82579LM gigabit port). Switching the Wi-Fi driver remotely could cut the
only network link, so it is not done.

### Measured on the Dell (2026-10-31, i5-3337U, 3.7 GiB)

| State | RAM used | CPU |
|---|---|---|
| Desktop off | ~560 MiB | idle |
| Desktop on, nobody watching | ~890–950 MiB (+~330–390 MiB) | ~99 % idle, Xvnc ~1 % |
| Desktop on, viewer connected, mouse moving | ~940 MiB | ~99 % idle, Xvnc ~1–2 % |
| Desktop off again | ~570 MiB | idle |

### Rescue (always over SSH; the desktop never touches SSH or Tailscale)

```bash
systemctl --user stop hlc-desktop                       # normal stop
pkill -u "$USER" -f 'Xtigervnc :1'                      # if the stop hangs
systemctl --user reset-failed hlc-desktop               # clear a "failed" state
journalctl --user -u hlc-desktop -n 50 --no-pager       # why it failed
```

"Server is already active for display 1" with no Xvnc running (after a crash):
`rm -f /tmp/.X1-lock /tmp/.X11-unix/X1`, then start again.

### Undo

```bash
systemctl --user stop hlc-desktop
rm ~/.config/systemd/user/hlc-desktop.service ~/.local/libexec/hlc-desktop-session
systemctl --user daemon-reload
sudo loginctl disable-linger "$USER"                    # only if nothing else needs it
sudo apt-get remove tigervnc-standalone-server tigervnc-common   # optional
```

## Power: light sleep, clean up, restart (D-27)

The web app's Power card (System page) can stop optional background work and restart the Dell.
There is no shut down: nothing could switch the Dell back on (Wi-Fi cannot wake it, no LAN cable).

| File | Installed to | Role |
|---|---|---|
| `50-homelab-control.rules` | `/etc/polkit-1/rules.d/` | Lets **your user only** start/stop the 9 optional system services listed in it, and reboot, without a password. Never ssh, Tailscale, the network or power-off |
| `power-setup.sh` | — (run it once) | Fills in your user name and installs the rule (`sudo`, once) |

```bash
bash ~/hlc-deploy/power-setup.sh      # last line: "CanReboot without password: yes"
sudo rm /etc/polkit-1/rules.d/50-homelab-control.rules   # undo
```

User services (the desktop, audio) need no rule. The list of optional tasks lives in
`backend/app/services/power.py`; a test keeps it identical to the rule file.

Restart and the BIOS F1 prompt: the owner confirmed a normal restart does not stop at F1; that
prompt only appears after a power loss (weak CMOS battery). The desktop stays off after a restart.

### Notes for M6

- The backend must run as the same user as the desktop (to open the 0600 socket) and needs
  `XDG_RUNTIME_DIR=/run/user/<uid>` plus the user bus to call `systemctl --user`.
- Then set `DESKTOP_VNC=unix:/run/user/<uid>/hlc-vnc.sock` and `DESKTOP_UNIT=hlc-desktop.service`,
  and Start/Stop work from the web page.
