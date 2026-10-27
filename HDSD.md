# HƯỚNG DẪN SỬ DỤNG QUẢN LÝ HÓA ĐƠN PHƯỢNG NGUYỄN v1.0 (DIRECT API)

Ứng dụng quản lý, tra cứu và tải hóa đơn điện tử (**Mua vào** & **Bán ra**) kết nối **trực tiếp qua hệ thống REST API của Tổng cục Thuế** (`https://hoadondientu.gdt.gov.vn/`), chạy độc lập trên máy tính, bảo mật thông tin và không phụ thuộc vào thao tác click trình duyệt ảo.

---

## 1. Cơ Chế Đăng Nhập & Giải Quyết Vấn Đề Hết Hạn Captcha

### Phân tích cơ chế bảo mật của Tổng Cục Thuế:
- Hệ thống Cổng Thuế sử dụng **JWT Bearer Token** để xác thực:
  - Mã Captcha SVG chỉ được sử dụng **duy nhất 1 lần** tại endpoint xác thực `POST /api/security-taxpayer/authenticate`.
  - Khi xác thực thành công, Cổng Thuế cấp một chuỗi mã phiên làm việc (**Token**) có hiệu lực trong thời gian dài (nhiều giờ).
  - Toàn bộ các thao tác sau đó: tra cứu hóa đơn mua vào/bán ra (`/api/query/invoices/...`), tải file ZIP gốc (`/api/query/invoices/export-xml`)... **hoàn toàn chỉ sử dụng Token này mà KHÔNG cần Captcha nữa**.

### Giải pháp trong phần mềm:
- **Nút "🔑 ĐĂNG NHẬP CỔNG THUẾ"**: Thiết kế nổi bật ngay góc trên bên trái giao diện chính.
- Khi người dùng bấm vào hoặc bấm "Đăng nhập ngay" trong danh sách doanh nghiệp:
  1. Hộp thoại đăng nhập hiện ra với mã Captcha SVG trực tiếp từ Cổng Thuế (có nút `🔄 Đổi mã`).
  2. Người dùng nhập thông tin hoặc chọn doanh nghiệp từ danh sách đã lưu.
  3. Bấm **"🚀 ĐĂNG NHẬP & LƯU PHIÊN LÀM VIỆC"**:
     - Ứng dụng tự động lưu thông tin (MST, Tên doanh nghiệp, Mật khẩu, Token) vào cơ sở dữ liệu SQLite cục bộ (`data/hoadon.db`).
     - Trạng thái góc trên đổi sang **"🟢 ĐÃ ĐĂNG NHẬP ([MST])"**.
     - Bạn có thể thoải mái thao tác trong hàng giờ liền mà **không bao giờ lo bị hết hạn Captcha hay phải nhập lại Captcha**!

---

## 2. Hệ Thống Phân Quyền Admin & Bảo Mật Chống Phát Tán Nội Bộ

### 2.1. Cơ chế Bảo Mật Hai Lớp (Role Separation)
- **Quyền Quản Trị Viên (Admin)**:
  - Chỉ người giữ **Mật khẩu Quản trị (Admin)** mới có quyền:
    - Thêm doanh nghiệp mới vào hệ thống.
    - Sửa thông tin, thay đổi mật khẩu Cổng Thuế của doanh nghiệp.
    - Xóa doanh nghiệp và dữ liệu hóa đơn.
    - Đổi mật khẩu Admin.
- **Chế độ Nhân Viên (Employee Mode - Mặc định khi phân phát)**:
  - Nhân viên chỉ được **chọn các công ty có sẵn** mà Admin đã cấu hình.
  - Mật khẩu Cổng Thuế được hệ thống **tự động điền ẩn (`●●●●●●`)** và khóa chỉnh sửa (`readOnly`), nhân viên không thể nhìn thấy, không thể bôi đen copy.
  - Mục `➕ [Thêm mới / Nhập tài khoản khác]` bị ẩn hoàn toàn đối với nhân viên.
  - Nhân viên **không thể thêm bất kỳ mã số thuế của công ty nào khác** vào phần mềm.

### 2.2. Mã Hóa Cơ Sở Dữ Liệu SQLite (AES-Fernet)
- Toàn bộ mật khẩu Cổng Thuế lưu trữ trong file `data/hoadon.db` đều được **mã hóa tự động bằng thuật toán AES-128-CBC + HMAC-SHA256 (Fernet)**.
- Kể cả khi nhân viên copy file `hoadon.db` mở bằng các phần mềm đọc cơ sở dữ liệu (SQLite Browser), mật khẩu vẫn hoàn toàn là chuỗi mã hóa ngẫu nhiên, không thể xem trộm mật khẩu thuế của doanh nghiệp.

