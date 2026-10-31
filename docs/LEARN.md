# HomeLab Control: toàn bộ ngữ cảnh để học và để giao việc

> Cập nhật: 2026-10-31, sau M3. File này giải thích dự án bằng lời dễ hiểu. Phần cuối (§14) là **prompt dán được** cho một phiên AI mới.
> Khi có mâu thuẫn, docs gốc thắng: `SPEC.md` → `ARCHITECTURE.md` → `MILESTONES.md` → `CONTEXT.md`.
> File này không chứa mật khẩu, IP, tên tailnet, username hay hostname, và không bao giờ được chứa.

---

## 1. Dự án là gì?

Một **trang web riêng** để chủ nhà (owner) theo dõi và điều khiển một laptop Dell cũ, đang dùng làm server tại nhà 24/7.

- Mở từ **ASUS** (máy viết code), **điện thoại Xiaomi** hoặc **tablet Samsung**, qua mạng riêng **Tailscale**. Không public ra Internet.
- Có 4 trang: **Dashboard** (thông số realtime), **Remote Desktop** (điều khiển màn hình Dell), **Files** (M4), **System** (M5).
- Về sau (M7), web còn quản lý **chính điện thoại/tablet** như thiết bị đích, qua app Android có sự đồng ý của chủ máy.

Nguyên tắc vàng: **viết và thử trên ASUS trước → nối Dell có kiểm soát → mới deploy hẳn lên Dell.**

## 2. Thiết bị và vai trò

| Máy | Vai trò | Ghi chú |
|---|---|---|
| ASUS Vivobook (Windows 11) | Máy dev: viết code, chạy thử frontend + backend | Python 3.13, Node 24 |
| Dell Latitude 3330 (Linux Mint 22.3 XFCE) | Server production | i5-3337U, 3,7 GiB RAM, HDD; boot vào chế độ chữ (`multi-user.target`); Python 3.12, nên code phải chạy được trên 3.12 |
| Xiaomi (Android 16) + Samsung Tab S10 Lite | v1: mở web; M7: thiết bị đích | Đã có Tailscale, chưa có agent |

Rủi ro phần cứng: pin Dell hỏng, pin CMOS nghi yếu. Sau khi mất điện, Dell **kẹt ở màn hình BIOS đòi bấm F1**. Phần mềm không sửa được việc này, nên không bao giờ hứa "tự phục hồi 100%".

## 3. Bức tranh kiến trúc

**Lúc dev (bây giờ):**

```
Trình duyệt ASUS ──► Vite :5173 (React, proxy /api) ──► FastAPI :8000 (127.0.0.1)
                                                            │
                                     (thử Remote Desktop)   └─► SSH tunnel 127.0.0.1:5901 ──► Dell: Unix socket ──► Xvnc + XFCE
```

**Lúc production (M6):**

```
ASUS / phone / tablet ──HTTPS tailnet──► Tailscale Serve ──► FastAPI 127.0.0.1:8000 trên Dell
                                                              ├─ /            web tĩnh (React đã build)
                                                              ├─ /api/*       API (đăng nhập, metrics, desktop...)
                                                              └─ /api/desktop/ws ──► /run/user/<uid>/hlc-vnc.sock ──► Xvnc :1 + XFCE
```

Ý chính:
- **Một tiến trình duy nhất** (FastAPI) phục vụ cả web lẫn API: "modular monolith". Không Docker, không database, không Redis, không microservice.
- App chỉ nghe **127.0.0.1** (loopback), nên mạng ngoài không gọi thẳng vào được. Đường vào từ xa là Tailscale Serve (M6).
- Frontend chỉ gọi **cùng origin** (`/api/...`), nên không phải cấu hình CORS.

## 4. Công nghệ và lý do chọn

