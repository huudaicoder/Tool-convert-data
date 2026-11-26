# Chuyển địa phương tòa xử Tiền án

Tool chạy riêng, kết nối một DB mới. Preview đọc `PN_TIEN_AN.PNTA_DIA_PHUONG_ID`, tra `DM_DIA_PHUONG.ID -> DP_MA`, rồi tìm đúng duy nhất `DM_TINH_THANH_PHO.TTP_MA` và cập nhật ID tương ứng vào FK tiền án.

- Chỉ xử lý bản ghi tiền án đang hoạt động nếu bảng có `IS_DELETED`.
- Preview không ghi DB; mã thiếu/trùng được liệt kê để rà soát.
- Có thể cập nhật dòng chọn hoặc toàn bộ dòng khớp duy nhất; kiểm tra lại mapping trước ghi và rollback toàn bộ khi phát hiện khác biệt.
- Ghi nhận ID đã chuyển cục bộ tại `%LOCALAPPDATA%\QLPNTienAnDiaPhuong\conversion_ledger.json`, không lưu mật khẩu.
- Oracle user cần SELECT trên ba bảng, UPDATE trên `PN_TIEN_AN`.

Build: cài Python dependencies từ `requirements.txt`, rồi chạy `build_exe.bat`. EXE nằm ở `dist\ChuyenDiaPhuongTienAn.exe`.
