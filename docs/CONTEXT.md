# Server Control — Context & Working Agreement

> **Nguồn sự thật hiện tại:** cuộc trao đổi với owner, 2026-10-31. Dùng cùng `SPEC.md`, `ARCHITECTURE.md`, `MILESTONES.md`. Không tự coi các dự kiến là đã kiểm chứng.

## 1. Bối cảnh và mục đích

Owner muốn tận dụng laptop Linux cũ làm server tại nhà 24/7 và tự viết giao diện quản trị cá nhân, thay vì dùng Cockpit làm sản phẩm. Có ASUS Vivobook chính để viết code và Claude, Codex, Antigravity hỗ trợ thực thi. Mục tiêu là **có một web duy nhất** theo dõi và điều khiển server từ ASUS, điện thoại, tablet, qua Tailscale. **Yêu cầu bổ sung đã chốt:** sau v1 web phải có hướng mở rộng để **điều khiển chính điện thoại/máy tính bảng như thiết bị đích**, không chỉ dùng mobile để mở web.

## 2. Inventory đã quan sát

| Thành phần | Thông tin | Độ tin cậy |
|---|---|---|
| ASUS | Windows; thư mục tên `Server Control` đã tạo | Owner xác nhận |
| ASUS Node | v24.19.0 | Đã quan sát |
| ASUS npm | 11.17.0 | Đã quan sát |
| ASUS Git | 2.54.0.windows.1 | Đã quan sát |
| ASUS Python | 3.13.15 (Dell 3.12.3 → code phải tương thích 3.12) | Đã quan sát |
| Dell model | Dell Latitude 3330 | `dmidecode`/DMI đã quan sát |
| Dell OS | Linux Mint 22.3 (Zena), kernel 7.0.0-34-generic | Đã quan sát |
| Dell CPU | Intel i5-3337U, 2 cores/4 logical CPUs | Đã quan sát |
| Dell memory | `free -h`: ~3.7 GiB; swap 4 GiB | Đã quan sát |
| Dell disk | HDD `sda` ~465.8 GiB, Linux root ~96 GiB, ~62 GiB free lúc đo | Đã quan sát |
| Dell software | Python 3.12.3, Git 2.43, Node 22.23.3, lm-sensors hiện diện | Đã quan sát từ screenshot |
| Dell network | NetworkManager active, Wi-Fi autoconnect; SSH và tailscaled active | Đã quan sát một lần |
| Dell GUI | `multi-user.target`, TTY, chưa quan sát session desktop đang chạy | Đã quan sát |
| Dell power | Battery 0%, `Communication Error`; AC adapter nhận 65W | BIOS + upower |
| Dell BIOS | `Wake on AC` enabled; `Adapter Warnings` initially enabled | BIOS images |
| Dell POST | Sau tháo nguồn, báo `Invalid configuration information` + `Time-of-day not set`, đòi F1 | Trực tiếp chụp ảnh |
| Dell RTC | Nghi CMOS/RTC yếu/hỏng; **chưa được xác nhận bằng thay linh kiện** | Suy luận kỹ thuật |
| Tailscale + SSH | Owner đã SSH từ ASUS vào Dell | Owner xác nhận |

## 3. Quyết định đã chốt (DO NOT RE-ASK)

- `D-01` Website **tự xây**, không lấy Cockpit làm frontend chính.
- `D-02` **Code/build/test trước trên ASUS**, khi ổn mới deploy full production lên Dell.
- `D-03` Frontend và backend **đều chạy trên ASUS** khi develop.
- `D-04` Production Dell chạy độc lập; ASUS có thể tắt, truy cập qua Tailscale.
- `D-05` Website có Dashboard realtime, Remote Desktop GUI, File Manager, System Control.
- `D-06` Không có **Web CLI/terminal page riêng**. Muốn gõ Bash thì mở Terminal **trong desktop Linux GUI**.
- `D-07` Remote GUI là màn hình desktop dùng chuột/bàn phím qua trình duyệt, không chỉ live screenshot.
- `D-08` Dùng Tailscale để truy cập private và SSH để bảo trì, deploy.
- `D-09` Khả năng F1 sau mất điện **tạm gác**; không cản việc phát triển web, nhưng là rủi ro reliability chưa xử lý.
- `D-10` Tối ưu nhẹ, không overengineering; Dell RAM ~4GB và HDD.
- `D-11` Trước khi coding cần **đặc tả, architecture, milestones, context** rõ.
- `D-12` Kiến trúc **phải mở rộng lên quản lý/điều khiển điện thoại, máy tính bảng** như các managed targets (Android/iOS/iPadOS), không chỉ xem chúng là browser clients. Thực thi M7 sau v1; hỗ trợ chi tiết theo quyền và hạn chế của OS.

### Ranh giới v1 và tương lai của mobile

- **V1:** điện thoại/tablet truy cập web Server Control để quản trị Dell. Không có tính năng tự điều khiển điện thoại/tablet.
- **M7:** người dùng có thể chọn điện thoại/tablet như một **thiết bị đích** để xem trạng thái, truyền file, và điều khiển màn hình/input nếu nền tảng hỗ trợ có cấp quyền.
- Android và iOS/iPadOS **không tương đương**. Không hứa điều khiển iPhone/iPad toàn quyền như desktop; Tailscale là đường truyền, không phải giải pháp remote control của OS.
- M1–M6 chỉ giữ ranh giới thiết kế `device_id`/`platform`/`capabilities`; không cài mobile agent sớm.

### Quyết định bổ sung khi duyệt M0 (2026-10-31)