| Phần | Công nghệ | Vì sao |
|---|---|---|
| Backend | Python + **FastAPI**, `psutil` | Nhẹ, chạy tốt trên Dell 4 GB; psutil đọc CPU/RAM/disk/mạng thật |
| Frontend | **React 19 + TypeScript + Vite** | Phổ biến, build ra file tĩnh |
| Biểu đồ | SVG tự vẽ (`LineChart.tsx`) | Không cần thư viện chart nặng |
| Desktop từ xa | **TigerVNC** (Xvnc) + **XFCE** + **noVNC** (trình duyệt) | GUI thật trong browser, Terminal nằm trong desktop |
| Test | pytest + ruff (backend), vitest + tsc (frontend) | `scripts\test.ps1` chạy hết |
| Mạng riêng | **Tailscale** | Không mở port router, không public |

## 5. Cấu trúc thư mục (file quan trọng)

```
backend/app/
  main.py                 tạo app: state (settings, adapter, metrics, auth, desktop), guard, routers, web tĩnh
  config.py               đọc biến môi trường / backend/.env
  __main__.py             `python -m app` (chạy server) và `python -m app set-password`
  api/
    guard.py              "người gác cổng" duy nhất: Origin + JSON cho request ghi, rồi kiểm session; denial() dùng chung cho WebSocket
    auth.py               /api/auth/login | logout | session
    system.py, metrics.py /api/system, /api/metrics
    device.py             PATCH /api/device (đổi tên thiết bị)
    desktop.py            /api/desktop/status | start | stop + WebSocket /api/desktop/ws (cầu nối VNC)
    power.py              /api/power + sleep | wake | cleanup | reboot
    errors.py             mọi lỗi trả {code, message}
  services/
    auth.py               scrypt, cookie ký HMAC, khóa sau 5 lần sai
    metrics.py            thu thập số liệu thật
    platform_adapter.py   khác biệt Windows/Linux
    device.py             id, tên, capabilities của thiết bị
    desktop.py            đọc DESKTOP_VNC, kiểm tra VNC (banner RFB), systemctl --user, đếm viewer
    runner.py             chạy lệnh server: tại chỗ, hoặc qua SSH khi staging (REMOTE_SSH, D-28)
    power.py              ngủ nhẹ / thức dậy / dọn dẹp / restart (D-27)
backend/tests/            pytest (109+ test)
frontend/src/
  App.tsx                 cổng session: Login | Shell | cửa sổ desktop tách rời
  Shell.tsx               khung app: topbar, sidebar, poll health/system/metrics
  routes.ts               danh sách trang (thêm trang ở đây là có menu)
  api/client.ts           fetchJson / sendJson, chuẩn hóa lỗi
  hooks/                  usePolling, useMetrics, useSession, useVnc, usePopout, useDesktopDock
  pages/                  Dashboard, RemoteDesktop, DesktopWindow, Files, System, Login
  components/             Card, StatusBadge, Sidebar, Topbar, DeviceName, VncToolbar, LiveDesktop, FloatingDesktop, PowerCard...
  lib/                    hàm thuần có test: format, history, status, label, desktop
  styles/theme.css        token màu theme cà phê (D-13)
deploy/linux/             script + unit + polkit rule cho Dell (desktop M3, power D-27; service backend ở M6)
scripts/                  setup, dev (+ tự mở tunnel), stop, test, build, set-password, env (PowerShell)
start.bat / stop.bat      bấm đúp để chạy/dừng dev
docs/                     SPEC, ARCHITECTURE, MILESTONES, CONTEXT, PROJECT_OVERVIEW, LEARN (file này)
```

## 6. Lộ trình và trạng thái

| Mốc | Nội dung | Trạng thái |
|---|---|---|
| M0 | Chốt tài liệu | Duyệt |
| M1 | Dựng khung frontend + backend trên ASUS | Duyệt |
| M2 | Metrics thật, chart realtime, trạng thái offline/stale | Duyệt |
| M2.5 | Đăng nhập owner, chống CSRF, đổi tên thiết bị | Duyệt |
| **M3** | **Remote Desktop GUI Dell** | **Xong A + B, chờ owner duyệt** |
| M4 | File Manager (thư mục được phép) | Chưa; cần chốt O-01, O-05 |
| M5 | Services + logs (allowlist) | Chưa; cần O-03 |
| M6 | Deploy lên Dell, Tailscale Serve, systemd, rollback = **v1** | Chưa |
| M7 | Nhiều thiết bị, điện thoại/tablet là thiết bị đích (M7D: chạy nền, giữ sáng màn hình) | Sau v1 |

