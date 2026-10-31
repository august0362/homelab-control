# Server Control — Product & Technical Specification

> Status: **DRAFT v0.3** (2026-10-31: thêm FR-08 Mobile Background & Screen Control, giai đoạn M7 sau v1). v0.2 đã duyệt ở M0.  
> Phạm vi v1: **một chủ sở hữu**, **một Dell Linux server**, truy cập từ nhiều client qua browser. **Yêu cầu lâu dài đã chốt:** điện thoại/tablet cũng là thiết bị đích có thể được quản lý/điều khiển, không chỉ là client.

## 1. Actors, môi trường và quy ước

| ID | Actor / environment | Vai trò |
|---|---|---|
| AC-OWN | Owner | Người duy nhất được phép quản trị server qua UI ở v1 |
| AC-DEV | ASUS Windows | Viết code, chạy thử frontend + backend, kiểm thử dữ liệu máy ASUS |
| AC-SRV | Dell Linux Mint | Host production: API, metric collector, desktop ảo, file roots |
| AC-CL | Browser client | ASUS, Android, tablet (iOS/iPadOS nếu có) trên tailnet |
| AC-MOB | Future managed target | Điện thoại Android, tablet Android, iPhone/iPad: thiết bị cần quan sát, chuyển file, chia sẻ màn hình và có thể điều khiển theo quyền OS (sau v1) |

Phân biệt **desktop ảo** (một session Xvnc/XFCE của Dell) với **máy ảo** (guest OS riêng) và **màn hình vật lý** (console `:0`). V1 chọn **desktop ảo**; không cam kết chia sẻ chính xác màn hình vật lý.

## 2. Yêu cầu chức năng (FR)

### FR-01 — Dashboard hệ thống (P0)
- `FR-01.1`: Hiển thị tên thiết bị, OS, thời điểm cập nhật, trạng thái online/offline.
- `FR-01.2`: CPU tổng %, RAM used/total/%; ổ đĩa root used/total/%; uptime.
- `FR-01.3`: Lưu lượng mạng receive/transmit theo **bytes/s**, tính bằng delta counters giữa các mẫu; có xử lý reset counters, đổi interface.
- `FR-01.4`: Biểu đồ cập nhật chu kỳ khoảng **2 giây**, giữ lịch sử tối thiểu 10 phút trong RAM của browser. Không cần DB MVP.
- `FR-01.5`: Nhiệt độ CPU, pin và nguồn AC được hiển thị **nếu hỗ trợ**; nếu hỏng/thiếu dữ liệu, `N/A` + lý do. Không hiển thị 0% như một số đo tin cậy khi sensor lỗi.
- `FR-01.6`: Frontend xử lý đang tải, timeout, mất kết nối, kết nối lại, dữ liệu cũ và lỗi API rõ ràng.
- `FR-01.7`: Trong ASUS dev phải ghi nhãn **"Monitoring this ASUS"**. Trong Dell production ghi nhãn **"Monitoring Dell"**; không tráo nguồn dữ liệu. Nhãn mặc định lấy từ `DEVICE_LABEL`/`MACHINE_ROLE` (D-14); từ M2.5 owner đổi được tên trên UI (D-24), tên đặt trên UI được ưu tiên.

### FR-02 — Remote Desktop GUI (P0)
- `FR-02.1`: Có trang Remote Desktop tích hợp trong web, dùng chuột, bàn phím, cuộn, fullscreen và cơ chế phím bổ trợ trên mobile nếu khả thi.
- `FR-02.2`: Dell chạy một session **XFCE + TigerVNC Xvnc** ảo, độ phân giải mặc định thử nghiệm 1280×720.
- `FR-02.3`: Browser dùng **noVNC** qua WebSocket bridge của backend (`/api/desktop/ws`, D-26, không websockify); VNC chỉ listen Unix socket trên Dell hoặc được tunnel an toàn.
- `FR-02.4`: Có trạng thái Starting / Running / Disconnected / Stopped / Error; không hiển thị desktop giả như đang connected.
- `FR-02.5`: Cho phép khởi chạy/dừng desktop theo quyền có giới hạn; giữ SSH độc lập để cứu hộ. **Terminal có trong GUI**, không có Web Terminal page riêng.
- `FR-02.6`: Desktop ảo phải dùng chung filesystem, user và app Linux như SSH, nhưng là session đồ họa **khác** với màn hình vật lý.
- `FR-02.7`: Trong giai đoạn dev trên ASUS, trang này được scaffold hoặc tích hợp tới Dell test target; **không** hứa chạy desktop Linux thật khi chỉ có ASUS Windows.

