# Thiết kế: Tool desktop kiểm soát chuyển đổi dữ liệu C10

Ngày: 2026-11-13  
Trạng thái: Bản đề xuất để người dùng duyệt; chưa triển khai.

## Mục đích

Làm một ứng dụng desktop Windows cho cán bộ/người phụ trách kiểm soát chuyển đổi dữ liệu phạm nhân C10. Người dùng nhập thông tin kết nối CSDL cũ và mới, kiểm tra kết nối, chạy các đối soát có thể tự động, xem kết quả trên giao diện, cập nhật checklist nghiệp vụ và tải báo cáo. Workbook `Checklist kiểm soát chuyển đổi dữ liệu C10.xlsx` là bộ yêu cầu và tiêu chí nghiệm thu gốc.

## Bối cảnh đã xác nhận

- Người dùng chọn tool desktop thay cho web và muốn nhập thông tin kết nối hai CSDL.
- `db-compare` là tài liệu tham khảo cho cách nhập DSN, user, mật khẩu, schema; kiểm tra kết nối; chạy việc nặng nền; ghi nhật ký; và xuất Excel.
- `db-compare` dùng Oracle `python-oracledb` thin mode, không cần Oracle Client. Mapping của nó có vẻ cùng mô hình DB đích với code C10 trong `bxd.c10-qlpn` (ví dụ `PN_LAI_LICHS`), nên là cơ sở tham khảo trực tiếp cần kiểm tra/đối chiếu lại, không được loại bỏ mặc định.
- UI C10 trong `bxd.c10-qlpn/angular` có ba top tab: `Thông tin lai lịch`, `Thông tin diễn biến`, `Thông tin kết thúc`. Các menu con hiện khai báo lần lượt 12, 19 và 7 mục.
- `db-compare/mapping.py` hiện có 37 cấu hình so sánh (12 Lý lịch, 18 Diễn biến, 7 Kết thúc); README nói 33 màn nên đã cũ. So với menu C10 hiện tại, mapping còn thiếu mục `Tài liệu đính kèm` của Diễn biến.
- Workbook có sheet đối soát 38 dòng với các tên kiểu `HS_DOI_TUONG`; tên và cách chia nhóm này khác schema/menu thực tế trong code C10. Theo yêu cầu người dùng, danh sách đó là ví dụ/tham khảo, không phải nguồn chân lý để định nghĩa menu hay giới hạn phạm vi chức năng.

## Mục tiêu

1. Theo dõi đủ 51 mục checklist và hiển thị tiến độ tổng thể, theo giai đoạn và theo nhóm Lý lịch/Diễn biến/Kết thúc.
2. Kiểm tra kết nối tới hai CSDL độc lập, chạy truy vấn chỉ đọc và báo lỗi kết nối/truy vấn dễ hiểu.
3. Đối soát các màn con theo đúng ba cụm menu C10; hiển thị số liệu, chênh lệch, trạng thái và chi tiết theo từng màn. Workbook là nguồn tiêu chí kiểm soát, không cố định số màn/bảng của hệ thống.
4. Thực hiện các kiểm tra dữ liệu tự động được khi đã có mapping, schema, khóa đối chiếu và quy tắc nghiệp vụ.
5. Quản lý các phần cần quyết định hoặc bằng chứng thủ công: nhóm dữ liệu cũ chưa có chỗ, rủi ro đặc tả, checklist, người xử lý, ngày, ghi chú và quyết định.
6. Hiển thị số liệu, lỗi và danh sách bản ghi/giá trị cần xem xét trên giao diện; tải báo cáo Excel để lưu, chia sẻ và nghiệm thu.
7. Không ghi hay sửa dữ liệu trên hai CSDL nguồn. Mật khẩu không được lưu vào cấu hình dự án hay báo cáo.

## Ngoài phạm vi

- Tool không tự chuyển/nạp dữ liệu, không sửa schema, không chạy DDL/DML, không tự quyết định cách xử lý dữ liệu thiếu.
- Tool không thể thay cán bộ nghiệp vụ ký xác nhận, duyệt rủi ro, khôi phục backup, kiểm tra màn hình phần mềm mới hay nghiệm thu.
- Không kết luận “chuyển hết” chỉ từ tổng số hàng nếu mapping hoặc quy tắc kiểm tra chưa được xác nhận.
- Không coi danh sách bảng mẫu trong workbook là danh sách menu/mapping hoàn chỉnh.

## Approaches