Commit trên nhánh `navi`, **chưa push** (repo GitHub public; chỉ push khi owner nói "push").

## 7. Từng tính năng đã làm và cách nó chạy

### M1: khung dự án
- Backend FastAPI trả `/api/health`. Frontend React có sidebar và 4 trang; trang chưa làm thì hiện **"Not configured"** trung thực, không giả dữ liệu.
- Mọi payload có `device` (`id`, `label`, `platform`...) để M7 thêm thiết bị khác không phải đập đi làm lại.

### M2: số liệu thật
- Frontend **poll** (hỏi định kỳ) `/api/metrics` mỗi 2 giây, giữ 10 phút lịch sử trong bộ nhớ trình duyệt để vẽ biểu đồ.
- Mỗi nhóm số liệu có `status`: `ok | unsupported | unavailable | error`. Cảm biến không có thì hiện N/A, **không bịa số 0**.
- Mất kết nối thì badge chuyển "Stale" rồi "Offline"; có lại thì tự hồi phục.

### M2.5: đăng nhập
- **Mật khẩu riêng của app** (một owner, không username). Chỉ lưu **hash scrypt** trong `backend/.env`, đặt bằng `scripts\set-password.ps1`.
- Đăng nhập xong nhận **cookie** `hlc_session` = `<hạn>.<chữ ký HMAC>`:
  - HttpOnly: JavaScript không đọc được cookie.
  - SameSite=Strict: trang khác không gửi kèm được.
  - Nhớ 1 năm; restart server vẫn còn hiệu lực.
  - Đổi mật khẩu thì mọi thiết bị bị đăng xuất.
- **Chống CSRF:** mọi request ghi (POST/PATCH...) phải có header `Origin` đúng host và `Content-Type: application/json`.
- Sai 5 lần thì khóa 60 giây.
- **D-25:** dev trên ASUS (role `dev`, chỉ nghe loopback, gọi bằng `127.0.0.1`/`localhost`) **không cần đăng nhập**, vì máy chỉ owner dùng. Host lạ vẫn bị chặn, để chống "DNS rebinding".
- Đổi tên thiết bị: Dashboard → thẻ Device → cây bút. Ưu tiên tên đặt trên UI, rồi `DEVICE_LABEL`, rồi hostname.

### M3: Remote Desktop (mới nhất)

**Ý tưởng:** Dell có thêm một **màn hình ảo** (XFCE vẽ lên Xvnc). Màn hình laptop Dell vẫn đen trắng; desktop chỉ hiện trên web.

**Luồng dữ liệu:**

```
noVNC (trình duyệt) ──WebSocket /api/desktop/ws──► FastAPI (kiểm session + Origin) ──byte──► Unix socket 0600 ──► Xvnc :1 ──► XFCE
```

- **Không websockify, không cổng VNC (D-26).** Xvnc chỉ nghe một **Unix socket**, tức một "lối đi nội bộ" dạng file, quyền 0600: chỉ user của bạn mở được. `-rfbport -1` nghĩa là không có cổng TCP nào. Vì vậy dùng `SecurityTypes None` (không mật khẩu VNC) vẫn an toàn.
- **Cầu nối:** backend nhận WebSocket từ trình duyệt rồi chuyển byte hai chiều tới socket.
  - Middleware HTTP **không chạy cho WebSocket**, nên endpoint tự gọi `denial()` của guard: cùng luật, một chỗ.
  - Dùng task group của **anyio** (có sẵn trong Starlette); `asyncio.wait` thuần bị treo khi đóng.
- **Trạng thái:**
  - `running` khi socket trả lời đúng **banner RFB** (`RFB 003.008`). Chỉ mở được kết nối TCP thì chưa đủ, vì đường hầm SSH luôn nhận kết nối.
  - Badge: Starting / Running / Disconnected (viewer rớt trong khi server vẫn chạy) / Stopped / Error / Not configured.