### FR-03 — Files (P1)
- `FR-03.1`: Duyệt thư mục, breadcrumb, xem metadata cơ bản, upload/download file trong một/một số thư mục cấu hình.
- `FR-03.2`: Giới hạn root, chặn `..`, symlink escape, path traversal và truy cập file nhạy cảm; không chạy shell qua file names.
- `FR-03.3`: Có tiến độ, lỗi mạng và xử lý file trùng tên bằng chính sách rõ; giới hạn kích thước do owner cấu hình.
- `FR-03.4`: Trao đổi file qua browser ↔ server. Truyền trực tiếp giữa **hai thiết bị client** hoặc đồng bộ đa chiều là **giai đoạn sau**, không hàm ý tự có từ Files v1.
- `FR-03.5`: Lệnh xóa/ghi đè có xác nhận và chỉ bật sau khi có test; v1 có thể chỉ upload/download/rename nếu kiểm thử đạt.

### FR-04 — System & Services (P1)
- `FR-04.1`: Trạng thái service đã cho phép, uptime, logs gần đây có phân trang và giới hạn truy vấn.
- `FR-04.2`: Ban đầu **read-only**. Sau test mới mở `start/stop/restart` cho danh sách service cụ thể với xác nhận chủ sở hữu.
- `FR-04.3`: Không có endpoint nhận lệnh shell tùy ý, không truyền tham số trực tiếp vào `sudo`; không cho UI tự sửa firewall, SSH, Tailscale.
- `FR-04.4`: `shutdown`/`reboot` qua UI **tắt ở v1** do máy có lỗi BIOS/F1 sau mất điện, chỉ xem xét khi owner xác nhận đã khắc phục hoặc chấp nhận rủi ro.

### FR-05 — Truy cập, bảo mật và thiết bị (P0)
- `FR-05.1`: ASUS dev bind frontend/backend vào `127.0.0.1`; dev không tự mở cổng cho LAN.
- `FR-05.2`: Dell production bind API vào `127.0.0.1` và xuất bản HTTPS bằng **Tailscale Serve** trong tailnet; không dùng Funnel.
- `FR-05.3`: Có lớp xác thực chủ sở hữu và kiểm soát session/quyền trước khi cho phép các hành động quản trị; tailnet **không tự động thay thế** phân quyền app. **Đã chốt (D-23):** mật khẩu riêng của app, session cookie 1 năm (D-25); mọi `/api/*` trừ `/api/health` và `/api/auth/*` cần đăng nhập. Ngoại lệ D-25: dev trên ASUS bind loopback, truy cập qua tên loopback ⇒ không cần đăng nhập.
- `FR-05.4`: Chống CSRF cho action có tác dụng thay đổi trạng thái khi dùng cookie/session; validate Origin/WebSocket; rate-limit nếu phù hợp.
- `FR-05.5`: Không lưu token, mật khẩu, key vào repo hoặc log; có `.env.example` và file secrets riêng không commit.
- `FR-05.6`: Responsive ở desktop/tablet/mobile; smartphone truy cập remote GUI có thể khó thao tác do màn hình nhỏ nhưng phải dùng được tối thiểu.

