# Kế hoạch triển khai: Tool desktop mới kiểm soát chuyển đổi C10

Ngày: 2026-11-13  
Trạng thái: Bản nháp; chưa triển khai. Kế hoạch này thực hiện theo đặc tả `2026-11-13-c10-desktop-tool-spec.md`.

## Nguyên tắc thực hiện

- Tạo project mới trong `D:\QPLN\check-db-tool` (tên thư mục có thể đổi trước khi bắt đầu); `D:\QPLN\db-compare` chỉ đọc/tham khảo, không sửa.
- Dùng stack phù hợp với app Tkinter/Python hiện có nếu không phát sinh ràng buộc khác; tái sử dụng kiến thức/cách làm chứ không import code hoặc ghi sang repo cũ.
- Đối soát Oracle ở chế độ SELECT-only; HSLĐ duy nhất là khóa ghép phạm nhân.
- Theo từng pha, có đầu ra xem được trước khi chuyển pha tiếp theo. Không chạy trên DB nghiệp vụ thật nếu chưa có kết nối được cấp và mapping duyệt.

## Các pha

### Pha 0 — Chốt thiết kế và dựng project độc lập

- Chốt spec, danh sách workbook và quy tắc HSLĐ.
- Tạo skeleton project mới: source, cấu hình mapping, resource checklist, log, thư mục export và đóng gói.
- Ghi rõ phụ thuộc/runtime và hướng dẫn cài/chạy; không sửa repo db-compare.

**Đầu ra:** project khởi chạy được, README, spec đã duyệt, cấu hình ví dụ không có mật khẩu.

### Pha 1 — Mô hình checklist, phiên và Excel

- Đọc workbook gốc làm căn cứ; workbook đầu ra chỉ gồm `Tổng quan`, `Đối soát số lượng`, `Ghép phạm nhân`, `Chi tiết sai lệch`. Không thêm sheet mapping/schema/checklist/rủi ro/lịch sử/dữ liệu cũ chưa có chỗ hay Dropdown options.
- Mô hình hóa checklist, dữ liệu cũ chưa có chỗ, rủi ro, phiên chạy, dataset/mapping.
- Làm bộ sinh Excel với 4 sheet theo spec; chi tiết sai lệch chỉ chứa bản ghi thiếu/thừa hoặc lệch trường, phân biệt chưa chạy và chưa thể kết luận.
- Lưu project local và giữ lịch sử phiên, không lưu password.

**Đầu ra:** project local lưu trạng thái công việc; báo cáo Excel mẫu 4 sheet dùng dữ liệu giả.

### Pha 2 — Kết nối và kiểm kê schema chỉ đọc

- Form cấu hình DB cũ/mới, test từng kết nối, kiểm soát secret.
- Lấy catalog Oracle: tables, columns, types, nullability và quyền đọc.
- So schema live với DDL/mapping cấu hình, xuất lỗi thiếu bảng/cột/quyền.
- Kiểm kê row count và field populated theo cách có giới hạn tải, có thể hủy.

**Đầu ra:** màn kết nối và kiểm kê schema; chưa có kết luận chuyển đổi.

### Pha 3 — Ghép HSLĐ và đối soát Lai lịch

- Xây phép chuẩn hóa HSLĐ đã chốt (không tự bỏ số 0 đầu nếu chưa duyệt).
- Phân loại HSLĐ duy nhất, thiếu, duplicate ở mỗi bên, chỉ có cũ/mới, matched.
- Chỉ cho matched HSLĐ duy nhất đi tiếp vào đối soát child.
- Đối chiếu các trường Lai lịch phạm nhân và hiển thị sai lệch.

**Đầu ra:** bảng ghép hai chiều và báo cáo Lai lịch; mọi trạng thái duplicate/missing thể hiện riêng.

### Pha 4 — Mapping và engine đối soát màn hình