- **Bật/tắt:** unit `hlc-desktop` của systemd ở mức user, gọi bằng lệnh cố định `systemctl --user start|stop hlc-desktop` (D-15). Unit không có `[Install]`, nên **không thể tự bật lúc boot** (ADR-008: tiết kiệm RAM).
- **Thanh công cụ:** Ctrl+Alt+Del, Esc, Tab, Keyboard (mở bàn phím điện thoại, mức cố gắng), Fullscreen, và **Pop out**: tách màn hình ra cửa sổ trình duyệt riêng; nút **Return to page** đưa nó về khung.
- **Khung nổi:** bỏ tick **Docked in page** thì màn hình nhấc ra thành khung nổi trong app. Khung nằm trên mọi trang, kéo thanh tiêu đề để di chuyển, kéo góc để đổi cỡ, vị trí và cỡ được nhớ. Tick lại thì nó về nằm gọn trong trang. Khung nổi do `Shell` giữ (`useDesktopDock`), nên chuyển trang không làm mất kết nối.
- **Đo trên Dell:** desktop tắt ~560 MiB RAM; bật thêm ~330–390 MiB; Xvnc ăn ~1–2 % CPU. Tắt thì trả lại hết RAM.
- **Cấu hình** (`backend/.env`):
  - `DESKTOP_VNC`: `unix:/run/user/<uid>/hlc-vnc.sock` trên Dell, hoặc `tcp:127.0.0.1:5901` qua đường hầm.
  - `DESKTOP_UNIT`: để trống thì start/stop phải làm trên server.
  - `DESKTOP_LABEL`: tên máy hiện trên trang, ví dụ "Dell".
- **Dùng từ ASUS (staging, D-28):** `backend/.env` có `REMOTE_SSH` (alias SSH của Dell), nên `start.bat` tự mở đường hầm và nút **Start/Stop** trên web ra lệnh cho Dell qua SSH. Bấm Start → Connect là thấy desktop. Hướng dẫn ở README → "Remote desktop (staging)". Cứu hộ và gỡ bỏ: `deploy/linux/README.md`.

### Bổ sung sau M3: thẻ Power (trang System, D-27)

- **Light sleep** (ngủ nhẹ): tắt các tác vụ nền **tùy chọn** đang chạy (Docker, máy in, firmware, modem, âm thanh, màn hình ảo…) và **ghi nhớ** chúng. **Wake up** bật lại đúng những thứ đó.
- **Clean up** (reset nhẹ): tắt hết tác vụ tùy chọn, **không ghi nhớ**; dùng khi Dell lag hoặc lười tắt từng thứ.
- **Restart**: khởi động lại máy, phải xác nhận lần hai.
- **Đổi tên server:** bút chì cạnh "Desktop: Dell" (lưu `STATE_DIR/server.json`). Dòng đầu trang hiện tên thiết bị bạn đặt, không còn hiện hostname.
- **Chế độ tập trung:** bấm vào màn hình là bàn phím thuộc về desktop (viền cam); bấm ra ngoài là trả lại; ở Fullscreen, Edge/Chrome chuyển cả Alt+Tab, phím Windows, Ctrl+W vào desktop (giữ Esc để thoát fullscreen).
- **Vì sao màn hình lag/mờ:** card Wi-Fi Dell (Broadcom BCM4313) gửi đi chỉ ~20–120 KB/s; hình ảnh đi Dell → trình duyệt nên bị nghẽn. Đã giảm tải (tắt compositor, nền trơn, nén mạnh hơn). UDP không giúp được (Tailscale đã là UDP); cache ảnh chỉ đỡ 3 giây đầu. Cách chữa thật: **cắm dây LAN**.
- **Không có Shut down**: Wi-Fi Broadcom không đánh thức được và chưa cắm dây LAN, nên tắt rồi thì không bật lại từ xa được.
- SSH, Tailscale, mạng, systemd và app **không bao giờ** bị tắt. Danh sách cố định trong code. Quyền trên Dell do một quy tắc **polkit** cấp cho đúng user của bạn (`deploy/linux/power-setup.sh`, chạy sudo 1 lần).