1. **Tool C10 mới, project riêng (đã chọn theo yêu cầu mới nhất):** tạo ứng dụng Windows độc lập, tham khảo UX và cách kết nối/SELECT/xuất của `db-compare`, nhưng không sửa hoặc phụ thuộc vào repo đó. Có mapping, checklist, project store và báo cáo riêng.
2. **Fork hoặc mở rộng trực tiếp `db-compare`:** tái dùng nhiều code nhanh hơn, nhưng thay đổi tool hiện có và ghép phạm vi checklist vào cùng sản phẩm; không phù hợp với yêu cầu giữ db-compare nguyên trạng.

Phương án đã chọn là tool mới độc lập trong `D:\QPLN\check-db-tool`; dự kiến Python desktop/Oracle thin mode sau khi xác nhận môi trường. Spec và kế hoạch chi tiết ở `2026-11-13-c10-desktop-tool-spec.md` và `2026-11-13-c10-desktop-tool-plan.md`.

## Người dùng và luồng chính

Người dùng vận hành trên một máy Windows có quyền mạng tới cả hai CSDL. Luồng:

1. Mở project kiểm soát C10.
2. Nhập kết nối DB cũ và DB mới: DSN `host:port/service`, user, mật khẩu, schema tùy chọn.
3. Bấm kiểm tra kết nối từng DB; hiển thị thành công/thất bại, không đưa mật khẩu vào log.
4. Chạy kiểm tra cấu trúc/mapping trước. Nếu thiếu bảng/cột hoặc cấu hình chưa xác nhận, báo rõ và không giả kết quả là đạt.
5. Chọn chạy toàn bộ hoặc nhóm kiểm tra/bảng. Hiển thị tiến độ, bước hiện tại, thời gian, lỗi và khả năng hủy an toàn giữa các truy vấn.
6. Xem dashboard, bảng kết quả, danh sách chênh lệch; lọc theo nhóm, bảng, giai đoạn, mức độ, trạng thái.
7. Cập nhật checklist thủ công và bổ sung ghi chú/quyết định/bằng chứng.
8. Tải báo cáo Excel tổng hợp hoặc báo cáo chi tiết. Có thời điểm chạy, cấu hình schema (không có mật khẩu), trạng thái mỗi kiểm tra và nguồn dữ liệu của kết luận.

## Nội dung giao diện

- **Kết nối:** hai khối DB cũ/mới, DSN, user, mật khẩu dạng che, schema, kiểm tra kết nối; không tự lưu mật khẩu. Có thể lưu DSN/user/schema nếu người dùng chọn, nhưng mật khẩu chỉ tồn tại trong phiên.
- **Tổng quan:** các chỉ tiêu trong sheet `Tổng quan`, nhãn đạt/chưa đạt/cần xử lý; tổng quan theo Lý lịch, Diễn biến, Kết thúc; lần chạy và thời điểm dữ liệu.
- **Đối soát theo cụm màn:** menu con lấy theo code C10, không lấy số dòng bảng ví dụ trong workbook làm số màn. Từng màn có tìm/lọc, mở chi tiết, danh sách lỗi/chênh lệch, trạng thái truy vấn, người kiểm tra/ngày/ghi chú. Có thể xuất thêm báo cáo kiểu sheet `Đối soát số lượng` để giữ tương thích workbook.
- **Checklist 51 mục:** nhóm theo 8 giai đoạn, nội dung, tiêu chí đạt, mức độ, trạng thái, người phụ trách, ngày kiểm tra, kết quả/ghi chú. Trạng thái bám dropdown trong workbook: Chưa kiểm tra, Đang kiểm tra, Đạt, Không đạt, Không áp dụng.
- **Dữ liệu cũ chưa có chỗ (16 dòng hiện tại):** trạng thái, nguồn, số lượng, lý do, phương án, người quyết định, ghi chú; cho phép thêm nhóm tìm thấy khi kiểm kê.
- **Rủi ro đặc tả (13 dòng hiện tại):** mức độ, trạng thái, bằng chứng, nguy cơ, đề xuất, quyết định/người duyệt.
- **Báo cáo:** tải Excel gói toàn bộ dữ liệu và các sheet tương ứng; tùy chọn tải riêng tổng quan, đối soát, checklist, dữ liệu chưa có chỗ, rủi ro và chi tiết chênh lệch. Giữ cấu trúc/cách gọi gần workbook gốc để người dùng đối chiếu được.

## Phạm vi cụm màn theo code C10

