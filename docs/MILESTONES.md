# Server Control — Milestones & Release Gates

> **Quy tắc:** Không bắt đầu coding milestone nếu AC/kiểm thử trước đó chưa đạt; không tự tuyên bố tính năng xong khi mới có UI mock.  
> Tiến độ cập nhật theo **đầu ra và evidence**, không đo bằng % cảm tính.

## Tổng quan

| Mốc | Ưu tiên | Nội dung | Phụ thuộc | Done |
|---|---|---|---|---|
| **M0** | P0 | Chốt tài liệu đặc tả, kiến trúc, context, phạm vi | — | **Duyệt 2026-10-31** |
| **M1** | P0 | Khởi tạo repo + frontend/backend chạy trên ASUS | M0 | **Duyệt 2026-10-31** |
| **M2** | P0 | Dashboard metrics thật + realtime + trạng thái offline | M1 | **Duyệt 2026-10-31** |
| **M2.5** | P0 | Đăng nhập mật khẩu owner (D-23), bảo vệ `/api` trừ `/health`, CSRF/Origin, đổi tên thiết bị (D-24) | M1 | **Chờ duyệt** |
| **M3** | P0 | Remote Desktop GUI Dell tích hợp trong web | M1, M2, M2.5 | Chưa |
| **M4** | P1 | File Manager giới hạn quyền + upload/download | M1, M2.5 | Chưa |
| **M5** | P1 | System Services, logs, thao tác allowlist | M1, M2.5 | Chưa |
| **M6** | P0 | Production release trên Dell, Tailscale Serve, recovery/rollback | M2–M5 theo phạm vi release | Chưa |
| **M7** | P2 | Nhiều thiết bị, **Android/tablet/iPhone/iPad là managed target**, capability adapters, alerts/history; M7D Mobile Background & Screen Control (FR-08) | Sau v1 (M6) | Hoãn |

> Các milestone mô tả trình tự ưu tiên. Có thể có **MVP release** sau M2/M3 rồi triển khai Files/System sau; nếu đổi thứ tự thì cập nhật tài liệu trước.

## M0 — Requirements & architecture freeze

**Deliverables**
- `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/MILESTONES.md`, `docs/CONTEXT.md`, `docs/PROJECT_OVERVIEW.md`.
- Owner xác nhận phạm vi v1. Điểm mở O-01..O-06 (file roots, auth, service allowlist…) **hoãn có chủ đích**, chốt tại milestone tương ứng với safe default trong SPEC.
- Không tạo các trang chỉ để trông có vẻ hoàn thành.

**Gate**
- Không còn mâu thuẫn giữa "ASUS dev" và "Dell production".
- Remote desktop là desktop ảo Linux, không phải VM; không có trang CLI riêng.
- BIOS F1 sau mất điện được ghi là **known blocker**, không promise auto-recovery.

**Điều kiện mở rộng của M0:** Không triển khai mobile-control trong M1–M6, nhưng giữ ranh giới `device`/`platform`/`capabilities` trong API và UI để M7 không phải làm lại kiến trúc.

## M1 — Project bootstrap trên ASUS

**Task**
- Khởi tạo Git, `.gitignore`, `README.md`, `frontend/`, `backend/`, `deploy/linux/`.
- React + TypeScript + Vite, FastAPI; dùng Vite proxy `/api` → `127.0.0.1:8000`.
- Layout dark responsive bốn trang: Overview, Remote Desktop, Files, System (trang chưa hoạt động có trạng thái **not configured**, không mô phỏng giả).
- FastAPI health + system capability, adapter Windows/Linux. Cấu hình qua `.env.example`.
- Test/format/build scripts; không cài package vào global Python nếu tránh được.

**Acceptance**
- ASUS `localhost:5173` xem được UI; `localhost:8000/api/health` trả 200.
- Không có lỗi build TS hoặc test API; `git status` không chứa secrets, `.venv`, `node_modules`.
- Git commit M1 riêng, tài liệu lệnh chạy dev rõ ràng.

