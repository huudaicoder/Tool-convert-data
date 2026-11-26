# Thiết kế: Bổ sung dữ liệu lai lịch

## Mục tiêu

Tab **Cập nhật lai lịch** cho phép chọn từng trường cần bổ sung từ hồ sơ tương ứng trong DB cũ vào hồ sơ lai lịch DB mới. Các trường mới bổ sung trong phạm vi này là số tiền án và tái phạm.

## Phạm vi và ánh xạ

| DB cũ | DB mới |
|---|---|
| `PN_LAI_LICH.TOM_TAT_HV` | `PN_LAI_LICHS.LL_TOM_TAT_HV` |
| `PN_LAI_LICH.CHI_TIET_HV` | `PN_LAI_LICHS.LL_CHI_TIET_HV` |
| `PN_LAI_LICH.SO_TIEN_AN` | `PN_LAI_LICHS.LL_SO_TIEN_AN` |
| `PN_LAI_LICH.MA_TAI_PHAM` → tra `MA_TAI_PHAM.MA/ND` | `DM_TAI_PHAMS.TP_MA` → lấy `DM_TAI_PHAMS.ID` ghi vào `PN_LAI_LICHS.LL_TAI_PHAM` |

`SO_TIEN_AN` được đồng bộ theo DB cũ khi nguồn có dữ liệu. Với `MA_TAI_PHAM`, mã nguồn phải có đúng một tên trong danh mục DB cũ; mã đó phải khớp duy nhất với `TP_MA` trong danh mục DB mới, rồi lấy ID đích. Không suy đoán theo tên. Khi mã nguồn hợp lệ, ID tái phạm DB mới được cập nhật nếu đang trống hoặc khác ID dự kiến. Mã nguồn thiếu/trùng hoặc không có mã đích duy nhất sẽ được báo trong preview và không cập nhật.

## Luồng sử dụng

- Dùng thông tin kết nối hai DB và mã trại đã nhập trong ứng dụng.
- Nút **Lấy xem trước** đọc DB cũ ở chế độ chỉ đọc, ghép hồ sơ theo HSLĐ duy nhất và chỉ lấy hồ sơ DB mới thuộc trại được chọn.
- Lưới xem trước có một dòng cho mỗi hồ sơ, gồm HSLĐ, trạng thái ghép, ID lai lịch đích và cặp giá trị cũ/mới cho các trường được chọn. Các dòng đủ điều kiện cập nhật nằm trước; dòng không ghép được theo HSLĐ hiển thị trạng thái ngay cạnh HSLĐ để không nhầm là dòng cập nhật.
- Mỗi dòng có checkbox chọn hồ sơ. Người dùng có thể cập nhật các hồ sơ đã chọn hoặc cập nhật toàn bộ hồ sơ đủ điều kiện.
- Với `LL_SO_TIEN_AN` và `LL_TAI_PHAM`, DB cũ là nguồn chuẩn: nếu DB cũ có giá trị thì ghi sang DB mới khi đích trống hoặc khác; nếu DB cũ trống thì giữ nguyên DB mới. Những trường bổ sung khác chỉ điền khi đích NULL/rỗng. Không tạo hồ sơ mới và không cập nhật nếu HSLĐ thiếu/trùng hoặc ghép không duy nhất.
- Trước khi ghi, yêu cầu xác nhận và lập lại xem trước. Nếu dữ liệu thay đổi so với preview, không ghi. Ghi DB mới trong một transaction; lỗi thì rollback toàn bộ.
- Mỗi thao tác UPDATE khóa bằng ID hồ sơ lai lịch đích, HSLĐ/ID phạm nhân đã ghép và mã trại; chỉ cập nhật các cột còn NULL/rỗng.

## Phương án đã cân nhắc

1. Giữ DB mới khi đã có dữ liệu — không áp dụng cho số tiền án/tái phạm vì người dùng xác nhận DB cũ là nguồn chuẩn cho hai trường này.
2. Đồng bộ số tiền án và tái phạm theo DB cũ — được người dùng yêu cầu; DB cũ trống thì giữ DB mới.

## Ngoài phạm vi

Không sửa các trường khác, không xóa dữ liệu, không dùng CCCD/CMND để ghép, không tạo hồ sơ lai lịch đích. DB cũ luôn chỉ đọc.

## Trạng thái

Quy tắc hiện hành: số tiền án và tái phạm theo DB cũ; các trường còn lại theo quy tắc riêng trên giao diện. Luồng preview/cập nhật dùng mẫu của tab giảm thời hạn.
