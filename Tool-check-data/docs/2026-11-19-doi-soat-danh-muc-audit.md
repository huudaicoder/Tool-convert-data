# Rà soát mapping danh mục theo màn và cột

Ngày rà soát: 2026-11-19  
Phạm vi: tab **Đối soát**, toàn bộ 40 cấu hình trong `mapping.py`; đối chiếu schema đóng gói, DDL DB mới và code giao diện/service QLPN mới trong `bxd.c10-qlpn`.

## Kết quả

Trong 40 màn/dataset, cấu hình có 157 cột dùng danh mục: 119 `dm`, 12 `dmlist`, 2 `dm_legacy`, 24 `province`. Danh sách từng màn, từng cột và phép quy đổi nằm trong [Mapping_doi_soat_tung_bang_tung_cot.md](Mapping_doi_soat_tung_bang_tung_cot.md).

Rà soát đã tìm và sửa các nhóm sau:

1. **14 cột địa phương** bị khai báo nhầm `DM_DIA_PHUONG`; code QLPN mới dùng lookup tỉnh/thành `DM_TINH_THANH_PHO`. Các cột này nay chuyển mã cũ qua `MAPPING_PROVINCE` rồi tra `TTP_MA` lấy ID.
2. **Ân giảm:** `AG_LY_DO_AN_GIAM` là ô nhập text trên màn hình và là chuỗi tự do, không phải FK/ID của `DM_LY_DO_AN_GIAMS`. Đã bỏ phép tra ID. Tool hiện so nội dung text trực tiếp sau chuẩn hóa. Mã cũ `MA_LD_AN_GIAM` chưa được tự đổi thành tên hiển thị; cần coi khác biệt ở cột này là khác nội dung cho đến khi có quy tắc chuyển mã → tên được xác nhận.
3. **Mức án:** `LL03_ThiHanhAn`, `LL04_TienAn`, `LL06_BanAnKhac` dùng `DM_MA_THOI_GIANS`/`MTG_MA`; không dùng `DM_MUC_ANS` cho màn Bản án khác.
4. **Tiền án:** giữ `DM_DIA_PHUONG` cho `PNTA_DIA_PHUONG_ID`; component dùng `DmDiaPhuongServiceProxy`, khác với các màn địa phương quyết định dùng tỉnh/thành.
5. **Dân tộc/tôn giáo:** tiếp tục dùng đúng chuỗi danh mục cũ → ID danh mục cũ → bảng mapping → ID danh mục mới → mã hiện hành.

## Các cột địa phương đã sửa

Trong bảng dưới, code của component/API xác nhận lookup là `DmTinhThanhPho` (tên property ở một vài màn vẫn gọi “Địa phương”). Quy tắc dùng cho cả cột là `MA_DP_*` cũ → `MAPPING_PROVINCE.MA_TINH_OLD/MA_TINH_NEW` → `DM_TINH_THANH_PHO.TTP_MA` → `ID`.