### FR-07 — Mobile/tablet managed targets (P2 — sau v1, yêu cầu kiến trúc)
- `FR-07.1`: Phân biệt rõ **client** (thiết bị dùng trình duyệt để vào Server Control) và **managed target** (thiết bị bị giám sát/điều khiển). Điện thoại và tablet có thể đảm nhiệm cả hai vai trò.
- `FR-07.2`: Kiến trúc hỗ trợ `device_id`, `platform`, `device_type`, `online_status`, `capabilities` để về sau thêm Windows/Linux/Android/iOS mà không phải viết lại UI Dashboard hoặc toàn bộ backend.
- `FR-07.3`: Khả năng theo dõi trạng thái, gửi/nhận file, chia sẻ màn hình, điều khiển chuột/chạm/bàn phím phải **đàm phán theo capabilities** của từng loại thiết bị, không mặc định mọi nền tảng có quyền như Linux.
- `FR-07.4`: Android: nghiên cứu agent/ADB/scrcpy và điều kiện cấp quyền, kết nối USB/mạng; phải có đồng ý của chủ thiết bị, không tự động bật debug hay can thiệp vượt quyền.
- `FR-07.5`: iOS/iPadOS: ưu tiên khả năng nền tảng cho phép như chia sẻ màn hình hoặc file; có thể **không có điều khiển toàn màn hình từ xa**, phải mô tả giới hạn trung thực.
- `FR-07.6`: M7 chỉ được bắt đầu sau khi v1 ổn định; không thêm mobile runtime, agent, cổng hay permission mới vào MVP chỉ để dự phòng.
- `FR-07.7`: Không xây công cụ truy cập ẩn, điều khiển không đồng ý hoặc vượt cơ chế bảo mật của hệ điều hành; mỗi thiết bị có thể từ chối/ngắt phiên.

### FR-08 — Mobile Background & Screen Control (P2 — sau v1, M7D)

Owner dùng Server Control trên ASUS để quản lý điện thoại/tablet **đã đăng ký** (managed target, FR-07.1). Mọi hành vi trên thiết bị do **companion agent** có sự đồng ý của chủ thiết bị thực hiện. Tailscale chỉ là đường truyền; một thiết bị chỉ cài Tailscale thì chưa có agent và chưa điều khiển được. Kiến trúc chi tiết: `ARCHITECTURE.md` §4A.

**A. Background operations**
- `FR-08.1`: Danh sách thiết bị hiển thị online/offline theo **heartbeat của agent** (`last_seen` trong ngưỡng), không theo việc thiết bị có trong tailnet. Thiết bị chưa đăng ký agent hiển thị "chưa đăng ký", không có nút điều khiển.
- `FR-08.2`: Owner yêu cầu bật/tắt hoạt động nền của agent, **trong giới hạn hệ điều hành**. Nếu OS không cho phép, hiển thị `unsupported` hoặc `denied` kèm lý do.
- `FR-08.3`: Trạng thái điều khiển chỉ có các giá trị `enabled | disabled | pending | denied | unsupported | offline | error`, theo quy tắc ở `ARCHITECTURE.md` §4A.4.
- `FR-08.4`: Tách **desired** (owner yêu cầu) và **reported** (thiết bị xác nhận, có `reported_at`). UI hiển thị reported là trạng thái thật; khi hai giá trị khác nhau thì hiển thị cả hai.
- `FR-08.5`: Không giả định agent chạy nền vĩnh viễn. OS, chế độ tiết kiệm pin hoặc người dùng có thể dừng agent; mất heartbeat ⇒ `offline`. UI không được ghi "luôn chạy".

**B. Keep screen awake**
- `FR-08.6`: Owner yêu cầu bật/tắt giữ màn hình sáng. Chế độ này chỉ có hiệu lực khi **ứng dụng điều khiển (agent app hoặc trang Server Control) đang hiển thị** và màn hình chưa khóa. Reported state có thêm `active` (đang thực sự giữ sáng hay không).
- `FR-08.7`: Hỗ trợ **tablet dashboard mode**: tablet mở Dashboard toàn màn hình và giữ sáng. Ưu tiên Screen Wake Lock API của trình duyệt (cần HTTPS, có qua Tailscale Serve) hoặc dùng agent app. Ghim màn hình / Guided Access do owner tự bật trên thiết bị.
- `FR-08.8`: **Giữ sáng ≠ đánh thức.** FR-08 không bật màn hình đã tắt/khóa từ xa và không có lệnh `wake_screen`. Nếu cần về sau thì đó là capability riêng, chỉ thêm sau khi kiểm chứng trên thiết bị thật.

