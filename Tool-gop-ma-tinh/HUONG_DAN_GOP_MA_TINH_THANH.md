# Tool gộp mã tỉnh/thành trong DB hiện tại

Đây là project riêng, nằm tại `D:\tool_c10\Tool-gop-ma-tinh`, tách khỏi `Tool-check-data` và tool convert DB cũ → DB mới. Tool này chỉ kết nối một DB hiện tại, không kết nối DB cũ, không ghép hồ sơ và không lấy dữ liệu từ DB danh mục bên ngoài.

## File chạy

- Chạy source: tạo môi trường ảo, cài `requirements.txt`, rồi chạy `python app_gop_ma_tinh.py` trong `D:\tool_c10\Tool-gop-ma-tinh`.
- Build EXE: chạy `build_gop_ma_tinh.bat`; file ra ở `dist\GopMaTinhThanh.exe`.
- File mapping `province_fk_merge.csv` phải ở cùng thư mục với source hoặc EXE. Build chỉ chép template vào `dist` khi chưa có file; nếu đã có CSV thì giữ nguyên file hiện có.

```powershell
cd D:\tool_c10\Tool-gop-ma-tinh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app_gop_ma_tinh.py
```

## CSV mã cũ → mã giữ

Header bắt buộc:

```csv
TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU
```

Mỗi dòng là một cặp đã được xác nhận. Chỉ `TRANG_THAI=APPROVED` mới được preview thành dữ liệu có thể cập nhật. Tool yêu cầu cả hai mã còn đúng một row active trong `DM_TINH_THANH_PHO`. Các mã thiếu, trùng, mapping trùng nguồn, hoặc chưa duyệt chỉ hiện lỗi, không được ghi. Hãy định dạng cột mã là text để giữ số 0 đầu mã.

## Phạm vi cột

Tool quét 30 cột tỉnh riêng biệt: whitelist `province` và `province_text_id` trong bản cấu hình `mapping.py` của project này, cộng với các field đã xác nhận:

- `GTH_KY_GIAM_THOI_HANS.KGTH_DIA_PHUONG_TOA_ID`
- `PN_BIENLAIES.BL_DIA_PHUONG`
- `PN_KET_THUC_RA_TRAIS.KTRT_CONG_AN_TINH_THANH_PHO_ID` (công an tỉnh/thành phố ở màn Ra trại)

Danh sách được lấy theo bảng/cột đích, loại trùng và kiểm tra kiểu dữ liệu schema snapshot cùng schema live. Cột NUMBER nhận ID dạng số; trường text chứa ID chỉ được hỗ trợ nếu được khai báo rõ là `province_text_id`. Trong phạm vi hiện có có ba FK tỉnh của Lai lịch, địa phương ở thi hành án, bản án/quyết định khác, giảm thời hạn, chữa bệnh bắt buộc, tăng/giảm hình phạt, trích xuất, tạm đình chỉ, hoãn, miễn/hủy hình phạt, tha có điều kiện, chuyển trại, chuyển giao, kỳ giảm thời hạn và biên lai.

| Bảng đích | Các cột được quét |
|---|---|
| `PN_LAI_LICHS` | `LL_DIA_CHI_THUONG_TRU_PROVICE`, `LL_NOI_OTRUOC_KHI_BAT_PROVICE`, `LL_NOI_THA_VE_CU_TRU_PROVICE` |
| `PN_THI_HANH_AN` | `THA_DIA_PHUONG_CO_QUAN_BAT_ID`, `THA_DIA_PHUONG_CAP_TOA_ID`, `THA_DIA_PHUONG_TOA_QD_THA_ID`, `THA_DIA_PHUONG_DON_VI_DE_NGHI_ID`, `THA_DIA_PHUONG_DON_CO_QUAN_LAP_ID` |
| `PN_BAN_AN_KHACS` | `BAK_TOA_XU_DP_ID` |
| `GIAM_THOI_HANS` | `DIA_PHUONG_ID` |
| `GTH_KY_GIAM_THOI_HANS` | `KGTH_DIA_PHUONG_TOA_ID` |
| `CHUA_BENH_BAT_BUOCS` | `DIA_PHUONG_QUYET_DINH_ID` |
| `TANG_GIAM_HINH_PHATS` | `DIA_PHUONG_QUYET_DINH_ID` |
| `TRICH_XUATS` | `TX_DIA_PHUONG_DE_NGHI_ID`, `TX_DIA_PHUONG_VE_ID` |
| `TAM_DINH_CHIS` | `DIA_PHUONG_ID`, `NOI_VE_DIA_PHUONG_ID` |
| `HOAN_THI_HANH_ANS` | `DIA_PHUONG_ID` |
| `MIEN_HINH_PHATS` | `MHP_DIA_PHUONG_QD` |
| `HUY_ANS` | `DIA_PHUONG_ID` |
| `THA_CO_DIEU_KIENS` | `DIA_PHUONG_QUYET_DINH_THA_ID`, `DIA_PHUONG_QUYET_DINH_LAI_ID` |
| `PN_CHUYEN_GIAO` | `PNCG_DIA_PHUONG_QDCGID`, `PNCG_DIA_PHUONG_THQDCGID` |
| `PHAM_NHAN_CHUYEN_TRAI` | `PNCT_CO_QUAN_DE_NGHI_DIA_PHUONG_ID`, `PNCT_TRAI_DEN_DIA_PHUONG_ID` |
| `PN_QUYET_DINH_BAN_AN_KHACS` | `QDBAK_TOA_QUYET_DINH_DP_ID`, `QDBAK_TOA_XU_DP_ID` |
| `PN_BIENLAIES` | `BL_DIA_PHUONG` |
| `PN_KET_THUC_RA_TRAIS` | `KTRT_CONG_AN_TINH_THANH_PHO_ID` |

