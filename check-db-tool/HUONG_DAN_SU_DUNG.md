# Hướng dẫn sử dụng tool kiểm soát chuyển đổi dữ liệu C10


## 1. Mở ứng dụng

Chạy file `dist\QLPNC10Checker.exe`. Máy cần truy cập được mạng tới cả hai máy chủ Oracle. Tool dùng kết nối Oracle Thin, không yêu cầu cài Oracle Client.

## 2. Nhập kết nối DB cũ và DB mới

Nhập riêng cho từng khung **DB CŨ** và **DB MỚI**:

- **DSN:** theo dạng `host:port/service_name`, ví dụ `10.20.30.40:1521/ORCLPDB1`.
- **User / Mật khẩu:** tài khoản Oracle có quyền đọc các bảng và danh mục cần đối soát.
- **Schema:** tùy chọn. Để trống nếu bảng nằm trong schema mặc định của user; nếu cần đọc schema khác thì nhập tên schema.

Bấm **Kiểm tra kết nối** trong từng khung. Chỉ chạy đối soát sau khi cả hai kết nối hoạt động. Tool đặt giao dịch ở chế độ chỉ đọc và không cập nhật dữ liệu trong hai DB.

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

## Lưu ý về các mapping chưa hoàn tất

- TNDS và HPBS hiện chưa được tách đối soát theo quy tắc legacy đã xác nhận; xem trạng thái của mapping trên báo cáo.
- Biên lai chưa tự đối soát do chưa chốt mapping danh mục khoản cha và ý nghĩa trường ngày cũ/mới.
- Tool chỉ đọc dữ liệu; nên chạy bằng tài khoản được cấp quyền SELECT tối thiểu cần thiết.