**C. Capabilities**
- `FR-08.9`: Bổ sung `background_operations`, `keep_screen_awake`. Giữ nguyên các tên M7 đã có: `screen_view`, `remote_input`, `file_transfer` (triển khai ở M7B, không thuộc FR-08). `files` là File Manager trên server (M4); `file_transfer` là truyền file tới/từ thiết bị đích. Hai tên này không trùng nghĩa.

**D. Android và iOS/iPadOS** (mọi giới hạn dưới đây đều **[cần xác minh trên thiết bị thật]**, chi tiết ở `ARCHITECTURE.md` §4A.5)
- `FR-08.10`: Android dùng companion app có chủ thiết bị đồng ý. Chạy nền bằng foreground service, luôn có notification hiển thị. Giữ sáng bằng cờ cửa sổ khi app đang hiển thị. Quyền (thông báo, miễn tối ưu pin…) do chủ thiết bị tự cấp qua hộp thoại/Settings của OS.
- `FR-08.11`: iOS/iPadOS không có cơ chế chạy nền liên tục cho agent kiểu này ⇒ `background_operations` mặc định `unsupported`. Giữ sáng chỉ khi app/trang web đang hiển thị. Không có API công khai để điều khiển input toàn hệ thống. Agent native cần macOS + Xcode; owner không có Mac và hiện không có thiết bị iOS (D-22) ⇒ chỉ giữ ở mức thiết kế.
- `FR-08.12`: Không root/jailbreak, không tự bật quyền nguy hiểm hay USB/wireless debugging, không chạy ẩn, không vượt cơ chế bảo mật OS. Chủ thiết bị luôn có thể tắt agent, thu hồi quyền hoặc gỡ app.

**E. Command lifecycle**
- `FR-08.13`: Mỗi lệnh đi qua `requested → delivered → acknowledged → applied | denied | failed | timed_out`. Lệnh có `command_id` (server sinh), `device_id`, `type`, `params`, `requested_by`, timestamp từng bước, `expires_at`, `result {code, message}`.
- `FR-08.14`: `type` thuộc **enum cố định** (`set_background_operations`, `set_keep_screen_awake`); `params` được validate theo schema. Không có lệnh shell hay lệnh tự do gửi tới thiết bị (mở rộng D-15).
- `FR-08.15`: Trước khi tạo lệnh, kiểm tra 3 điều: owner đã xác thực (M2.5), thiết bị đã đăng ký và chưa bị thu hồi, capability ở trạng thái `supported`. Không đạt ⇒ trả lỗi `{code, message}` và không tạo lệnh.
- `FR-08.16`: **Không báo thành công khi mới gửi lệnh.** Chỉ `applied` (agent xác nhận đã áp dụng) mới được hiển thị là thành công. Ở các bước trước, UI hiện "đang chờ thiết bị". Quá hạn ⇒ `timed_out`. Agent bỏ qua lệnh trùng `command_id`.
- `FR-08.17`: Mọi lệnh và kết quả được ghi audit log có giới hạn dung lượng, không chứa token.

### FR-06 — Deployment/operations (P0)
- `FR-06.1`: Cùng source code chạy được trên Windows và Linux; platform-specific provider chỉ khác chỗ đọc metrics, services, desktop.
- `FR-06.2`: Build frontend trên ASUS; Dell phục vụ static build và backend qua **một origin**; không chạy Vite dev server trên Dell production.
- `FR-06.3`: App backend chạy bằng systemd non-root với restart on failure; healthcheck và log giới hạn.
- `FR-06.4`: Có script/tài liệu backup cấu hình, build, cập nhật, rollback; không làm thay đổi SSH/Tailscale mạng đang dùng nếu chưa có phương án cứu hộ.
- `FR-06.5`: Chỉ tuyên bố "auto resume after normal reboot" sau khi đã test; **không tuyên bố "power outage recovery"** khi BIOS yêu cầu F1.

## 3. Non-functional requirements (NFR)

