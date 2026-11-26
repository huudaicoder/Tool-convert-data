# Rà soát mapping màn hình C10: DB cũ và DB mới

Ngày: 2026-11-13  
Trạng thái: Kết quả khảo sát DDL và code giao diện; các quy tắc nghiệp vụ đánh dấu cần xác nhận chưa được coi là mapping đã duyệt.

## Kết luận chính

Đã đối chiếu check-db/DB/DLL_SUOI_HAI_old.sql (schema cũ QLPN_SUOI_HAI) với check-db/DB/DLL_QLPN_NEW.sql (schema mới QLPN) và xem các component Angular của bxd.c10-qlpn. Parser DDL xác nhận 256 bảng cũ, 361 bảng mới; 37 cấu hình hiện có trong db-compare/mapping.py tìm thấy đủ bảng/cột đã khai báo ở cả hai DDL. Đây chỉ là xác thực cấu trúc tĩnh; chưa chạy truy vấn trên dữ liệu thật.

Menu thực tế có 38 màn (12 lai lịch, 19 diễn biến, 7 kết thúc). db-compare có 37 cấu hình, nhưng một cấu hình TNDS hiện chỉ đếm; thiếu hẳn các lưới phụ: Phân buồng, Quyết định thi hành án khác, Tiền chi lao động; và chưa có màn Tài liệu đính kèm. Để đạt đủ màn hình, phải xem mỗi lưới là một dataset đối soát riêng, không gộp tất cả thành một bảng theo tên màn.

## Quy tắc nối dùng chung

1. Tạo crosswalk phạm nhân cũ → mới từ PN_LAI_LICH.PN_ID sang PN_LAI_LICHS.ID **chỉ theo HSLĐ**. HSLĐ phải có giá trị và duy nhất ở cả hai DB. HSLĐ NULL/rỗng hoặc trùng ở một trong hai DB là lỗi khóa; không thử CCCD, CMND, họ tên hay trường khác để ghép dự phòng. Kiểm tra tính duy nhất và quan hệ một-một trước khi ghép dữ liệu con.
2. Với mỗi bảng con, nối bản ghi cũ và mới qua crosswalk người trước: old PN_ID → old person → new person ID → FK người trên bảng mới. Không so trực tiếp PN_ID với FK số của DB mới.
3. Các FK danh mục mới là ID: tra ID về mã danh mục trong chính DB mới rồi mới so mã với DB cũ. Phải kiểm tra danh mục cũ/mới có cùng ngữ nghĩa; mã không tương đương cần bảng quy đổi đã duyệt.
4. Khớp bản ghi bằng khóa nghiệp vụ nhiều cột trong phạm vi một phạm nhân. Khóa trùng thì so theo multiset/giữ số lần xuất hiện và báo trùng khóa; không ghép tùy theo thứ tự trả về. Dữ liệu có thể sửa danh mục phải ghi cả lỗi không map được danh mục.
5. Với quan hệ cha-con, ghép cha trước rồi mới ghép con qua ID cha. Báo riêng số lượng, bản ghi thiếu/thừa, trường lệch và truy vấn lỗi. DB mới có IS_DELETED: kiểm tra chính sách loại bản ghi xóa mềm trước khi so; không tự mặc định các bảng cũ cũng có cùng semantics.

## Bốn màn nhiều bảng cần cấu hình riêng

### 1. Phân đội: lưới Phân đội và Phân buồng

