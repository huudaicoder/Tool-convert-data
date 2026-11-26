# Thiết kế tool chuyển đổi địa danh từ DB cũ sang DB mới

Ngày: 2026-11-25  
Trạng thái: Đã triển khai; DB cũ là dữ liệu của một trại, chỉ nhập mã trại DB mới để giới hạn hồ sơ đích.

## Mục tiêu

Tạo một ứng dụng desktop Windows độc lập, kết nối đồng thời DB cũ và DB mới, để chuyển các giá trị mã địa phương tỉnh/thành phố, cơ quan/tòa và địa phương của cơ quan/tòa từ các bản ghi cũ sang các bản ghi tương ứng đã tồn tại trong DB mới. Tool chỉ cập nhật các cột đích thuộc whitelist sau khi người vận hành xem preview và chọn dòng cập nhật.

## Phương án đã chọn

1. **Tool riêng DB cũ → DB mới (được chọn):** có source, cấu hình, UI, build và tài liệu riêng; chỉ chứa phạm vi địa danh. Cách này đáp ứng yêu cầu độc lập và giữ riêng với tool gộp tỉnh trong DB mới, tool chuẩn hóa tòa hiện tại và Tool-check-data.
2. **Thêm chức năng vào tab Convert địa phương của Tool-check-data:** tái sử dụng engine ghép hồ sơ và sự kiện hiện có, nhưng không tạo tool mới độc lập như yêu cầu.

## Quy tắc tra danh mục

- Đọc mã ở DB cũ dưới dạng chuỗi, trim khoảng trắng nhưng giữ nguyên số 0 đầu mã.
- `MA_CQ` nguồn tra trong DB mới theo `DM_CO_QUANS.CQ_MA`; nếu có đúng một dòng chưa xóa mềm thì lấy `DM_CO_QUANS.ID`.
- `MA_DP` nguồn tra trong DB mới theo `DM_TINH_THANH_PHO.TTP_MA`; nếu có đúng một dòng chưa xóa mềm thì lấy `DM_TINH_THANH_PHO.ID`.
- Với xã/phường Lai lịch, `PN_LAI_LICH.DC_*_PHUONG_XA` là tên text. Dùng mã tỉnh `MA_DP_DC_*` tương ứng làm khóa `MA_QH`, tìm tên trong `MA_DP_XA_PHUONG.ND`, lấy `MA`, đối chiếu exact toàn danh mục với `DM_XA_PHUONG.XP_MA`, rồi lấy `DM_XA_PHUONG.ID`. Không lọc thêm theo tỉnh ở DB mới.
- “Chưa xóa mềm” nghĩa là `IS_DELETED=0` (hoặc cột không tồn tại). Không lọc theo `CQ_TRANG_THAI`/`TTP_TRANG_THAI`, vì trạng thái nghiệp vụ không đồng nghĩa với bản ghi không còn dùng được cho lịch sử.
- Không dùng CSV crosswalk cho tool này. Không tra theo tên gần đúng, không tự đoán mã thay thế.
- Mã nguồn rỗng được giữ nguyên. Mã đích không tìm thấy hoặc trùng mã được hiển thị thành lỗi/ngoại lệ trong preview và không được cập nhật.
- Riêng `MIEN_HINH_PHATS.MHP_TOA_QUYET_DINH` và `MHP_DIA_PHUONG_QD` lưu ID dưới dạng text; tool phải bind ID dạng chuỗi ở hai cột này, còn các cột FK số dùng kiểu NUMBER.

## Ghép bản ghi cũ và mới