**Tiến độ**
```text
Milestone: M1
Status: DONE (owner duyệt 2026-10-31)
Commit: 3875422 "M1: project bootstrap ..." + start.bat/stop.bat, branch navi
Changes: backend/app (config, api/{health,system,errors}, services/{device,platform_adapter,status}, main, __main__),
         backend/tests, frontend/ (routes registry, components, 4 pages, coffee theme), scripts/*.ps1, README.md
Tests: scripts\test.ps1 -> ruff OK, pytest 9 passed, vitest 6 passed, tsc + vite build OK
Evidence: /api/health 200 và /api/system (ASUS, role=dev) trên 127.0.0.1; UI 5173 desktop + 360px;
          tắt backend -> Disconnected, bật lại -> Connected
Risks: cpu_model trên Windows là chuỗi thô; Linux adapter mới test bằng unit test (chưa chạy trên Dell)
Next: M2
```

## M2 — Monitoring thật

**Task**
- `psutil` CPU, RAM, disk root, network rates, uptime, nhiệt độ/pin capability-aware.
- REST polling ~2s và biểu đồ in-memory ≥10 phút; UI online/offline/stale.
- Dữ liệu Asus Windows real, không dùng Dell name hardcoded; Linux provider bằng test/mocks.

**Acceptance**
- Dashboard số liệu thay đổi khi tạo tải thử; % trong ngưỡng hợp lý.
- Tắt backend rồi bật lại: UI offline, sau đó tự khôi phục.
- Không có dữ liệu giả xuất hiện như sensor thật; có tests field missing/counter reset.

**Tiến độ**
```text
Milestone: M2
Status: DONE (owner duyệt 2026-10-31)
Commit: f96457f "M2: real metrics, realtime charts, offline/stale", branch navi
Changes: backend/app/services/metrics.py (MetricsCollector), api/metrics.py (GET /api/metrics),
         platform_adapter.py (battery/ac_power; Linux đọc /sys/class/power_supply, pin hỏng -> status=error),
         device.py (metrics = supported, battery theo adapter), tests/test_metrics.py;
         frontend: lib/history.ts (300 mẫu = 10 phút), hooks/useMetrics.ts, components/LineChart.tsx (SVG tự viết),
         Dashboard (4 KPI, chart CPU/RAM + network, Sensors, Live/Stale/Offline), lib/status.ts (freshness)
Tests: scripts\test.ps1 -> ruff OK, pytest 23 passed, vitest 13 passed, tsc + vite build OK
Evidence: ASUS (label "this ASUS"): tải 8 tiến trình -> CPU 24% -> 52-65% trên chart; 3 viewer gọi đồng thời nhận cùng giá trị;
          kill backend -> "Offline · last updated hh:mm:ss", giữ chart cũ; bật lại -> Live không reload, chart có khoảng trống;
          360px không tràn ngang (scrollWidth 360). Temperature/fans Windows = N/A + lý do; pin 80%, AC plugged in.
Risks: Linux battery/sysfs/AC và nhiệt độ chỉ test bằng mock, chưa chạy trên Dell; quy tắc nhận diện pin hỏng
       (capacity đọc lỗi, hoặc 0% mà không Discharging, hoặc psutil không thấy pin mà sysfs có) cần xác nhận trên Dell.
       CPU % tự tính từ delta cpu_times() (psutil.cpu_percent giữ mẫu theo từng thread -> trả 0.0 trên threadpool).
Next: M2.5
```

## M2.5 — Đăng nhập owner + đổi tên thiết bị