| Lưới | DB cũ | DB mới | Ghép và so sánh |
|---|---|---|---|
| Phân đội | PN_PHAN_DOI(PN_ID, NGAY_CHUYEN_DEN, MA_PHAN_DOI_DEN, GHI_CHU) | PHAM_NHAN_PHAN_DOI(PNPD_LAI_LICH_ID, PNPD_NGAY_CHUYEN, PNPD_PHAN_DOI_ID, PNPD_PHAN_TRAI_ID, PNPD_GHI_CHU) | Ghép người bằng crosswalk; khóa gợi ý: ngày chuyển + mã phân đội sau khi tra DM_PHAN_DOIS.PD_MA→ID; so ghi chú. Cấu hình hiện tại chỉ khóa ngày nên có thể đụng nếu một ngày có nhiều dòng; cần bổ sung phân đội vào khóa. PNPD_PHAN_TRAI_ID không có cột trực tiếp tương ứng ở bảng cũ; chỉ đối soát nếu xác định được quan hệ phân đội→phân trại và mã nguồn cũ. |
| Phân buồng | PN_PHAN_BUONG(PN_ID, NGAY_CHUYEN, SO_HIEU_BUONG, GHI_CHU) | PHAM_NHAN_PHAN_BUONG(PNPB_LAI_LICH_ID, PNPB_NGAY_CHUYEN, PNPB_SO_BUONG, PNPB_PHAN_KHU, PNPB_GHI_CHU) | Ghép người; khóa gợi ý: ngày chuyển + số hiệu buồng, so ghi chú. PNPB_PHAN_KHU không có trường cũ hiển nhiên; đánh dấu chỉ có ở DB mới/không so cho tới khi xác minh nguồn. Không gộp lưới này vào PN_PHAN_DOI.

### 2. Trách nhiệm dân sự, HPBS: hai lưới cha và một lưới biên lai

| Lưới | DB cũ | DB mới | Ghép và so sánh |
|---|---|---|---|
| Hình phạt bổ sung | PN_HPBS_HINH_PHAT | PN_HINH_PHAT_BO_SUNGS với HPBS_THUOC_LOAI_TRACH_NHIEM_DAN_SU=0 | Ghép theo người và danh sách khoản phạt; ưu tiên loại hình phạt + thời hạn + tổng tiền + ghi chú/chi tiết làm khóa ghép mềm, giữ duplicate và báo mơ hồ. So MA_HINH_PHAT, MA_MUC_THOI_HAN, MA_HE_SO_TIEN, MA_GHI_CHU_HPBS sau quy đổi danh mục; tiền phạt, nội dung, ghi chú. TONG_DA_NOP cần kiểm chứng qua bảng thực hiện, không đối chiếu trực tiếp vào cột tổng nếu cột mới được tính theo công thức khác. |
| Trách nhiệm dân sự bằng tiền | Cùng bảng PN_HPBS_HINH_PHAT | Cùng bảng mới nhưng HPBS_THUOC_LOAI_TRACH_NHIEM_DAN_SU=1 | Code mới lọc TNDS bằng cờ này và danh mục HPBS_LOAI_HPBS='TNDS'. Cần quy tắc/catalog legacy để tách tương ứng; không đoán loại chỉ từ mã. Mapping LL12 hiện chỉ đếm gộp theo người nên chưa đủ kết luận. |
| Danh sách biên lai | PN_HPBS_THUC_HIEN(MA_PN_HPBSHP, BIEN_LAI_SO, BIEN_LAI_NGAY, NGAY_NOP, SO_TIEN_NOP, MA_CQ_THU_NOP, MA_DP_THU_NOP, GHI_CHU_HPBS_TH, ...) | PN_BIENLAIES(HPBS_ID, BL_SO_BIEN_LAI, BL_NGAY_NOP, BL_NGAY_NHAN_VAN_BAN, BL_SO_VAN_BAN, BL_SO_TIEN, BL_NOP_TAI_CO_QUAN, BL_DIA_PHUONG, BL_TRUONG_HOP_THUC_HIEN, BL_GHI_CHU, ...) | Ghép khoản cha trước: MA_PN_HPBSHP → old parent → mapped new parent ID → PN_BIENLAIES.HPBS_ID; sau đó ghép biên lai theo số biên lai + ngày + số tiền, xử lý trùng. Cơ quan/địa phương cần map mã cũ↔ID danh mục mới. Cặp BIEN_LAI_NGAY với BL_NGAY_NHAN_VAN_BAN hay BL_NGAY_NOP cần nghiệp vụ xác nhận; old NGAY_NOP nhiều khả năng tương ứng BL_NGAY_NOP. So tổng theo cha giữa SUM(SO_TIEN_NOP) và SUM(BL_SO_TIEN) như kiểm tra chéo. Các trường văn bản mới (BL_SO_VAN_BAN, BL_LOAI_VAN_BAN_ID) không có nguồn cũ rõ ràng: báo riêng, không điền bằng suy đoán. Cả ba lưới cha/con cần phân trang đủ dữ liệu, không giữ giới hạn 100 dòng của component làm phạm vi đối soát.

