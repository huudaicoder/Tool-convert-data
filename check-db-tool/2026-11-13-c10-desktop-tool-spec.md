# Đặc tả: Tool desktop kiểm soát chuyển đổi dữ liệu C10

Ngày: 2026-11-13  
Trạng thái: Bản nháp để duyệt; chưa triển khai.

## 1. Mục tiêu

Xây dựng ứng dụng desktop Windows độc lập để kết nối trực tiếp một CSDL QLPN cũ và một CSDL QLPN mới, đối chiếu dữ liệu theo cấu trúc và các màn hình thực tế của C10, hiển thị tiến độ/chênh lệch trên giao diện và xuất workbook Excel làm báo cáo kiểm soát. Tool phải hỗ trợ checklist chuyển đổi trong `Checklist kiểm soát chuyển đổi dữ liệu C10.xlsx`.

Tool mới có project, mã nguồn, cấu hình và bản build riêng. `D:\QPLN\db-compare` chỉ là tài liệu tham khảo về cách nhập Oracle DSN, kiểm tra kết nối, chạy SELECT, xuất Excel và bố trí UI. Không sửa, không thêm tính năng, không ghi file vào repo `db-compare`.

## 2. Đối tượng và luồng sử dụng

Người dùng là cán bộ chuyển đổi/kiểm soát dữ liệu C10 làm việc trên máy Windows có quyền mạng tới hai DB. Luồng chính:

1. Tạo phiên kiểm soát mới, đặt tên đợt/đơn vị và chọn file checklist gốc hoặc dùng template đi kèm.
2. Nhập thông tin kết nối DB cũ và DB mới: Oracle DSN, user, password, schema. Mật khẩu chỉ lưu trong bộ nhớ phiên.
3. Kiểm tra kết nối từng bên; báo tên DB/schema đã kết nối và lỗi dễ hiểu, không log bí mật.
4. Kiểm kê schema hai DB: bảng/cột, kiểu dữ liệu, quyền đọc, số bản ghi và tình trạng có dữ liệu. So với mapping cấu hình.
5. Người dùng chọn tất cả hoặc một phần cụm Lý lịch (12), Diễn biến (19), Kết thúc (7), checklist hoặc kiểm kê schema.
6. Tool lập danh sách hồ sơ ghép theo **HSLĐ duy nhất**; hiển thị hai chiều: chỉ có ở DB cũ, chỉ có ở DB mới, HSLĐ thiếu/trùng ở mỗi DB, ghép thành công. Không dùng CCCD, CMND, họ tên hay khóa khác để ghép dự phòng.
7. Với hồ sơ ghép thành công, so từng dataset/lưới bằng khóa sự kiện và mapping trường đã cấu hình. Dữ liệu con của hồ sơ không ghép được được đánh dấu chưa đối soát, không tự ghép sang người khác.
8. Tool hiển thị tổng hợp và chi tiết; người dùng cập nhật trạng thái checklist/thủ công, ghi chú, người phụ trách và quyết định.
9. Xuất workbook kết quả, giữ nguồn gốc/phiên chạy, thời gian, trạng thái, các mapping và giới hạn của kết luận.

## 3. Phạm vi chức năng

### 3.1 Kết nối và phiên làm việc

- Hai cấu hình kết nối độc lập: DB cũ/DB mới; trường DSN, user, password, schema.
- Nút kiểm tra kết nối riêng; cấu hình schema có thể để trống nếu dùng schema mặc định.
- Cho phép lưu project cục bộ (đợt, schema, checklist, trạng thái, ghi chú, lịch sử). Mặc định không lưu mật khẩu; có tùy chọn lưu DSN/user/schema.
- Hiển thị trạng thái kết nối và thời điểm kiểm tra.

### 3.2 Kiểm kê và kiểm tra mapping

- Đọc Oracle catalog ở chế độ chỉ đọc để liệt kê bảng, cột, kiểu dữ liệu, nullable và quyền đọc.
- Kiểm tra mọi bảng/cột trong mapping tồn tại ở đúng schema trước khi chạy.
- Liệt kê trường cũ có dữ liệu nhưng chưa có mapping; hỗ trợ trạng thái quyết định xử lý.
- Liệt kê danh mục cần quy đổi old code ↔ new ID/code.
- Không tự suy diễn tên bảng từ dữ liệu người dùng; SQL dùng whitelist cấu hình và bind parameters.

