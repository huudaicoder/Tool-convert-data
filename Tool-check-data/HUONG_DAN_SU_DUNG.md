# Hướng dẫn sử dụng tool kiểm soát chuyển đổi dữ liệu C10

## 1. Mở ứng dụng

Chạy file `dist\QLPNC10Checker.exe`. Máy cần truy cập được mạng tới cả hai máy chủ Oracle. Tool dùng kết nối Oracle Thin, không yêu cầu cài Oracle Client.

## 2. Nhập kết nối DB cũ và DB mới

Nhập riêng cho từng khung **DB CŨ** và **DB MỚI**:

- **DSN:** theo dạng `host:port/service_name`, ví dụ `10.20.30.40:1521/ORCLPDB1`.
- **User / Mật khẩu:** tài khoản Oracle có quyền đọc các bảng và danh mục cần đối soát.
- **Schema:** tùy chọn. Để trống nếu bảng nằm trong schema mặc định của user; nếu cần đọc schema khác thì nhập tên schema.

Bấm **Kiểm tra kết nối** trong từng khung. Chỉ chạy chức năng sau khi cả hai kết nối hoạt động. Tab **Đối soát** chỉ đọc; các tab cập nhật chỉ đọc DB cũ và chỉ ghi có điều kiện vào DB mới sau khi người dùng xác nhận. Tài khoản DB mới cần quyền cập nhật đúng bảng của chức năng.

Thông tin kết nối chỉ được giữ trong phiên chạy hiện tại; tool không lưu DSN, user, schema hoặc mật khẩu vào máy. Khi mở lại tool, nhập lại thông tin kết nối.

## 3. Chọn màn hình và lưới cần chạy

Trong vùng **Chọn màn / lưới cần đối soát**:

1. Chọn nhóm **Thông tin lai lịch**, **Thông tin diễn biến** hoặc **Thông tin kết thúc** ở dropdown **Cụm thông tin**.
2. Chọn màn hình hoặc lưới trong dropdown **Màn hình / bảng dữ liệu**.
3. Bấm **Chọn mapping này** để đưa vào lần chạy; bấm **Bỏ mapping này** nếu không muốn chạy mục đó.
4. Danh sách bên dưới cho biết mapping nào đã chọn. Bấm **Chọn lại tất cả** để khôi phục toàn bộ mapping có thể chạy; có thể bỏ từng mapping bằng nút **Bỏ mapping này**.

Một số màn có nhiều bảng dữ liệu nên mỗi bảng xuất hiện thành một mapping riêng. Mục chưa có mapping sẽ được ghi rõ trong kết quả và không được tính là đã đối soát. Tài liệu đính kèm đã được loại khỏi phạm vi.

## 4. Chọn nơi lưu báo cáo và chạy

1. Trong khung **File Excel xuất ra** ngay dưới phần kết nối, kiểm tra đường dẫn đang hiển thị hoặc bấm **Chọn nơi lưu...**.
2. Bấm **Chạy đối soát**. Thanh trạng thái hiển thị tiến độ; bấm **Hủy** nếu cần dừng.
3. Khi chạy xong, tool báo đường dẫn file Excel đã tạo.

Hồ sơ phạm nhân chỉ được ghép theo HSLĐ duy nhất. HSLĐ trống hoặc trùng được báo riêng; tool không dùng CCCD/CMND để ghép thay thế. Dữ liệu con của hồ sơ không ghép được sẽ không được so sánh.

## 5. Lọc và đọc kết quả trên giao diện

Trong vùng **Kết quả lần chạy**:

- Dropdown **Lọc cụm** giới hạn kết quả theo nhóm thông tin.
- Dropdown **Lọc màn / lưới** giới hạn theo một mapping cụ thể.
- Chọn một dòng trong bảng tổng hợp để xem các sai lệch chi tiết ở bảng bên dưới.
- Dùng thanh cuộn dọc bên phải mỗi bảng để xem thêm dòng; dùng thanh cuộn ngang bên dưới bảng nếu các cột không vừa cửa sổ.