### 2.3. Quy Trình Cấu Hình & Bàn Giao Cho Nhân Viên
1. **Admin khởi động phần mềm lần đầu**:
   - Hệ thống tự động hiện hộp thoại yêu cầu Admin đặt **Mật khẩu Quản trị (Admin)**.
2. **Admin cấu hình danh sách doanh nghiệp**:
   - Bấm vào nút `🏢 Doanh nghiệp` hoặc `👑 Quản Trị Viên`.
   - Nhập MST, Tên công ty, Mật khẩu Cổng Thuế rồi bấm **"Lưu / Cập nhật"**.
   - Dữ liệu được mã hóa bảo mật trực tiếp vào `data/hoadon.db`.
3. **Bàn giao cho nhân viên**:
   - Sau khi cấu hình xong, Admin chỉ cần gửi thư mục phần mềm (kèm file `data/hoadon.db` đã mã hóa) cho nhân viên.
   - Nhân viên mở lên: mặc định ở **Chế độ Nhân viên**, chỉ việc chọn công ty -> nhập mã Captcha Cổng Thuế -> bấm Đăng nhập & tra cứu bình thường.
   - Nếu nhân viên đem phần mềm chia sẻ cho người ngoài: Người ngoài mở lên cũng không thể thêm công ty của họ vào dùng được vì không có mật khẩu Admin!

---

## 3. Các Tính Năng & Bộ Lọc Nâng Cao (Thừa Hưởng Trọn Vẹn)

### 3.1. Loại Hóa Đơn & Kỳ Kế Toán
- **LOẠI HĐ**: Chuyển đổi linh hoạt giữa hai chế độ:
  - `[ Bán ra ]`
  - `[ Mua vào ]`
- **KỲ KẾ TOÁN**: Hỗ trợ đầy đủ 5 chế độ lọc:
  - `Theo Ngày`: Chọn 1 ngày cụ thể (`dd/MM/yyyy`).
  - `Theo Tháng`: Chọn Tháng (Tháng 01 -> Tháng 12) và Năm.
  - `Theo Quý`: Chọn Quý (Quý 1 -> Quý 4) và Năm.
  - `Theo Năm`: Chọn Năm (VD: 2026).
  - `Tùy Chọn`: Chọn khoảng thời gian bất kỳ từ ngày ... đến ngày ...
  > **Đặc biệt (Bypass giới hạn 31 ngày)**: Cổng Thuế quy định mỗi lần tra cứu không được vượt quá 31 ngày. Phần mềm đã tích hợp thuật toán **tự động chia nhỏ (chunking)** khoảng thời gian theo từng giai đoạn 30 ngày rồi ghép kết quả và loại bỏ trùng lặp, giúp bạn có thể tra cứu trọn vẹn cả Quý hoặc cả Năm mà không bao giờ bị lỗi!

### 3.2. Tra Cứu Nội Bộ & Đồng Bộ Thuế
- **`🔍 TÌM NỘI BỘ`**: Tra cứu dữ liệu hóa đơn đã lưu sẵn trong cơ sở dữ liệu SQLite trên máy (tốc độ tức thì, không cần kết nối mạng).
- **`☁ ĐỒNG BỘ TỔNG CỤC THUẾ`**: Kết nối REST API lên Cổng Thuế để đồng bộ dữ liệu mới nhất về máy tính.

### 3.3. Thanh Tác Vụ (Toolbar)
- **`⬇ TẢI XML`**: Tải toàn bộ file XML gốc của các hóa đơn hiển thị trong bảng.
- **`📊 XUẤT EXCEL (F5)`**: Xuất dữ liệu ra file Excel với 2 định dạng:
  - `Bảng kê tiêu chuẩn`: Đầy đủ ký hiệu mẫu, ký hiệu, số HĐ, người bán, người mua, tiền hàng, tiền thuế, tổng thanh toán.
  - `Bảng kê chi tiết hàng hóa`: Tách chi tiết từng dòng mặt hàng, tên hàng hóa/dịch vụ, ĐVT, số lượng, đơn giá, thuế suất từ file XML gốc.
- **`📑 TẢI PDF HÀNG LOẠT`**: Tải trọn gói và chuyển đổi sang file PDF hóa đơn điện tử chuẩn biểu mẫu Tổng Cục Thuế.
- **Bộ lọc & Tìm kiếm**:
  - Dropdown `Lọc: Tất cả`, `Lọc: Đã có XML`, `Lọc: Chưa có XML`.
  - Ô tìm kiếm tức thời `🔍 Tìm kiếm hóa đơn...` (gõ mã số, tên người bán/mua, số hóa đơn để lọc nhanh).