**Task**
- `scripts\set-password.ps1` (gọi `python -m app set-password`): nhập mật khẩu ẩn, ghi `OWNER_PASSWORD_HASH` (scrypt) vào `backend/.env`; không in, không log mật khẩu.
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`; cookie ký HMAC 1 năm (D-25), secret sinh một lần trong `STATE_DIR`.
- Dev trên ASUS (role `dev` + bind loopback + Host loopback): không cần đăng nhập, không hiện Logout (D-25).
- Mọi `/api/*` trừ `/api/health`, `/api/auth/*` trả `401 {code, message}` khi chưa đăng nhập.
- Request ghi (POST/PUT/PATCH/DELETE): kiểm tra `Origin` khớp host + bắt buộc `application/json`; sai ⇒ `403`.
- Sai mật khẩu 5 lần ⇒ `429` trong 60 s.
- `PATCH /api/device {label}`: lưu `STATE_DIR/device.json`, `null` = về mặc định; validate 1–40 ký tự.
- UI: trang Login, nút Logout, 401 ở bất kỳ request nào ⇒ về Login; sửa tên tại thẻ Device.

**Acceptance**
- Dev trên ASUS mở thẳng Dashboard, không hỏi mật khẩu; Host lạ/`production`/bind ra ngoài vẫn bắt đăng nhập.
- Chưa đăng nhập (ngoài dev loopback): `/api/health` 200; `/api/system`, `/api/metrics` 401. Đăng nhập xong: dashboard như M2.
- Restart backend: vẫn đăng nhập. Đổi mật khẩu: session cũ bị đá ra.
- Request ghi khác Origin ⇒ 403; sai 5 lần ⇒ 429.
- Đổi tên ⇒ topbar, Dashboard và `/api/metrics` hiện tên mới, giữ sau restart; "về mặc định" trả lại `DEVICE_LABEL`/hostname.
- Không có mật khẩu/hash/secret trong git, log hay response.

**Tiến độ**
```text
Milestone: M2.5
Status: Chờ owner duyệt (code + test xong 2026-10-31)
Commit: ac33e7b "M2.5: owner login, CSRF/Origin, device rename" + "M2.5: no login in dev on loopback (D-25), 1-year session", branch navi (chưa push)
Changes: backend/app/services/auth.py (scrypt, cookie "<expires>.<hmac>", key = STATE_DIR/session_secret + hash, khóa 5 lần/60 s),
         api/guard.py (middleware duy nhất: Origin + JSON cho request ghi, rồi session; chỉ /api/health, /api/auth/* public),
         api/auth.py (login/logout/session), api/device.py (PATCH /api/device), services/device.py (device.json, label_source),
         api/errors.py (ApiError có code), config.py (OWNER_PASSWORD_HASH, ALLOWED_ORIGINS, ghi .env),
         __main__.py (python -m app set-password), scripts/set-password.ps1, .env.example;
         frontend: App = cổng session (không poll API bảo vệ trước khi login), Shell.tsx (app cũ + 401 -> Login, Logout),
         pages/Login.tsx, components/DeviceName.tsx (đổi tên inline, Reset khi label_source=custom), lib/label.ts,
         api/client.ts (sendJson, 401 -> unauthorized), vite.config.ts (proxy changeOrigin:false để giữ Host);
         D-25: Auth.open_to() (dev + bind loopback + Host loopback = không cần session), session trả login_required,
         ẩn Logout khi không cần đăng nhập, cookie 1 năm, config.is_loopback dùng chung
Tests: scripts\test.ps1 -> ruff OK, pytest 58 passed, vitest 15 passed, tsc + vite build OK
Evidence: ASUS: chưa có mật khẩu -> Login báo "No owner password set yet" + lệnh set-password, login 503;
          mật khẩu tạm -> /api/health 200, /api/system 401 khi chưa login; login 204 -> Dashboard Live như M2;
          sai 5 lần -> lần 6 trả 429 (Retry-After: 60), đúng mật khẩu cũng 429 trong lúc khóa;
          restart backend -> cookie cũ vẫn dùng được; đổi hash -> cookie cũ 401;
          PATCH Origin lạ / thiếu Origin / form-encoded -> 403; qua Vite dev proxy cùng origin -> 200;
          đổi tên "Dell thử nghiệm ☕" -> topbar, Dashboard, /api/metrics cập nhật, giữ sau restart; Reset -> "this ASUS" (env);
          Logout -> Login; 360px Login và form đổi tên không tràn ngang. Log backend không có mật khẩu/hash/cookie.
          Mật khẩu tạm đã xóa khỏi backend/.env sau khi test.
          D-25: ASUS dev không đặt mật khẩu -> mở thẳng Dashboard, không có nút Logout; Host lạ -> 401.
Risks: Host/Origin sau Tailscale Serve chưa kiểm (M6); nếu Serve đổi Host thì thêm URL Serve vào ALLOWED_ORIGINS.
       Khóa đăng nhập tính chung (một owner; sau Serve mọi request đều từ 127.0.0.1), nên người khác trong tailnet có thể
       làm owner phải chờ 60 s. Đổi mật khẩu cần restart backend (hash đọc lúc khởi động).
       D-25: tiến trình khác trên chính ASUS gọi được API dev (chấp nhận: máy chỉ owner dùng); lên Dell phải để
       MACHINE_ROLE=production, nếu không thì Tailscale Serve (gọi tới 127.0.0.1) sẽ lọt qua chế độ mở -> kiểm ở M6.
Next: M3
```

## M3 — Remote Desktop tích hợp GUI

**Task**
- React tích hợp core `@novnc/novnc`, keyboard/mouse/fullscreen/status.
- Xây desktop manager API rõ ràng; dev ở ASUS dùng mock hoặc remote test target ghi nhãn.
- Trên Dell: cài XFCE/TigerVNC/websockify với cấu hình loopback, user không phải root; start on demand.
- WebSocket bridge có xác thực; thử xuyên Tailscale từ frontend ASUS tới Dell **không cần deploy toàn bộ app** (staging có kiểm soát).

**Acceptance**
- Remote Desktop hiển thị GUI Linux **thật** trên Dell; mở app và Terminal chạy `hostname` là Dell.
- Ngắt VNC rồi bật lại: state chính xác, không hỏng monitoring.
- Kiểm thử không có cổng VNC public; chỉ tailnet/localhost tùy hop.
- Đo RAM CPU khi mở và đóng GUI; có bước rescue SSH.

**Rủi ro:** Test này bắt buộc có thời gian chạy dịch vụ trên Dell; không thể nghiệm thu chỉ bằng ASUS Windows.

## M4 — File Manager

**Task**
- Duyệt, upload, download, breadcrumb/size, size cap, progress; directory allowlist.
- Path validation/symlink escaping tests; file trùng tên và rename.
- Có thể hoãn xóa/ghi đè để giảm rủi ro.

**Acceptance**
- Upload/download file mẫu kiểm tra checksum trùng.
- Thử `../`, URL encoding, symlink escape: tất cả bị reject.
- Upload lỗi giữa chừng không để lại file hỏng như file thành công.

## M5 — System Control (có giới hạn)

**Task**
- Read-only service status/logs trước; whitelist services.
- Chỉ sau khi có auth + audit + tests, cho phép restart một số service an toàn.
- Không bật power off/reboot trong UI khi F1/CMOS chưa xử lý.

**Acceptance**
- Từ client chưa auth không gọi được action; không có endpoint shell arbitrary.
- Service không thuộc allowlist không thể điều khiển.
- Tailscale/SSH không bị restart từ UI.

## M6 — Deployment Dell + production hardening

**Task**
- ASUS build frontend; chép artifacts sang Dell; Python venv trên Dell; systemd non-root.
- Backend + frontend một origin, listen loopback, HTTPS qua Tailscale Serve.
- Đảm bảo basic auth/app owner access, protection WebSocket, không lộ secrets.
- Viết deploy/rollback, log retention, healthcheck, smoke tests, hướng dẫn nâng cấp.

**Acceptance**
- ASUS có thể tắt dev server; web production từ Dell vẫn mở được bằng PC và mobile trong tailnet.
- `systemctl restart` và reboot Linux **bình thường** khôi phục web/API.
- Tailscale Serve không thành Funnel; không có service quản trị public.
- Dashboard Dell thật, desktop thật, file manager hoạt động, dịch vụ phân quyền.
- Ghi rõ: sau mất điện đột ngột, BIOS có thể đòi F1; tình trạng này **không được tính passed**.

## M7 — Hướng mở rộng (chưa giao coding)

- **M7A — Device registry + capabilities:** thêm ASUS/Windows, nhiều Linux; điện thoại/tablet xuất hiện như **thiết bị đích**, không chỉ trình duyệt để điều khiển Dell.
- **M7B — Mobile integration:** đánh giá Android (agent/ADB/scrcpy + quyền truy cập), iOS/iPadOS (chức năng được OS cho phép); theo dõi/truyền file/chia sẻ màn hình/remote input chỉ triển khai khi đã kiểm thử thực tế.
- **M7C — Reliability & UX:** lịch sử > 10 phút (SQLite nếu cần), cảnh báo offline/nhiệt độ, notification; tùy chọn chia sẻ màn hình vật lý.
- **M7D — Mobile Background & Screen Control (FR-08):** chi tiết ở dưới.
- Không cam kết Android/iOS có cùng mức độ điều khiển, không truy cập thiết bị ẩn và không phá bảo vệ OS.
- **Nghiệm thu M7:** danh sách nhiều thiết bị; UI căn cứ capabilities; chức năng điều khiển phải có quyền được cấp, hủy phiên được, thử trên phần cứng thật.
- Giải quyết CMOS/UPS/remote KVM là **hạ tầng phần cứng**, không phải milestone sửa code.

### M7D — Mobile Background & Screen Control (FR-08)

**Phụ thuộc:** M2.5 (auth owner, CSRF), M6 (server Dell chạy qua Tailscale Serve để agent kết nối tới; backend dev chỉ chạy ở loopback trên ASUS), M7A (device registry, enrollment). Không phụ thuộc M7B (screen_view/remote_input).

| Subtask | Nội dung | Kiểm thử chính |
|---|---|---|
| M7D-0 | Spike trên thiết bị thật: ghi model/phiên bản OS (O-07), kiểm chứng từng ô trong bảng `ARCHITECTURE.md` §4A.5 bằng app/trang thử nhỏ; cập nhật bảng thành "đã xác minh/không khả thi" | Ghi chép + ảnh chụp đã làm mờ; chưa merge code sản phẩm |
| M7D-1 | Backend `device_control`: model lệnh, state machine, TTL/timeout, desired/reported, audit; API §4A.3 | pytest: mọi chuyển trạng thái hợp lệ/không hợp lệ, hết hạn, kết quả đến muộn, lệnh trùng `command_id`, token thu hồi, sai thiết bị, capability không `supported` |
| M7D-2 | UI Devices: danh sách online/offline, control state theo §4A.4, nút bật/tắt chỉ khi `supported`, hiển thị "đang chờ thiết bị" | vitest: hàm suy ra control state; không có đường nào hiện "thành công" trước `applied` |
| M7D-3 | Web companion: tablet dashboard mode + `keep_screen_awake` bằng Screen Wake Lock API | Test trên tablet thật qua HTTPS tailnet (AT-M7-08) |
| M7D-4 | Android companion agent (O-08): enroll, heartbeat, long-poll, foreground service, giữ sáng | Test trên Android thật (AT-M7-05/06/07/11), đo hao pin và RAM Dell |
| M7D-5 | iOS/iPadOS: báo `unsupported` trung thực. **Tạm hoãn**: không có Mac và không có thiết bị iOS (D-22) | AT-M7-09 khi có iPhone/iPad |

Trên ASUS có thể chạy agent giả lập trong pytest, ghi rõ là **test double**. Kết quả từ agent giả lập không được tính là nghiệm thu thiết bị.

**Acceptance (trên thiết bị thật)**
- AT-M7-05..08, 10, 11 trong `SPEC.md` đạt trên **cả máy Xiaomi và máy Samsung** của owner; ghi model/phiên bản OS cho từng kết quả. AT-M7-09 (iOS) hoãn theo D-22.
- Không có trạng thái `applied`/`enabled` nào hiển thị khi agent chưa xác nhận.
- Thu hồi thiết bị trên web ⇒ agent mất quyền ngay; gỡ app trên thiết bị ⇒ UI chuyển `offline`.
- RAM/CPU Dell không tăng đáng kể khi có 2–3 thiết bị heartbeat; không có tiến trình/cổng mới trên Dell.
- Tính năng nào chưa xác minh được thì vẫn để `unsupported`/`not_configured`, không ghi là xong.

## Tiến độ cập nhật cho mỗi mốc

Điền thông tin theo mẫu khi làm xong mỗi milestone:

```text
Milestone: Mx
Status: TODO | IN_PROGRESS | BLOCKED | DONE
Commit: <hash>
Changes: <files/modules>
Tests: <command + result>
Evidence: <screenshots/logs/URL localhost hoặc tailnet đã làm mờ>
Risks: <known issue>
Next: <one next milestone>
```

## Quy tắc phân công AI

- **Một agent một milestone/module tại một thời điểm**, tránh cả ba sửa cùng file.
- AI có thể đề xuất đổi công nghệ, nhưng **phải ghi đề xuất vào tài liệu** và chờ owner duyệt khi đổi kiến trúc/phạm vi.
- Không yêu cầu LLM tự chạy deployment lên Dell ở M1/M2, không đẩy code lên remote mặc định.
- Đầu ra của AI phải có changes, tests, caveats; không chỉ có screenshot/UI đẹp.