- Ghép phạm nhân bằng HSLĐ duy nhất ở cả hai DB. HSLĐ thiếu hoặc trùng ở một trong hai DB không được ghép dự phòng bằng CCCD, họ tên hay thứ tự truy vấn.
- DB cũ được xác định là CSDL của một trại nên đọc toàn bộ hồ sơ nguồn, không hỏi/lọc theo `MA_TRAI_GIAM`. DB mới bắt buộc nhập `TG_MA`; chỉ hồ sơ có `LL_TRAI_GIAM_ID` trỏ tới đúng trại này được xét ghép và cập nhật.
- Với màn chỉ có một dòng trên mỗi phạm nhân: chỉ ghép khi mỗi bên có đúng một dòng.
- Với bảng sự kiện: dùng khóa sự kiện khai báo rõ theo từng màn. Chỉ ghép khi khóa đủ giá trị và duy nhất ở cả hai phía. Thiếu/trùng khóa được báo preview, không chọn dòng theo thứ tự DB.
- Chỉ ghi lên dòng đích đã có ở DB mới. Không INSERT, DELETE hoặc tạo bản ghi danh mục.

## Phạm vi bảng/cột

Phạm vi kế thừa danh sách mapping địa danh đã rà trong `Tool-check-data/mapping.py`; bản triển khai độc lập sẽ có whitelist riêng và không import runtime từ tool khác.

