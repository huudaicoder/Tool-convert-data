# Thiết kế: cập nhật xếp loại quý IV năm 2026

## Mục tiêu

Thêm tab **Cập nhật xếp loại** vào ứng dụng. Tab tìm phạm nhân thuộc trại đang chọn có bản ghi xếp loại năm 2026 trong DB mới nhưng `XEP_LOAI_QUY_IV` đang trống; nếu DB cũ có kết quả quý IV năm 2026 tương ứng thì cho phép bổ sung vào DB mới.

## Phương án đã chọn

Lấy DB cũ làm nguồn: `PN_KET_QUA_CAI_TAO.NAM_XL = 2026`, giá trị từ `MA_XEP_LOAI_Q4`. Ghép phạm nhân bằng HSLĐ qua crosswalk hiện có và giới hạn DB mới theo mã trại đã nhập. Đối chiếu mã xếp loại sau khi bỏ khoảng trắng đầu/cuối và chuẩn hóa chữ hoa giữa `MA_XEP_LOAI.MA` ở DB cũ với `DM_XEP_LOAIES.XL_MA` ở DB mới; chỉ dùng khi mỗi bên có đúng một mã tương ứng. Ghi ID danh mục mới vào `XEP_LOAIS.XEP_LOAI_QUY_IV`.

Phương án tính kết quả quý IV từ các tháng 10–12 không được chọn vì có thể tạo kết quả khác với quý IV đã lưu trong DB cũ.

## Quy tắc và an toàn dữ liệu

- Chỉ xét bản ghi năm 2026 của đúng phạm nhân và đúng trại; không tạo bản ghi xếp loại mới.
- Chỉ cập nhật khi bản ghi mục tiêu tồn tại duy nhất và quý IV đang `NULL`; giữ nguyên giá trị đã có.
- Chỉ cập nhật khi HSLĐ ghép duy nhất, nguồn có một kết quả quý IV duy nhất, và mã nguồn ánh xạ duy nhất sang danh mục mới. Mã trống, không khớp hoặc trùng được báo trong xem trước và không tự đoán.
- Xem trước là chỉ đọc; người dùng có thể chọn nhiều dòng để cập nhật hoặc cập nhật toàn bộ các dòng hợp lệ. Giao dịch cập nhật có kiểm tra lại điều kiện quý IV vẫn đang trống trước khi ghi và rollback nếu phát sinh lỗi.
- Hiển thị HSLĐ, kết quả cũ, ID/tên kết quả mới dự kiến và trạng thái để người dùng rà soát.

## Giao diện và cách dùng

Tab mới dùng chung hai kết nối DB và mã trại đã nhập. Có các nút **Lấy xem trước**, **Cập nhật dòng đã chọn**, **Cập nhật toàn bộ** và bảng kết quả có checkbox theo dòng, theo cách các tab cập nhật hiện có.

## Phạm vi thay đổi dự kiến

- `app.py`: thêm tab, bảng xem trước, chọn dòng và luồng nút thao tác.
- `engine.py`: đọc dữ liệu nguồn/đích, tạo preview, ánh xạ mã danh mục và cập nhật có điều kiện.
- Cập nhật hướng dẫn sử dụng nếu cần.

## Cách xác nhận hoàn tất

Kiểm tra tĩnh các truy vấn preview/update và đóng gói EXE sau khi triển khai theo yêu cầu chạy ứng dụng của người dùng. Không thêm bản ghi mới hoặc sửa các quý khác.