Các trạng thái như **Chỉ có ở DB cũ (thiếu ở DB mới)**, **Chỉ có ở DB mới (thiếu ở DB cũ)**, **Lệch giá trị** và **Trùng khóa cần rà soát** cần được kiểm tra trong bảng chi tiết.

## 6. Đọc file Excel

File gồm bốn sheet:

- **Tổng quan:** tổng số hồ sơ ghép và sai lệch.
- **Đối soát số lượng:** kết quả theo từng màn/lưới.
- **Ghép phạm nhân:** đối chiếu HSLĐ giữa hai DB.
- **Chi tiết sai lệch:** từng bản ghi chỉ có ở một DB, giá trị trường khác nhau hoặc khóa trùng cần rà soát.

## 7. Cập nhật xếp loại quý IV/2026

1. Nhập kết nối DB cũ, DB mới và **Mã trại DB mới (TG_MA)** ở phía trên.
2. Mở tab **Cập nhật xếp loại**, bấm **Lấy xem trước**.
3. Rà soát HSLĐ, mã/kết quả quý IV trong DB cũ và danh mục dự kiến ở DB mới. Chỉ những bản ghi năm 2026 đang thiếu quý IV và ghép/mapping duy nhất mới có ô chọn.
4. Tick các dòng cần xử lý rồi bấm **Cập nhật dòng đã chọn**, hoặc bấm **Cập nhật toàn bộ** để xử lý mọi dòng hợp lệ trong xem trước; xác nhận hộp thoại.

Chức năng lấy `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_Q4` của năm 2026 ở DB cũ, ghép phạm nhân theo HSLĐ trong phạm vi trại, rồi tìm mã tương ứng trong `DM_XEP_LOAIES.XL_MA`. Tool chỉ điền ID danh mục vào `XEP_LOAIS.XEP_LOAI_QUY_IV` của bản ghi năm 2026 đang trống. Tool không tạo bản ghi xếp loại, không sửa quý khác và giữ nguyên quý IV đã có. Thiếu/trùng bản ghi hoặc mã danh mục không khớp duy nhất sẽ hiện trạng thái cần rà soát và không được cập nhật.

### Bổ sung trường trong tab Cập nhật lai lịch

1. Kết nối DB cũ, DB mới và nhập mã trại DB mới; mở tab **Cập nhật lai lịch**.
2. Chọn các trường cần xử lý. `Số tiền án` lấy `PN_LAI_LICH.SO_TIEN_AN` sang `PN_LAI_LICHS.LL_SO_TIEN_AN`.
3. `Tái phạm` lấy `PN_LAI_LICH.MA_TAI_PHAM`, tra mã và tên trong danh mục `MA_TAI_PHAM` của DB cũ, rồi dò mã chính xác ở `DM_TAI_PHAMS.TP_MA` của DB mới. Nếu có đúng một mã đích, tool ghi ID danh mục đó vào `PN_LAI_LICHS.LL_TAI_PHAM`.
4. Bấm **Lấy xem trước**, rà từng dòng và chọn cập nhật dòng hoặc toàn bộ dòng đủ điều kiện.

Với `Số tiền án` và `Tái phạm`, DB cũ là nguồn chuẩn: nếu DB cũ có dữ liệu thì tool điền vào DB mới khi đang trống hoặc ghi đè khi hai bên khác nhau; nếu DB cũ trống thì giữ nguyên giá trị DB mới. Preview hiện giá trị DB cũ và DB mới, trong đó giá trị mới thể hiện nội dung dự kiến sau cập nhật. Tái phạm chỉ cập nhật khi mã cũ tra được duy nhất và khớp đúng một mã `TP_MA`; mã thiếu/trùng/không khớp sẽ được báo rà soát và không tự ánh xạ theo tên. Các trường còn lại vẫn giữ quy tắc bổ sung khi DB mới đang trống (trừ trường có quy tắc riêng trên giao diện).