| Màn/bảng cũ → bảng mới | Mã cơ quan `MA_CQ` → ID cơ quan | Mã tỉnh `MA_DP` → ID tỉnh |
|---|---|---|
| Lai lịch `PN_LAI_LICH` → `PN_LAI_LICHS` | Không áp dụng | Tỉnh: `MA_DP_DC_TT/VAO/VE` → ba FK `*_PROVICE`; xã/phường: `DC_TT_PHUONG_XA` → `LL_DIA_CHI_THUONG_TRU_WARD`, `DC_VAO_PHUONG_XA` → `LL_NOI_OTRUOC_KHI_BAT_WARD`, `DC_VE_PHUONG_XA` → `LL_NOI_THA_VE_CU_TRU_WARD` |
| Thi hành án `PN_LAI_LICH` → `PN_THI_HANH_AN` | `MA_CQ_RL_BAT` → `THA_CO_QUAN_BAT_ID`; `MA_CQ_TOA_QD` → `THA_TOA_QD_ID`; `MA_CQ_DN_DC` → `THA_DON_VI_DE_NGHI_ID`; `MA_CQ_LAP_DB` → `THA_CO_QUAN_LAP_ID` | `MA_DP_RL_BAT` → `THA_DIA_PHUONG_CO_QUAN_BAT_ID`; `MA_DP_TOA_XU` → `THA_DIA_PHUONG_CAP_TOA_ID`; `MA_DP_TOA_QD` → `THA_DIA_PHUONG_TOA_QD_THA_ID`; `MA_DP_DN_DC` → `THA_DIA_PHUONG_DON_VI_DE_NGHI_ID`; `MA_DP_LAP_DB` → `THA_DIA_PHUONG_DON_CO_QUAN_LAP_ID` |
| Tiền án `PN_TIEN_AN` → `PN_TIEN_AN` | `MA_CQ_TOA_XU_TA` → `PNTA_TOA_XU_ID` | `MA_DP_TOA_XU_TA` → `PNTA_DIA_PHUONG_ID` (SQL hiển thị join `DM_TINH_THANH_PHO`) |
| Bản án khác `PN_BAN_AN` → `PN_BAN_AN_KHACS` | `MA_CQ_TOA_XU_BA` → `BAK_TOA_XU_ID` | `MA_DP_TOA_XU_BA` → `BAK_TOA_XU_DP_ID` |
| Giảm thời hạn `PN_GIAM_THOI_HAN` → `GIAM_THOI_HANS` | `MA_CQ_TOA_QD_GIAM` → `TOA_QUYET_DINH_ID` | `MA_DP_TOA_QD_GIAM` → `DIA_PHUONG_ID` |
| Chữa bệnh bắt buộc `PN_CHUA_BENH_BAT_BUOC` → `CHUA_BENH_BAT_BUOCS` | `MA_CQ_TOA_AN_QD` → `CO_QUAN_QUYET_DINH_ID` | `MA_DP_TOA_AN_QD` → `DIA_PHUONG_QUYET_DINH_ID` |
| Tăng/giảm hình phạt `PN_TANG_GIAM_HINH_PHAT` → `TANG_GIAM_HINH_PHATS` | `MA_CQ_TOA_QD` → `DON_VI_QUYET_DINH_ID` | `MA_DP_TOA_QD` → `DIA_PHUONG_QUYET_DINH_ID` |
| Trích xuất `PN_TX_TRICH_XUAT` → `TRICH_XUATS` | `MA_CQ_DN_TX` → `TX_DON_VI_DE_NGHI_ID`; `MA_CQ_TX_VE` → `TX_DON_VI_VE_ID` | `MA_DP_DN_TX` → `TX_DIA_PHUONG_DE_NGHI_ID`; `MA_DP_TX_VE` → `TX_DIA_PHUONG_VE_ID` |
| Tạm đình chỉ `PN_TDC_TAM_DINH_CHI` → `TAM_DINH_CHIS` | `MA_CQ_CUA_TOA` → `TOA_QUYET_DINH_ID` | `MA_DP_CUA_TOA` → `DIA_PHUONG_ID`; `MA_DP_NOI_VE` → `NOI_VE_DIA_PHUONG_ID` |
| Hoãn thi hành án `PN_HOAN_THI_HANH_AN` → `HOAN_THI_HANH_ANS` | `MA_CQ_TOA_QD_HOAN` → `TOA_QUYET_DINH_ID` | `MA_DP_TOA_QD_HOAN` → `DIA_PHUONG_ID` |
| Miễn hình phạt `PN_MIEN_HINH_PHAT` → `MIEN_HINH_PHATS` | `MA_CQ_TOA_QD_MIEN` → `MHP_TOA_QUYET_DINH` | `MA_DP_TOA_QD_MIEN` → `MHP_DIA_PHUONG_QD` (ID lưu dạng text) |
| Hủy án `PN_HUY_AN` → `HUY_ANS` | `MA_CQ_TOA_HUY` → `TOA_QUYET_DINH_ID` | `MA_DP_TOA_HUY` → `DIA_PHUONG_ID` |
| Tha có điều kiện `PN_THA_CO_DK` → `THA_CO_DIEU_KIENS` | `MA_CQ_TOA_QD_TT` → `TOA_QUYET_DINH_THA_ID`; `MA_CQ_TOA_QD_TL` → `TOA_QUYET_DINH_LAI_ID` | `MA_DP_TOA_QD_TT` → `DIA_PHUONG_QUYET_DINH_THA_ID`; `MA_DP_TOA_QD_TL` → `DIA_PHUONG_QUYET_DINH_LAI_ID` |
| Chuyển giao `PN_CHUYEN_GIAO` → `PN_CHUYEN_GIAO` | `MA_CQ_TOA_CG` → `PNCG_TOA_QDCG`; `MA_CQ_TOA_QDTH_CG` → `PNCG_TOA_QDTHQDCG` | `MA_DP_TOA_CG` → `PNCG_DIA_PHUONG_QDCGID`; `MA_DP_TOA_QDTH_CG` → `PNCG_DIA_PHUONG_THQDCGID` |
| Chuyển trại `PN_CHUYEN_TRAI` → `PHAM_NHAN_CHUYEN_TRAI` | `MA_CQ_DN_CHUYEN` → `PNCT_CO_QUAN_DE_NGHI_CHUYEN_ID` | `MA_DP_TRAI_DEN` → `PNCT_TRAI_DEN_DIA_PHUONG_ID`; `MA_DP_DN_CHUYEN` → `PNCT_CO_QUAN_DE_NGHI_DIA_PHUONG_ID` |
| Quyết định thi hành án khác `PN_QD_THI_HANH_AN` → `PN_QUYET_DINH_BAN_AN_KHACS` | `MA_CQ_TOA_QDTH_AN` → `QDBAK_TOA_QUYET_DINH_ID`; `MA_CQ_TOA_XU` → `QDBAK_TOA_XU_ID` | `MA_DP_TOA_QDTH_AN` → `QDBAK_TOA_QUYET_DINH_DP_ID`; `MA_DP_TOA_XU` → `QDBAK_TOA_XU_DP_ID` |
| Biên lai TNDS/HPBS `PN_HPBS_THUC_HIEN` → `PN_BIENLAIES` | `MA_CQ_THU_NOP` → `BL_NOP_TAI_CO_QUAN` | `MA_DP_THU_NOP` → `BL_DIA_PHUONG`; ghép qua HPBS cha bằng `BIEN_LAI_SO + NGAY_NOP + SO_TIEN_NOP` ↔ `BL_SO_BIEN_LAI + BL_NGAY_NOP + BL_SO_TIEN` |

