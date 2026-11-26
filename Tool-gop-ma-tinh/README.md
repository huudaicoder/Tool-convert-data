# Tool gộp mã tỉnh/thành trong DB hiện tại

Project độc lập, không nằm trong `Tool-check-data`. Source và EXE chỉ kết nối DB hiện tại; tool dùng CSV crosswalk để đổi các FK tỉnh từ ID mã cũ sang ID mã giữ lại trước khi xóa row danh mục.

- Source: `app_gop_ma_tinh.py`
- CSV riêng: `province_fk_merge.csv`
- Build: `build_gop_ma_tinh.bat`
- Hướng dẫn: `HUONG_DAN_GOP_MA_TINH_THANH.md`
- Whitelist: `mapping.py` cộng ba field đã xác nhận nằm trong `app_gop_ma_tinh.py`.

Chi tiết phạm vi bảng/cột, quy tắc preview/update và giới hạn: xem hướng dẫn sử dụng.
