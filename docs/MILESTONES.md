# Server Control — Milestones & Release Gates

> **Quy tắc:** Không bắt đầu coding milestone nếu AC/kiểm thử trước đó chưa đạt; không tự tuyên bố tính năng xong khi mới có UI mock.  
> Tiến độ cập nhật theo **đầu ra và evidence**, không đo bằng % cảm tính.

## Tổng quan

| Mốc | Ưu tiên | Nội dung | Phụ thuộc | Done |
|---|---|---|---|---|
| **M0** | P0 | Chốt tài liệu đặc tả, kiến trúc, context, phạm vi | — | **Duyệt 2026-10-31** |
| **M1** | P0 | Khởi tạo repo + frontend/backend chạy trên ASUS | M0 | Xong, chờ owner duyệt |
| **M2** | P0 | Dashboard metrics thật + realtime + trạng thái offline | M1 | Chưa |
| **M2.5** | P0 | Auth owner (chốt O-02), bảo vệ `/api` trừ `/health`, CSRF/Origin | M1 | Chưa |
| **M3** | P0 | Remote Desktop GUI Dell tích hợp trong web | M1, M2, M2.5 | Chưa |
| **M4** | P1 | File Manager giới hạn quyền + upload/download | M1, M2.5 | Chưa |
| **M5** | P1 | System Services, logs, thao tác allowlist | M1, M2.5 | Chưa |
| **M6** | P0 | Production release trên Dell, Tailscale Serve, recovery/rollback | M2–M5 theo phạm vi release | Chưa |
| **M7** | P2 | Nhiều thiết bị, **Android/tablet/iPhone/iPad là managed target**, capability adapters, alerts/history | Sau v1 | Hoãn |

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
Status: DONE (chờ owner duyệt checkpoint 3)
Commit: commit "M1: project bootstrap ..." trên branch navi (xem git log; chưa push)
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
- Không cam kết Android/iOS có cùng mức độ điều khiển, không truy cập thiết bị ẩn và không phá bảo vệ OS.
- **Nghiệm thu M7:** danh sách nhiều thiết bị; UI căn cứ capabilities; chức năng điều khiển phải có quyền được cấp, hủy phiên được, thử trên phần cứng thật.
- Giải quyết CMOS/UPS/remote KVM là **hạ tầng phần cứng**, không phải milestone sửa code.

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
