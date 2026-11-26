# Thiết kế và triển khai: hai tool xử lý mã địa phương

Ngày: 2026-11-25  
Trạng thái: Đã tách chương trình; chưa chạy trên DB người dùng.

## Phân chia

1. `QLPNC10Checker.exe`: dành cho convert dữ liệu DB cũ → DB mới, cần hai kết nối và ghép hồ sơ/sự kiện.
2. `D:\tool_c10\Tool-gop-ma-tinh\GopMaTinhThanh.exe`: project độc lập ngoài `Tool-check-data`, chỉ xử lý DB mới hiện tại; gộp các FK tỉnh đang trỏ mã cũ sang ID tỉnh giữ lại trước khi người vận hành xóa row danh mục cũ.

CSV `province_fk_merge.csv` có header `TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU`. Đặt cạnh source/EXE. Chỉ dòng `APPROVED` được xét. Không tự tạo mapping từ danh sách tỉnh; cả mã cũ và mã giữ phải có đúng một row active trong `DM_TINH_THANH_PHO`.

## Tool mới gộp mã tỉnh

- Source: `D:\tool_c10\Tool-gop-ma-tinh\app_gop_ma_tinh.py`; build bằng `D:\tool_c10\Tool-gop-ma-tinh\build_gop_ma_tinh.bat` / `GopMaTinhThanh.spec`.
- Tự lấy whitelist cột tỉnh từ các cặp đích `province`/`province_text_id` trong `mapping.py`.
- Bổ sung hai cặp đã xác nhận ngoài mapping convert: `GTH_KY_GIAM_THOI_HANS.KGTH_DIA_PHUONG_TOA_ID` và `PN_BIENLAIES.BL_DIA_PHUONG`.
- Chỉ quét field tồn tại trong schema snapshot và schema live; ID NUMBER được bind số, field text chứa ID chỉ cho phép khi khai báo `province_text_id`.
- Preview cho từng row: bảng/cột/ID dòng/mã cũ/mã giữ/ID trước/ID sau/trạng thái. Hỗ trợ chọn dòng hoặc toàn bộ READY.
- Update dùng whitelist cố định, `WHERE ID + giá trị cũ`, rollback toàn transaction nếu bất kỳ rowcount nào khác 1. Audit nối vào `Documents\QLPNC10_gop_ma_tinh_audit.csv`.
- Không update danh mục, xã/phường, cột không nằm trong whitelist, hoặc xóa tỉnh.

### Trường ngoài phạm vi

- `PN_TIEN_AN.PNTA_DIA_PHUONG_ID`: lookup `DM_DIA_PHUONG`, không phải FK tỉnh.
- `PN_LAI_LICHS.LL_NOI_OKHAC_PROVICE`: chưa có mã nguồn cũ rõ ràng.
- `DIEU_CHUYENS`, `PN_GIAO_NHAN_PHAN_NHANS`: quan hệ/nguồn chưa được xác nhận đầy đủ.
- `PN_LAI_LICH_CHI_TIET_RT`, bảng backup, bảng lỗi: không update trực tiếp.
- `PN_KET_THUC_RA_TRAIS.KTRT_CONG_AN_TINH_THANH_PHO_ID`: được quét trong tool DB hiện tại; không phụ thuộc nguồn legacy.

## Quy trình vận hành

1. Sao lưu DB; bảo đảm row cũ và row giữ vẫn còn để tra ID.
2. Điền CSV các cặp đã xác nhận.
3. Chạy `GopMaTinhThanh.exe`, nhập kết nối DB mới, lấy preview và rà các row READY/lỗi.
4. Cập nhật dòng chọn hoặc toàn bộ dòng READY; stale preview làm rollback cả transaction.
5. Lấy preview lại. Kiểm kê mọi FK tỉnh trong DB, kể cả ngoài whitelist.
6. Chỉ sau khi không còn tham chiếu mới tự xóa row mã cũ và cập nhật `XP_MA_TINH_THANH_PHO` theo quy trình danh mục.

Không thay tên tòa/cơ quan, địa danh huyện hoặc text địa chỉ. Ví dụ địa danh lịch sử “Tòa án nhân dân huyện Quỳnh Phụ, tỉnh Thái Bình” phải được giữ ở trường văn bản; ID tỉnh không biểu diễn cấp huyện.

## Files

- Tool mới: `D:\tool_c10\Tool-gop-ma-tinh\app_gop_ma_tinh.py`, `GopMaTinhThanh.spec`, `build_gop_ma_tinh.bat`.
- Hướng dẫn: `D:\tool_c10\Tool-gop-ma-tinh\HUONG_DAN_GOP_MA_TINH_THANH.md`.
- Tool DB cũ → DB mới: `app.py`, tab Convert địa phương; UI không còn chế độ gộp DB hiện tại.
