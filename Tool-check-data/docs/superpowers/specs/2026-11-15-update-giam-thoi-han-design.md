# Thiết kế: Cập nhật và bổ sung giảm thời hạn

## Mục tiêu

Trong phần **Giảm thời hạn**, cung cấp hai luồng preview riêng: **Cập nhật** các bản ghi đã có ở DB mới và **Bổ sung** bản ghi có ở DB cũ nhưng thiếu ở DB mới. Dữ liệu chỉ được ghi sau preview, lựa chọn của người dùng và xác nhận.

## Phạm vi hai luồng

- **Cập nhật:** chỉ xử lý sáu trường hiện tại. Điền trường đích trống; với `MUC_GIAM_ID` và `DIA_PHUONG_ID`, điền hoặc sửa khi ID đích không khớp mã nguồn được ánh xạ duy nhất. Không sửa các trường khác.
- **Bổ sung:** tạo một dòng `GIAM_THOI_HANS` mới từ cùng bản ghi `PN_GIAM_THOI_HAN`, với toàn bộ trường có ánh xạ nguồn-đích được xác định trong bảng dưới đây, không chỉ sáu trường cập nhật.
- Dùng cùng mã trại DB mới, ghép phạm nhân bằng HSLĐ duy nhất và ghép lần giảm theo phạm nhân + `NGAY_XET`.
- Không tạo khi người, ngày xét hoặc khóa nguồn không xác định duy nhất. Dòng thiếu mapping bắt buộc sẽ bị loại khỏi danh sách có thể bổ sung và hiện lý do.

## Ánh xạ cho Bổ sung

| DB cũ `PN_GIAM_THOI_HAN` | DB mới `GIAM_THOI_HANS` | Cách đổi |
|---|---|---|
| `NGAY_XET` | `NGAY_XET` | Chuyển ngày sang timestamp, giữ nguyên ngày lịch |
| `MA_MUC_DN_GIAM_TG` | `MUC_DE_NGHI_ID` | Tra duy nhất mã `MTG_MA` trong `DM_MA_THOI_GIANS` còn hiệu lực, ghi `ID` |
| `MA_MUC_DN_GIAM_V26` | `CAP_TREN_DUYET_ID` | Mức BCA/cấp trên duyệt; tra duy nhất mã `MTG_MA` trong `DM_MA_THOI_GIANS` còn hiệu lực, ghi `ID` |
| `MA_MUC_TG_CHAP_HANH` | `DA_CHAP_HANH` | Tra duy nhất `MTG_MA`, ghi `MTG_TITLE` vì đích là trường văn bản |
| `MA_MUC_TG_CON_LAI` | `CON_LAI` | Tra duy nhất `MTG_MA`, ghi `MTG_TITLE` vì đích là trường văn bản |
| `NHAN_XET_TG` | `NHAN_XET` | Văn bản trực tiếp |
| `SO_QD_GIAM` | `SO_QUYET_DINH` | Văn bản trực tiếp |
| `NGAY_QD_GIAM` | `NGAY_QUYET_DINH` | Ngày sang timestamp |
| `MA_CQ_TOA_QD_GIAM` | `TOA_QUYET_DINH_ID` | Tra duy nhất mã cơ quan trong danh mục mới, ghi `ID` |
| `MA_DP_TOA_QD_GIAM` | `DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE.MA_TINH_NEW` → `DM_TINH_THANH_PHO.TTP_MA` duy nhất → ghi `ID` tỉnh |
| `MA_MUC_QD_GIAM_TOA_AN` | `MUC_GIAM_ID` | Tra duy nhất `MTG_MA` trong `DM_MA_THOI_GIANS`, ghi `ID` |
| `NGAY_THA_GIAM_HET_AN` | `NGAY_THA_GIAM_HET_AN` | Ngày sang timestamp |
| `KQCT_PHIEU_GIAM` | `KQCT_PHIEU` | Văn bản trực tiếp |
| `KQCT_DS_GIAM` | `KQCT_DANHSACH` | Văn bản trực tiếp |