### 3.3 Ghép phạm nhân

- Khóa nghiệp vụ duy nhất là HSLĐ: old `PN_LAI_LICH.SO_HSLD` với new `PN_LAI_LICHS.LL_SO_HO_SO_LAN_DAU`.
- Chuẩn hóa khoảng trắng/format theo quy tắc được thống nhất, không thay đổi ý nghĩa số HSLĐ.
- HSLĐ không rỗng và chỉ xuất hiện một lần ở mỗi phía mới được ghép.
- HSLĐ null/rỗng, trùng ở DB cũ hoặc trùng ở DB mới là trạng thái lỗi riêng. Không thử CCCD, CMND, họ tên hoặc dữ liệu con để tự ghép.
- So hai chiều để nhận biết hồ sơ chỉ có ở DB cũ và chỉ có ở DB mới. Với HSLĐ trùng, báo nhóm trùng và không tính những dòng đó là match/old-only/new-only một cách sai lệch.
- Lai lịch phạm nhân là đối soát đầy đủ các trường đã được mapping; HSLĐ đồng thời là khóa ghép. Báo trạng thái và chênh lệch trường lai lịch bên cạnh kết quả hồ sơ.

### 3.4 Đối soát màn/lưới

- Danh sách menu lấy theo component/route C10: 12/19/7. Dòng trong sheet 38 ví dụ không phải danh sách chính thức.
- Một màn có nhiều lưới thì tách thành dataset riêng. Bộ dữ liệu có quan hệ cha-con phải ghép cha trước, rồi dùng ID cha đã ghép để đối chiếu con.
- Mỗi dataset cấu hình: mã màn, tên màn/lưới, bảng cũ/mới, cột FK người, khóa nghiệp vụ, trường so sánh, quy tắc ngày/số/chuỗi/null, mapping danh mục, lọc xóa mềm, trạng thái phê duyệt.
- Trạng thái tối thiểu: Khớp; Lệch giá trị; Chỉ có ở DB cũ; Chỉ có ở DB mới; HSLĐ không ghép được; Trùng khóa; Thiếu mapping; Không truy vấn được; Chưa chạy.
- Khóa không duy nhất phải giữ số lần xuất hiện, báo duplicate và tránh ghép tùy tiện theo thứ tự truy vấn.
- Khi bảng quá lớn, truy vấn phân trang/chia lô theo khóa; hiển thị tiến độ, cho hủy giữa các lô an toàn.

### 3.5 Bốn màn nhiều lưới và mục còn thiếu

Dùng mapping chi tiết trong `2026-11-13-c10-screen-mapping-review.md` làm cơ sở ban đầu; trước khi bật kết luận đạt, mapping từng lưới/cột cần trạng thái đã rà soát.

- Phân đội: dataset `PN_PHAN_DOI` ↔ `PHAM_NHAN_PHAN_DOI` và dataset Phân buồng `PN_PHAN_BUONG` ↔ `PHAM_NHAN_PHAN_BUONG`.
- Trách nhiệm dân sự/HPBS: tách dataset TNDS, HPBS từ cùng bảng cha theo quy tắc phân loại; dataset biên lai ghép con qua parent crosswalk. Hiện quy tắc tách loại, ngày biên lai và tổng tiền cần xác nhận.
- Bản án khác: `PN_BAN_AN` ↔ `PN_BAN_AN_KHACS`; đồng thời `PN_QD_THI_HANH_AN` ↔ `PN_QUYET_DINH_BAN_AN_KHACS`.
- Tiền công lao động: thu `PN_TIEN_CONG_SX` ↔ `TIEN_LAO_DONG_SAN_XUATS`; chi `PN_TIEN_CHI_TIEU` ↔ `TIEN_CHI_LAO_DONG_SAN_XUATS`; kiểm tra thêm số dư theo công thức đã xác nhận.
- Tài liệu đính kèm: ngoài phạm vi đối soát theo yêu cầu người dùng.

