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

## Tool riêng gộp mã tỉnh trong DB hiện tại

Tool gộp mã được đặt riêng tại `D:\tool_c10\Tool-gop-ma-tinh`. Chạy `python app_gop_ma_tinh.py` trong thư mục đó hoặc build bằng `build_gop_ma_tinh.bat` để tạo `dist\GopMaTinhThanh.exe`. Hướng dẫn ở [`../Tool-gop-ma-tinh/HUONG_DAN_GOP_MA_TINH_THANH.md`](../Tool-gop-ma-tinh/HUONG_DAN_GOP_MA_TINH_THANH.md). `QLPNC10Checker.exe` giữ riêng luồng convert DB cũ → DB mới.

## Quy tắc an toàn

- Các tab đối soát/preview chỉ đọc. Tab convert địa phương và các tab cập nhật chỉ ghi DB mới sau preview, chọn dòng và xác nhận; cần tài khoản DB mới có quyền UPDATE tối thiểu trên các bảng đích.
- Tab Convert địa phương của `QLPNC10Checker.exe` chỉ dành cho DB cũ → DB mới. Gộp mã trong DB hiện tại chạy bằng `GopMaTinhThanh.exe` riêng; mỗi tool có file `province_fk_merge.csv` riêng cạnh source/EXE, chỉ dòng `APPROVED` được áp dụng.
- Tool gộp mã hiện tại xử lý FK tỉnh trong whitelist `mapping.py` cùng `GTH_KY_GIAM_THOI_HANS.KGTH_DIA_PHUONG_TOA_ID` và `PN_BIENLAIES.BL_DIA_PHUONG`; không xóa danh mục tỉnh hoặc cập nhật xã/phường. Chạy preview/update trước khi tự xóa mã tỉnh cũ; kiểm kê FK toàn DB trước khi xóa.
- Cả hai tool không sửa text tên tòa/cơ quan/địa danh huyện.
- Ghép hồ sơ chỉ theo HSLĐ duy nhất. Không dùng CCCD/CMND để ghép dự phòng.
- Thông tin kết nối và mật khẩu chỉ được giữ trong RAM trong phiên; tool không lưu chúng vào máy.
- Workbook có 4 sheet: `Tổng quan`, `Đối soát số lượng`, `Ghép phạm nhân`, `Chi tiết sai lệch`.
- Dataset chưa có nguồn/mapping nghiệp vụ sẽ hiển thị rõ trạng thái chưa thể đối soát.

## Cấu hình mapping

`mapping.py` là cấu hình riêng của ứng dụng. `assets/schema_old.json` và `assets/schema_new.json` là bản chụp schema để kiểm tra tĩnh; trước khi so sánh ứng dụng còn kiểm tra bảng/cột trên schema live được nhập.

File `province_fk_merge.csv` phải nằm cạnh `app.py` khi chạy source hoặc cạnh `QLPNC10Checker.exe` khi chạy bản build. Dùng UTF-8/UTF-8 BOM với header `TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU`; trạng thái phải là `APPROVED` viết hoa. CSV mẫu được tạo sẵn nhưng để trống dữ liệu để tránh tự suy diễn các cặp mã.

Tài liệu đính kèm đã được loại khỏi phạm vi. Mapping danh mục legacy để tách TNDS/HPBS và ngữ nghĩa ngày biên lai vẫn cần xác minh trước khi kết luận đầy đủ.

Trong code C10 mới, TNDS được nhận diện bằng `HPBS_THUOC_LOAI_TRACH_NHIEM_DAN_SU = 1`; `PnHinhPhatBoSungsAppService` cũng chọn danh mục TNDS theo `DM_HINH_PHAT_BO_SUNGS.HPBS_LOAI_HPBS = 'TNDS'`. DDL legacy không có cờ tương đương; stored logic chỉ cho thấy mã hình phạt 201–299 được xử lý như HPBS trong một nghiệp vụ cụ thể, chưa đủ để phân loại toàn bộ dữ liệu cũ. Biên lai cũ nối cha qua `MA_PN_HPBSHP`; ở UI mới biên lai nối qua `HPBS_ID` và có hai ngày riêng `BL_NGAY_NHAN_VAN_BAN`, `BL_NGAY_NOP`, nên cần xác nhận ánh xạ `BIEN_LAI_NGAY` trước khi bật so sánh con.