Nguồn nhận diện menu là `menuItems` trong ba component chi tiết Angular và các child route tương ứng. `db-compare/mapping.py` giúp kiểm tra mapping dữ liệu nhưng không được dùng làm danh sách menu chuẩn nếu thiếu mục so với code.

| Cụm trên giao diện | Màn con hiện có trong code C10 |
|---|---|
| Thông tin lai lịch (12) | Lai lịch phạm nhân; Thi hành án; Thông tin tiền án; Thông tin tiền sự; Hành vi phạm tội; Trách nhiệm dân sự, HPBS; Bản án khác; Người thân thích; Con theo mẹ vào trại; Nhận dạng; Ma túy; Phân đội. |
| Thông tin diễn biến (19) | Xếp loại; Giảm thời hạn; Phân loại; Chữa bệnh bắt buộc; Thông tin sức khỏe; Phạm tội mới; Ân giảm; Tăng giảm hình phạt; Khen thưởng; Kỷ luật; Giam riêng; Trốn trại; Trích xuất; Tạm đình chỉ; Hoãn thi hành án; Miễn hình phạt; Hủy án; Tiền công lao động sản xuất; Tài liệu đính kèm. |
| Thông tin kết thúc (7) | Nộp lưu; Ra trại; Chết; Chuyển trại; Tha có điều kiện; Đặc xá; Chuyển giao. |

`db-compare` cấu hình hiện 37 màn: khớp 12 màn Lý lịch và 7 màn Kết thúc; nhóm Diễn biến có 18 cấu hình. Tài liệu đính kèm được loại khỏi phạm vi theo yêu cầu người dùng. Các mapping vẫn cần kiểm tra tên bảng/cột trên đúng schema C10 trước khi kết luận.

## Bao phủ checklist

Mọi mục đều được quản lý trong tool. Mức tự động hóa dự kiến như sau; “tự động có điều kiện” chỉ được bật khi có schema, mapping, đường dẫn file hoặc quy tắc nghiệp vụ đã xác nhận.

| Giai đoạn / mục | Phạm vi tool |
|---|---|
| 1. Kiểm kê dữ liệu cũ (1–7) | Có thể lấy danh sách bảng/cột và đếm bản ghi/cột có dữ liệu từ metadata và truy vấn. Mapping trường cũ→mới, phương án dữ liệu thiếu, kiểm kê file, số liệu nền và biên bản cut-off cần cấu hình/bằng chứng; thống kê theo đơn vị/tình trạng cần định nghĩa nguồn và điều kiện lọc. |
| 2. Chuẩn bị (8–10) | Theo dõi cut-off, sao lưu/khôi phục và quyết định rủi ro như checklist có bằng chứng/ghi chú; không tự dừng ghi hoặc backup/restore DB. |
| 3. Danh mục (11–15) | Đếm/so mã–tên và phát hiện mã chưa map khi có cặp danh mục/mapping; giữ danh mục ngừng sử dụng, ĐVHC, danh mục thiếu và quyết định ánh xạ cần người xác nhận. |
| 4. Lý lịch (16–24) | Kiểm tra theo các màn Lý lịch thực tế (ví dụ lai lịch, thi hành án, tiền án/tiền sự, thân nhân, nhận dạng). Các phép kiểm tra số lượng, quan hệ, độ dài/ký tự, trường định danh, tội danh, ảnh cần mapping/khóa đã xác nhận. Tên `HS_DOI_TUONG` trong workbook chỉ là ví dụ, cần ánh xạ sang schema thực tế. |
| 5. Diễn biến (25–33) | Kiểm tra theo các màn Diễn biến thực tế; tự so số phạm nhân có dữ liệu, phát hiện khóa ngoại mồ côi, số/thứ tự sự kiện, định dạng thời gian, tổng tiền, liên kết quyết định và các đối soát nhóm khi đã cấu hình quan hệ/đơn vị tính. Kiểm tra ngoài khoảng thời gian cần ngoại lệ có giải trình. |
| 6. Kết thúc (34–42) | Kiểm tra theo các màn Kết thúc thực tế; tự đối chiếu tình trạng/sự kiện cuối, liên kết đợt tha và các bảng kết thúc, số lượng hồ sơ nộp lưu, file và nhật ký khi có mapping; kiểm tra snapshot và trường người/ngày tạo sửa cần xác nhận nguồn chuẩn khi dữ liệu có thể hợp lệ theo nhiều cách. |
| 7. Đối soát hoàn tất (43–47) | Tự đối chiếu tổng từng bảng, từng trường, log lỗi nạp và báo cáo thống kê khi các nguồn, mapping, log và quy tắc cùng thời điểm được cung cấp. Kiểm tra tối thiểu 50 hồ sơ trên giao diện cũ/mới vẫn cần người thao tác và ghi nhận kết quả. |
| 8. Nghiệm thu (48–52) | Lưu từng lần chạy thử, bổ sung sau cut-off, bằng chứng rollback, biên bản nghiệm thu và xác nhận chế độ chỉ đọc thành các mục checklist; tool không tự phê duyệt hoặc thay đổi quyền DB. |