### 3.6 Checklist và ghi nhận thủ công

- Đọc/nhập các mục checklist, tiêu chí đạt, trạng thái, mức độ, người phụ trách, ghi chú/bằng chứng.
- Các việc cần thao tác ngoài DB (backup/restore, so màn hình, duyệt rủi ro, biên bản) được theo dõi thủ công, không giả lập thành kiểm tra SQL.
- Trạng thái mặc định từ workbook; trạng thái tự động của tool không được tự ghi đè ghi nhận nghiệp vụ đã nhập.

## 4. Cấu trúc giao diện desktop

- **Kết nối:** form hai DB, thử từng kết nối, mở/lưu phiên.
- **Tổng quan:** tiến độ lần chạy, số HSLĐ ghép/thiếu/trùng, số dataset khớp/lệch/không thể kết luận, tiến độ checklist.
- **Kiểm kê & mapping:** cây bảng/cột hai DB, trạng thái tồn tại, trường nguồn có dữ liệu chưa map, dataset và khóa.
- **Đối soát:** cây cụm > màn > lưới, bảng kết quả theo dataset, bộ lọc, xem lỗi theo người/khóa/trường.
- **Checklist:** bảng nội dung theo giai đoạn và thông tin người xử lý/bằng chứng.
- **Báo cáo:** chọn loại workbook và xuất file.

## 5. Workbook Excel đầu ra

Đầu ra là workbook báo cáo mới, không ghi đè checklist gốc. Theo yêu cầu, workbook chỉ có 4 sheet: `Tổng quan`, `Đối soát số lượng`, `Ghép phạm nhân`, `Chi tiết sai lệch`. Không đưa vào workbook các sheet Checklist, Rủi ro từ đặc tả, Lịch sử chạy, Mapping trường, Kiểm kê schema, Dữ liệu cũ chưa có chỗ hoặc Dropdown options. Checklist, lịch sử phiên và các ngoại lệ cần theo dõi vẫn có thể được lưu trong project/app theo phạm vi đã thống nhất; bỏ sheet Excel không có nghĩa tự động bỏ chức năng trong ứng dụng.

### 4 sheet đầu ra

1. **Tổng quan** — thời điểm/phạm vi lần chạy, DB/schema (không mật khẩu), số HSLĐ ghép được, chỉ có ở từng DB, HSLĐ thiếu/trùng và tổng khớp/lệch theo màn/lưới. Giúp xem nhanh tình trạng chung.
2. **Đối soát số lượng** — một dòng cho mỗi dataset/lưới: màn, bảng nguồn/đích, tổng dòng, khớp, lệch giá trị, chỉ có ở DB cũ, chỉ có ở DB mới, duplicate và chưa thể kết luận. Dùng để định vị màn cần xem.
3. **Ghép phạm nhân** — crosswalk theo HSLĐ duy nhất, gồm người ghép được, chỉ có ở DB cũ, chỉ có ở DB mới, HSLĐ thiếu và HSLĐ trùng ở từng phía. Không dùng CCCD/CMND để ghép. Sheet này cho biết phạm nhân nào ghép được để so dữ liệu con.
4. **Chi tiết sai lệch** — danh sách chi tiết các dòng có chênh lệch ở các màn/lưới: (a) bản ghi chỉ có ở DB cũ, tức thiếu ở DB mới; (b) bản ghi chỉ có ở DB mới, tức thiếu ở DB cũ; (c) bản ghi ghép được nhưng một hay nhiều trường có giá trị khác nhau. Mỗi dòng ghi dataset, trạng thái, HSLĐ (nếu ghép được), khóa bản ghi, cột và giá trị cũ/mới. Một bản ghi có nhiều cột lệch có thể xuất thành nhiều dòng, mỗi dòng cho một cột. Hồ sơ không ghép được do HSLĐ thiếu/trùng được ghi ở `Ghép phạm nhân`; dữ liệu con của hồ sơ đó không thể khẳng định thiếu ở bên kia vì chưa định danh được người tương ứng, nên đánh dấu chưa đối soát thay vì tạo chênh lệch giả.