- **`⌃ Mở rộng bảng`**: Thu gọn/mở rộng khu vực bộ lọc phía trên để tối đa hóa không gian xem bảng hóa đơn.

### 3.4. Bảng Dữ Liệu 15 Cột Chuẩn
1. `STT`
2. `TRẠNG THÁI XML`
3. `KÝ HIỆU`
4. `SỐ HÓA ĐƠN`
5. `NGÀY LẬP`
6. `THÔNG TIN NGƯỜI BÁN`
7. `THÔNG TIN NGƯỜI MUA`
8. `TỔNG TIỀN CHƯA THUẾ`
9. `TỔNG TIỀN THUẾ`
10. `TỔNG TIỀN THANH TOÁN`
11. `TRẠNG THÁI`
12. `KẾT QUẢ KIỂM TRA`
13. `HÓA ĐƠN LIÊN QUAN`
14. `CẢNH BÁO`
15. `PHÂN LOẠI`

### 3.5. Biểu Đồ & Thống Kê Tổng Hợp
- Khối **"BIỂU ĐỒ HÓA ĐƠN MUA - BÁN"** hiển thị tức thì các thẻ chỉ số:
  - 📦 Tổng số lượng HĐ (Mua vào / Bán ra)
  - 💵 Tổng tiền chưa thuế (đ)
  - 💸 Tổng tiền thuế GTGT (đ)
  - 💳 Tổng tiền thanh toán (đ)
  - 📥 Tỷ lệ hóa đơn đã tải file XML gốc (%)
- Thanh trạng thái phía chân màn hình: Tổng kết tổng giá trị bằng chữ số VNĐ định dạng chuẩn.

---

## 4. Khởi Chạy Ứng Dụng

- **Cách 1**: Double-click vào file [Chay_Tool.bat](file:///d:/Manh_Project/HoaDon/Chay_Tool.bat) trên màn hình làm việc để mở bản Desktop.
- **Cách 2**: Chạy qua dòng lệnh Terminal:
  ```bash
  python main.py
  ```

---

## 5. Phiên Bản Web & Phát Trực Tuyến Cho Nhân Viên (Cloudflare Tunnel)

### 5.1. Vì sao không nên host trực tiếp trên Cloud quốc tế (Streamlit Cloud, AWS...)?
- Cổng Thuế của Tổng cục Thuế Việt Nam (`hoadondientu.gdt.gov.vn`) có hệ thống **Tường Lửa chặn các dải IP Datacenter nước ngoài (Geo-blocking / Anti-DDoS)**. Khi máy chủ ở nước ngoài gửi request lấy Captcha, Cổng Thuế sẽ ngắt kết nối (báo lỗi `Connection timed out`).
- **Giải pháp tối ưu:** Ứng dụng chạy trên máy tính tại Việt Nam (có IP mạng FPT, Viettel, VNPT) ➔ Cổng Thuế mở 100%, tải Captcha và tra cứu siêu tốc.

### 5.2. Cách phát Web cho nhân viên truy cập từ xa (1 Cú Click):
1. **Khởi chạy:** Double-click vào file [Phat_Web_Online.bat](file:///d:/Manh_Project/HoaDon/Phat_Web_Online.bat).
2. Hệ thống tự động:
   - Khởi động máy chủ Web Streamlit nội bộ.
   - Kích hoạt đường truyền bảo mật **Cloudflare Tunnel**.
   - Tự động sinh ra đường link HTTPS công cộng an toàn (ví dụ: `https://xxxx.trycloudflare.com`).
   - Tự động mở trình duyệt.
3. **Chia sẻ cho nhân viên:**
   - Bạn chỉ cần copy đường link `https://xxxx.trycloudflare.com` gửi cho nhân viên (có thể mở trên điện thoại, máy tính ở nhà hay bất kỳ đâu).
   - Giao diện có Cổng xác thực: Nhân viên nhập mã truy cập (mặc định: `hoadon2026`).
   - Quản trị viên nhập Mật khẩu Admin để vào toàn quyền cấu hình doanh nghiệp và đổi mã truy cập nhân viên bất cứ lúc nào.
4. **Tắt ứng dụng:** Khi không dùng nữa, chỉ cần tắt cửa sổ đen hoặc nhấn `Ctrl + C`.