- Chuyển 37 mapping hiện có sang cấu hình riêng của project mới; review từng field, key, kiểu dữ liệu, null, ngày, số, danh mục.
- Không đối soát `Tài liệu đính kèm` theo yêu cầu người dùng.
- Nâng engine để phân trang/chia batch, giữ duplicate multiplicity, tách bản ghi của hồ sơ không ghép được, thống kê hai chiều.
- Thêm dataset riêng cho Phân buồng, Quyết định thi hành án khác, Tiền chi; thiết kế TNDS/HPBS cha-con và biên lai.
- Chỉ ánh xạ trường/danh mục và kết luận đạt khi có trạng thái xác nhận.

**Đầu ra:** màn cây Cụm > Màn > Lưới, kết quả theo dataset và danh sách mapping chưa xác nhận.

### Pha 5 — Dashboard, checklist, chi tiết và xuất Excel

- Gắn trạng thái đối soát tự động với mục checklist liên quan nhưng không tự ghi đè trạng thái nghiệp vụ.
- Giao diện xem tổng quan, lọc, phân trang sai lệch, nguyên nhân lỗi và tiến độ.
- Xuất đủ các sheet; giữ checklist gốc; ghi thời gian/phạm vi/schema/mapping version; bảo vệ file khỏi rò password.
- Hỗ trợ workbook tổng hợp và file chi tiết riêng nếu lượng lệch lớn.

**Đầu ra:** quy trình hoàn chỉnh từ kết nối đến báo cáo Excel.

### Pha 6 — Đóng gói và bàn giao

- Đóng gói bản Windows độc lập, hướng dẫn cài/run, cấu hình quyền chỉ đọc Oracle và xử lý lỗi.
- Rà soát mã nguồn để xác nhận không có DML/DDL và không ghi secret.
- Bàn giao README, mẫu mapping, mẫu project/báo cáo và danh sách câu hỏi nghiệp vụ còn mở.
- Chạy kiểm tra kỹ thuật trên DB test/snapshot được cho phép; không tự kết nối DB thật khi chưa được cung cấp thông tin/quyền.

**Đầu ra:** gói desktop riêng và tài liệu vận hành.

## Luồng build theo màn hình

`Kết nối` → `Kiểm kê schema` → `Ghép HSLĐ` → `Đối soát Lai lịch` → `Đối soát từng cụm/màn/lưới` → `Checklist & xử lý ngoại lệ` → `Tổng quan` → `Xuất Excel`.

Ở mỗi bước nếu lỗi quyền/schema/query thì dừng dataset tương ứng, ghi nguyên nhân, cho phép chạy lại; lỗi một dataset không xóa kết quả những dataset đã chạy thành công.

## Rủi ro và cách kiểm soát

- **HSLĐ không duy nhất/thiếu:** báo lỗi và không ghép bằng CCCD/CMND/tên; phân loại bản ghi liên quan riêng để kiểm tra.
- **Khóa sự kiện trùng/yếu:** bổ sung khóa nhiều trường hoặc báo cần xác nhận; không ghép theo thứ tự DB trả ra.
- **Mapping danh mục chưa tương đương:** trạng thái chưa thể kết luận, không tính đạt.
- **DB thay đổi trong lúc chạy:** ghi thời điểm, phạm vi; ưu tiên read-consistency/snapshot nếu DBA cho phép.
- **Bảng lớn:** chạy phân lô, giới hạn chi tiết tải vào RAM, cho hủy an toàn và xuất chi tiết có kiểm soát.
- **Thông tin phạm nhân trong Excel:** xuất định danh tối thiểu theo nhu cầu kiểm tra; không xuất CCCD, không ghi password.
- **Checklist chưa được tự động hóa:** giữ là việc thủ công có người phụ trách/bằng chứng, không đánh dấu tự động hoàn tất.

## Tiêu chí hoàn thành theo phase

Mỗi pha phải có: đầu ra chạy/xem được, cách kiểm tra được ghi lại, xử lý lỗi rõ, không thay đổi dữ liệu DB nguồn, và checklist/tài liệu được cập nhật. Kiểm thử hoặc kết nối vào DB thật chỉ thực hiện trong phạm vi đã được người dùng cung cấp/cho phép.
