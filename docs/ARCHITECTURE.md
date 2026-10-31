# Server Control — Architecture

> Status: DRAFT v0.3 (2026-10-31: thêm §4A Mobile Device Control cho FR-08, M7). Chiến lược: **modular monolith**, không phải nhiều server/microservice.

## 1. Kiến trúc tổng quan

```mermaid
flowchart TB
    U[Browser: ASUS / phone / tablet] -->|HTTPS in tailnet| TS[Tailscale Serve]
    TS -->|localhost| APP[FastAPI app + built React static]
    APP --> MET[Metrics adapter: psutil / sensors]
    APP --> FILES[Scoped files adapter]
    APP --> SVC[Allowlisted systemd services]
    APP --> WS[Authorized WebSocket proxy]
    WS -->|localhost| WEB[websockify]
    WEB -->|localhost| VNC[TigerVNC Xvnc + XFCE]
    subgraph Dell_Linux_Production["Dell Linux production (RAM ~4 GB)"]
      TS
      APP
      MET
      FILES
      SVC
      WS
      WEB
      VNC
    end
```

**Diễn giải:** browser không kết nối thẳng VNC/SSH public. Tailscale Serve nhận HTTPS riêng trong tailnet và chuyển về app ở loopback. Frontend chỉ gọi cùng origin. Agent metrics là module nội bộ của backend, không phải dịch vụ riêng trong MVP. Hướng reverse proxy WebSocket cần được kiểm thử trên môi trường thực, tránh giả định mặc định mọi proxy route đều tương thích.

### Hướng mở rộng multi-device (sau v1, chưa triển khai)

V1 tập trung một Dell. Tuy nhiên hệ thống **không được đồng nhất "thiết bị" với "trình duyệt đang mở web"**. Trong tương lai, mobile/tablet có thể là thiết bị đích được quản lý từ ASUS hoặc từ một trình duyệt khác.

```mermaid
flowchart TB
    UI[Server Control Web: quản lý các thiết bị] --> REG[Device registry + capabilities]
    REG --> LINUX[Linux adapter: Dell + Linux khác]
    REG --> WINDOWS[Windows adapter: ASUS + PC khác]
    REG --> ANDROID[Android adapter / consented agent / ADB bridge - future]
    REG --> IOS[iOS/iPadOS limited adapter - future]
    ANDROID -.-> A[Phone / Tablet Android]
    IOS -.-> I[iPhone / iPad: only OS-permitted functions]
```

- Khóa định danh thiết bị (`device_id`) độc lập khỏi URL/IP Tailscale; có `platform`, `device_type`, `capabilities`, `last_seen`.
- `capabilities` quyết định được xem metrics, file transfer, screen view, remote input hay không. **Không thiết kế UI giả định iOS/Android có quyền điều khiển giống Dell**.
- Phần **transport** (Tailscale/SSH/USB) tách khỏi phần **control adapter** (Linux, Windows, Android, iOS) và phần **authorization/consent**.
- Chỉ chuẩn bị ranh giới module và schema có thể mở rộng; không triển khai microservices hoặc mobile agents khi đang làm v1.
- Điều khiển nền/màn hình mobile (FR-08) là module trong cùng backend, xem §4A.

## 2. Development trên ASUS

```mermaid
flowchart LR
    B[ASUS browser] -->|localhost:5173| FE[Vite/React dev]
    FE -->|/api proxy| API[FastAPI localhost:8000]
    API --> W[Windows psutil / capabilities]
    FE -.->|UI placeholder or secured test connector| DX[Dell test target via Tailscale]
```

- Frontend dev dùng Vite + React + TypeScript.
- Backend dev dùng Python 3.12+ khi có trên ASUS (phiên bản Windows **chưa xác minh**), FastAPI + Uvicorn + psutil.
- `Vite proxy` cùng path `/api` để giảm CORS trong dev; không public dev server.
- Unit/API test, build, layout và simulated desktop states trên ASUS.
- **Chỉ test desktop Dell thật khi đã có Dell VNC**. Việc này là tích hợp có kiểm soát, không đồng nghĩa deploy web production sớm.
- Không lấy CPU Dell khi API trên ASUS đang đọc local Windows, trừ khi có kết nối/agent rõ ràng.

