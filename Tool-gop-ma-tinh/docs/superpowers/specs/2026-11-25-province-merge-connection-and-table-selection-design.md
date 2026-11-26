# Thiết kế: kiểm tra kết nối và chọn bảng preview

## Mục tiêu

Thêm vào tool gộp mã tỉnh trong DB hiện tại nút kiểm tra kết nối riêng và lựa chọn bảng trước khi quét preview. Người dùng cần xác nhận cấu hình DB hoạt động, rà soát theo phạm vi bảng mong muốn và chỉ cập nhật dữ liệu thuộc preview đó.

## Phương án

- **A — Nút kết nối và checkbox theo bảng trong cùng màn hình (chọn):** giữ giao diện hiện tại, thêm nút kiểm tra kết nối chỉ đọc và danh sách checkbox bảng. Đây là thay đổi nhỏ, phù hợp tool hiện có.
- **B — Tách thành tab kết nối và tab preview:** phân tách giao diện rõ hơn nhưng thêm điều hướng, không đem lại lợi ích đáng kể cho luồng ngắn này.
- **C — Chỉ cho lọc bảng sau khi quét toàn bộ:** không đáp ứng mục tiêu giảm phạm vi preview và thời gian quét.

## Thiết kế được duyệt

- Thêm nút **Kiểm tra kết nối**: mở Oracle ở chế độ read-only, truy vấn thông tin schema/metadata để xác nhận kết nối, sau đó đóng kết nối. Không đọc các bản ghi nghiệp vụ, không cập nhật DB.
- Thêm checkbox cho mỗi bảng đích có cột tỉnh trong whitelist. Mặc định tất cả bảng được chọn; có nút chọn tất cả/bỏ chọn tất cả.
- **Lấy preview** chỉ kiểm tra schema và quét các bảng đã chọn. Kết quả ghi rõ các bảng trong phạm vi; zero bảng được chọn thì cảnh báo và không chạy.
- Bảng preview giữ `Row ID` của bản ghi đích và thêm `Số HSLĐ` để người dùng nhận diện hồ sơ phạm nhân. HSLĐ được nối qua FK hồ sơ đã cấu hình; nếu bảng không có quan hệ hồ sơ hoặc không tra được quan hệ thì hiển thị trống, không ảnh hưởng khả năng cập nhật.
- Nút cập nhật dùng đúng preview hiện hành; kiểm tra phòng vệ rằng mọi bảng/cột trong update thuộc tập whitelist và bảng đã chọn. Cơ chế transaction, kiểm tra giá trị cũ, rollback và audit hiện tại được giữ nguyên.
- CSV, mapping mã tỉnh, các cột whitelist, và hành vi thay đổi dữ liệu không đổi.

## Ngoài phạm vi

Không thay đổi logic mapping, danh mục tỉnh/xã, không thêm bảng/cột địa phương, không thay đổi chiến lược kết nối Oracle, không chỉnh sửa CSV.

## Kế hoạch thực hiện

1. Thêm hàm kiểm tra kết nối read-only và thông báo kết quả qua worker UI.
2. Thêm bộ chọn bảng; truyền phạm vi vào preview và hiển thị số bảng/cột đã quét.
3. Ràng buộc cập nhật theo tập bảng trong preview.
4. Cập nhật hướng dẫn sử dụng và build lại EXE, chép CSV cạnh EXE.