## 8. Nguyên tắc bảo mật (luôn giữ)

1. Không lệnh shell nào lấy từ dữ liệu trình duyệt. Chỉ dùng lệnh cố định, argv list, không `shell=True` (D-15).
2. Chỉ bind `127.0.0.1`. Không mở port ra LAN/WAN. Không Tailscale Funnel.
3. VNC không bao giờ nghe trên mạng (không cổng 5901/6080 ra LAN/tailnet).
4. Không commit `.env`, khóa, mật khẩu, IP, tên tailnet, username, IMEI hay số sê-ri. Repo GitHub là **public**.
5. Không tự dừng hoặc restart SSH/Tailscale từ app, vì có thể tự khóa mình ở ngoài.
6. UI trung thực: không dữ liệu giả, không màn hình giả "đang kết nối".
7. Việc trên Dell cần sudo thì owner tự gõ mật khẩu; AI không giữ mật khẩu.

## 9. Chạy hằng ngày

| Việc | Cách |
|---|---|
| Chạy dev | Bấm đúp `start.bat` (mở backend + frontend + trình duyệt) |
| Dừng dev | Bấm đúp `stop.bat` |
| Kiểm tra toàn bộ (lint, test, build) | `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` |
| Đặt mật khẩu (dùng khi lên Dell) | `scripts\set-password.ps1`, rồi restart backend |
| Xem desktop Dell từ ASUS | `start.bat` → Remote Desktop → **Start** → **Connect** (tunnel tự mở) |
| Ngủ nhẹ / thức dậy / dọn dẹp / restart Dell | Trang **System** → thẻ **Power** |
| Bật/tắt desktop bằng tay (qua SSH) | `systemctl --user start hlc-desktop` / `stop` |

URL dev: http://localhost:5173 · API: http://127.0.0.1:8000/api/health · tài liệu API (dev): http://127.0.0.1:8000/api/docs

## 10. Thuật ngữ

| Từ | Nghĩa ngắn |
|---|---|
| API / endpoint | Địa chỉ backend trả dữ liệu, ví dụ `/api/metrics` |
| Polling | Frontend hỏi lại định kỳ (2 s cho metrics, 3 s cho desktop) |
| WebSocket | Kết nối hai chiều luôn mở; dùng cho màn hình desktop |
| VNC / RFB | Giao thức truyền màn hình và chuột/phím; RFB là tên kỹ thuật |
| Xvnc / TigerVNC | Phần mềm tạo màn hình ảo nói VNC |
| noVNC | Thư viện JavaScript hiển thị VNC trong trình duyệt |
| Unix socket | "Cổng" dạng file trong máy, có quyền như file; mạng không với tới |
| SSH tunnel (`-L`) | Đường hầm qua SSH: cổng trên ASUS dẫn tới socket trên Dell |
| systemd unit / `--user` | Dịch vụ do systemd quản lý; `--user` là của riêng user, không cần root |
| linger | Cho dịch vụ `--user` chạy cả khi user không đăng nhập |
| Loopback (127.0.0.1) | Địa chỉ "chính máy này"; máy khác không gọi vào được |
| CSRF | Trang lạ lừa trình duyệt gửi lệnh thay bạn; chặn bằng Origin + JSON + SameSite |
| Origin / Host | Header cho biết trang gửi request đến từ đâu, và nó gọi tới host nào |
| scrypt / HMAC | Băm mật khẩu chậm, chống dò; chữ ký chống làm giả cookie |
| DNS rebinding | Trang lạ trỏ tên miền của nó về 127.0.0.1 để đọc app; chặn bằng kiểm Host |
| Tailscale Serve / Funnel | Serve: HTTPS chỉ trong tailnet (dùng). Funnel: ra Internet (cấm) |
| Capability | Thiết bị **có thể** làm gì: `supported` / `unsupported` / `not_configured` / `requires_consent` |
| polkit | Cơ chế cấp quyền của Linux: cho user thường làm một việc cần quyền admin, đúng việc đó thôi |
| Wake-on-LAN | Đánh thức máy đã tắt bằng gói tin qua **dây mạng**; Wi-Fi của Dell không hỗ trợ |
| Keyboard Lock | API của Edge/Chrome: ở fullscreen, trang nhận được cả phím hệ thống (Alt+Tab, phím Windows) |
| Compositor | Phần vẽ hiệu ứng (bóng, mờ dần) của cửa sổ; tắt đi thì ít phải gửi hình hơn |