| ID | Yêu cầu | Mức/gate thử nghiệm |
|---|---|---|
| NFR-01 | Footprint nhẹ | Production ưu tiên CPU/RAM thấp, không bắt buộc Docker/DB. Đo RSS của từng service trên Dell trước khi chốt. |
| NFR-02 | Realtime ổn định | Poll metrics ~2s; refresh không tạo tiến trình vô hạn; không đòi hard realtime. |
| NFR-03 | Không bịa chỉ số | Sensor thiếu/trả lỗi => `null` + `status`, không gán 0 giả. |
| NFR-04 | Khả năng phục hồi | Mất Wi-Fi/API phải hiển thị offline và tự retry; systemd restart nếu backend crash. |
| NFR-05 | Bảo mật | No shell executor, bind localhost, tailnet-only, auth owner, allowlist operation. |
| NFR-06 | Portability | Windows dev và Linux prod có cùng API schema; adapter không hỗ trợ trả trạng thái rõ. |
| NFR-07 | UX | Responsive 360px → desktop; keyboard/desktop functionality rõ giới hạn touch. |
| NFR-08 | Testability | Backend API tests + frontend build/test; smoke test mạng và VNC trên Dell. |
| NFR-09 | Sử dụng tài nguyên | VNC/XFCE được bật theo nhu cầu; không bật khi server idle nếu không cần. |
| NFR-10 | Bảo trì | Lệnh setup/run/build/deploy/rollback trong README; tài liệu re-entry 10 phút. |
| NFR-11 | Trạng thái điều khiển trung thực (M7) | Không có `applied` nếu agent chưa xác nhận; mọi reported state có `reported_at`; lệnh luôn kết thúc (có timeout). |
| NFR-12 | Nhẹ cho Dell và pin mobile (M7) | Không thêm tiến trình/dịch vụ mới trên Dell; agent dùng heartbeat/long-poll có chu kỳ cấu hình được; đo mức hao pin trên thiết bị thật trước khi chốt chu kỳ. |
| NFR-13 | Bảo mật thiết bị (M7) | Token riêng từng thiết bị, thu hồi được, server chỉ lưu hash; agent chỉ đọc lệnh của chính nó; không mở cổng lắng nghe trên điện thoại/tablet. |

## 4. API contract dự kiến (có thể đổi trước M2)

```text
GET  /api/health           -> {status, timestamp, version}
GET  /api/system           -> {timestamp, device, os, hardware, capabilities}
POST /api/auth/login       -> {password} -> 204 + session cookie | 401 | 429 (M2.5)
POST /api/auth/logout      -> 204, xóa cookie (M2.5)
GET  /api/auth/session     -> {authenticated, login_required, configured, expires_at?} (public, M2.5; login_required=false = dev loopback, D-25)
PATCH /api/device          -> {label: string | null} -> device; null = về mặc định (M2.5, owner + CSRF)
GET  /api/metrics          -> {timestamp, device, cpu, memory, swap, disk, network, uptime_seconds, sensors{temperature, fans, battery, ac}}
GET  /api/desktop/status   -> {status, message, label, can_control, viewers, connection_url} (M3)
POST /api/desktop/start    -> 204 | 409 desktop_unmanaged | 503 desktop_not_configured (owner + CSRF, M3)
POST /api/desktop/stop     -> như start; đóng luôn các viewer đang mở (M3)
WS   /api/desktop/ws       -> byte RFB browser <-> VNC; Origin + session kiểm lúc mở, sai -> đóng 1008 (M3, D-26)
GET  /api/power            -> {available, reachable, label, sleeping_since, tasks[{unit, scope, active}], message} (D-27)
POST /api/power/sleep      -> {stopped}: ngủ nhẹ, tắt các tác vụ tùy chọn đang chạy và ghi nhớ (owner + CSRF)
POST /api/power/wake       -> {started}: bật lại đúng những gì sleep đã tắt
POST /api/power/cleanup    -> {stopped}: tắt mọi tác vụ tùy chọn, không ghi nhớ ("reset nhẹ")
POST /api/power/reboot     -> {confirm: "reboot"} -> 204; KHÔNG có tắt nguồn (D-27)
GET  /api/files/*          -> limited to configured roots (M4)
GET  /api/services         -> allowlisted service statuses (M5)
POST /api/services/{id}/restart -> disabled until M5 authorization verified
```