Ba mức án là các dữ liệu riêng, không thay thế lẫn nhau: `MA_MUC_DN_GIAM_TG` → `MUC_DE_NGHI_ID` (mức trại đề nghị), `MA_MUC_DN_GIAM_V26` → `CAP_TREN_DUYET_ID` (mức BCA/cấp trên duyệt), và `MA_MUC_QD_GIAM_TOA_AN` → `MUC_GIAM_ID` (mức Tòa quyết định). Mapping `MA_MUC_DN_GIAM_V26` → `CAP_TREN_DUYET_ID` được xác nhận bởi view cũ hiển thị trường này thành `MUC_GIAM_TC8` và các view DB mới gọi `CAP_TREN_DUYET_ID` là mức BCA.

Các cột khác của DB mới không có nguồn cũ tương ứng sẽ không được tự điền. `ID` để identity tự sinh; `PHAM_NHAN_ID` lấy từ hồ sơ ghép; `CREATION_TIME` lấy thời điểm insert; `IS_DELETED=0`. `MUC_DE_NGHI_ID` là bắt buộc: nếu nguồn rỗng hoặc mã danh mục không ánh xạ đúng duy nhất thì không cho bổ sung dòng đó. `NHAN_XET_GIAM_V26` chưa có cột đích riêng; cần giữ nguyên quy tắc mapping `NHAN_XET_TG` → `NHAN_XET`, không gộp hai ghi chú khi chưa xác định quy tắc ưu tiên.

## Quy tắc kiểm tra mapping

- Chỉ chấp nhận một đích duy nhất cho mỗi mã nguồn sau khi loại danh mục đã xóa; không chọn tùy tiện khi trùng.
- Với `MUC_DE_NGHI_ID`, `CAP_TREN_DUYET_ID`, `MUC_GIAM_ID`, `TOA_QUYET_DINH_ID` và địa phương, kiểm tra mã nguồn có giá trị và ID đích tồn tại trước khi preview dòng bổ sung.
- Với thời gian chấp hành/còn lại, chỉ đổi mã thành `MTG_TITLE` qua mã danh mục duy nhất; không ghi mã hoặc ID vào cột văn bản.
- Preview thể hiện giá trị nguồn và giá trị đích dự kiến; báo rõ các dòng bị loại cùng nguyên nhân như thiếu mã, thiếu mapping, mapping trùng, HSLĐ thiếu/trùng, ngày xét thiếu/trùng.
- Không coi một dòng DB mới đã xóa mềm là dòng khớp đang hoạt động. Nếu có dòng active trùng khóa, không bổ sung lần nữa.

## Luồng ghi

- Hai tab có preview, checkbox và nút thao tác riêng. Tab **Cập nhật** có “Cập nhật dòng đã chọn”/“Cập nhật toàn bộ”; tab **Bổ sung** có “Bổ sung dòng đã chọn”/“Bổ sung toàn bộ”.
- DB cũ luôn chỉ đọc; DB mới chỉ mở ghi khi người dùng xác nhận.
- Trước khi ghi, tải lại dữ liệu và xác nhận tập thay đổi vẫn giống preview. Dùng transaction; lỗi bất kỳ thì rollback toàn bộ lượt ghi.
- Bản ghi mới phải được kiểm tra lại không có active row cùng `PHAM_NHAN_ID + NGAY_XET` trước insert để tránh tạo trùng do dữ liệu đổi sau preview.

## Phương án

1. **Hai tab riêng, mapping bổ sung tường minh:** cập nhật giữ phạm vi sáu trường; bổ sung tạo bản ghi mới từ các trường nguồn có mapping chuẩn, với quy tắc chuyển đổi riêng cho ba mức thời gian, tòa/cơ quan và tỉnh. Đây là hướng được chọn vì tách rõ sửa dòng hiện hữu và tạo dòng mới, đồng thời tránh dùng chung ánh xạ danh mục chưa đúng cho tỉnh.
2. Dùng một preview chung với thao tác cập nhật/bổ sung lẫn nhau: không chọn vì dễ nhầm phạm vi ghi.

## Ngoài phạm vi

Không xóa dữ liệu, không ghi đè sáu trường khác quy tắc cập nhật, không dùng CCCD/CMND ghép người, không tự chuyển các trường cũ không có mapping rõ ràng, không tính lại nghiệp vụ hoặc sinh dữ liệu cấp trên.

## Trạng thái

Người dùng yêu cầu triển khai trực tiếp; thiết kế này là cơ sở triển khai.
