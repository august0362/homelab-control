# Server Control — Project Overview

> **Phiên bản:** 0.3 (M1 đã code; thêm FR-08 Mobile Background & Screen Control cho M7)  
> **Cập nhật:** 2026-10-31  
> **Mục tiêu:** HomeLab Control — web riêng quản trị Dell Linux từ ASUS/điện thoại/tablet qua Tailscale; kiến trúc phải mở rộng được để **quản lý/điều khiển chính điện thoại, máy tính bảng** trong tương lai.  
> **Nguyên tắc:** **Viết và kiểm thử trên ASUS trước → tích hợp Dell có kiểm soát → deploy lên Dell để chạy độc lập 24/7**.

## Project re-entry — đọc trong 10 phút

1. **Mục tiêu:** Một website chủ sở hữu dùng để xem giám sát realtime, điều khiển desktop Linux GUI, quản lý file và xem/điều khiển có giới hạn các dịch vụ. Không có trang CLI riêng: terminal nằm trong desktop Linux.
2. **Tình trạng:** M0 và M1 (bootstrap trên ASUS) đã duyệt 2026-10-31; M2 (metrics thật, chart realtime, offline/stale) duyệt 2026-10-31; kế tiếp M2.5; xem trạng thái thực tế trong `MILESTONES.md`, không suy từ đặc tả.
3. **Thiết bị:** ASUS Vivobook Windows = máy phát triển; Dell Latitude 3330, Linux Mint 22.3, i5-3337U (2C/4T), ~3.7 GiB RAM, HDD ~500 GB, phân vùng Linux ~96 GB = server production; điện thoại/tablet = browser client của v1 **và thiết bị mục tiêu cần hỗ trợ trong tương lai**. Điện thoại Xiaomi (HyperOS 3 / Android 16) và tablet Samsung Galaxy Tab S10 Lite 5G (không có thiết bị iOS, không có Mac) đã cài Tailscale và có IP tailnet, nhưng **chưa có companion agent và chưa điều khiển được**.
4. **Đã có trên Dell:** SSH, Tailscale, NetworkManager hoạt động; `Wake on AC` đã bật; đã có ý định cấu hình systemd chống sleep và lid switch. **Chưa xác minh lại toàn bộ sau reboot và chưa có kiểm thử dashboard**.
5. **Rủi ro nghiêm trọng:** Pin chính báo 0% / `Communication Error`. Sau khi ngắt nguồn điện, BIOS báo `Invalid configuration information` và `Time-of-day not set`, yêu cầu **F1**. Có khả năng pin CMOS/RTC yếu. **Không được quảng cáo tự phục hồi 100% khi mất điện.** Chưa có xử lý phần cứng.
6. **Cách truy cập production dự kiến:** HTTPS riêng trong tailnet qua **Tailscale Serve**, chuyển tiếp về ứng dụng trên `127.0.0.1`. Không dùng Funnel, không mở router port forwarding.
7. **Ranh giới:** Windows có thể test monitoring thật của **ASUS**; muốn xem GUI Linux thật phải chạy desktop/VNC trên **Dell**, dù frontend/backend đang phát triển trên ASUS.
8. **Đọc thứ tự:** `SPEC.md` → `ARCHITECTURE.md` → `MILESTONES.md` → `CONTEXT.md`.
9. **Việc kế tiếp:** **M2.5**: đăng nhập bằng mật khẩu riêng của app (D-23, đã chốt O-02) + đổi tên thiết bị (D-24). O-01..O-11 chốt tại milestone tương ứng; chưa cài Cockpit hoặc giao diện nặng trên Dell. FR-08 (mobile chạy nền / giữ sáng màn hình) đã đặc tả cho **M7D**, chưa code.
10. **Quy tắc vận hành:** Không cài/deploy gì lên Dell khi chưa có bước thử/rollback rõ ràng; không tự chạy lệnh nguy hiểm từ UI.

## Vision & trải nghiệm

- Trên ASUS/điện thoại/tablet, mở một URL trong tailnet để vào **Dashboard, Remote Desktop, Files, System**.
- Dashboard: thông số **thật** có timestamp, biểu đồ realtime, trạng thái offline, đơn vị rõ ràng; cảm biến không hỗ trợ phải hiển thị `N/A`, không tự bịa.
- Remote Desktop: GUI Linux có cửa sổ, chuột/bàn phím và **Terminal nằm trong desktop**. Có toàn màn hình; có thể bắt đầu/kết thúc phiên khi cần.
- Files: duyệt/tải lên/tải xuống file trong **thư mục được cho phép**, chặn đi ra ngoài vùng đó.
- System: health, services, logs; thao tác thay đổi hệ thống chỉ mở theo allowlist, cần xác nhận. Trước khi sửa lỗi F1, không cho tắt/reboot từ UI bằng một cú nhấp.
- Sau v1 (M7D): từ ASUS xem điện thoại/tablet đã đăng ký online hay offline, yêu cầu bật/tắt chạy nền của agent và giữ màn hình sáng (tablet làm dashboard cố định). UI chỉ báo thành công khi thiết bị xác nhận.

