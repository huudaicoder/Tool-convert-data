# Tool convert địa danh DB cũ → DB mới

Tool Windows độc lập, tách khỏi `Tool-check-data`, `Tool-gop-ma-tinh` và `Tool-chuan-hoa-toa-an`.

## Cách mapping

- Đọc mã `MA_CQ` trong các bảng nguồn cũ, tra `DM_CO_QUANS.CQ_MA` ở DB mới, lấy `DM_CO_QUANS.ID`.
- Đọc mã `MA_DP` trong các bảng nguồn cũ, tra `DM_TINH_THANH_PHO.TTP_MA` ở DB mới, lấy `DM_TINH_THANH_PHO.ID`.
- Ba trường xã/phường của Lai lịch: dùng tên text `DC_*_PHUONG_XA` cùng mã `MA_DP_DC_*` tương ứng để lọc `MA_DP_XA_PHUONG` theo `ND` và `MA_QH`; lấy `MA`, đối chiếu chính xác toàn danh mục DB mới với `DM_XA_PHUONG.XP_MA`, rồi lấy `DM_XA_PHUONG.ID`.
- Mã được so sánh sau khi trim/kết gọn khoảng trắng, không bỏ số 0 đầu. Chỉ dùng dòng danh mục chưa xóa mềm (`IS_DELETED=0` nếu có). Mã thiếu hoặc không duy nhất được báo trong preview; tool không dò tên gần đúng và không dùng CSV crosswalk.
- Tên xã/phường được chuẩn hóa khoảng trắng và bỏ tiền tố `Xã`/`Phường`/`Thị trấn` trước khi dò exact match. Nếu tên + `MA_QH` ở DB cũ hoặc mã `MA` → `XP_MA` ở DB mới không khớp duy nhất, tool chỉ báo preview và không cập nhật.
- Ghép hồ sơ theo HSLĐ duy nhất. Ghép bản ghi sự kiện theo khóa trong `mapping.py`; thiếu/trùng khóa thì bỏ qua.

## Cài và chạy source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Build EXE

Chạy `build_exe.bat`. File chạy độc lập nằm tại `dist\ConvertDiaDanhCuMoi.exe`. Không cần CSV mapping kèm theo. Máy đích cần truy cập mạng tới hai Oracle DB.

## Quy trình

1. Nhập DSN/user/password/schema cho DB cũ và DB mới; mật khẩu chỉ giữ trong RAM.
2. DB cũ được xem là dữ liệu của một trại nên tool đọc toàn bộ hồ sơ cũ, không yêu cầu nhập `MA_TRAI_GIAM`. Nhập mã trại DB mới (`TG_MA`) để giới hạn hồ sơ đích cần ghép và cập nhật.
3. Bấm kiểm tra kết nối từng DB, chọn một màn/bảng rồi lấy preview.
4. Preview hiển thị một dòng cho mỗi bản ghi DB và một cột riêng cho mỗi trường địa danh của bảng đang chọn. Mỗi ô cho biết mã cũ + tên cũ, ID hiện tại + tên hiện tại, rồi ID đích + tên đích. Chỉ trường lệch hoặc lỗi tra mã mới hiện; giá trị cũ có mã thì được ưu tiên, mã nguồn trống thì giữ nguyên ID DB mới. Chọn một dòng để cập nhật tất cả trường READY của bản ghi đó, hoặc cập nhật toàn bộ READY trong bảng đang preview.
5. Mỗi lần cập nhật chạy trong một transaction ở DB mới; thay đổi bất ngờ làm rollback. Audit được ghi tại `Documents\QLPNC10_convert_dia_danh_cu_moi_audit.csv`.

DB cũ chỉ SELECT. Tool chỉ cập nhật các cột ID địa danh trong whitelist, không thêm/xóa hồ sơ, sửa danh mục hoặc đổi text địa danh lịch sử. Tiền án map `MA_DP_TOA_XU_TA` → `PNTA_DIA_PHUONG_ID`. Biên lai TNDS/HPBS map `MA_CQ_THU_NOP` → `BL_NOP_TAI_CO_QUAN` và `MA_DP_THU_NOP` → `BL_DIA_PHUONG`; dòng biên lai ghép qua HPBS cha theo số biên lai, ngày nộp và số tiền. `LL_NOI_OKHAC_PROVICE` chưa có nguồn mã rõ và `KTRT_CONG_AN_TINH_THANH_PHO_ID` không thuộc phạm vi.

Thiết kế chi tiết: `docs\superpowers\specs\2026-11-25-old-new-location-conversion-design.md`.