## 11. Bài học, lỗi đã gặp và cách sửa

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| Ghi qua Vite :5173 bị 403 | Proxy dạng chuỗi tự đổi Host, nên Origin ≠ Host | Proxy dạng object, `changeOrigin: false` (+ `ws: true` cho desktop) |
| Test "chỉ có route GET" luôn qua mà không kiểm gì | FastAPI 0.16x include router kiểu lười, `app.routes` rỗng | Duyệt `app.openapi()["paths"]` |
| Cầu nối WebSocket treo hoặc lỗi khi đóng | `asyncio.wait` + `gather` va với cơ chế hủy của anyio trong Starlette | Dùng `anyio.create_task_group()` |
| Test WS với base_url không có tác dụng | `TestClient.websocket_connect` bỏ qua base_url | Truyền URL tuyệt đối `ws://127.0.0.1:8000/...` |
| Viewer thật bị đá ra sau vài lần poll | **TigerVNC blacklist**: probe trạng thái (kết nối, đọc banner, ngắt) bị tính là "đăng nhập dở"; mọi client socket chung một địa chỉ | `-UseBlacklist=0` + bỏ probe khi đang có viewer |
| Log `app.*` không hiện | Uvicorn chỉ cấu hình logger của nó | `logging.basicConfig` trong `__main__` |
| Script `.sh` hỏng trên Linux | Windows lưu CRLF | `.gitattributes`: `*.sh`, `*.service` dùng `eol=lf` |
| Chạy lệnh qua SSH từ Node bị vỡ dấu nháy | cmd.exe xử lý quoting | Gửi script qua stdin: `ssh host bash -s` |
| Màn hình Dell lag, mờ | Wi-Fi BCM4313 upload ~20–120 KB/s | Giảm dữ liệu (compositor off, nền trơn, nén 6); cắm dây LAN |

## 12. Quyết định đã chốt (không hỏi lại)

- **D-01..D-11:** tự xây web (không dùng Cockpit); code và test trên ASUS trước; production trên Dell chạy độc lập; 4 trang; **không có trang terminal riêng** (Terminal nằm trong desktop GUI); Tailscale + SSH; tạm gác lỗi F1; nhẹ, không overengineering.
- **D-12, D-17..D-22:** kiến trúc phải mở rộng để quản lý điện thoại/tablet (M7). Lệnh có vòng đời `requested → … → applied`; chỉ `applied` mới là thành công. Agent làm trong quyền OS cho phép, không root. Thiết bị đích hiện tại là 2 máy Android; không làm iOS native.
- **D-13:** giao diện bố cục NexusHost, **theme nâu cà phê tối**; màu trạng thái luôn kèm chữ.
- **D-14, D-24:** nhãn thiết bị lấy từ `DEVICE_LABEL`, đổi được trên UI.
- **D-15:** "không shell" = không lệnh nào từ input; chỉ lệnh cố định.
- **D-16, D-23, D-25:** đăng nhập là M2.5; dùng mật khẩu riêng của app; dev trên ASUS không cần login.
- **D-26:** desktop qua Unix socket + cầu nối trong backend, không websockify.
- **D-27:** thẻ Power: ngủ nhẹ / thức dậy / dọn dẹp / restart có xác nhận; **không tắt nguồn**; danh sách tác vụ cố định; polkit cho đúng 1 user.
- **D-28:** staging: backend trên ASUS ra lệnh cho Dell qua SSH alias (`REMOTE_SSH`); `start.bat` tự mở tunnel.
- **O-04:** chọn **màn hình ảo** (không chia sẻ màn hình vật lý); owner vẫn đổi được trước khi duyệt M3.