- Mọi payload phải có `timestamp` hoặc `last_updated` để nhận biết dữ liệu cũ.
- `device` = `{id, label, label_source, role, platform, device_type}` (FR-07.2). `label_source` = `custom` (đặt trên UI, D-24) | `env` (`DEVICE_LABEL`) | `hostname`. `id` ổn định, không phụ thuộc IP/hostname: env `DEVICE_ID`, nếu trống thì UUID sinh một lần và lưu ở `backend/.state/device_id` (gitignored). `online_status`/`last_seen` thuộc device registry ở M7.
- `capabilities` = map `{tên: {status, message}}`, `status ∈ supported | unsupported | not_configured | requires_consent`. Tên v1: `metrics`, `temperature`, `fans`, `battery`, `desktop`, `files`, `services`. M7 bổ sung `screen_view`, `remote_input`, `file_transfer`, `background_operations`, `keep_screen_awake` (FR-08.9). Capability nói thiết bị **có thể** làm gì; trạng thái bật/tắt hiện tại là **control state** riêng (FR-08.3).
- `device_type` v1 = `computer`; M7 thêm `phone`, `tablet`.
- v1 giữ endpoint phẳng cho thiết bị local; M7 thêm `/api/devices/{id}/...`, endpoint phẳng thành alias của thiết bị local.
- M7D (dự kiến, chốt khi làm): `GET /api/devices`, `POST /api/devices/{id}/commands` → `202 {command_id, status: "requested"}`, `GET /api/devices/{id}/commands/{command_id}`; nhóm `/api/agent/*` (enroll, heartbeat/state, lấy lệnh, ack, result) chỉ nhận token thiết bị. Xem `ARCHITECTURE.md` §4A.3.
- `/api/metrics` không truyền password/token; field invalid/unsupported phải có trạng thái dễ nhận biết: mỗi nhóm là `{status, data, message}`, `status ∈ ok | unsupported | unavailable | error`, `data = null` khi không phải `ok`.
- Error format ổn định (`code`, `message`, `request_id?`) để frontend xử lý.
- `GET /api/desktop/status`: `status ∈ not_configured | stopped | starting | running | error`; `running` = VNC trả banner RFB; `connection_url` chỉ có khi `running`; `can_control=false` khi không đặt `DESKTOP_UNIT` (start/stop làm trên server); `label` = máy sở hữu desktop. **Không trả token/mật khẩu VNC trong dữ liệu công khai**.

## 5. Acceptance criteria (AT)

| ID | Phương pháp nghiệm thu |
|---|---|
| AT-01 | Chạy frontend + backend trên ASUS; Dashboard đọc được CPU/RAM/disk của ASUS và ghi đúng nguồn. |
| AT-02 | Giết backend hoặc tắt mạng: UI hiện offline/stale và tự hồi phục sau khi dịch vụ trở lại. |
| AT-03 | Frontend build trên ASUS; server Dell chạy được bản build mà không cần npm dev server. |
| AT-04 | Browser trong tailnet mở HTTPS app; máy ngoài tailnet không truy cập được; không public port. |
| AT-05 | Desktop XFCE ảo trên Dell hiển thị qua web; chuột/keyboard hoạt động; mở terminal **trong desktop** và `hostname` cho Dell. |
| AT-06 | Tắt desktop ảo không làm dừng monitoring/API/SSH/Tailscale. |
| AT-07 | Upload/download file hợp lệ thành công; `../` và symlink escaping bị từ chối. |
| AT-08 | Người chưa xác thực không thể gọi endpoints thay đổi trạng thái; lỗi được ghi log không chứa bí mật. |
| AT-09 | Restart backend bằng systemd; phục hồi sau reboot Linux bình thường; giới hạn outage/F1 được ghi rõ. |
| AT-10 | Thiết bị di động trong tailnet sử dụng được Dashboard, Files và điều khiển GUI ở mức cơ bản. |

## 6. Chưa quyết định — không tự đoán

