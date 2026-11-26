# db-compare — so sánh dữ liệu DB cũ (QLPN_SUOI_HAI) với DB mới (QLPN)

Tool độc lập, không thuộc code QLPN. Chỉ chạy `SELECT`, không ghi gì vào DB.

## Cài đặt
```bash
pip install -r requirements.txt     # oracledb (thin mode, không cần Oracle Client) + openpyxl
```

## Chạy
```bash
# Kiểm tra file mapping so với 2 file DDL (không cần kết nối DB)
python compare.py --check-mapping

# So sánh thật (mật khẩu được hỏi khi chạy, hoặc đặt biến OLD_PWD / NEW_PWD)
python compare.py --old-dsn HOST:1521/SERVICE_CU --old-user QLPN_SUOI_HAI \
                  --new-dsn 10.0.229.237:1521/FREEPDB1 --new-user QLPN \
                  --screens LL01,DB08,KT01 --out ket_qua.xlsx
```
Bỏ `--screens` để chạy cả 33 màn. Thêm `--ignore-case` nếu muốn bỏ qua hoa/thường. Nếu user kết nối không
phải chủ schema, thêm `--old-schema` / `--new-schema`.

## Cách so sánh
1. **Ghép phạm nhân** (bảng lai lịch): theo Số HSLĐ; không có thì theo CCCD/CMND. Kết quả ở sheet `PhamNhan`
   (Khớp HSLĐ + CCCD / lệch CCCD / chỉ khớp CCCD / chỉ có ở một bên / trùng không phân biệt được).
2. **Từng màn**: với mỗi cặp phạm nhân đã ghép, ghép từng dòng theo `key` khai báo trong `mapping.py`
   (ví dụ khen thưởng = Số QĐ + Ngày). Màn không có key thì mỗi phạm nhân một dòng.
3. Giá trị được chuẩn hóa trước khi so: bỏ khoảng trắng thừa, NULL = chuỗi rỗng, ngày chỉ so phần ngày,
   số so theo giá trị, danh mục đổi `ID` (DB mới) ra `MÃ` rồi so với mã DB cũ.
4. Kết luận mỗi màn: **Trùng khớp toàn bộ / Trùng key (lệch giá trị) / Trùng một phần / Không trùng / Không có dữ liệu**.

## Kết quả Excel
`Tong_hop` (33 màn) · `PhamNhan` · `Cot_lech` (cột nào lệch nhiều nhất) · mỗi màn một sheet liệt kê các dòng không
khớp (Lệch giá trị / Chỉ có ở DB cũ / Chỉ có ở DB mới, kèm giá trị cũ và mới).

## Sửa mapping
Mọi cặp bảng, cặp cột, key nằm trong `mapping.py`. Các cặp còn nghi vấn nằm ở `DISABLED_SCREENS`
(Xếp loại, Nộp lưu, Chuyển trại, Trách nhiệm dân sự) — muốn bật thì chuyển sang `SCREENS` kèm `cols`.
`schema_old.json` / `schema_new.json` sinh từ 2 file DDL bằng `parse_ddl.py`.

## Giao diện (GUI)
Có bản GUI (`gui.py`, tkinter — có sẵn trong Python, không cần cài thêm) để nhập DSN/user/mật khẩu,
tick chọn màn cần so sánh, chọn nơi lưu file Excel rồi bấm chạy, không cần gõ lệnh.

```bash
python gui.py
```

Nút **"Kiểm tra mapping"** chạy `--check-mapping` (không cần kết nối DB). Nút **"Chạy so sánh"** chạy
toàn bộ các màn đã tick. Nhật ký tiến trình hiện trong khung bên dưới; xong sẽ hỏi mở file Excel luôn.

### Đóng gói thành .exe (không cần cài Python trên máy chạy)
```bash
build_exe.bat
```
File `dist\SoSanhQLPN.exe` tạo ra là 1 file độc lập (đã có sẵn), copy mang đi máy khác chạy được luôn
— miễn máy đó mở được tới 2 Oracle DB qua mạng. Build lại mỗi khi sửa `compare.py`/`mapping.py`/`gui.py`.