## Màn hình và thao tác

- Kết nối/test riêng DB cũ và DB mới; thông tin mật khẩu chỉ giữ trong RAM.
- Chọn các màn/bảng cần preview bằng checkbox.
- Preview thể hiện HSLĐ, ID hồ sơ cũ/mới, bảng, cột nguồn/đích, mã nguồn, ID hiện tại, ID dự kiến, tên danh mục đích và trạng thái.
- Lọc READY, đã đúng, mã không tồn tại, mã trùng, không ghép được hồ sơ/sự kiện và lỗi schema/truy vấn.
- Cập nhật các dòng READY được chọn hoặc toàn bộ READY. Mỗi UPDATE dùng ID dòng đích và giá trị cũ trong điều kiện; một rowcount khác 1 làm rollback toàn transaction.
- Ghi audit CSV sau commit, gồm thời gian, schema, bảng/cột, ID đích, HSLĐ, mã/ID trước và sau; không ghi mật khẩu.

## An toàn dữ liệu

- DB cũ chỉ SELECT. DML chỉ thực hiện trên DB mới và chỉ ở whitelist cột đích.
- Không thay đổi `DM_CO_QUANS`, `DM_TINH_THANH_PHO`, `DM_XA_PHUONG`; không xóa/gộp mã trong danh mục.
- Không tự chuẩn hóa tên tòa, tên tỉnh hoặc tên huyện trong trường text.
- `PN_LAI_LICHS.LL_NOI_OKHAC_PROVICE` tạm ngoài phạm vi vì chưa xác định được cột mã nguồn.
- Tiền án `PNTA_DIA_PHUONG_ID` được đưa vào mapping tỉnh/thành theo xác nhận từ SQL hiển thị join `DM_TINH_THANH_PHO`.
- Biên lai được lọc theo hồ sơ qua HPBS cha ở cả hai DB. Chỉ ghép khi số biên lai, ngày nộp và số tiền đủ, duy nhất; khóa lặp sẽ báo không ghép duy nhất.
- `PN_KET_THUC_RA_TRAIS.KTRT_CONG_AN_TINH_THANH_PHO_ID` ngoài phạm vi theo quyết định trước đó.
- Ba trường xã/phường chỉ cập nhật khi tên + `MA_QH` khớp duy nhất trong danh mục cũ và mã `MA` khớp duy nhất `DM_XA_PHUONG.XP_MA`; trường hợp thiếu/trùng chỉ báo preview.
- Thông tin “huyện Quỳnh Phụ, tỉnh Thái Bình” không thể biểu diễn trong FK chỉ đến tỉnh/thành; nếu dữ liệu lịch sử cần giữ thì để ở trường text lịch sử/nghiệp vụ, tool không ghi đè text đó.

## Điều kiện triển khai còn cần xác nhận

- Lookup mã cơ quan và mã tỉnh là exact match sau trim, duy nhất trong danh mục active của DB mới; mã khác/mất/trùng sẽ không cập nhật.
- Dùng danh sách mapping/khóa sự kiện đã rà trong `Tool-check-data/mapping.py` làm căn cứ, nhưng chép cấu hình cần thiết vào project mới; không import runtime từ Tool-check-data.
- Snapshot schema chỉ để kiểm tra ban đầu; tool phải kiểm tra schema live ở cả hai DB trước preview/apply.

## Bố trí project dự kiến

`D:\tool_c10\Tool-convert-dia-danh-cu-moi\` chứa app Tkinter, engine Oracle thin, whitelist mapping, spec/hướng dẫn, file cấu hình không chứa mật khẩu, script build và EXE trong `dist`. Tool không chia sẻ source hoặc CSV với các tool hiện tại.