### 3. Bản án khác: hai lưới độc lập

| Lưới | DB cũ | DB mới | Ghép và so sánh |
|---|---|---|---|
| Danh sách bản án khác | PN_BAN_AN | PN_BAN_AN_KHACS | Mapping hiện có phù hợp về bảng; khóa gợi ý số bản án + ngày xử trong từng người; so cấp tòa, tòa, địa phương, tội danh, mức án qua danh mục và ghi chú. Cột quyết định thi hành án nhúng trong PN_BAN_AN_KHACS không thay thế lưới bên dưới. |
| Quyết định thi hành án khác | PN_QD_THI_HANH_AN(PN_ID, SO_QDTH_AN, NGAY_QDTH_AN, MA_CQ_TOA_QDTH_AN, MA_DP_TOA_QDTH_AN, SO_BAN_AN, NGAY_BAN_AN, MA_CQ_TOA_XU, MA_DP_TOA_XU, GHI_CHU_QDTHA) | PN_QUYET_DINH_BAN_AN_KHACS(QDBAK_PN_LAI_LICH_ID, QDBAK_SO_QUYET_DINH, QDBAK_NGAY_QUYET_DINH, QDBAK_TOA_QUYET_DINH_ID, QDBAK_TOA_QUYET_DINH_DP_ID, QDBAK_SO_BAN_AN, QDBAK_NGAY_BAN_AN, QDBAK_TOA_XU_ID, QDBAK_TOA_XU_DP_ID, QDBAK_GHI_CHU) | Ghép người; khóa số quyết định + ngày quyết định, thêm tòa nếu trùng; so số/ngày bản án, các tòa/địa phương qua danh mục, ghi chú. Đây là entity/bảng riêng được component gọi qua service riêng; mapping hiện tại thiếu. Không ghép vào PN_BAN_AN_KHACS dù bảng đó có một số cột quyết định tương tự.

### 4. Tiền công lao động sản xuất: lưới thu và lưới chi

| Lưới | DB cũ | DB mới | Ghép và so sánh |
|---|---|---|---|
| Tiền công lao động sản xuất (thu) | PN_TIEN_CONG_SX(PN_ID, NAM_SX, TIEN_Q1..Q4, TIEN_KHAC, GHI_CHU) | TIEN_LAO_DONG_SAN_XUATS(PHAM_NHAN_ID, NAM, TIEN_Q1..Q4, TIEN_KHAC, GHI_CHU) | Mapping hiện có; crosswalk người + khóa năm; so 4 quý, khoản khác, ghi chú. |
| Tiền chi lao động sản xuất | PN_TIEN_CHI_TIEU(PN_ID, NGAY_CHI, SO_TIEN_CHI, MUC_DICH) | TIEN_CHI_LAO_DONG_SAN_XUATS(PHAM_NHAN_ID, NGAY_CHI, SO_TIEN, LY_DO) | Thiếu mapping hiện tại. Ghép người; khóa gợi ý ngày + số tiền + mục đích/lý do; duplicate-aware. Xác minh kỳ vọng đối với bản ghi cùng ngày/cùng khoản. So thêm số dư/tổng tiền hiện có theo công thức UI/API; không chỉ so riêng từng bảng. Lưới chi không phải cột trong bảng thu.

## Mapping hiện có cho toàn bộ menu 12/19/7

Khóa dưới đây là khóa đang khai báo trong mapping.py, chưa phải lúc nào cũng đủ/đúng. — có nghĩa cần khóa xác nhận; bản ghi một dòng trên mỗi người phải được kiểm tra cardinality trước khi dùng.

