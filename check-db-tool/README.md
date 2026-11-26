# Tool kiểm soát chuyển đổi dữ liệu C10

Ứng dụng desktop Windows độc lập. Project này không sửa và không phụ thuộc runtime vào `D:\QPLN\db-compare`; mapping/configuration được đặt riêng trong project.

## Chạy từ source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Hướng dẫn từng bước: [`HUONG_DAN_SU_DUNG.md`](HUONG_DAN_SU_DUNG.md).

## Build file EXE

Chạy `build_exe.bat`. File đầu ra: `dist\QLPNC10Checker.exe`. Máy chạy file EXE cần được cấp quyền mạng tới hai Oracle DB; không cần cài Python/Oracle Client nếu dùng Oracle thin mode.


## Quy tắc an toàn

- Tool chạy truy vấn SELECT và đặt transaction Oracle ở chế độ READ ONLY.
- Ghép hồ sơ chỉ theo HSLĐ duy nhất. Không dùng CCCD/CMND để ghép dự phòng.
- Thông tin kết nối và mật khẩu chỉ được giữ trong RAM trong phiên; tool không lưu chúng vào máy.
- Workbook có 4 sheet: `Tổng quan`, `Đối soát số lượng`, `Ghép phạm nhân`, `Chi tiết sai lệch`.
- Dataset chưa có nguồn/mapping nghiệp vụ sẽ hiển thị rõ trạng thái chưa thể đối soát.

## Cấu hình mapping

`mapping.py` là cấu hình riêng của ứng dụng. `assets/schema_old.json` và `assets/schema_new.json` là bản chụp schema để kiểm tra tĩnh; trước khi so sánh ứng dụng còn kiểm tra bảng/cột trên schema live được nhập.

Tài liệu đính kèm đã được loại khỏi phạm vi. Mapping danh mục legacy để tách TNDS/HPBS và ngữ nghĩa ngày biên lai vẫn cần xác minh trước khi kết luận đầy đủ.

Trong code C10 mới, TNDS được nhận diện bằng `HPBS_THUOC_LOAI_TRACH_NHIEM_DAN_SU = 1`; `PnHinhPhatBoSungsAppService` cũng chọn danh mục TNDS theo `DM_HINH_PHAT_BO_SUNGS.HPBS_LOAI_HPBS = 'TNDS'`. DDL legacy không có cờ tương đương; stored logic chỉ cho thấy mã hình phạt 201–299 được xử lý như HPBS trong một nghiệp vụ cụ thể, chưa đủ để phân loại toàn bộ dữ liệu cũ. Biên lai cũ nối cha qua `MA_PN_HPBSHP`; ở UI mới biên lai nối qua `HPBS_ID` và có hai ngày riêng `BL_NGAY_NHAN_VAN_BAN`, `BL_NGAY_NOP`, nên cần xác nhận ánh xạ `BIEN_LAI_NGAY` trước khi bật so sánh con.