## Quy tắc kết luận và trạng thái

- Bảng/chỉ tiêu chỉ được đánh dấu **Đạt/Khớp** khi truy vấn thành công, mapping hợp lệ và điều kiện đạt của workbook thỏa mãn.
- Không có mapping, thiếu quyền, truy vấn lỗi, dữ liệu chưa cung cấp hoặc điều kiện chưa xác nhận phải hiện **Chưa thể kết luận** riêng với **Không đạt**; không tính vào số mục đạt.
- Kết quả lưu kèm loại kiểm tra, thời điểm, bảng/cột, điều kiện, số đếm và thông tin lỗi đã làm sạch bí mật. Bản ghi lệch được phân trang để tránh tải cả CSDL vào RAM.
- Khi chạy lại, kết quả của lần mới không xóa báo cáo cũ. Checklist thủ công và lịch sử chạy được quản lý riêng; việc cập nhật checklist lưu người/ngày/ghi chú.
- Dashboard giữ các KPI kiểm soát tương ứng workbook: mọi màn/mapping trong phạm vi đã chọn được đối soát, không có chênh lệch chưa xử lý, tổng bản ghi thiếu 0, nhóm dữ liệu chưa có phương án 0, rủi ro mức Cao chưa xử lý 0, checklist Đạt 51/51, checklist Không đạt 0. Số màn lấy từ menu/mapping đã duyệt, không cố định theo 38 dòng ví dụ trong sheet. KPI chỉ báo đạt khi dữ liệu kiểm tra đã đầy đủ; trạng thái chưa chạy không được coi là 0 lỗi.

## An toàn và xử lý dữ liệu

- Chỉ dùng kết nối và truy vấn SELECT. Tool kiểm tra quyền tối thiểu; không yêu cầu quyền ghi. Trường hợp cần metadata, chỉ đọc catalog.
- Dùng tham số cho giá trị; tên bảng/cột phải lấy từ whitelist mapping đã khai báo/kiểm tra, không ghép trực tiếp đầu vào tùy ý thành SQL.
- Mật khẩu chỉ giữ trong bộ nhớ trong phiên, không ghi log, file cấu hình hay Excel; không hiển thị lại sau khi đóng phiên.
- Không lưu trữ bản sao toàn bộ dữ liệu phạm nhân. Kết quả chi tiết chỉ lấy các cột cần đối soát và định danh tối thiểu cần cho điều tra chênh lệch; hạn chế hoặc che dữ liệu định danh trong báo cáo theo chính sách người dùng.
- Dữ liệu checklist, lần chạy, ghi chú và cấu hình không bí mật lưu cục bộ để tiếp tục công việc; vị trí/định dạng lưu để người xây đề xuất. Người dùng có thể xuất và xóa project.
- Có timeout, đóng cursor/kết nối khi kết thúc/lỗi, log không chứa password/connection string đầy đủ. Không chạy song song nhiều truy vấn nặng mặc định.

## Báo cáo tải xuống

Workbook kết quả tối thiểu gồm: `Tổng quan`, `Checklist`, `Đối soát số lượng`, `Dữ liệu cũ chưa có chỗ`, `Rủi ro từ đặc tả`, `Chi tiết lỗi`, `Lịch sử chạy`. Có thể thêm sheet `Kiểm kê schema` và `Đối soát trường` vì các kiểm tra này cần được lưu lại. Giữ số liệu đầu vào, số liệu đích, chênh lệch và tiêu chí/kết luận; không sửa file checklist gốc.

## Dữ liệu/cấu hình phải có để kết luận đầy đủ