Tool không quét `LL_NOI_OKHAC_PROVICE` vì chưa có nguồn mã cũ rõ ràng. Các cột được bổ sung ngoài danh sách mapping gốc là kỳ giảm thời hạn, biên lai và `PN_KET_THUC_RA_TRAIS.KTRT_CONG_AN_TINH_THANH_PHO_ID`. Cột Ra trại được đưa vào vì tool này chuyển FK ngay trong DB hiện tại, không phụ thuộc nguồn legacy.

Không quét cột chỉ vì tên giống địa phương. Không gồm `PN_TIEN_AN.PNTA_DIA_PHUONG_ID` (danh mục `DM_DIA_PHUONG`), trường chưa xác nhận như điều chuyển/giao nhận, `LL_NOI_OKHAC_PROVICE` chưa có nguồn/mapping, bảng RT/tổng hợp và bảng backup.

## Quy trình

1. Sao lưu DB và hoàn tất cập nhật các danh mục tỉnh/xã theo runbook của đơn vị.
2. Giữ nguyên row tỉnh cũ và row tỉnh muốn giữ; nhập các cặp mã đã duyệt vào CSV.
3. Mở tool, nhập DSN, user, mật khẩu và schema DB hiện tại; bấm **Kiểm tra kết nối** để xác nhận đăng nhập và quyền đọc danh mục tỉnh. Nút này chỉ chạy truy vấn metadata, không đọc/ghi dữ liệu nghiệp vụ.
4. Chọn các bảng cần rà soát trong danh sách checkbox (mặc định chọn tất cả). **Chọn tất cả** và **Bỏ chọn tất cả** hỗ trợ đổi phạm vi nhanh.
5. Bấm **Lấy preview**. Tool chỉ kiểm tra schema và quét các bảng đang chọn; status hiển thị số bảng/cột trong phạm vi và các dòng READY. Mỗi dòng nêu bảng, cột, Row ID (ID của bản ghi đích), Số HSLĐ của phạm nhân liên quan nếu xác định được, mã cũ, mã giữ, ID hiện tại và ID dự kiến. Một số bảng không gắn trực tiếp hồ sơ phạm nhân nên Số HSLĐ có thể để trống.
6. Chọn từng dòng hoặc bấm **Cập nhật tất cả dòng hợp lệ**. Phạm vi cập nhật chính là các bảng của preview hiện tại. Nếu một cột trong bảng đã chọn không đọc được hoặc schema live không khớp, tool khóa cập nhật để tránh chạy thiếu phạm vi. Khi apply, tool cập nhật có điều kiện theo row ID và giá trị FK cũ; nếu bất kỳ dòng nào đã đổi từ lúc preview, toàn bộ transaction rollback.
7. Preview lại với các bảng cần xác nhận. Sau đó kiểm tra toàn DB không còn FK trỏ ID tỉnh sắp bỏ; cuối cùng mới xóa row mã cũ theo quy trình thủ công.

Tool không xóa `DM_TINH_THANH_PHO`, không cập nhật `DM_XA_PHUONG`, không tự động cập nhật cột không có trong whitelist. Lưu ý: nếu tồn tại FK tỉnh trong bảng chưa được khai báo, tool không tự tìm hoặc cập nhật chúng; phải kiểm kê trước khi xóa row danh mục.

Audit nối vào `Documents\QLPNC10_gop_ma_tinh_audit.csv` sau khi DB commit. Nếu ghi audit thất bại, trạng thái sẽ báo DB đã commit nhưng không ghi được file.