## Lưu ý về các mapping chưa hoàn tất

- TNDS và HPBS hiện chưa được tách đối soát theo quy tắc legacy đã xác nhận; xem trạng thái của mapping trên báo cáo.
- Biên lai chưa tự đối soát do chưa chốt mapping danh mục khoản cha và ý nghĩa trường ngày cũ/mới.
- Với tab **Đối soát**, nên chạy bằng tài khoản được cấp quyền SELECT tối thiểu cần thiết. Các tab cập nhật cần quyền SELECT ở cả hai DB và quyền UPDATE bảng đích tương ứng trong DB mới.

## 8. Convert địa phương

File mapping là `province_fk_merge.csv`, nằm cùng `app.py` khi chạy source hoặc cùng `QLPNC10Checker.exe` khi chạy bản build. Header CSV: `TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU`. Chỉ các dòng có `TRANG_THAI=APPROVED` mới được dùng; để trống/khác trạng thái này thì chỉ hiện cảnh báo. Hãy nhập mã dưới dạng text để giữ nguyên số 0 đầu mã. Danh mục tỉnh trong `Danh_muc_34_tinh_thanh.md` chưa tự được nạp vào CSV; chỉ điền các cặp đã được bạn xác nhận.

### 8.1 Gộp FK tỉnh trong DB hiện tại bằng tool riêng

Không chạy chức năng này trong tab Convert địa phương. Mở `D:\tool_c10\Tool-gop-ma-tinh\dist\GopMaTinhThanh.exe` (hoặc chạy source trong `D:\tool_c10\Tool-gop-ma-tinh`); tool chỉ cần kết nối DB hiện tại. Hướng dẫn, whitelist bảng/cột và cách build: [`../Tool-gop-ma-tinh/HUONG_DAN_GOP_MA_TINH_THANH.md`](../Tool-gop-ma-tinh/HUONG_DAN_GOP_MA_TINH_THANH.md).

### 8.2 Chuyển địa phương từ DB cũ sang DB mới

1. Trong tab **Convert địa phương**, tick các màn cần chạy rồi bấm **Lấy preview**.
2. Với mã nguồn có trong CSV, tool lấy `TTP_MA_GIU`; với mã không có dòng CSV, tool thử mã y nguyên. Mã đích phải khớp đúng một row `DM_TINH_THANH_PHO.TTP_MA`; ID của row đó là giá trị FK đích. Mapping có trạng thái chưa duyệt, thiếu mã, trùng mã hoặc mã đích không tìm thấy đều không được ghi.
3. Rà màn/bảng, hồ sơ, khóa sự kiện, mã nguồn, mã TTP đích, ID hiện tại và ID dự kiến. Mã tỉnh/ID chưa xác định duy nhất hoặc khóa sự kiện thiếu/trùng chỉ xuất hiện để rà soát.
4. Chọn từng dòng READY hoặc cập nhật tất cả dòng READY. Tool đọc DB cũ, chỉ ghi DB mới; trước mỗi update so sánh giá trị hiện tại với giá trị đã preview, sai khác sẽ rollback toàn transaction.
5. Lấy preview lại sau cập nhật. Nhật ký được nối vào `Documents\QLPNC10_convert_dia_danh_audit.csv`.

Chế độ này chỉ xử lý các cột địa phương được khai báo trong `mapping.py`; không đổi tên tòa/cơ quan, text địa chỉ hoặc dữ liệu huyện trong nội dung tự do. Các trường province được hỗ trợ cả ID NUMBER và trường text chứa ID như `MHP_DIA_PHUONG_QD` (chỉ khi schema live xác nhận là kiểu VARCHAR/NVARCHAR). Các bảng có nhiều dòng trên một phạm nhân chỉ cập nhật khi ghép được bằng khóa sự kiện duy nhất. DB cũ cần quyền SELECT; DB mới cần SELECT và UPDATE đúng các bảng đích.