1. Xác nhận DDL/schema của hai DB C10 với `schema_old.json`, `schema_new.json` và mapping trong `db-compare`.
2. Rà soát/bổ sung mapping theo từng màn con; xác nhận khóa ghép hồ sơ/sự kiện, quan hệ, cột bị bỏ qua và các màn chỉ kiểm tra file/chứng từ.
3. Danh mục mapping mã cũ→ID/mã mới; quy tắc chuẩn hóa NULL, chuỗi, ngày, số và dữ liệu bị loại (mục tiêu workbook hiện nêu không loại bản ghi).
4. Cấu hình đường dẫn gốc/kho file đính kèm và quyền truy cập nếu muốn tự kiểm tra tồn tại/mở file.
5. Định nghĩa nhóm, trạng thái, thời điểm cut-off và các công thức/đơn vị thống kê nghiệp vụ.
6. Cách lưu project/lịch sử và phạm vi người dùng (một máy hay nhiều máy) nếu cần dùng chung trạng thái.

## Tiêu chí nghiệm thu thiết kế

- Đủ 51 mục checklist, 16 nhóm dữ liệu chưa có phương án, 13 rủi ro và các dropdown gốc; đủ các cụm/màn con theo code C10 (12/19/7) và thể hiện rõ các mapping chưa xác nhận.
- Người dùng kiểm tra riêng hai kết nối, chạy kiểm tra cấu hình, chạy một phần/toàn bộ, xem chi tiết và tải Excel.
- Mục không chạy được hoặc chưa đủ cấu hình hiển thị rõ lý do và không bị tính nhầm là đạt.
- Không có thao tác ghi trên hai CSDL; mật khẩu không xuất hiện trong file/log/lịch sử.
- Các mục cần phê duyệt, bằng chứng hoặc kiểm tra giao diện có trạng thái và trường nhập liệu để theo dõi đến nghiệm thu.

## Quyết định còn chờ người dùng

- Xác nhận hai DB đúng môi trường đều là Oracle và phiên bản/kiểu DSN tương thích với `python-oracledb`.
- Xác nhận schema Oracle nguồn/đích và duyệt mapping đã chuyển sang project mới. `db-compare` chỉ là tài liệu tham khảo, không được sửa.
- Tool dùng một máy hay cần sao chép/chia sẻ project giữa nhiều máy; thiết kế hiện đề xuất chạy cục bộ trên một máy và lưu project cục bộ.
- Có cần tự kiểm tra file đính kèm từ share/ổ mạng không; nếu có, cung cấp đường dẫn và quyền truy cập.
- Quy tắc ghép hồ sơ đã chốt theo HSLĐ duy nhất; không dùng CCCD/CMND để ghép. Xác nhận có cần che HSLĐ/tên trên file báo cáo tải xuống không.

## Rà soát mapping bảng theo từng lưới giao diện

Chi tiết bảng cũ/mới, khóa đề xuất, các lưới nhiều bảng và điểm cần xác nhận đã được lập tại [2026-11-13-c10-screen-mapping-review.md](2026-11-13-c10-screen-mapping-review.md). Kết quả này dựa trên DDL và code giao diện; mapping chưa xác nhận nghiệp vụ không được coi là kết luận đạt.
## Quy tắc ghép hồ sơ phạm nhân đã chốt

- Chỉ ghép hồ sơ cũ và mới theo số HSLĐ, với điều kiện HSLĐ có giá trị và duy nhất ở mỗi DB.
- Không dùng CCCD, CMND, họ tên hoặc khóa khác làm phương án ghép dự phòng. CCCD ở DB cũ có thể NULL nên không đáng tin làm định danh; không dùng CCCD để quyết định ghép.
- HSLĐ thiếu hoặc trùng ở một trong hai DB được báo thành lỗi riêng. Không ghép hồ sơ đó và không đối chiếu bảng con của hồ sơ chưa ghép; vẫn tính/hiển thị nó trong thống kê hai chiều của bảng lai lịch.
- Hiện compare.py còn logic fallback CCCD/CMND; cần bỏ logic đó khi triển khai theo thiết kế này.

## Đặc tả và kế hoạch tool desktop độc lập

Theo yêu cầu tạo tool mới và giữ nguyên `db-compare`, spec cùng kế hoạch được tách thành [đặc tả tool desktop](2026-11-13-c10-desktop-tool-spec.md) và [kế hoạch triển khai](2026-11-13-c10-desktop-tool-plan.md). Workbook đầu ra được mô tả trong mục 5 của spec.

Theo yêu cầu mới nhất, workbook kết quả chỉ có 4 sheet: `Tổng quan`, `Đối soát số lượng`, `Ghép phạm nhân`, `Chi tiết sai lệch`. Không xuất `Checklist`, `Rủi ro từ đặc tả`, `Lịch sử chạy`, `Mapping trường`, `Kiểm kê schema`, `Dữ liệu cũ chưa có chỗ`. Chi tiết xem mục 5 trong spec desktop.
