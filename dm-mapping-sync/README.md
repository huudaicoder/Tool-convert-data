# Tool đồng bộ danh mục theo ID

Tool desktop độc lập để đồng bộ các dòng thiếu theo `ID` giữa hai cặp bảng Oracle:

- `QLPN.DM_DAN_TOCS_OLD` → `QLPN.DM_DAN_TOCS`
- `QLPN.DM_TON_GIAOS_OLD` → `QLPN.DM_TON_GIAOS`

## Chạy tool

Mở `QLPNDMSync.exe`, nhập DSN, user, mật khẩu và schema (mặc định `QLPN`). Bấm **Kiểm tra kết nối và ID thiếu** để xem preview. Nếu có dòng cần thêm, bấm **Chèn các ID đang thiếu** và xác nhận hộp thoại.

Tool giữ nguyên ID và các cột audit, không cập nhật ID đã tồn tại. Cả hai cặp bảng được ghi trong cùng transaction và rollback nếu có lỗi. Mật khẩu chỉ được giữ trong RAM.

## Chạy từ mã nguồn

```powershell
python -m pip install -r requirements.txt
python dm_mapping_tool.py
```

## Build EXE

Chạy `build_exe.bat`; file đầu ra là `dist\QLPNDMSync.exe`. Build cần Python 3.13, PyInstaller, oracledb và Tkinter.