- `D-13` UI theo bố cục tham chiếu NexusHost (sidebar nhóm + thẻ health, header `thiết bị · OS · online`, 4 thẻ KPI viền nét đứt, biểu đồ lớn + donut, thẻ chi tiết sparkline) với **theme nâu cà phê tối**. Token màu ở `frontend/src/styles/theme.css`; màu series đã kiểm định CVD trên nền `#1c1512`: caramel `#c8742c`, aqua `#199e70`, violet `#9085e9`, gold `#c98500`. Màu trạng thái dành riêng, luôn kèm nhãn. Thành phần giả của ảnh mẫu (search, user, MySQL…) không được đưa vào.
- `D-14` Nhãn nguồn dữ liệu (FR-01.7) lấy từ env `DEVICE_LABEL` + `MACHINE_ROLE=dev|production`, không suy từ OS.
- `D-15` "Không shell" nghĩa là: không lệnh nào lấy từ input browser. Hành động allowlist (vd. start/stop desktop ở M3) được gọi **lệnh cố định** qua subprocess argv, không `shell=True`.
- `D-16` Auth là milestone riêng **M2.5**, bắt buộc trước M3/M4/M5; O-02 chốt tại M2.5.

## 4. Đề xuất kỹ thuật đang ở mức DRAFT

- React + TypeScript + Vite; FastAPI + psutil.
- REST polling 2 giây cho metrics; không DB cho 10 phút history client-side.
- XFCE + TigerVNC Xvnc + noVNC (virtual session, không phải console vật lý).
- Vite dev proxy; static frontend + FastAPI production; Tailscale Serve HTTPS.
- Localhost ports dev: frontend 5173, backend 8000; có thể thay nếu bị chiếm.
- Auth production phải có; cơ chế cụ thể chưa chốt.

Các đề xuất này có thể sửa trước M1 nếu owner có lý do; AI không tự quyết định biến thành yêu cầu tuyệt đối.

## 5. Các điểm đang mở (owner cần phê duyệt khi đến milestone)

| ID | Câu hỏi | Khi nào cần |
|---|---|---|
| O-01 | Các thư mục Dell được Files quản lý? | Trước M4 |
| O-02 | Auth owner: local login hay verified identity qua Tailscale? | Trước M3/M4 |
| O-03 | Allowlist của services được phép restart? | Trước M5 |
| O-04 | Muốn share desktop vật lý hay XFCE session ảo? Đề xuất phiên ảo | Trước nghiệm thu M3 |
| O-05 | Cần gửi file giữa **các client** trực tiếp hay chỉ browser↔server? V1 browser↔server | Trước M4 |
| O-06 | Có muốn theo dõi nhiều host trong dashboard v1 không? Mặc định 1 host Dell | Trước M7 |

Không hỏi lại các điều đã chốt ở §3; nếu không có trả lời kịp thời thì làm theo safe default trong SPEC và ghi assumption.

## 6. Important gotchas / lessons learned

1. **Windows CMD ≠ Linux shell.** Lệnh `systemctl`, `command -v`, cú pháp `/dev/null` chỉ chạy trên Dell qua SSH, không chạy trong `C:\Users\...>`.
2. **Dữ liệu Windows ≠ dữ liệu Dell.** Không lấy metric ASUS gọi là metric server Dell.
3. **Remote GUI cần Dell runtime.** Không thể khẳng định M3 hoàn thành chỉ bằng scaffold React trên ASUS.
4. **VNC có thể nguy hiểm nếu expose trực tiếp.** Không mở TCP 5901/6080 ra LAN/WAN; ưu tiên loopback + authenticated proxy.
5. **Lỗi F1 xảy ra trước Linux.** Không thể xử lý bằng systemd/SSH/Tailscale. Không yêu cầu server tự khôi phục 100% sau mất điện cho đến khi hardware issue giải quyết.
6. **Dừng/restart Tailscale/SSH từ app có thể tự khóa quyền truy cập.** Cấm ở v1.
7. **Battery metric có lỗi.** 0% không có nghĩa một số đo pin khỏe; cần hiển thị `fault/unavailable`.
8. **VNC on-demand.** Không chạy desktop vô ích khi hệ thống chỉ cần giám sát.

## 7. Làm việc với Claude / Codex / Antigravity

**Trước mỗi task:**

1. Đọc `PROJECT_OVERVIEW.md` (Project re-entry), rồi `SPEC.md` relevant FR/AT, `ARCHITECTURE.md`, `MILESTONES.md` milestone hiện tại.
2. Báo lại scope, file sẽ sửa, tiêu chí test.
3. Không tự đổi yêu cầu đã chốt; nếu mâu thuẫn, ghi issue/decision trước khi code.
4. Trong M1/M2 chỉ sửa source trên ASUS; **không tự SSH để cài package hoặc restart Dell**.
5. Không commit `.env`, private keys, password, dữ liệu cá nhân trong logs/screenshots.
6. Chạy build/tests, nêu giới hạn môi trường và nghiệm thu thực tế.
7. Một task/một commit; không tự push/merge nếu chưa được owner yêu cầu.

**Handoff template:**

```text
Milestone/task:
Implemented:
Files changed:
Commands run:
Tests and output:
Assumptions:
Known blockers:
Next recommended step:
```

## 8. Chốt bước tiếp theo

- M0 đã duyệt 2026-10-31; các điểm mở O-01..O-06 chốt tại milestone tương ứng (safe default trong SPEC).
- M1 bootstrap giao cho **một** agent, chưa triển khai Dell.
- Khi M1 pass mới giao M2, sau đó tiến hành tích hợp GUI thật với Dell ở M3.