Câu hỏi còn mở:
- **O-01:** thư mục nào trên Dell cho trang Files (trước M4).
- **O-03:** dịch vụ nào được phép restart (trước M5).
- **O-05:** gửi file giữa các client hay chỉ browser↔server (trước M4).
- **O-06:** nhiều host trên dashboard (trước M7).
- **O-07:** phiên bản One UI của tablet (trước M7D-0).
- **O-08:** công nghệ và cách cài agent Android (trước M7D-4).
- **O-09:** lưu registry bằng JSON hay SQLite.
- **O-11:** heartbeat và TTL lệnh.

## 13. Việc tiếp theo

1. Owner **duyệt M3** (hoặc đổi O-04).
2. **M4 Files:** chốt O-01 (thư mục) và O-05 trước.
3. Push lên GitHub khi owner nói "push" (các commit từ M2.5 tới giờ vẫn chưa push: `git log origin/navi..navi`).
4. Nên đổi mật khẩu Linux của Dell (`passwd`), vì nó từng được gửi trong chat.
5. M6 sẽ: chạy backend trên Dell bằng systemd (cùng user với desktop), đặt mật khẩu app, `MACHINE_ROLE=production`, Tailscale Serve, kiểm Host/Origin và WebSocket qua Serve.

---

## 14. Prompt khởi động cho phiên AI mới (copy nguyên khối)

```text
You are continuing "HomeLab Control" (folder "Server Control", git branch navi): a private web app to
monitor and control a Dell Linux Mint server from an ASUS Windows laptop, phone and tablet over Tailscale.
Reply to the owner in Vietnamese, in plain words; the owner finds complexity burdensome.

Read first: docs/LEARN.md (overview), then docs/PROJECT_OVERVIEW.md, SPEC.md, ARCHITECTURE.md,
MILESTONES.md, CONTEXT.md. The docs are the source of truth; decisions D-01..D-28 are final (do not re-ask).

State: M0, M1, M2, M2.5 approved. M3 (Remote Desktop: noVNC page, backend WebSocket bridge to a TigerVNC
Xvnc Unix socket, XFCE virtual session on the Dell, pop-out window, floating in-app panel with a "Docked in page" toggle; plus a Power card on the System page: light sleep / wake up / clean up / confirmed restart, never shut down, D-27; staging runs server commands over SSH via REMOTE_SSH, D-28) done and verified on the real Dell,
waiting for owner approval. Next: M4 Files (needs O-01, O-05). Commits are local; the GitHub repo is
PUBLIC: push only when the owner explicitly says "push".

Stack: FastAPI + psutil (Python 3.12-compatible), React 19 + TypeScript + Vite, pytest/ruff/vitest.
Run all checks with scripts\test.ps1. Dev: start.bat / stop.bat. Errors are always {code, message}.

Rules:
- Modular, minimal code that matches the surrounding style; no overengineering; coffee theme tokens; usable at 360px.
- One guard (backend/app/api/guard.py) protects /api: Origin + JSON on writes, then the session; WebSockets call denial().
- No shell from web input: fixed argv, never shell=True. Bind 127.0.0.1 only; no public/LAN ports; never expose VNC.
- No Docker, database, Redis or microservices. No new dependencies without a reason stated up front.
- Never print, log or commit passwords, hashes, cookies, IPs, tailnet names, usernames, uids, IMEI or serials;
  use placeholders <dell>, <user>, <uid>. The Dell is reached by an SSH alias in ~/.ssh/config (key auth).
- Dell: never reboot, never stop/restart ssh or tailscaled, no firewall changes; any sudo command is shown
  to the owner and run by the owner. The Dell can hang at a BIOS F1 prompt after power loss.
- Honest UI: no fake data, no fake "connected" screens; unsupported things say so.
- Work milestone by milestone; read the docs before coding; update MILESTONES "Tiến độ" with evidence;
  commit at the end of a milestone part; report in Vietnamese (CONTEXT.md handoff template).
```
