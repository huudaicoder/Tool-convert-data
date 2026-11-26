# Thiết kế tool đổi mã cơ quan/tòa án và địa phương

## Mục tiêu

Tạo ứng dụng Windows độc lập để áp mapping `mã cơ quan cũ → mã cơ quan chuẩn + mã tỉnh/thành chuẩn` trong DB hiện tại. Tool tra ID đích trong danh mục đang kết nối, preview các FK sẽ đổi, sau đó mới cập nhật.

## Phương án

- **CSV crosswalk theo mã (chọn):** người dùng cung cấp ba mã; tool tra duy nhất các ID cơ quan/tỉnh trong DB. Phù hợp vì tên cơ quan cũ không có một quy tắc chuẩn hóa duy nhất.
- **Tách tự động tên cơ quan:** dễ nhập nhưng dễ nhầm khi tên cũ khác cấu trúc hoặc có tên tỉnh lồng trong tên tòa; không chọn làm nguồn cập nhật.
- **Sửa trực tiếp tên danh mục cơ quan:** không đáp ứng chuyển FK sang mã cơ quan chuẩn đã tồn tại.

## Thiết kế

- Project nằm riêng tại `D:\tool_c10\Tool-chuan-hoa-toa-an`, không dùng chung thư mục/mã chạy với `Tool-check-data` hay `Tool-gop-ma-tinh`.
- CSV ba cột: `CQ_MA_CU,CQ_MA_MOI,TTP_MA_MOI`. Tool resolve các mã duy nhất trong `DM_CO_QUANS` và `DM_TINH_THANH_PHO`; mọi giá trị ghi vào DB là ID.
- Mỗi cặp tòa/cơ quan và địa phương được khai báo rõ theo bảng. Preview chỉ tìm dòng mà FK cơ quan đang bằng ID cũ; apply đổi FK cơ quan sang ID mới và FK tỉnh sang ID chuẩn. Địa phương mapping là đích chuẩn nên được áp kể cả khi giá trị hiện tại khác hoặc đang NULL.
- Danh mục `DM_CO_QUANS` không bị sửa/xóa/tạo. Mã trùng, không tồn tại, mapping trùng nguồn hoặc schema thiếu cột sẽ chặn cập nhật.
- Giao diện có kiểm tra kết nối, checkbox bảng, preview, cập nhật dòng chọn/tất cả, transaction có điều kiện theo giá trị cũ và audit.
- `PN_TIEN_AN.PNTA_DIA_PHUONG_ID` dùng `DM_DIA_PHUONG`, không đưa vào tool tỉnh/thành này.

## Kế hoạch

1. Tạo CSV mẫu ba cột và whitelist cặp FK cơ quan–địa phương.
2. Xây giao diện Tkinter, kiểm tra kết nối, resolve danh mục, preview và cập nhật transaction.
3. Viết hướng dẫn, build EXE độc lập, chép CSV mẫu cạnh EXE.