## 3. Production trên Dell

```text
Tailscale tailnet
      |
 Tailscale Serve [HTTPS]
      |
 127.0.0.1:8000   FastAPI (systemd, non-root)
      |-- /          frontend/dist static (SPA fallback)
      |-- /api/*     API + auth + metrics + files + services
      `-- /desktop-ws  authenticated WebSocket proxy
                                |
                      127.0.0.1:6080 websockify
                                |
                      127.0.0.1:5901 TigerVNC Xvnc :1
                                |
                           XFCE session
```

- Static build tạo ở ASUS, chép lên Dell cùng backend code/config.
- Backend chạy `127.0.0.1`, dưới user hạn chế, do systemd giám sát.
- Xvnc không tự bật toàn thời gian nếu không cần; XFCE được khởi chạy trong session ảo và không yêu cầu monitor vật lý.
- VNC và websockify chỉ bind loopback; kiểm tra lại bằng `ss -lntp` sau setup.
- **Lưu ý WebSocket:** nếu proxy auth/route tùy chỉnh gây phức tạp, có thể dùng một reverse proxy nhỏ đã được kiểm thử hoặc một endpoint bridge riêng. Không được mở websockify thẳng ra WAN/tailnet như cách né khó. Giải pháp cuối phải được ghi lại khi M3 hoàn thành.

## 4. Components

| Module | Trách nhiệm | Không làm |
|---|---|---|
| `frontend` | Dashboard, charts, responsive nav, VNC viewer, Files, System | Không chứa server credentials, không execute shell |
| `backend/api` | HTTP endpoints, schema validation, auth, access policy | Không đọc filesystem tùy tiện, không chạy command do browser đưa lên |
| `backend/services/metrics` | psutil + optional sensors; normalized metrics | Không lưu DB hay scan máy khác ở MVP |
| `backend/services/files` | thao tác tệp trong configured roots | Không expose `/etc`, home root hay toàn disk |
| `backend/services/system` | trạng thái dịch vụ allowlist và logs giới hạn | Không `sudo` tùy ý hoặc edit firewall |
| `backend/services/desktop` | quản lý trạng thái session VNC và websockify | Không xử lý raw video encoding từ đầu |
| `deploy/linux` | systemd, env template, healthcheck, deploy/rollback docs | Không cấu hình lại BIOS hoặc thay đổi mạng bắt buộc |
| `backend/services/devices` (M7) | Device registry, enrollment, heartbeat, capabilities của thiết bị đích | Không quét mạng/tailnet để tự thêm thiết bị |
| `backend/services/device_control` (M7D) | Command lifecycle, desired/reported state, audit lệnh | Không gửi lệnh tự do/shell, không kết nối chủ động vào điện thoại |
| Companion agent (M7D, ngoài repo hoặc thư mục riêng) | Chạy trên thiết bị đích, áp dụng lệnh trong quyền OS, báo trạng thái | Không root/jailbreak, không chạy ẩn, không mở cổng lắng nghe |

## 4A. Mobile Device Control module (FR-08, M7D — chưa triển khai)

### 4A.1 Vị trí trong modular monolith

```mermaid
flowchart LR
    OWN[Owner browser ASUS] -->|HTTPS tailnet + owner session| API
    subgraph APP["FastAPI trên Dell (một tiến trình)"]
      API[api/devices + api/agent]
      AUTH[Auth + authorization M2.5]
      REG[Device registry + enrollment]
      CAP[Capabilities]
      DC[Device control: commands + desired/reported]
      ST[(STATE_DIR store)]
      AUD[Audit log]
      API --> AUTH --> DC
      DC --> REG
      DC --> CAP
      DC --> ST
      DC --> AUD
      REG --> ST
    end
    AND[Android companion agent] -->|outbound HTTPS qua Tailscale + device token| API
    WEB[Tablet web companion: trang Server Control] -->|same origin + device token| API