| Mã cấu hình | Màn | DB cũ | DB mới | Khóa đang khai báo |
|---|---|---|---|---|
| LL01_LaiLich | Lai lịch phạm nhân | PN_LAI_LICH | PN_LAI_LICHS | khóa hiện cấu hình rỗng |
| LL02_HanhVi | Hành vi phạm tội | PN_LAI_LICH | PN_LAI_LICHS | khóa hiện cấu hình rỗng |
| LL03_ThiHanhAn | Thi hành án | PN_LAI_LICH | PN_THI_HANH_AN | khóa hiện cấu hình rỗng |
| LL04_TienAn | Tiền án | PN_TIEN_AN | PN_TIEN_AN | NAM_XU |
| LL05_TienSu | Tiền sự | PN_TIEN_SU | PN_TIEN_SUS | QD_SO, QD_NGAY |
| LL06_BanAnKhac | Bản án khác | PN_BAN_AN | PN_BAN_AN_KHACS | SO_BAN_AN, NGAY_BAN_AN |
| LL07_NguoiThan | Người thân thích | PN_QUAN_HE_GIA_DINH | THAN_NHAN_NGUOI_THANS | HO_TEN_QHGD, MA_QUAN_HE |
| LL08_ConTheoMe | Con theo mẹ vào trại | PN_CON_PHAM_NHAN | THAN_NHAN_CON_CAIS | HO_TEN_CPN |
| LL09_NhanDang | Nhận dạng | PN_DAC_DIEM_NHAN_DANG | PN_NHAN_DANGS | khóa hiện cấu hình rỗng |
| LL10_MaTuy | Ma túy | PN_DOI_TUONG_NGHIEN_MT | PN_NGHIEN_MT | khóa hiện cấu hình rỗng |
| LL11_PhanDoi | Phân đội | PN_PHAN_DOI | PHAM_NHAN_PHAN_DOI | NGAY_CHUYEN_DEN |
| DB00_XepLoai | Xếp loại | PN_KET_QUA_CAI_TAO | XEP_LOAIS | NAM_XL |
| DB01_GiamThoiHan | Giảm thời hạn | PN_GIAM_THOI_HAN | GIAM_THOI_HANS | NGAY_XET |
| DB02_PhanLoai | Phân loại | PN_PHAN_LOAI_GIAM_GIU | PHAN_LOAIS | NGAY_PHAN_LOAI |
| DB03_ChuaBenhBB | Chữa bệnh bắt buộc | PN_CHUA_BENH_BAT_BUOC | CHUA_BENH_BAT_BUOCS | QD_SO, QD_NGAY |
| DB04_SucKhoe | Thông tin sức khỏe | PN_SUC_KHOE_BENH_TAT | PN_SUC_KHOES | NGAY_KHAM |
| DB05_PhamToiMoi | Phạm tội mới | PN_PHAM_TOI_MOI | PHAM_TOI_MOIS | NGAY_PT_MOI |
| DB06_AnGiam | Ân giảm | PN_QD_AN_GIAM | AN_GIAMS | SO_QD, NGAY_QD |
| DB07_TangGiamHP | Tăng giảm hình phạt | PN_TANG_GIAM_HINH_PHAT | TANG_GIAM_HINH_PHATS | SO_QD, NGAY_QD |
| DB08_KhenThuong | Khen thưởng | PN_KHEN_THUONG | KHEN_THUONGS | SO_QD_KHEN, NGAY_KHEN |
| DB09_KyLuat | Kỷ luật | PN_KL_KY_LUAT | KY_LUATS | SO_QD_KL, NGAY_QD_KL |
| DB10_GiamRieng | Giam riêng | PN_GR_GIAM_RIENG | PN_GIAM_RIENGS | SO_QD_GR, NGAY_QD_GR |
| DB11_TronTrai | Trốn trại | PN_TT_TRON_TRAI | TRON_TRAIS | NGAY_TRON |
| DB12_TrichXuat | Trích xuất | PN_TX_TRICH_XUAT | TRICH_XUATS | SO_LENH_TX, NGAY_LENH_TX |
| DB13_TamDinhChi | Tạm đình chỉ | PN_TDC_TAM_DINH_CHI | TAM_DINH_CHIS | SO_QD, NGAY_QD |
| DB14_HoanTHA | Hoãn thi hành án | PN_HOAN_THI_HANH_AN | HOAN_THI_HANH_ANS | SO_QD_HOAN, NGAY_QD_HOAN |
| DB15_MienHP | Miễn hình phạt | PN_MIEN_HINH_PHAT | MIEN_HINH_PHATS | QD_MIEN_SO, QD_MIEN_NGAY |
| DB16_HuyAn | Hủy án | PN_HUY_AN | HUY_ANS | SO_QD_HUY, NGAY_QD_HUY |
| DB17_TienCongLDSX | Tiền công lao động sản xuất | PN_TIEN_CONG_SX | TIEN_LAO_DONG_SAN_XUATS | NAM_SX |
| KT01_RaTrai | Ra trại | PN_RA_TRAI | PN_KET_THUC_RA_TRAIS | NGAY_THA |
| KT02_Chet | Chết | PN_PNC_CHET | PN_KET_THUC_CHETS | khóa hiện cấu hình rỗng |
| KT03_ThaCoDK | Tha có điều kiện | PN_THA_CO_DK | THA_CO_DIEU_KIENS | NGAY_XET_TT |
| KT04_DacXa | Đặc xá | PN_DX_DAC_XA | PN_DAC_XAS | NGAY_XET_DX |
| KT05_ChuyenGiao | Chuyển giao | PN_CHUYEN_GIAO | PN_CHUYEN_GIAO | SO_QD_CG, NGAY_QD_CG |
| KT06_ChuyenTrai | Chuyển trại | PN_CHUYEN_TRAI | PHAM_NHAN_CHUYEN_TRAI | SO_QD_CHUYEN, NGAY_QD_CHUYEN |
| KT07_NopLuu | Nộp lưu hồ sơ | PN_HSPN_NOP_LUU | NOP_LUUS | SO_DANG_KY |
| LL12_TNDS | Trách nhiệm dân sự | PN_HPBS_HINH_PHAT | PN_HINH_PHAT_BO_SUNGS | khóa hiện cấu hình rỗng |
| DB18_TaiLieu | Tài liệu đính kèm | Không đối soát theo yêu cầu người dùng | Không đối soát | Đã loại khỏi phạm vi và menu tool. |