1. Danh sách thư mục file được quản lý (`~/Documents`, một thư mục dedicated, v.v.) và giới hạn upload.
2. ~~Cơ chế xác thực production~~: **đã chốt mật khẩu riêng của app** (D-23); Tailscale identity có thể bổ sung sau M6.
3. Các service được phép restart và có cần nhập lại mật khẩu khi thực hiện thao tác nhạy cảm không.
4. Giao diện đồ họa có dùng XFCE ảo riêng hay ưu tiên chia sẻ console thật? **Đang chọn mặc định XFCE ảo**, có thể điều chỉnh nếu owner cần chia sẻ chính xác desktop vật lý.
5. Lưu lịch sử metrics lâu dài (SQLite) và thông báo cảnh báo qua điện thoại: không thuộc MVP.
6. Khi bổ sung giám sát nhiều máy, từng máy có agent hay API proxy theo SSH: để milestone sau.
7. FR-08: model/phiên bản OS của điện thoại/tablet, công nghệ và cách phân phối agent Android, nơi lưu registry, có cần agent iOS native không, chu kỳ heartbeat/timeout: xem `CONTEXT.md` O-07..O-11.

### Acceptance criteria cho mở rộng M7 (không dùng để nghiệm thu v1)
- `AT-M7-01`: Danh sách thiết bị phân biệt browser client và managed target; hiển thị platform/capabilities từ dữ liệu thật.
- `AT-M7-02`: Tính năng không hỗ trợ trên Android/iOS hiển thị rõ lý do, không hiện nút điều khiển giả hoặc trạng thái thành công giả.
- `AT-M7-03`: Chỉ truy cập thiết bị được chủ sở hữu cho phép; kết thúc phiên hoặc thu hồi quyền phải làm mất quyền điều khiển tương ứng.
- `AT-M7-04`: Trước khi tuyên bố đã điều khiển được Android/iPad/iPhone, bắt buộc kiểm thử trên thiết bị thật và ghi rõ giới hạn theo OS.
- `AT-M7-05` (FR-08.1): Tắt agent hoặc mạng trên thiết bị ⇒ sau ngưỡng heartbeat UI chuyển `offline`; bật lại ⇒ `online`. Thiết bị chỉ có Tailscale, chưa có agent ⇒ hiển thị "chưa đăng ký".
- `AT-M7-06` (FR-08.13/16): Gửi lệnh tới thiết bị offline ⇒ `requested` rồi `timed_out`, **không bao giờ** hiện thành công. Gửi tới thiết bị online ⇒ đủ các bước tới `applied`, có timestamp từng bước.
- `AT-M7-07` (FR-08.2/10): Trên Android thật, bật background ⇒ notification foreground service xuất hiện và agent vẫn gửi heartbeat sau khi tắt màn hình N phút (N chốt khi test). Tắt ⇒ notification biến mất. Kết quả ghi theo model/phiên bản Android.
- `AT-M7-08` (FR-08.6/7): Tablet ở dashboard mode giữ sáng quá thời gian tự tắt màn hình của OS khi trang/app đang hiển thị; chuyển app khác hoặc khóa máy ⇒ `active=false`. Không có lệnh nào bật được màn hình đã khóa.
- `AT-M7-09` (FR-08.11/12): Trên iPhone/iPad, `background_operations` hiển thị `unsupported` kèm lý do; không có nút điều khiển giả.
- `AT-M7-10` (FR-08.15/NFR-13): Chưa xác thực owner, token thiết bị bị thu hồi, sai `device_id` hoặc capability không `supported` ⇒ bị từ chối và không tạo lệnh. Agent không đọc được lệnh của thiết bị khác.
- `AT-M7-11` (FR-08.12): Chủ thiết bị từ chối quyền trên OS ⇒ kết quả `denied` hiển thị đúng; không có bước nào tự cấp quyền hay yêu cầu root/jailbreak.

## 7. Tham chiếu chính thức

- Tailscale Serve: https://tailscale.com/docs/features/tailscale-serve
- Tailscale CLI Serve: https://tailscale.com/docs/reference/tailscale-cli/serve
- noVNC: https://novnc.com/
- TigerVNC Xvnc: https://tigervnc.org/doc/Xvnc.html