Các dòng mẫu của sheet `Đối soát số lượng` trong template gốc không phải danh sách màn chuẩn; báo cáo tạo dòng theo các dataset/lưới thực tế đã cấu hình. Sheet `Chi tiết sai lệch` chỉ xuất sai lệch bản ghi/trường, không chép lại toàn bộ dòng khớp. Nếu không có sai lệch, sheet vẫn có header và ghi rõ không có dòng lệch cho lần chạy/phạm vi đó. Các sheet có lọc, cố định hàng tiêu đề, định dạng ngày/số và chú giải trạng thái. Chi tiết quá lớn có thể xuất file riêng. Không xuất password.

## 6. An toàn và chất lượng kết luận

- Chỉ SELECT và đọc catalog; tool không chạy INSERT/UPDATE/DELETE/DDL.
- Không ghi password, chuỗi kết nối đầy đủ, hoặc bản sao toàn DB vào project/log/Excel.
- Cột/ bảng truy vấn phải từ whitelist mapping; giá trị đầu vào dùng bind parameter.
- Kết quả cần lưu giờ chạy, schema, phạm vi và mapping version để có thể giải thích/tái lập.
- DB mới có soft delete: lọc theo cấu hình đã duyệt và ghi điều kiện vào kết quả.
- Không kết luận đạt khi HSLĐ không ghép được, thiếu mapping, lỗi truy vấn, khóa duplicate chưa xử lý hoặc checklist chưa có bằng chứng.
- Chỉ so dữ liệu cùng phạm vi/cut-off; nếu hai DB thay đổi trong lúc chạy, hiển thị cảnh báo/thời điểm snapshot.

## 7. Ngoài phạm vi

- Không migrate/ghi dữ liệu, sửa schema, hoặc thay thế công cụ triển khai chuyển đổi.
- Không sửa `db-compare`.
- Không tự quyết định mapping nghiệp vụ chưa được duyệt.
- Không tự kiểm tra backup/khôi phục, ký nghiệm thu hoặc xác nhận màn hình nghiệp vụ nếu thiếu người dùng/bằng chứng.
- Không mặc định kiểm tra nội dung file khi chưa có quyền/truy cập kho file.

## 8. Tiêu chí nghiệm thu

- Cài/chạy tool độc lập với `db-compare`; mã nguồn và build nằm trong project mới.
- Kết nối/test DB cũ và DB mới độc lập; password không xuất hiện trong log/project/report.
- HSLĐ là khóa duy nhất ghép người; HSLĐ thiếu/trùng đều được báo và không có fallback khác.
- Có thể nhận biết người chỉ có ở mỗi phía; lai lịch được so trường theo mapping.
- Danh sách menu đầy đủ 12/19/7; mọi lưới được tách dataset rõ ràng, không coi 38 dòng mẫu là menu chuẩn.
- Thấy trạng thái, tiến độ và chi tiết chênh lệch; query lỗi/hủy không bị coi là đạt.
- Excel đầu ra có các sheet nêu trên, giữ checklist/rủi ro/dữ liệu chưa có chỗ, và tách count khỏi record-level details.
- Chỉ đọc DB; không tạo DML/DDL.

## 9. Điểm cần xác nhận trước khi triển khai đối soát thật

- Oracle phiên bản, DSN/service name và driver/thin-mode tương thích.
- Chuẩn hóa HSLĐ (trim khoảng trắng, hoa/thường, số 0 đầu có giữ nguyên không); nếu có biến thể format, phải đồng ý quy tắc nhưng vẫn không dùng khóa khác.
- Cách phân loại TNDS/HPBS và mapping danh mục; quan hệ biên lai và hai trường ngày.
- Chính sách bản ghi soft-delete và phạm vi/cut-off của từng DB.
- Nguồn legacy của file/ảnh đính kèm, quyền share và tiêu chí so.
- Có cần che HSLĐ/tên trên file Excel hay không; mặc định chỉ dùng HSLĐ làm định danh nghiệp vụ, không xuất CCCD.
- Dùng một máy hay chia sẻ project nhiều máy; bản đầu đề xuất lưu local.