LL12_TNDS trong mapping hiện tại được xếp cuối file nhưng thuộc menu Lý lịch; danh sách menu cần hiển thị theo thứ tự giao diện: đặt TNDS ở vị trí thứ 6 và Phân đội ở thứ 12. Khi chỉnh code, không dùng thứ tự khai báo cấu hình hiện tại làm thứ tự menu.

Các cấu hình còn lại trong bảng trên có danh sách cột so sánh trong db-compare/mapping.py; DDL xác thực đủ tên bảng/cột cấu hình. Cần giữ cơ chế xem chi tiết và trạng thái mapping chưa duyệt; danh sách trên không khẳng định mọi cột đã được nghiệp vụ nghiệm thu.

## Các vấn đề của thuật toán so hiện tại

### Cập nhật rà soát danh mục ngày 2026-11-19

Engine hiện không so trực tiếp mã danh mục DB cũ với ID DB mới. Mapping `dm` đổi ID phía mới về cột mã `*_MA` trong danh mục tương ứng rồi mới so; `dmlist` đổi từng ID trong danh sách; các mã tỉnh đi qua `MAPPING_PROVINCE` và `DM_TINH_THANH_PHO`.

Riêng dân tộc/tôn giáo, mapping đã dùng chuỗi `mã DB cũ → danh mục *_OLD → ID legacy → bảng DM_*_MAPPING → ID danh mục hiện hành → mã *_MA hiện hành`, sau đó so với mã của ID đang lưu ở `LL_DM_DAN_TOC_ID`/`LL_DM_TON_GIAO_ID`.

Đây chưa phải xác nhận toàn bộ quy tắc danh mục bằng dữ liệu thật. DDL có 8 cột đang khai báo `dm` nhưng kiểu đích là chuỗi; một số có thể là ID dạng chuỗi, mã, hoặc nội dung. Đặc biệt `DX_TINH_TRANG_DAC_XA` được truy vấn ứng dụng phân tích như danh sách mã `DDX_MA`; cần sửa/xác minh loại mapping trước khi kết luận cột đó khớp hay lệch. Danh sách chi tiết và phương án đóng rà soát nằm tại `docs/2026-11-19-doi-soat-danh-muc-audit.md`.