| Màn | Cột DB cũ | Cột DB mới | Bằng chứng trong code QLPN mới |
|---|---|---|---|
| Thi hành án | `PN_LAI_LICH.MA_DP_RL_BAT` | `PN_THI_HANH_AN.THA_DIA_PHUONG_CO_QUAN_BAT_ID` | `thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Thi hành án | `PN_LAI_LICH.MA_DP_TOA_XU` | `PN_THI_HANH_AN.THA_DIA_PHUONG_CAP_TOA_ID` | `thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Thi hành án | `PN_LAI_LICH.MA_DP_TOA_QD` | `PN_THI_HANH_AN.THA_DIA_PHUONG_TOA_QD_THA_ID` | `thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Thi hành án | `PN_LAI_LICH.MA_DP_DN_DC` | `PN_THI_HANH_AN.THA_DIA_PHUONG_DON_VI_DE_NGHI_ID` | `thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Thi hành án | `PN_LAI_LICH.MA_DP_LAP_DB` | `PN_THI_HANH_AN.THA_DIA_PHUONG_DON_CO_QUAN_LAP_ID` | `thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Bản án khác | `PN_BAN_AN.MA_DP_TOA_XU_BA` | `PN_BAN_AN_KHACS.BAK_TOA_XU_DP_ID` | `PnBanAnKhacsAppService` lấy `DmTinhThanhPho`; giao diện gán ID vào `bakToaXuDpId` |
| Chữa bệnh bắt buộc | `PN_CHUA_BENH_BAT_BUOC.MA_DP_TOA_AN_QD` | `CHUA_BENH_BAT_BUOCS.DIA_PHUONG_QUYET_DINH_ID` | `chua-benh-bat-buoc.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Tăng giảm hình phạt | `PN_TANG_GIAM_HINH_PHAT.MA_DP_TOA_QD` | `TANG_GIAM_HINH_PHATS.DIA_PHUONG_QUYET_DINH_ID` | `tang-giam-hinh-phat-list.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Trích xuất | `PN_TX_TRICH_XUAT.MA_DP_DN_TX` | `TRICH_XUATS.TX_DIA_PHUONG_DE_NGHI_ID` | `trich-xuat-list.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Trích xuất | `PN_TX_TRICH_XUAT.MA_DP_TX_VE` | `TRICH_XUATS.TX_DIA_PHUONG_VE_ID` | `trich-xuat-list.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Tạm đình chỉ | `PN_TDC_TAM_DINH_CHI.MA_DP_CUA_TOA` | `TAM_DINH_CHIS.DIA_PHUONG_ID` | `tam-dinh-chi.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Tạm đình chỉ | `PN_TDC_TAM_DINH_CHI.MA_DP_NOI_VE` | `TAM_DINH_CHIS.NOI_VE_DIA_PHUONG_ID` | `tam-dinh-chi.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Hoãn thi hành án | `PN_HOAN_THI_HANH_AN.MA_DP_TOA_QD_HOAN` | `HOAN_THI_HANH_ANS.DIA_PHUONG_ID` | `hoan-thi-hanh-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Miễn hình phạt | `PN_MIEN_HINH_PHAT.MA_DP_TOA_QD_MIEN` | `MIEN_HINH_PHATS.MHP_DIA_PHUONG_QD` | `mien-hinh-phat.component.ts` nạp `DmTinhThanhPho`; option lưu `ID` |
| Hủy án | `PN_HUY_AN.MA_DP_TOA_HUY` | `HUY_ANS.DIA_PHUONG_ID` | `huy-an.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Tha có điều kiện | `PN_THA_CO_DK.MA_DP_TOA_QD_TT` | `THA_CO_DIEU_KIENS.DIA_PHUONG_QUYET_DINH_THA_ID` | `tha-co-dieu-kien.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Tha có điều kiện | `PN_THA_CO_DK.MA_DP_TOA_QD_TL` | `THA_CO_DIEU_KIENS.DIA_PHUONG_QUYET_DINH_LAI_ID` | `tha-co-dieu-kien.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Quyết định thi hành án khác | `PN_QD_THI_HANH_AN.MA_DP_TOA_QDTH_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_QUYET_DINH_DP_ID` | Component Bản án khác dùng chung lookup `DmDiaPhuongToaAn`, backend trả `DmTinhThanhPho` ID |
| Quyết định thi hành án khác | `PN_QD_THI_HANH_AN.MA_DP_TOA_XU` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_XU_DP_ID` | Component Bản án khác dùng chung lookup `DmDiaPhuongToaAn`, backend trả `DmTinhThanhPho` ID |
| Chuyển giao | `PN_CHUYEN_GIAO.MA_DP_TOA_CG` | `PN_CHUYEN_GIAO.PNCG_DIA_PHUONG_QDCGID` | `chuyen-giao.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Chuyển giao | `PN_CHUYEN_GIAO.MA_DP_TOA_QDTH_CG` | `PN_CHUYEN_GIAO.PNCG_DIA_PHUONG_THQDCGID` | `chuyen-giao.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Chuyển trại | `PN_CHUYEN_TRAI.MA_DP_TRAI_DEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_TRAI_DEN_DIA_PHUONG_ID` | `chuyen-trai.component.ts` dùng `DmTinhThanhPhoServiceProxy` |
| Chuyển trại | `PN_CHUYEN_TRAI.MA_DP_DN_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_CO_QUAN_DE_NGHI_DIA_PHUONG_ID` | `chuyen-trai.component.ts` dùng `DmTinhThanhPhoServiceProxy` |

`LL04_TienAn.MA_DP_TOA_XU_TA → PN_TIEN_AN.PNTA_DIA_PHUONG_ID` là ngoại lệ có căn cứ: `thong-tin-tien-an.component.ts` gọi `DmDiaPhuongServiceProxy`, nên giữ `DM_DIA_PHUONG.ID → DP_MA`.

## Các dạng danh mục khác

### Danh mục đơn