## Những gì không làm trong phiên bản đầu

- Không xây terminal web độc lập (`xterm.js`/web SSH terminal); vẫn giữ SSH cho bảo trì ngoài UI.
- Không xây hệ thống giả lập VM Linux/Windows toàn bộ; desktop ảo trên **Dell vật lý** là đủ.
- Chưa điều khiển Android/iOS từ web trong MVP. **Đây là yêu cầu mở rộng bắt buộc phải tính tới trong kiến trúc**, không bị loại khỏi roadmap; mức độ điều khiển phụ thuộc Android/iOS/iPadOS, quyền người dùng và kết nối thực tế.
- Không tạo microservices, Redis, Kubernetes, database hoặc Docker bắt buộc cho MVP.
- Không public web lên Internet; không dùng `tailscale funnel`.
- Không làm "pin ảo", tự nhấn F1, tự sửa CMOS trong phạm vi phần mềm này.

## Hướng mở rộng chính thức: mobile/tablet là cả client lẫn managed device

- **Vai trò 1 — client:** Điện thoại, máy tính bảng mở web để điều khiển Dell.
- **Vai trò 2 — managed target (sau v1):** Dell/ASUS dùng Server Control để theo dõi, truyền file và, khi nền tảng cho phép, xem hoặc điều khiển điện thoại/máy tính bảng.
- **Android:** khảo sát kết nối ADB/scrcpy hoặc agent có sự đồng ý của chủ thiết bị; chưa cam kết remote qua Internet hay mọi chức năng đều hoạt động.
- **iOS/iPadOS:** phải khảo sát giới hạn chia sẻ màn hình và điều khiển do hệ điều hành áp đặt; **không hứa toàn quyền điều khiển như desktop**.
- Thiết kế `device_id`, `platform`, `capabilities` và adapter/driver phù hợp từ đầu, **chưa cài service mobile trong MVP**.
- **FR-08 (M7D):** companion agent có sự đồng ý của chủ thiết bị nhận lệnh `background_operations` / `keep_screen_awake` theo lifecycle có xác nhận. Android dùng foreground service; iOS/iPadOS chạy nền là `unsupported`, giữ sáng chỉ khi app/trang đang hiển thị. Không đánh thức màn hình đã khóa, không root/jailbreak. Chi tiết: SPEC FR-08, ARCHITECTURE §4A.

## Roadmap

M0 tài liệu (duyệt) → M1 bootstrap ASUS (duyệt) → M2 metrics thật (duyệt) → M2.5 auth → M3 Remote Desktop Dell → M4 Files → M5 Services → M6 production Dell = **v1** → M7 nhiều thiết bị + mobile managed target (M7A registry, M7B screen/input/file, M7C history/alerts, M7D background & screen control). Trạng thái thật: `MILESTONES.md`.

## Nguyên tắc thiết kế

1. **Local-first development:** ASUS chạy frontend/backend ở `localhost`; Dell không phải máy build.
2. **Production-light:** Chỉ chạy Python API và static frontend; desktop ảo bật khi cần.
3. **Single origin:** Production dùng chung origin cho web và `/api`; kênh desktop dùng cùng chính sách truy cập.
4. **Security-by-default:** localhost bind, tailnet-only HTTPS, xác thực owner, quyền tối thiểu; không arbitrary shell APIs.
5. **Recoverable:** có tài liệu cài, restart, kiểm thử, rollback; logs vừa đủ.
6. **Truthful UI:** dữ liệu mô phỏng phải có nhãn demo; không claim dashboard thật khi còn mock.

## Definition of Done (toàn dự án v1)

- Dev trên ASUS chạy được theo README, test tự động và build frontend thành công.
- Trên Dell, app phục vụ web tĩnh + API được chạy bằng systemd và tự trở lại sau reboot **bình thường**.
- Mở HTTPS qua Tailscale Serve từ ASUS và ít nhất một thiết bị di động trong tailnet.
- Dashboard hiển thị CPU/RAM/disk/network/uptime thật của Dell, xử lý loss/reconnect; nhiệt độ/pin có thể `N/A`.
- Remote Desktop mở được **phiên XFCE/Xvnc thật** trên Dell, thao tác chuột và keyboard được, terminal chạy trong GUI, phiên không phải video giả.
- File upload/download/directory listing hoạt động trong vùng được cấp phép; chặn truy cập vượt thư mục.
- Quyền điều khiển services hạn chế và có xác nhận, không chạy lệnh bất kỳ từ browser.
- Có bản ghi rõ hạn chế **BIOS F1 sau mất điện**, chưa tính là tự phục hồi khép kín.

## Các tài liệu

- [`SPEC.md`](SPEC.md): yêu cầu sản phẩm, phạm vi, tiêu chí nghiệm thu.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): thành phần, luồng, deployment và bảo mật.
- [`MILESTONES.md`](MILESTONES.md): thứ tự thực thi, deliverable và gate kiểm thử.
- [`CONTEXT.md`](CONTEXT.md): những quyết định đã chốt, việc chưa quyết và quy tắc làm việc với AI.