```

- **Device registry** (M7A): bản ghi `{device_id, label, platform, device_type, agent: {kind, version}, enrollment: pending|active|revoked, last_seen, capabilities}`. Một thiết bị có thể vừa là **client** (mở web) vừa là **managed target** (có agent đã đăng ký); hai vai trò này độc lập nhau. Mở web trên điện thoại không tự đăng ký điện thoại đó.
- **Capabilities:** agent tự khai báo trong heartbeat; server dùng kết quả đó để quyết định UI và kiểm tra lệnh. Không suy luận từ `platform`.
- **Authorization:** owner session (M2.5) cho `/api/devices/*`; token thiết bị cho `/api/agent/*`. Một token chỉ đọc/ghi được dữ liệu của chính thiết bị đó. Phía thiết bị, quyền OS do chủ thiết bị cấp là lớp đồng ý thứ hai.
- **Platform adapters:** phía server không có adapter điều khiển mobile. Việc gọi API của OS nằm trong agent (Android app, web companion). Server chỉ biết `type` lệnh, capability và kết quả.
- **Command transport:** agent **chủ động kết nối ra** server (heartbeat + long-poll lấy lệnh) qua URL Tailscale Serve nhập khi enroll, không hardcode IP. Server không cần với tới điện thoại, nên điện thoại không mở cổng nào. Transport tách khỏi device control: sau này có thể đổi sang WebSocket mà không đổi lifecycle.
- **Store:** registry, hash token và desired/reported state cần sống qua restart. Mặc định dùng file JSON trong `STATE_DIR` (không DB, ADR-003); chuyển sang SQLite nếu lịch sử/audit lớn (O-09). Lệnh đang chạy giữ trong bộ nhớ và được ghi xuống audit khi kết thúc.

### 4A.2 Command lifecycle

```mermaid
stateDiagram-v2
    [*] --> requested: owner tạo lệnh, đã qua authorization
    requested --> delivered: agent lấy lệnh
    requested --> timed_out: quá delivery TTL
    delivered --> acknowledged: agent ack, params hợp lệ
    delivered --> timed_out: không có ack
    acknowledged --> applied: OS áp dụng, agent gửi reported state
    acknowledged --> denied: OS hoặc chủ thiết bị từ chối
    acknowledged --> failed: lỗi khi thực thi
    acknowledged --> timed_out: không có kết quả
    applied --> [*]
    denied --> [*]
    failed --> [*]
    timed_out --> [*]
```

```mermaid
sequenceDiagram
    autonumber
    participant O as Owner UI (ASUS)
    participant S as FastAPI device control
    participant A as Agent (phone/tablet)
    O->>S: POST /api/devices/{id}/commands
    S->>S: owner auth, enrollment, capability supported, schema
    S-->>O: 202 command_id, requested
    Note over O: UI hiện "đang chờ thiết bị", chưa báo thành công
    A->>S: GET /api/agent/commands (long-poll, device token)
    S-->>A: lệnh, đánh dấu delivered
    A->>S: POST ack
    A->>A: gọi API hệ điều hành trong quyền đã cấp
    alt OS cho phép
        A->>S: POST result applied + reported state
    else bị từ chối hoặc lỗi
        A->>S: POST result denied hoặc failed + reason
    end
    O->>S: GET command / device (poll)
    S-->>O: status cuối + reported state + timestamps
```

- `delivered` do server ghi nhận khi trả lệnh cho agent; `acknowledged` và `applied|denied|failed` do agent xác nhận. `timed_out` do server quyết định theo `expires_at`.
- Hằng số khởi điểm: delivery TTL ~60 s, hạn chờ kết quả ~30 s. Giá trị sẽ chỉnh trên thiết bị thật (O-11).
- Kết quả đến sau `timed_out` chỉ được ghi audit, trạng thái lệnh giữ nguyên. Reported state vẫn cập nhật từ heartbeat.
- Agent lưu các `command_id` đã xử lý gần đây để không áp dụng một lệnh hai lần.
- Không tự gửi lại desired state khi thiết bị online trở lại. Owner gửi lệnh mới nếu muốn, để tránh hành động bất ngờ (O-11).

### 4A.3 API dự kiến (chốt khi làm M7D)

```text
GET  /api/devices                              owner: danh sách + online/last_seen + capabilities + controls
POST /api/devices/{id}/commands                owner + CSRF: {type, params} -> 202 {command_id, status}
GET  /api/devices/{id}/commands/{command_id}   owner: trạng thái lệnh
POST /api/devices/{id}/revoke                  owner: thu hồi token thiết bị
POST /api/agent/enroll                         pairing code một lần (hiện trên web, nhập ở thiết bị) -> device token
POST /api/agent/heartbeat                      token: capabilities + reported state
GET  /api/agent/commands?wait=25               token: long-poll lệnh của chính thiết bị
POST /api/agent/commands/{command_id}/ack      token
POST /api/agent/commands/{command_id}/result   token: applied|denied|failed + {code, message} + reported
```

### 4A.4 Control state hiển thị (FR-08.3)

Mỗi control (`background_operations`, `keep_screen_awake`) có `desired`, `reported {value, active?, reported_at}` và lệnh gần nhất. UI xét các điều kiện theo thứ tự sau, gặp điều kiện đầu tiên thì dừng:

| Hiển thị | Điều kiện |
|---|---|
| `unsupported` | capability `unsupported` (kèm lý do của agent/OS) |
| `offline` | quá ngưỡng heartbeat; vẫn hiện reported cuối + thời điểm |
| `pending` | có lệnh chưa kết thúc |
| `denied` | lệnh gần nhất `denied` hoặc capability `requires_consent` |
| `error` | lệnh gần nhất `failed`/`timed_out` |
| `enabled` / `disabled` | theo `reported.value` |

`denied`/`error` được hiển thị kèm reported value và mất đi khi owner gửi lệnh mới. Với `keep_screen_awake`, `enabled` + `active=false` nghĩa là đã bật nhưng chỉ có hiệu lực khi app/trang đang hiển thị.

### 4A.5 Giới hạn nền tảng (tất cả **[cần xác minh trên thiết bị thật]**)

| Capability | Android companion app | iOS/iPadOS | Web companion (trang Server Control trên tablet) |
|---|---|---|---|
| `background_operations` | Foreground service + notification thường trực. Android 14+ phải khai báo loại foreground service. Android 12+ cấm bắt đầu foreground service khi app đang ở nền, nên lệnh "bật" chỉ áp dụng được khi agent đang chạy. Doze và trình quản lý pin của hãng có thể dừng agent; miễn tối ưu pin do chủ thiết bị tự bật. Thiết bị owner: Xiaomi (HyperOS/MIUI: Autostart, Battery saver) và Samsung (One UI: Sleeping apps) đều nổi tiếng dừng app nền ⇒ cần xác minh riêng từng máy. | Không có cơ chế chạy nền liên tục cho agent; BGTaskScheduler/silent push do OS quyết định và cần APNs ⇒ `unsupported` | `unsupported` (tab nền bị throttle/suspend) |
| `keep_screen_awake` | `FLAG_KEEP_SCREEN_ON` khi activity đang hiển thị; không cần quyền đặc biệt | `isIdleTimerDisabled` khi app đang foreground | Screen Wake Lock API khi trang hiển thị và có HTTPS; hỗ trợ Safari/iPadOS theo phiên bản (cần xác minh, kể cả khi thêm vào màn hình chính) |
| Bật màn hình đã khóa | Chỉ dành cho kiểu báo thức/cuộc gọi ⇒ **ngoài phạm vi** | Không có ⇒ ngoài phạm vi | Không có |
| `screen_view` (M7B) | MediaProjection, người dùng đồng ý mỗi phiên | ReplayKit broadcast, người dùng tự bắt đầu | Không |
| `remote_input` (M7B) | AccessibilityService do chủ thiết bị tự bật (nhạy cảm) hoặc ADB/scrcpy có ủy quyền | Không có API công khai ⇒ `unsupported` | Không |
| Kiosk/dashboard | Ghim màn hình thủ công; lock task mode cần device owner ⇒ ngoài phạm vi | Guided Access do owner bật thủ công | Fullscreen + ghim/Guided Access thủ công |

Agent iOS native cần macOS + Xcode + Apple ID/Developer Program; owner không có Mac và thiết bị đích hiện tại đều là Android (D-22). Nếu sau này có iPad thì đi đường **web companion**.

## 5. Data model (định hướng, chưa khóa schema)

```json
{
  "timestamp": "2026-10-31T10:00:00+07:00",
  "source": "local-host",
  "device": {"id": "<uuid>", "label": "Dell", "role": "production", "platform": "linux", "device_type": "computer"},
  "cpu": {"usage_percent": 12.5},
  "memory": {"used_bytes": 1000000000, "total_bytes": 3900000000},
  "disk": {"mount": "/", "used_bytes": 1000, "total_bytes": 2000},
  "network": {"rx_bytes_per_sec": 1000, "tx_bytes_per_sec": 500},
  "sensors": {"battery": {"value": null, "status": "unavailable"}},
  "uptime_seconds": 21000
}
```

Đây là schema **minh họa**, không phải sample đo thật. Phân biệt `bytes total` và `bytes/s`. Frontend có thể rolling history 10 phút in-memory. Nếu cần data lịch sử ngày/tuần mới xem xét SQLite theo một quyết định mới.

## 6. Security boundaries

1. **Network:** chỉ tailnet HTTPS qua Tailscale Serve; không router forwarding; backend và VNC bind localhost.
2. **Identity:** owner cần cơ chế xác thực đáng tin cậy trong app hoặc thông qua Tailscale identity được kiểm chứng chặt chẽ; không tin header tự gửi từ client, không tin `X-Forwarded-*` tùy tiện. Nếu dùng headers Tailscale, chỉ chấp nhận khi backend không thể bị gọi bỏ qua reverse proxy.
3. **Authorization:** metrics/read-only có thể đơn giản nhưng nên bảo vệ app; files & service actions phải xác thực, validate resource, CSRF/Origin tương ứng.
4. **Filesystem:** root allowlist, resolve realpath rồi kiểm tra containment; cấm symlink bypass. Chặn upload file quá giới hạn; sanitize file name.
5. **Process:** không gọi shell từ request. Nếu cần điều khiển vài service, dùng wrapper được kiểm soát (policykit/sudoers hẹp) và ghi audit; không cấp sudo toàn backend.
6. **Desktop:** VNC credential lưu ngoài Git; không hiển thị trên UI/log; WebSocket handshake authenticated. Session của GUI chạy với user thường.
7. **Observability:** log request failures, trạng thái services, desktop lifecycle; không ghi password/token, lọc path/PII nhạy cảm.
8. **Disaster:** lỗi BIOS/F1 không chữa bằng software. Không tuyên bố tự khởi động sau mất điện cho tới khi sửa/kiểm chứng độc lập.

## 7. Resource budget và trade-off

- Dell i5-3337U, ~3.7 GiB RAM, HDD. Ưu tiên một FastAPI process, frontend static, không phát triển build trực tiếp trên Dell.
- Polling 2s phù hợp MVP đơn máy; WebSocket dành cho desktop. Thay vì stream metrics liên tục bằng WebSocket, trước mắt REST polling dễ bảo trì.
- Nhiệt độ qua `psutil.sensors_temperatures()` có thể không khả dụng ở Windows; UI phải nhận capability.
- VNC/XFCE chiếm RAM; chỉ một session, tối ưu 1280×720; đo trước khi chọn làm service 24/7.
- Không dùng Docker bắt buộc; có thể dùng Docker sau nếu có lý do cụ thể và đo tài nguyên.
- Test thật mức độ hỗ trợ keyboard/mobile: noVNC được hỗ trợ trình duyệt hiện đại, nhưng UX thao tác terminal trên màn nhỏ không chắc tương đương PC.

## 8. Triển khai và rollback (phác thảo; viết script ở M6)

1. Build và test trên ASUS → đóng gói frontend dist, backend requirements lock.
2. Copy release lên một thư mục phiên bản trên Dell (qua SSH/SFTP/Git).
3. Cài venv cho release, đặt env/secrets ngoài repo, verify dependencies.
4. Chạy preflight localhost (`/api/health`), bảo đảm SSH/Tailscale vẫn sống.
5. Chuyển service systemd sang release mới; healthcheck; nếu lỗi rollback bản trước.
6. Dùng Tailscale Serve xuất bản port ứng dụng, kiểm tra từ ASUS + mobile.
7. Thực hiện smoke test metrics, desktop, file, logs.

Không dùng một lệnh deploy làm mất SSH/Tailscale khi chưa có kênh cứu hộ tại nhà. Không thay đổi `Wake on AC`/BIOS trong script.

## 8A. Mobile/tablet future target — security

- Việc chủ thiết bị mở web trên điện thoại **không tự cấp quyền** đọc dữ liệu hay điều khiển điện thoại đó.
- Điều khiển/stream màn hình phải có cấp phép theo thiết bị, có thể thu hồi; không hỗ trợ điều khiển bí mật hoặc vượt quyền OS.
- Nếu muốn kết nối qua ADB/scrcpy, phải kiểm thử rõ USB hay IP, trạng thái authorization/debugging, quyền và độ ổn định; không giả định chỉ cần Tailscale là điều khiển được.
- Với iOS/iPadOS phải chấp nhận các hạn chế API/OS, tránh cam kết tính năng giống Android trước khi có bằng chứng.
- Enrollment bắt buộc có thao tác trên chính thiết bị (nhập pairing code một lần, hết hạn nhanh). Server chỉ lưu hash của token; thu hồi có hiệu lực ngay ở request kế tiếp.
- Lệnh tới thiết bị là enum cố định + schema; agent bỏ qua `type` lạ. Không có kênh gửi script/shell xuống thiết bị.
- Agent Android phải hiển thị notification khi chạy nền; không chạy ẩn và không tự cấp quyền.

## 9. Decision log

| ADR | Quyết định | Lý do |
|---|---|---|
| ADR-001 | Code/build trên ASUS, production trên Dell | Dell yếu; dev thuận tiện; máy chính không cần bật 24/7 |
| ADR-002 | React + TS + Vite / FastAPI | UI tương tác tốt + Python đọc hệ thống |
| ADR-003 | Single backend, static frontend, no DB MVP | Giảm RAM và số tiến trình |
| ADR-004 | Virtual XFCE + TigerVNC + noVNC | GUI trong browser, terminal trong desktop, không cần full VM |
| ADR-005 | Không có web CLI page | Người dùng đã loại bỏ tính năng trùng lặp |
| ADR-006 | Tailscale Serve, không Funnel | Truy cập private, không công khai lên WAN |
| ADR-007 | Giám sát read-only trước điều khiển | An toàn khi server có sự cố CMOS/F1 |
| ADR-008 | Desktop on-demand | Tiết kiệm RAM 4 GB |
| ADR-009 | Mobile control = module trong backend + companion agent kết nối ra (outbound), lifecycle lệnh có xác nhận, desired/reported tách biệt | Không microservice/broker; điện thoại không mở cổng; không báo thành công giả |

## 10. Official references

- Tailscale Serve: https://tailscale.com/docs/features/tailscale-serve
- Tailscale Serve CLI: https://tailscale.com/docs/reference/tailscale-cli/serve
- noVNC: https://novnc.com/
- TigerVNC Xvnc: https://tigervnc.org/doc/Xvnc.html
