# Tool chuẩn hóa mã cơ quan/tòa án và địa phương

Project độc lập tại `D:\tool_c10\Tool-chuan-hoa-toa-an`; không dùng chung source với `Tool-check-data` hoặc `Tool-gop-ma-tinh`.

## CSV mapping

File `court_location_mapping.csv` có đúng ba cột:

```csv
CQ_MA_CU,CQ_MA_MOI,TTP_MA_MOI
```

Điền mã cơ quan cũ, mã cơ quan chuẩn đã tồn tại trong `DM_CO_QUANS`, và mã tỉnh/thành đích đã tồn tại trong `DM_TINH_THANH_PHO`. Tool tra ID duy nhất trong DB đang kết nối; Excel nên giữ các cột mã ở định dạng Text để không làm mất số 0 đầu mã. Không nhập ID DB vào CSV.

## Phạm vi

Tool cập nhật các cặp cột cơ quan–địa phương đã whitelist trong `mapping.py`. Chỉ các dòng có FK cơ quan đang trỏ đến ID tra từ `CQ_MA_CU` mới được preview. Khi cập nhật, FK cơ quan chuyển sang ID tra từ `CQ_MA_MOI`, FK tỉnh/thành chuyển sang ID tra từ `TTP_MA_MOI`, kể cả khi locality hiện tại không NULL. Danh mục cơ quan/tỉnh không bị sửa hoặc xóa.

`PN_TIEN_AN.PNTA_DIA_PHUONG_ID` không thuộc phạm vi vì dùng `DM_DIA_PHUONG`, không phải danh mục tỉnh/thành.

## Chạy và build

- Chạy source: cài `requirements.txt`, rồi `python app_chuan_hoa_toa_an.py`.
- Build: chạy `build_chuan_hoa_co_quan.bat`; EXE ra ở `dist\ChuanHoaCoQuan.exe`.
- Khi mang sang máy khác, chép EXE và `court_location_mapping.csv` cùng thư mục. Máy đích cần kết nối mạng tới Oracle DB.

## Quy trình

1. Sao lưu DB và điền CSV mapping.
2. Mở tool, nhập DSN/user/mật khẩu/schema, bấm **Kiểm tra kết nối**.
3. Chọn bảng cần rà soát, bấm **Lấy preview**; xác nhận mã và ID đích.
4. Chọn các dòng cần cập nhật hoặc cập nhật tất cả dòng READY. Nếu CSV, schema hoặc truy vấn có lỗi, tool khóa cập nhật.
5. Kiểm tra file audit tại `Documents\QLPNC10_chuan_hoa_co_quan_audit.csv`.

Mỗi lần apply dùng một transaction; nếu một dòng đổi sau preview, toàn bộ transaction rollback. Audit được ghi sau khi DB commit.