- compare.py hiện có nhánh fallback CCCD/CMND, không phù hợp với quy tắc đã chốt. Khi triển khai phải bỏ nhánh fallback này: chỉ ghép HSLĐ duy nhất. Báo riêng HSLĐ thiếu, HSLĐ trùng ở DB cũ, HSLĐ trùng ở DB mới, chỉ có ở một DB và dữ liệu con thuộc hồ sơ không ghép được; không dùng CCCD kể cả khi hiển thị chênh lệch để quyết định ghép.
- 
un_screen() gom bản ghi theo người, tạo khóa sự kiện từ key và đánh số lần xuất hiện sau khi sort. Khóa rỗng khiến mọi dòng của một người chung một khóa rỗng; đây chỉ hợp lý cho kiểm đếm khi cols=[], không phải so giá trị. Khóa nghiệp vụ thiếu trường có thể ghép sai hai bản ghi cùng ngày/năm.
- Tổng old_total/new_total hiện là tổng cả bảng, trong khi các match/diff chỉ được tính trên người đã ghép. Cần phân biệt bản ghi thuộc người chưa ghép khỏi chênh lệch màn hình.
- DB mới lọc IS_DELETED=0 khi cột tồn tại; cần thống nhất cách đối xử với NULL và dữ liệu xóa mềm theo bảng.
- Có truy vấn toàn bảng và giới hạn giao diện/service; khi làm tool cần dùng phân trang/chia lô, thời điểm snapshot nhất quán hoặc cảnh báo DB thay đổi trong khi chạy.

## Danh sách việc cần chốt để đưa mapping vào chạy chính thức

1. Quy tắc ghép hồ sơ đã chốt: chỉ dùng HSLĐ duy nhất, tuyệt đối không dùng CCCD/CMND làm khóa ghép. Code mới tách TNDS bằng HPBS_THUOC_LOAI_TRACH_NHIEM_DAN_SU=1 và danh mục HPBS_LOAI_HPBS='TNDS'. DDL cũ không có cờ này; stored logic chỉ dùng mã 201–299 như HPBS trong một nghiệp vụ, chưa chứng minh được quy tắc phân loại tổng quát. Cần mapping danh mục cũ sang loại TNDS/HPBS.
2. NGAY_NOP có khả năng tương ứng BL_NGAY_NOP; xác nhận ý nghĩa BIEN_LAI_NGAY với BL_NGAY_NHAN_VAN_BAN (ngày nhận văn bản) vì UI/code mới không chỉ ra phép chuyển đổi này. Xác nhận cách tính TONG_DA_NOP, tổng tiền hoàn/còn lại và khoản chi.
3. Xác nhận quy tắc ghép lịch sử phân đội/phân buồng, giá trị phân khu và danh mục phân đội/phân trại theo mã nào ở DB cũ.
4. Tài liệu đính kèm đã được loại khỏi phạm vi theo yêu cầu người dùng.
5. Xác nhận chính sách bản ghi xóa mềm, phạm vi thời điểm/cut-off và quyền SELECT trên các bảng/danh mục cần thiết.
6. Kiểm tra dữ liệu thực để đo trùng/thiếu khóa người, khóa sự kiện; với khóa không duy nhất thì thiết kế match theo nhiều pha hoặc yêu cầu xác nhận thủ công.
7. Hoàn thiện mapping của hai lưới phụ thuộc PN_HPBS_THUC_HIEN và chọn mã màn thống nhất với menu (hiện tên/code LL12_TNDS đặt cuối danh sách).

## Nguồn đã rà

- check-db/DB/DLL_SUOI_HAI_old.sql, check-db/DB/DLL_QLPN_NEW.sql.
- db-compare/mapping.py, db-compare/compare.py, db-compare/DB/DLL_SUOI_HAI.sql.
- Angular components: pham-nhan/.../phan-doi, hinh-phat-bo-sung, ban-an-khac; dien-bien/tien-cong-lao-dong-san-xuat, dien-bien/tien-chi-lao-dong-san-xuat, dien-bien/tai-lieu-dinh-kem.
- DDL là dump có thể cũ hơn code hiện tại; trước khi chạy ở môi trường thật, chạy kiểm tra schema và xác minh phần migration mới nhất.