Với `dm`, DB cũ được coi là mã; DB mới được coi là ID. Tool lấy `ID → cột mã *_MA` từ đúng danh mục được khai báo rồi so mã. Các bảng danh mục được cấu hình đều có `ID` và một cột mã `*_MA` theo schema đóng gói. Dân tộc/tôn giáo không dùng quy tắc này trực tiếp mà dùng cầu nối riêng.

Một số cột đích là `VARCHAR2/NVARCHAR2` nhưng giao diện vẫn chọn và lưu ID dạng chuỗi. Đã kiểm tra các trường đó trong code:

| Màn / cột | Bằng chứng UI | Cách đối chiếu |
|---|---|---|
| Giam riêng: `GR_LOAI_QUYET_DINH`, `GR_LY_DO`, `GR_THOI_HAN_GIAM_RIENG` | `giam-rieng.component.ts` tạo option có `value = ID`, lưu giá trị dropdown vào DTO | Giữ `dm`; đổi ID chuỗi thành mã từ `DM_LENH_GIAM_RIENGS`, `DM_LY_DO_GIAM_RIENG_PHAM_NHANS`, `DM_MA_THOI_GIANS` tương ứng |
| Miễn hình phạt: `MHP_TOA_QUYET_DINH`, `MHP_TRUONG_HOP_MIEN` | `mien-hinh-phat.component.ts` nạp option với `value = ID`; submit ID | Giữ `dm`; dùng `DM_CO_QUANS`, `DM_TRUONG_HOP_MIEN_HINH_PHATS` tương ứng |
| Đặc xá: `DX_TINH_TRANG_DAC_XA` | `dac-xa.service.ts` nạp cả ID/mã; `dac-xa.component.ts` lưu `id` vào DTO | Giữ `dm`; đổi ID (kể cả dạng chuỗi) về `DM_DUOC_DAC_XAS.DDX_MA` |

### Danh sách ID

`dmlist` tách các giá trị theo dấu phẩy/chấm phẩy/pipe; dịch từng ID mới về mã danh mục, sắp xếp rồi so như danh sách. Có 12 cột dạng này. Code của giao diện và dữ liệu thực tế cần thống nhất rằng từng cột thật sự chứa danh sách ID, không phải danh sách mã.

### Ân giảm là text, không phải khóa danh mục

`MA_LD_AN_GIAM → AG_LY_DO_AN_GIAM`: màn QLPN mới khai báo ô text tự nhập, DTO/entity mới là chuỗi; không có quan hệ lookup trong thao tác lưu. Cấu hình trước đây tra `AG_LY_DO_AN_GIAM` như ID danh mục là không đúng với giao diện hiện tại. Giờ tool so text trực tiếp. DB cũ có bảng `MA_LD_AN_GIAM(MA, ND)`, nhưng chưa có quy tắc được xác nhận để biến mã cũ thành `ND`; vì vậy tool chưa tự đổi mã thành tên.

## Giới hạn xác nhận

- Đã kiểm tra cấu hình từng màn/cột, tên và kiểu cột schema, DDL, cùng các component/service lookup nêu trong tài liệu.
- Chưa kết nối DB nghiệp vụ của trại để xác nhận dữ liệu thật: mã nào thiếu trong `MAPPING_PROVINCE`, mã danh mục có trùng hay không, ID có bị trỏ nhầm/đã xóa hay không.
- Đối với 119 cột `dm` và 12 cột `dmlist`, cấu hình hiện quy đổi theo đúng bảng danh mục khai báo và lookup code đã rà theo các màn có service tương ứng; kết quả dữ liệu thực vẫn phụ thuộc mã trong DB cũ và danh mục/ID đang có ở DB mới.
- Mã tỉnh không ánh xạ duy nhất hoặc ID không tra được phải được xem là cần rà soát, không thể coi là khác biệt nghiệp vụ đã xác nhận.

## Tab đối chiếu `MA_DP` với `DM_TINH_THANH_PHO`

Tab này so trực tiếp `MA_DP.MA` với `DM_TINH_THANH_PHO.TTP_MA` sau khi cắt khoảng trắng hai đầu; giữ nguyên số 0 đầu mã. Không dùng `MAPPING_PROVINCE` trong chức năng này, vì bảng đó có thể nối mã địa bàn cấp quận/huyện như `10101` tới mã tỉnh `01`, không phải cùng một mã danh mục.

Preview chỉ liệt kê mã cũ không có mã giống hệt trong danh mục mới, mã giống nhau nhưng tên khác nhau (bỏ qua dấu, hoa/thường và dấu câu khi so tên), cùng mã mới trùng để rà soát. Chức năng chỉ đọc hai DB.
