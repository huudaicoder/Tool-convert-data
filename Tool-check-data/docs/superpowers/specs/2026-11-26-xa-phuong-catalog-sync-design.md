# Thiết kế: đối chiếu và bổ sung danh mục xã/phường

Ngày: 2026-11-26  
Trạng thái: Chờ duyệt trước khi triển khai.

## Mục tiêu

Thêm một tab riêng trong `Tool-check-data` để so sánh `MA_DP_XA_PHUONG` ở DB cũ với `DM_XA_PHUONG` ở DB mới, liệt kê các mã `MA` chưa có trong `XP_MA`, và cho phép preview rồi insert tất cả mã thiếu.

## Hướng thực hiện

- **Tab đối chiếu riêng (đề xuất):** tách chức năng xã/phường khỏi tab tỉnh/thành phố hiện chỉ đọc; có thể đặt nút preview và insert rõ ràng.
- **Mở rộng tab tỉnh hiện tại:** ít thay đổi khung điều hướng hơn nhưng trộn đối chiếu tỉnh và thao tác ghi xã/phường khác phạm vi.

Chọn tab riêng để phân biệt rõ hai danh mục và quyền thao tác.

## Quy tắc dữ liệu

- So khớp chính xác `MA` với `XP_MA`; giữ nguyên mã dạng chuỗi để không mất số 0 đầu.
- Đưa vào preview các dòng có mã nguồn chưa tồn tại trong `DM_XA_PHUONG`.
- `XP_MA_TINH_THANH_PHO` lấy từ `MA_QH`; nếu `MA_QH` là NULL/rỗng thì dùng mã `00` (cột DB mới là NOT NULL). Preview cảnh báo nếu mã `00` không có trong danh mục tỉnh.
- `XP_TEN` lấy từ `ND`.
- Không insert `XP_LOAI` theo yêu cầu cập nhật của người dùng; để trường này null/default hiện có ở DB mới.
- `XP_TRANG_THAI=1`, `CREATION_TIME=SYSTIMESTAMP`, `IS_DELETED=0`. Bỏ qua `ID` để Oracle identity tự sinh; các trường audit khác để mặc định/null.

## Giao diện và ghi dữ liệu

- Tab có nút **Preview** và bảng liệt kê mã, tên, `MA_QH`, loại suy ra và trạng thái.
- Nút **Insert tất cả** chỉ hoạt động sau preview và khi có dòng hợp lệ.
- Khi insert, đọc lại dữ liệu đích; bỏ qua mã đã được thêm từ sau preview, từ chối/rollback nếu dữ liệu nguồn thay đổi hoặc có lỗi ghi. Hiển thị tổng số đã thêm, bỏ qua và lỗi.
- Ghi trong transaction; rollback toàn bộ lượt insert nếu bất kỳ insert nào thất bại. Yêu cầu xác nhận trước khi ghi.

## Giới hạn

Không tự ánh xạ `MA_QH` sang mã tỉnh khác, không sửa hoặc xóa dòng hiện có. Người dùng xác nhận `MA_QH` chính là giá trị cần lưu trong `XP_MA_TINH_THANH_PHO`.
