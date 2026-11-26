# Mapping đối soát từng màn, từng cột

> Nguồn: cấu hình `mapping.py`. Tài liệu liệt kê các cột tool đang cấu hình đối soát, không phải toàn bộ cột hiện có trong schema DB. Có 40 màn/dataset và 435 cặp cột.

## Mục lục

- [Lai lịch phạm nhân (`LL01_LaiLich`)](#ll01-lailich)
- [Hành vi phạm tội (`LL02_HanhVi`)](#ll02-hanhvi)
- [Thi hành án (`LL03_ThiHanhAn`)](#ll03-thihanhan)
- [Tiền án (`LL04_TienAn`)](#ll04-tienan)
- [Tiền sự (`LL05_TienSu`)](#ll05-tiensu)
- [Bản án khác (`LL06_BanAnKhac`)](#ll06-banankhac)
- [Người thân thích (`LL07_NguoiThan`)](#ll07-nguoithan)
- [Con theo mẹ vào trại (`LL08_ConTheoMe`)](#ll08-contheome)
- [Nhận dạng (`LL09_NhanDang`)](#ll09-nhandang)
- [Ma túy (`LL10_MaTuy`)](#ll10-matuy)
- [Phân đội (`LL11_PhanDoi`)](#ll11-phandoi)
- [Xếp loại (`DB00_XepLoai`)](#db00-xeploai)
- [Giảm thời hạn (`DB01_GiamThoiHan`)](#db01-giamthoihan)
- [Phân loại (`DB02_PhanLoai`)](#db02-phanloai)
- [Chữa bệnh bắt buộc (`DB03_ChuaBenhBB`)](#db03-chuabenhbb)
- [Thông tin sức khỏe (`DB04_SucKhoe`)](#db04-suckhoe)
- [Phạm tội mới (`DB05_PhamToiMoi`)](#db05-phamtoimoi)
- [Ân giảm (`DB06_AnGiam`)](#db06-angiam)
- [Tăng giảm hình phạt (`DB07_TangGiamHP`)](#db07-tanggiamhp)
- [Khen thưởng (`DB08_KhenThuong`)](#db08-khenthuong)
- [Kỷ luật (`DB09_KyLuat`)](#db09-kyluat)
- [Giam riêng (`DB10_GiamRieng`)](#db10-giamrieng)
- [Trốn trại (`DB11_TronTrai`)](#db11-trontrai)
- [Trích xuất (`DB12_TrichXuat`)](#db12-trichxuat)
- [Tạm đình chỉ (`DB13_TamDinhChi`)](#db13-tamdinhchi)
- [Hoãn thi hành án (`DB14_HoanTHA`)](#db14-hoantha)
- [Miễn hình phạt (`DB15_MienHP`)](#db15-mienhp)
- [Hủy án (`DB16_HuyAn`)](#db16-huyan)
- [Tiền công lao động sản xuất (`DB17_TienCongLDSX`)](#db17-tiencongldsx)
- [Ra trại (`KT01_RaTrai`)](#kt01-ratrai)
- [Chết (`KT02_Chet`)](#kt02-chet)
- [Tha có điều kiện (`KT03_ThaCoDK`)](#kt03-thacodk)
- [Đặc xá (`KT04_DacXa`)](#kt04-dacxa)
- [Chuyển giao (`KT05_ChuyenGiao`)](#kt05-chuyengiao)
- [Chuyển trại (`KT06_ChuyenTrai`)](#kt06-chuyentrai)
- [Nộp lưu hồ sơ (`KT07_NopLuu`)](#kt07-nopluu)
- [Trách nhiệm dân sự, HPBS (`LL12_TNDS`)](#ll12-tnds)
- [Phân buồng (`LL11b_PhanBuong`)](#ll11b-phanbuong)
- [Quyết định thi hành án khác (`LL06b_QDThiHanhAnKhac`)](#ll06b-qdthihanhankhac)
- [Tiền chi lao động sản xuất (`DB17b_TienChiLDSX`)](#db17b-tienchildsx)

## Quy ước

- `dm`: DB cũ lưu mã; DB mới lưu ID. Engine tra ID qua danh mục mới lấy mã `*_MA`, rồi so mã.
- `dm_legacy`: đi từ mã DB cũ qua danh mục `_OLD`, lấy ID legacy, qua bảng mapping lấy ID hiện hành, tra mã hiện hành rồi so mã.
- `province`: mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO` → ID tỉnh mới.
- `dmlist`: tách danh sách; đổi từng ID DB mới sang mã qua danh mục, sắp xếp rồi so với mã DB cũ.
- `text`, `date`, `num`: lần lượt chuẩn hóa văn bản, ngày hoặc số rồi so.
- Các khóa ghép dòng được đánh dấu trong cột logic. Ghép hồ sơ phạm nhân dùng HSLĐ theo quy tắc chung của tool.
- Đây là mapping theo code/schema; một số cột danh mục kiểu chuỗi cần đối chiếu dữ liệu thật trước khi kết luận mapping đã được nghiệp vụ xác nhận. Chi tiết xem [báo cáo rà soát danh mục](2026-11-19-doi-soat-danh-muc-audit.md).

<a id="ll01-lailich"></a>

## Lai lịch phạm nhân (`LL01_LaiLich`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_LAI_LICH` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_LAI_LICHS` (liên kết phạm nhân: `ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_LAI_LICH.SO_HSLD` | `PN_LAI_LICHS.LL_SO_HO_SO_LAN_DAU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.SO_HSPHU` | `PN_LAI_LICHS.LL_SO_HO_PHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.SO_CCCD` | `PN_LAI_LICHS.LL_CCCD` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.HO_TEN` | `PN_LAI_LICHS.LL_HO_TEN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.TEN_KHAC` | `PN_LAI_LICHS.LL_TEN_KHAC` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_SINH_PN` | `PN_LAI_LICHS.LL_NGAY_SINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_GIOI_TINH` | `PN_LAI_LICHS.LL_DM_GIOI_TINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_GIOI_TINHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.NGUYEN_QUAN` | `PN_LAI_LICHS.LL_NGUYEN_QUAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.CHO_O_KHAC` | `PN_LAI_LICHS.LL_NOI_OKHAC` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.MA_DAN_TOC` | `PN_LAI_LICHS.LL_DM_DAN_TOC_ID` | Mã cũ → `DM_DAN_TOCS_OLD` (`DT_MA`/`TG_MA`) lấy ID → `DM_DAN_TOC_MAPPING.DT_MA` → `DT_MA_NEW` (ID mới) → `DM_DAN_TOCS.ID` lấy mã `*_MA`; so mã. |
| `PN_LAI_LICH.MA_TON_GIAO` | `PN_LAI_LICHS.LL_DM_TON_GIAO_ID` | Mã cũ → `DM_TON_GIAOS_OLD` (`DT_MA`/`TG_MA`) lấy ID → `DM_TON_GIAO_MAPPING.TG_MA` → `TG_MA_MOI_NEW` (ID mới) → `DM_TON_GIAOS.ID` lấy mã `*_MA`; so mã. |
| `PN_LAI_LICH.MA_QUOC_TICH` | `PN_LAI_LICHS.LL_DM_QUOC_TICH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_QUOC_TICHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_HOC_VAN` | `PN_LAI_LICHS.LL_DM_HOC_VAN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HOC_VANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_NGHE_NGHIEP` | `PN_LAI_LICHS.LL_DM_NGHE_NGHIEP_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_NGHE_NGHIEPS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.NGHE_CU_THE` | `PN_LAI_LICHS.LL_NGHE_CU_THE` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.TRINH_DO_CHUYEN_MON` | `PN_LAI_LICHS.LL_TRINH_DO_CHUYEN_MON` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.MA_SUC_KHOE_VAO` | `PN_LAI_LICHS.LL_SUC_KHOE_KHI_VAO_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_SUC_KHOE_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_BENH_TAT_VAO` | `PN_LAI_LICHS.LL_BENH_TAT_VAO_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_BENH_TATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.BENH_TAT_VAO` | `PN_LAI_LICHS.LL_CHI_TIET_BENH_VAO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.MA_BENH_TAT_HT` | `PN_LAI_LICHS.LL_BENH_HIEN_TAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_BENH_TATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.BENH_TAT_HT` | `PN_LAI_LICHS.LL_CHI_TIET_BENH_HIEN_TAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.GHI_CHU_RIENG` | `PN_LAI_LICHS.LL_GHI_CHU_RIENG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.MA_TRAI_GIAM` | `PN_LAI_LICHS.LL_TRAI_GIAM_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRAI_GIAMS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_TINH_TRANG` | `PN_LAI_LICHS.LL_TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_PHAN_DOI` | `PN_LAI_LICHS.LL_PHAN_DOI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_PHAN_DOIS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_TAI_PHAM` | `PN_LAI_LICHS.LL_TAI_PHAM` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TAI_PHAMS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_TINH_TRANG_HOC_TAP` | `PN_LAI_LICHS.LL_TINH_TRANG_HOC_TAP_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_HOC_TAP_PHAM_NHAN_VI_THANH_NIENS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_TINH_TRANG_DOC_VIET` | `PN_LAI_LICHS.LL_BIET_DOC_VIET_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_BIET_DOC_VIETS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.SO_TIEN_SU` | `PN_LAI_LICHS.LL_SO_TIEN_SU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.SO_TIEN_AN` | `PN_LAI_LICHS.LL_SO_TIEN_AN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.GHI_CHU_TIEN_SU` | `PN_LAI_LICHS.LL_GHI_CHU_TIEN_SU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NHAN_THAN` | `PN_LAI_LICHS.LL_NHAN_THAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.GHI_CHU_HPBS` | `PN_LAI_LICHS.LL_GHI_CHU_CHUNG_HPBS` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.BUONG_GIAM` | `PN_LAI_LICHS.LL_BUONG_GIAM` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll02-hanhvi"></a>

## Hành vi phạm tội (`LL02_HanhVi`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_LAI_LICH` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_LAI_LICHS` (liên kết phạm nhân: `ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_LAI_LICH.TOM_TAT_HV` | `PN_LAI_LICHS.LL_TOM_TAT_HV` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.CHI_TIET_HV` | `PN_LAI_LICHS.LL_CHI_TIET_HV` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll03-thihanhan"></a>

## Thi hành án (`LL03_ThiHanhAn`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_LAI_LICH` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_THI_HANH_AN` (liên kết phạm nhân: `THA_PNLAI_LICH_ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_LAI_LICH.NGAY_BAT` | `PN_THI_HANH_AN.THA_NGAY_BAT` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.NGAY_PHAM_TOI` | `PN_THI_HANH_AN.THA_NGAY_PHAM_TOI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_MUC_AN_PHAT` | `PN_THI_HANH_AN.THA_MUC_AN_ID` | DB cũ lưu mã mức thời gian; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → `MTG_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_CQ_RL_BAT` | `PN_THI_HANH_AN.THA_CO_QUAN_BAT_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_DP_RL_BAT` | `PN_THI_HANH_AN.THA_DIA_PHUONG_CO_QUAN_BAT_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_LAI_LICH.BAN_AN_SO` | `PN_THI_HANH_AN.THA_SO_BAN_AN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_XU` | `PN_THI_HANH_AN.THA_NGAY_BAN_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_CAP_TOA_XU` | `PN_THI_HANH_AN.THA_CAP_TOA_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CAP_TOA_XUS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_DP_TOA_XU` | `PN_THI_HANH_AN.THA_DIA_PHUONG_CAP_TOA_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_LAI_LICH.SO_QD_TH_AN` | `PN_THI_HANH_AN.THA_SO_QD_THA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_QD_TH_AN` | `PN_THI_HANH_AN.THA_NGAY_QD_THA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_CQ_TOA_QD` | `PN_THI_HANH_AN.THA_TOA_QD_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_DP_TOA_QD` | `PN_THI_HANH_AN.THA_DIA_PHUONG_TOA_QD_THA_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_LAI_LICH.NGAY_DEN_TRAI` | `PN_THI_HANH_AN.THA_NGAY_DEN_TRAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_TOI_DANH` | `PN_THI_HANH_AN.THA_TOI_DANH` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_TOI_DANHS.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_LAI_LICH.MA_LOAI_DOI_TUONG` | `PN_THI_HANH_AN.THA_DOI_TUONG` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LOAI_DOI_TUONGS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.SO_QD_DC` | `PN_THI_HANH_AN.THA_SO_QD_DIEU_CHUYEN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_QD_DC` | `PN_THI_HANH_AN.THA_NGAY_QD_DIEU_CHUYEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.SO_DE_NGHI_DC` | `PN_THI_HANH_AN.THA_SO_DE_NGHI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_DE_NGHI_DC` | `PN_THI_HANH_AN.THA_NGAY_DE_NGHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_CQ_DN_DC` | `PN_THI_HANH_AN.THA_DON_VI_DE_NGHI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_DP_DN_DC` | `PN_THI_HANH_AN.THA_DIA_PHUONG_DON_VI_DE_NGHI_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_LAI_LICH.SO_DB` | `PN_THI_HANH_AN.THA_SO_DANH_BAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.NGAY_LAP_DB` | `PN_THI_HANH_AN.THA_NGAY_LAP_DANH_BAN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_LAI_LICH.MA_CQ_LAP_DB` | `PN_THI_HANH_AN.THA_CO_QUAN_LAP_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_LAI_LICH.MA_DP_LAP_DB` | `PN_THI_HANH_AN.THA_DIA_PHUONG_DON_CO_QUAN_LAP_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_LAI_LICH.CT_VAN_TAY1` | `PN_THI_HANH_AN.THA_CONG_THUC_VAN_TAY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_LAI_LICH.CT_VAN_TAY2` | `PN_THI_HANH_AN.THA_CONG_THUC_VAN_TAY_2` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll04-tienan"></a>

## Tiền án (`LL04_TienAn`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_TIEN_AN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_TIEN_AN` (liên kết phạm nhân: `PNTA_LAI_LICH_ID`)
- **Khóa ghép dòng:** `NAM_XU`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TIEN_AN.NAM_XU` | `PN_TIEN_AN.PNTA_NAM_XU` | Chuẩn hóa giá trị số rồi so. **Khóa ghép dòng.** |
| `PN_TIEN_AN.MA_CQ_TOA_XU_TA` | `PN_TIEN_AN.PNTA_TOA_XU_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TIEN_AN.MA_DP_TOA_XU_TA` | `PN_TIEN_AN.PNTA_DIA_PHUONG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_DIA_PHUONG.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TIEN_AN.MA_TOI_DANH_TA` | `PN_TIEN_AN.PNTA_TOI_DANH_ID` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_TOI_DANHS.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_TIEN_AN.MA_MUC_AN_TA` | `PN_TIEN_AN.PNTA_MUC_AN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TIEN_AN.MA_TRAI_GIAM_TA` | `PN_TIEN_AN.PNTA_NOI_CHAP_HANH_AN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRAI_GIAMS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TIEN_AN.MA_GHI_CHU_TA` | `PN_TIEN_AN.PNTA_GHI_CHU_TOA_AN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_GHI_CHU_TIEN_ANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TIEN_AN.NAM_THA` | `PN_TIEN_AN.PNTA_NAM_THA` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_AN.GHI_CHU_TA` | `PN_TIEN_AN.PNTA_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TIEN_AN.MA_TINH_TRANG_TA` | `PN_TIEN_AN.PNTA_TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_TIEN_ANS.ID` → cột mã `*_MA`, rồi so mã. |

<a id="ll05-tiensu"></a>

## Tiền sự (`LL05_TienSu`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_TIEN_SU` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_TIEN_SUS` (liên kết phạm nhân: `TS_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `QD_SO`, `QD_NGAY`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TIEN_SU.NGAY_THANG` | `PN_TIEN_SUS.TS_THOI_GIAN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TIEN_SU.QD_SO` | `PN_TIEN_SUS.TS_SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_TIEN_SU.QD_NGAY` | `PN_TIEN_SUS.TS_NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TIEN_SU.HANH_VI_VP` | `PN_TIEN_SUS.TS_HANH_VI_VI_PHAM` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TIEN_SU.DON_VI_XL` | `PN_TIEN_SUS.TS_DON_VI_XU_LY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TIEN_SU.HINH_THUC_XL` | `PN_TIEN_SUS.TS_HINH_THUC_XU_LY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TIEN_SU.NOI_CHAP_HANH` | `PN_TIEN_SUS.TS_NOI_CHAP_HANH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TIEN_SU.NGAY_BAT_DAU` | `PN_TIEN_SUS.TS_NGAY_BAT_DAU` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TIEN_SU.NGAY_KET_THUC` | `PN_TIEN_SUS.TS_NGAY_KET_THUC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TIEN_SU.GHI_CHU_TS` | `PN_TIEN_SUS.TS_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll06-banankhac"></a>

## Bản án khác (`LL06_BanAnKhac`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_BAN_AN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_BAN_AN_KHACS` (liên kết phạm nhân: `BAK_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `SO_BAN_AN`, `NGAY_BAN_AN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_BAN_AN.SO_BAN_AN` | `PN_BAN_AN_KHACS.BAK_SO_BAN_AN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_BAN_AN.NGAY_BAN_AN` | `PN_BAN_AN_KHACS.BAK_NGAY_BAN_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_BAN_AN.MA_CAP_TOA_XU_BA` | `PN_BAN_AN_KHACS.BAK_CAP_TOA_XU_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CAP_TOA_XUS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_BAN_AN.MA_CQ_TOA_XU_BA` | `PN_BAN_AN_KHACS.BAK_TOA_XU_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_BAN_AN.MA_DP_TOA_XU_BA` | `PN_BAN_AN_KHACS.BAK_TOA_XU_DP_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_BAN_AN.MA_TOI_DANH_BA` | `PN_BAN_AN_KHACS.BAK_TOI_DANH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TOI_DANHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_BAN_AN.MA_MUC_AN_BA` | `PN_BAN_AN_KHACS.BAK_MUC_AN_ID` | DB cũ lưu mã mức thời gian; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → `MTG_MA`, rồi so mã. |
| `PN_BAN_AN.GHI_CHU_BA` | `PN_BAN_AN_KHACS.BAK_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll07-nguoithan"></a>

## Người thân thích (`LL07_NguoiThan`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_QUAN_HE_GIA_DINH` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `THAN_NHAN_NGUOI_THANS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `HO_TEN_QHGD`, `MA_QUAN_HE`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_QUAN_HE_GIA_DINH.HO_TEN_QHGD` | `THAN_NHAN_NGUOI_THANS.HO_TEN_THAN_NHAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_QUAN_HE_GIA_DINH.MA_QUAN_HE` | `THAN_NHAN_NGUOI_THANS.QUAN_HE_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_QUAN_HE_VOI_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. **Khóa ghép dòng.** |
| `PN_QUAN_HE_GIA_DINH.MA_GIOI_TINH_QHGD` | `THAN_NHAN_NGUOI_THANS.GIOI_TINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_GIOI_TINHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_QUAN_HE_GIA_DINH.NGAY_SINH_QHGD` | `THAN_NHAN_NGUOI_THANS.NGAY_SINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_QUAN_HE_GIA_DINH.NGHE_NGHIEP_QHGD` | `THAN_NHAN_NGUOI_THANS.NGHE_NGHIEP` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_QUAN_HE_GIA_DINH.NOI_O` | `THAN_NHAN_NGUOI_THANS.NOI_O` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_QUAN_HE_GIA_DINH.GHI_CHU_QHGD` | `THAN_NHAN_NGUOI_THANS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_QUAN_HE_GIA_DINH.BAO_TIN` | `THAN_NHAN_NGUOI_THANS.THONG_BAO` | Chuẩn hóa giá trị số rồi so. |
| `PN_QUAN_HE_GIA_DINH.DIEN_THOAI` | `THAN_NHAN_NGUOI_THANS.DIEN_THOAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll08-contheome"></a>

## Con theo mẹ vào trại (`LL08_ConTheoMe`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_CON_PHAM_NHAN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `THAN_NHAN_CON_CAIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `HO_TEN_CPN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_CON_PHAM_NHAN.HO_TEN_CPN` | `THAN_NHAN_CON_CAIS.HO_TEN_CON` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_CON_PHAM_NHAN.MA_GIOI_TINH_CPN` | `THAN_NHAN_CON_CAIS.GIOI_TINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_GIOI_TINHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CON_PHAM_NHAN.NGAY_SINH_CPN` | `THAN_NHAN_CON_CAIS.NGAY_SINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CON_PHAM_NHAN.MA_TH_SINH_CPN` | `THAN_NHAN_CON_CAIS.TRUONG_HOP_SINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_SINH_CON_THEO_MES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CON_PHAM_NHAN.NOI_SINH_CPN` | `THAN_NHAN_CON_CAIS.NOI_SINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CON_PHAM_NHAN.NGAY_DEN_CPN` | `THAN_NHAN_CON_CAIS.NGAY_DEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CON_PHAM_NHAN.NGAY_RA_CPN` | `THAN_NHAN_CON_CAIS.NGAY_RA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CON_PHAM_NHAN.MA_TINH_TRANG_CPN` | `THAN_NHAN_CON_CAIS.TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_CON_THEO_ME_VAO_TRAIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CON_PHAM_NHAN.GHI_CHU_CPN` | `THAN_NHAN_CON_CAIS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll09-nhandang"></a>

## Nhận dạng (`LL09_NhanDang`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_DAC_DIEM_NHAN_DANG` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_NHAN_DANGS` (liên kết phạm nhân: `ND_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_DAC_DIEM_NHAN_DANG.CHIEU_CAO` | `PN_NHAN_DANGS.ND_CHIEU_CAO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.SONG_MUI` | `PN_NHAN_DANGS.ND_SONG_MUI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.NEP_TAI_DUOI` | `PN_NHAN_DANGS.ND_NEP_TAI_DUOI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.DAI_TAI` | `PN_NHAN_DANGS.ND_DAI_TAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.TAM_VOC` | `PN_NHAN_DANGS.ND_TAM_VOC` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.GIONG_NOI` | `PN_NHAN_DANGS.ND_GIONG_NOI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.MAU_DA` | `PN_NHAN_DANGS.ND_MAU_DA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.DAU_VET_DB` | `PN_NHAN_DANGS.ND_DAU_VET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.DI_HINH` | `PN_NHAN_DANGS.ND_DI_HINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DAC_DIEM_NHAN_DANG.GHI_CHU` | `PN_NHAN_DANGS.ND_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll10-matuy"></a>

## Ma túy (`LL10_MaTuy`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_DOI_TUONG_NGHIEN_MT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_NGHIEN_MT` (liên kết phạm nhân: `NMT_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_DOI_TUONG_NGHIEN_MT.MA_TP_BAN_THAN` | `PN_NGHIEN_MT.NMT_THANH_PHAN_BAN_THAN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_THANH_PHAN_BAN_THANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TRINH_DO_HV` | `PN_NGHIEN_MT.NMT_TRINH_DO_HOC_VAN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TRINH_DO_HOC_VANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TINH_TRANG_HON_NHAN` | `PN_NGHIEN_MT.NMT_TINH_TRANG_HON_NHAN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TINH_TRANG_HON_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_HOAN_CANH_GD` | `PN_NGHIEN_MT.NMT_HOAN_CANH_GIA_DINH` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_HOAN_CANH_GIA_DINHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_NGHE_BO_ME` | `PN_NGHIEN_MT.NMT_NGHE_NGHIEP_BO_ME` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_MT_NGHE_NGHIEP_BO_MES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TINH_TRANG_KT_GD` | `PN_NGHIEN_MT.NMT_KINH_TE_GIA_DINH` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TINH_TRANG_KINH_TE_GIA_DINHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_CHAT_MA_TUY` | `PN_NGHIEN_MT.NMT_CHAT_MA_TUY` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_CHAT_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_HINH_THUC_SD` | `PN_NGHIEN_MT.NMT_HINH_THUC_SD` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_HINH_THUC_SU_DUNG_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_DO_TUOI_SD` | `PN_NGHIEN_MT.NMT_DO_TUOI_SD` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_DO_TUOI_SU_DUNG_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_SO_LAN_SD` | `PN_NGHIEN_MT.NMT_SO_LAN_SD` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_SO_LAN_SU_DUNG_MA_TUYS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.GIA_TIEN_SD_MOI_LAN` | `PN_NGHIEN_MT.NMT_GIA_TIEN_SD_MOI_LAN` | Chuẩn hóa giá trị số rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_THOI_GIAN_SD` | `PN_NGHIEN_MT.NMT_THOI_GIAN_SD` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_THOI_GIAN_SU_DUNG_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_MUC_THOI_HAN_SD` | `PN_NGHIEN_MT.NMT_THOI_HAN_SD` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_NGUON_TIEN_MUA_MT` | `PN_NGHIEN_MT.NMT_NGUON_TIEN_MUA_MT` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_NGUON_TIEN_MUA_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_DONG_CO_NGHIEN` | `PN_NGHIEN_MT.NMT_DONG_CO_NGHIEN` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_DONG_CO_SU_DUNG_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TINH_TRANG_CAI_NGHIEN` | `PN_NGHIEN_MT.NMT_TINH_TRANG_CAI_NGHIEN` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_MT_TINH_TRANG_CAI_NGHIEN_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_NGUYEN_NHAN_TAI_NGHIEN` | `PN_NGHIEN_MT.NMT_NGUYEN_NHAN_TAI_NGHIEN` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_NGUYEN_NHAN_TAI_NGHIEN_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_BP_CAI_NGHIEN_HQ` | `PN_NGHIEN_MT.NMT_BIEN_PHAP_CAI_HIEU_QUA` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_BIEN_PHAP_CAI_NGHIEN_MA_TUIES.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_YEU_TO_CAI_NGHIEN` | `PN_NGHIEN_MT.NMT_YEU_TO_CAI_NGHIEN` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_MT_YEU_TO_CAI_NGHIEN_HIEU_QUAS.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TRUONG_HOP_NGHIEN` | `PN_NGHIEN_MT.NMT_TRUONG_HOP_NGHIEN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TRUONG_HOP_NGHIEN_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TINH_TRANG_NGHIEN` | `PN_NGHIEN_MT.NMT_TINH_TRANG_NGHIEN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TINH_TRANG_NGHIEN_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_TRUONG_HOP_CAI` | `PN_NGHIEN_MT.NMT_TRUONG_HOP_CAI` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MT_TRUONG_HOP_CAIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.MA_CAN_CU_XAC_DINH` | `PN_NGHIEN_MT.NMT_CAN_CU_XAC_DINH` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CAN_CU_XAC_DINH_MA_TUIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DOI_TUONG_NGHIEN_MT.DE_XUAT_VOI_XA_HOI` | `PN_NGHIEN_MT.NMT_DE_XUAT_VOI_XA_HOI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DOI_TUONG_NGHIEN_MT.DE_XUAT_VOI_TG` | `PN_NGHIEN_MT.NMT_DE_XUAT_VOI_TRAI_GIAM` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DOI_TUONG_NGHIEN_MT.DE_XUAT_VOI_BAN_THAN` | `PN_NGHIEN_MT.NMT_DE_XUAT_VOI_BAN_THAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DOI_TUONG_NGHIEN_MT.CAM_DOAN_BAN_THAN` | `PN_NGHIEN_MT.NMT_CAM_DOAN_CUA_BAN_THAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DOI_TUONG_NGHIEN_MT.GHI_CHU` | `PN_NGHIEN_MT.NMT_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll11-phandoi"></a>

## Phân đội (`LL11_PhanDoi`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_PHAN_DOI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PHAM_NHAN_PHAN_DOI` (liên kết phạm nhân: `PNPD_LAI_LICH_ID`)
- **Khóa ghép dòng:** `NGAY_CHUYEN_DEN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_PHAN_DOI.NGAY_CHUYEN_DEN` | `PHAM_NHAN_PHAN_DOI.PNPD_NGAY_CHUYEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_PHAN_DOI.MA_PHAN_DOI_DEN` | `PHAM_NHAN_PHAN_DOI.PNPD_PHAN_DOI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_PHAN_DOIS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PHAN_DOI.GHI_CHU` | `PHAM_NHAN_PHAN_DOI.PNPD_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db00-xeploai"></a>

## Xếp loại (`DB00_XepLoai`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_KET_QUA_CAI_TAO` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `XEP_LOAIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NAM_XL`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_KET_QUA_CAI_TAO.NAM_XL` | `XEP_LOAIS.XEP_LOAI_NAM` | Chuẩn hóa giá trị số rồi so. **Khóa ghép dòng.** |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_Q1` | `XEP_LOAIS.XEP_LOAI_QUY_I` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_Q2` | `XEP_LOAIS.XEP_LOAI_QUY_II` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_Q3` | `XEP_LOAIS.XEP_LOAI_QUY_III` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_Q4` | `XEP_LOAIS.XEP_LOAI_QUY_IV` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_DAU` | `XEP_LOAIS.XEP_LOAI_6_THANG_DAU_NAM` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_CUOI` | `XEP_LOAIS.XEP_LOAI_6_THANG_CUOI_NAM` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.MA_XEP_LOAI_CA` | `XEP_LOAIS.XEP_LOAI_CA_NAM` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_XEP_LOAI_CAI_TAOS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KET_QUA_CAI_TAO.GHI_CHU` | `XEP_LOAIS.XEP_LOAI_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db01-giamthoihan"></a>

## Giảm thời hạn (`DB01_GiamThoiHan`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_GIAM_THOI_HAN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `GIAM_THOI_HANS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_XET`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_GIAM_THOI_HAN.NGAY_XET` | `GIAM_THOI_HANS.NGAY_XET` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_GIAM_THOI_HAN.MA_MUC_DN_GIAM_TG` | `GIAM_THOI_HANS.MUC_DE_NGHI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GIAM_THOI_HAN.NHAN_XET_TG` | `GIAM_THOI_HANS.NHAN_XET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GIAM_THOI_HAN.SO_QD_GIAM` | `GIAM_THOI_HANS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GIAM_THOI_HAN.NGAY_QD_GIAM` | `GIAM_THOI_HANS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_GIAM_THOI_HAN.MA_CQ_TOA_QD_GIAM` | `GIAM_THOI_HANS.TOA_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GIAM_THOI_HAN.MA_DP_TOA_QD_GIAM` | `GIAM_THOI_HANS.DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_GIAM_THOI_HAN.MA_MUC_QD_GIAM_TOA_AN` | `GIAM_THOI_HANS.MUC_GIAM_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GIAM_THOI_HAN.NGAY_THA_GIAM_HET_AN` | `GIAM_THOI_HANS.NGAY_THA_GIAM_HET_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_GIAM_THOI_HAN.KQCT_PHIEU_GIAM` | `GIAM_THOI_HANS.KQCT_PHIEU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GIAM_THOI_HAN.KQCT_DS_GIAM` | `GIAM_THOI_HANS.KQCT_DANHSACH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db02-phanloai"></a>

## Phân loại (`DB02_PhanLoai`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_PHAN_LOAI_GIAM_GIU` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PHAN_LOAIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_PHAN_LOAI`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_PHAN_LOAI_GIAM_GIU.NGAY_PHAN_LOAI` | `PHAN_LOAIS.NGAY_PHAN_LOAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_PHAN_LOAI_GIAM_GIU.MA_LOAI_PHAN_LOAI` | `PHAN_LOAIS.LOAI_PHAN_LOAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_PHAN_LOAIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PHAN_LOAI_GIAM_GIU.MA_TU_LOAI` | `PHAN_LOAIS.TU_LOAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_PHAN_LOAI_GIAM_GIUS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PHAN_LOAI_GIAM_GIU.MA_DEN_LOAI` | `PHAN_LOAIS.DEN_LOAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_PHAN_LOAI_GIAM_GIUS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PHAN_LOAI_GIAM_GIU.NGAY_BIEN_BAN` | `PHAN_LOAIS.NGAY_BIEN_BAN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PHAN_LOAI_GIAM_GIU.GHI_CHU` | `PHAN_LOAIS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db03-chuabenhbb"></a>

## Chữa bệnh bắt buộc (`DB03_ChuaBenhBB`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_CHUA_BENH_BAT_BUOC` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `CHUA_BENH_BAT_BUOCS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `QD_SO`, `QD_NGAY`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_CHUA_BENH_BAT_BUOC.QD_SO` | `CHUA_BENH_BAT_BUOCS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_CHUA_BENH_BAT_BUOC.QD_NGAY` | `CHUA_BENH_BAT_BUOCS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_CHUA_BENH_BAT_BUOC.MA_CQ_TOA_AN_QD` | `CHUA_BENH_BAT_BUOCS.CO_QUAN_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUA_BENH_BAT_BUOC.MA_DP_TOA_AN_QD` | `CHUA_BENH_BAT_BUOCS.DIA_PHUONG_QUYET_DINH_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_CHUA_BENH_BAT_BUOC.TU_NGAY` | `CHUA_BENH_BAT_BUOCS.TU_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUA_BENH_BAT_BUOC.MA_BENH_TAT` | `CHUA_BENH_BAT_BUOCS.BENH_TAT_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_BENH_TATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUA_BENH_BAT_BUOC.BENH_TAT` | `CHUA_BENH_BAT_BUOCS.CHI_TIET_BENH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUA_BENH_BAT_BUOC.NOI_CHUA_BENH` | `CHUA_BENH_BAT_BUOCS.NOI_CHUA_BENH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUA_BENH_BAT_BUOC.NGAY_BAT_DAU` | `CHUA_BENH_BAT_BUOCS.NGAY_BAT_DAU` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUA_BENH_BAT_BUOC.NGAY_KET_THUC` | `CHUA_BENH_BAT_BUOCS.NGAY_KET_THUC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |

<a id="db04-suckhoe"></a>

## Thông tin sức khỏe (`DB04_SucKhoe`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_SUC_KHOE_BENH_TAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_SUC_KHOES` (liên kết phạm nhân: `PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `NGAY_KHAM`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_SUC_KHOE_BENH_TAT.NGAY_KHAM` | `PN_SUC_KHOES.SK_NGAY_KHAM` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_SUC_KHOE_BENH_TAT.NOI_KHAM_BENH` | `PN_SUC_KHOES.SK_NOI_KHAM` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_SUC_KHOE_BENH_TAT.KET_LUAN_KHAM_BENH` | `PN_SUC_KHOES.KET_LUAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db05-phamtoimoi"></a>

## Phạm tội mới (`DB05_PhamToiMoi`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_PHAM_TOI_MOI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PHAM_TOI_MOIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_PT_MOI`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_PHAM_TOI_MOI.NGAY_PT_MOI` | `PHAM_TOI_MOIS.NGAY_PHAM_TOI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_PHAM_TOI_MOI.NOI_PT_MOI` | `PHAM_TOI_MOIS.NOI_PHAM_TOI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PHAM_TOI_MOI.MA_TOI_DANH_PTM` | `PHAM_TOI_MOIS.TOI_DANH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TOI_DANHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PHAM_TOI_MOI.HINH_THUC_XL` | `PHAM_TOI_MOIS.HINH_THUC_XU_LY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PHAM_TOI_MOI.GHI_CHU_PTM` | `PHAM_TOI_MOIS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db06-angiam"></a>

## Ân giảm (`DB06_AnGiam`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_QD_AN_GIAM` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `AN_GIAMS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD`, `NGAY_QD`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_QD_AN_GIAM.SO_QD` | `AN_GIAMS.AG_SO_QD_CHU_TICH_NUOC` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_QD_AN_GIAM.NGAY_QD` | `AN_GIAMS.AG_NGAY_QD_CHU_TICH_NUOC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_QD_AN_GIAM.QD_GIAM_TOA_AN_SO` | `AN_GIAMS.AG_SO_QD_TOA_AN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_QD_AN_GIAM.QD_GIAM_TOA_AN_NGAY` | `AN_GIAMS.AG_NGAY_QD_TOA_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_QD_AN_GIAM.MA_LD_AN_GIAM` | `AN_GIAMS.AG_LY_DO_AN_GIAM` | Cột mới là text nhập trực tiếp trên giao diện, không phải ID danh mục; so text sau khi chuẩn hóa khoảng trắng, hoa/thường và Unicode. Chưa tự đổi mã cũ sang tên danh mục. |
| `PN_QD_AN_GIAM.GHI_CHU` | `AN_GIAMS.AG_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db07-tanggiamhp"></a>

## Tăng giảm hình phạt (`DB07_TangGiamHP`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TANG_GIAM_HINH_PHAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TANG_GIAM_HINH_PHATS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD`, `NGAY_QD`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TANG_GIAM_HINH_PHAT.MA_LOAI_TGHP` | `TANG_GIAM_HINH_PHATS.LOAI_TANG_GIAM_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LOAI_TANG_GIAM_HINH_PHATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TANG_GIAM_HINH_PHAT.SO_QD` | `TANG_GIAM_HINH_PHATS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_TANG_GIAM_HINH_PHAT.NGAY_QD` | `TANG_GIAM_HINH_PHATS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TANG_GIAM_HINH_PHAT.MA_CQ_TOA_QD` | `TANG_GIAM_HINH_PHATS.DON_VI_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TANG_GIAM_HINH_PHAT.MA_DP_TOA_QD` | `TANG_GIAM_HINH_PHATS.DIA_PHUONG_QUYET_DINH_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_TANG_GIAM_HINH_PHAT.MA_MUC_THOI_HAN` | `TANG_GIAM_HINH_PHATS.THOI_HAN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TANG_GIAM_HINH_PHAT.GHI_CHU_TGHP` | `TANG_GIAM_HINH_PHATS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db08-khenthuong"></a>

## Khen thưởng (`DB08_KhenThuong`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_KHEN_THUONG` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `KHEN_THUONGS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD_KHEN`, `NGAY_KHEN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_KHEN_THUONG.SO_QD_KHEN` | `KHEN_THUONGS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_KHEN_THUONG.NGAY_KHEN` | `KHEN_THUONGS.NGAY_KHEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_KHEN_THUONG.NGAY_DE_NGHI` | `KHEN_THUONGS.NGAY_DE_NGHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_KHEN_THUONG.NOI_DE_NGHI` | `KHEN_THUONGS.NOI_DE_NGHI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KHEN_THUONG.MA_LY_DO_KT` | `KHEN_THUONGS.MA_LY_DO_KHEN_ID` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_LY_DO_KHENS.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_KHEN_THUONG.LY_DO_KHEN` | `KHEN_THUONGS.LY_DO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KHEN_THUONG.MA_HINH_THUC_KT` | `KHEN_THUONGS.MA_HINH_THUC_KHEN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HINH_THUC_KHEN_THUONGS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KHEN_THUONG.HINH_THUC_KHEN` | `KHEN_THUONGS.HINH_THUC_KHEN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KHEN_THUONG.GHI_CHU` | `KHEN_THUONGS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db09-kyluat"></a>

## Kỷ luật (`DB09_KyLuat`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_KL_KY_LUAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `KY_LUATS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD_KL`, `NGAY_QD_KL`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_KL_KY_LUAT.SO_QD_KL` | `KY_LUATS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_KL_KY_LUAT.NGAY_QD_KL` | `KY_LUATS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_KL_KY_LUAT.SO_BB_KL` | `KY_LUATS.SO_BIEN_BAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.NGAY_BB_KL` | `KY_LUATS.NGAY_BIEN_BAN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_KL_KY_LUAT.NOI_DUNG_VI_PHAM` | `KY_LUATS.NOI_DUNG_VI_PHAM` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.NGAY_DE_NGHI` | `KY_LUATS.NGAY_DE_NGHI_KY_LUAT` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_KL_KY_LUAT.NOI_DE_NGHI` | `KY_LUATS.NGUOI_DE_NGHI_KY_LUAT` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.MA_LY_DO_KL` | `KY_LUATS.MA_LY_DO_KY_LUAT_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LY_DO_KY_LUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KL_KY_LUAT.LY_DO_KL` | `KY_LUATS.LY_DO_KY_LUAT_CU_THE` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.MA_HINH_THUC_KL` | `KY_LUATS.MA_HINH_THUC_KY_LUAT_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HINH_THUC_KY_LUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_KL_KY_LUAT.HINH_THUC_KL` | `KY_LUATS.HINH_THUC_KY_LUAT_CU_THE` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.SO_QD_TB` | `KY_LUATS.SO_QUYET_DINH_TIEN_BO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_KL_KY_LUAT.NGAY_QD_TB` | `KY_LUATS.NGAY_QUYET_DINH_TIEN_BO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_KL_KY_LUAT.NGAY_DN_TB` | `KY_LUATS.NGAY_DE_NGHI_TIEN_BO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_KL_KY_LUAT.NOI_DE_NGHI_TB` | `KY_LUATS.NOI_DE_NGHI_TIEN_BO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db10-giamrieng"></a>

## Giam riêng (`DB10_GiamRieng`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_GR_GIAM_RIENG` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_GIAM_RIENGS` (liên kết phạm nhân: `GR_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `SO_QD_GR`, `NGAY_QD_GR`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_GR_GIAM_RIENG.MA_LENH_GIAM_RIENG` | `PN_GIAM_RIENGS.GR_LOAI_QUYET_DINH` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LENH_GIAM_RIENGS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GR_GIAM_RIENG.SO_QD_GR` | `PN_GIAM_RIENGS.GR_SO_QUYET_DINH_GIAM_RIENG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_GR_GIAM_RIENG.NGAY_QD_GR` | `PN_GIAM_RIENGS.GR_NGAY_QUYET_DINH_GIAM_RIENG` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_GR_GIAM_RIENG.MA_LY_DO_GR` | `PN_GIAM_RIENGS.GR_LY_DO` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LY_DO_GIAM_RIENG_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GR_GIAM_RIENG.LY_DO_GIAM_RIENG` | `PN_GIAM_RIENGS.GR_CHI_TIET_LY_DO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GR_GIAM_RIENG.MA_MUC_THOI_HAN_GR` | `PN_GIAM_RIENGS.GR_THOI_HAN_GIAM_RIENG` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_GR_GIAM_RIENG.NGAY_BD_GR` | `PN_GIAM_RIENGS.GR_NGAY_BAT_DAU` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_GR_GIAM_RIENG.SO_QD_RA` | `PN_GIAM_RIENGS.GR_SO_QUYET_DINH_RA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GR_GIAM_RIENG.NGAY_QD_RA` | `PN_GIAM_RIENGS.GR_NGAY_QUYET_DINH_RA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_GR_GIAM_RIENG.NGAY_KT_GR` | `PN_GIAM_RIENGS.GR_NGAY_KETTHUC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_GR_GIAM_RIENG.GHI_CHU_GR` | `PN_GIAM_RIENGS.GR_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_GR_GIAM_RIENG.LY_DO_DUA_RA` | `PN_GIAM_RIENGS.GR_LY_DO_DUA_RA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db11-trontrai"></a>

## Trốn trại (`DB11_TronTrai`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TT_TRON_TRAI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TRON_TRAIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_TRON`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TT_TRON_TRAI.NGAY_TRON` | `TRON_TRAIS.NGAY_TRON` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TT_TRON_TRAI.MA_TH_TRON` | `TRON_TRAIS.TRUONG_HOP_TRON_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_TRONS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TT_TRON_TRAI.NOI_TRON` | `TRON_TRAIS.NOI_TRON` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TT_TRON_TRAI.SO_QD_TN` | `TRON_TRAIS.SO_TRUY_NA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TT_TRON_TRAI.NGAY_QD_TN` | `TRON_TRAIS.NGAY_TRUY_NA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TT_TRON_TRAI.SO_QD_DN` | `TRON_TRAIS.QUYET_DINH_TRUY_NA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TT_TRON_TRAI.NGAY_QD_DN` | `TRON_TRAIS.NGAY_DINH_NA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TT_TRON_TRAI.NGAY_BAT_LAI` | `TRON_TRAIS.NGAY_BAT_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TT_TRON_TRAI.DON_VI_BAT` | `TRON_TRAIS.DONVI_BAT_LAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TT_TRON_TRAI.NOI_BAT_LAI` | `TRON_TRAIS.NOI_BAT_LAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TT_TRON_TRAI.MA_TH_BAT` | `TRON_TRAIS.TRUONG_HOP_BAT_LAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_BAT_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TT_TRON_TRAI.MA_HTXL_BAT` | `TRON_TRAIS.HINH_THUC_XU_LY_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HINH_THUC_XU_LY_BATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TT_TRON_TRAI.MA_TINH_TRANG_TRON` | `TRON_TRAIS.TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_TRONS.ID` → cột mã `*_MA`, rồi so mã. |

<a id="db12-trichxuat"></a>

## Trích xuất (`DB12_TrichXuat`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TX_TRICH_XUAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TRICH_XUATS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_LENH_TX`, `NGAY_LENH_TX`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TX_TRICH_XUAT.MA_LENH_TX` | `TRICH_XUATS.TX_LOAI_LENH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LOAI_QUYET_DINH_TRICH_XUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.SO_LENH_TX` | `TRICH_XUATS.TX_SO_LENH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_TX_TRICH_XUAT.NGAY_LENH_TX` | `TRICH_XUATS.TX_NGAY_RA_LENH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TX_TRICH_XUAT.SO_CV_DN_TX` | `TRICH_XUATS.TX_SO_DE_NGHI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TX_TRICH_XUAT.NGAY_CV_DN_TX` | `TRICH_XUATS.TX_NGAY_DE_NGHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TX_TRICH_XUAT.MA_CQ_DN_TX` | `TRICH_XUATS.TX_DON_VI_DE_NGHI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.MA_DP_DN_TX` | `TRICH_XUATS.TX_DIA_PHUONG_DE_NGHI_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_TX_TRICH_XUAT.MA_LY_DO_TX` | `TRICH_XUATS.TX_LY_DO_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LY_DO_TRICH_XUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.LY_DO_TX` | `TRICH_XUATS.TX_LY_DO_CU_THE` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TX_TRICH_XUAT.MA_MUC_THOI_HAN_TX` | `TRICH_XUATS.TX_THOI_HAN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.TU_NGAY_TX` | `TRICH_XUATS.TX_TU_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TX_TRICH_XUAT.NGAY_TX` | `TRICH_XUATS.TX_NGAY_TRICH_XUAT` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TX_TRICH_XUAT.NGAY_TRA_LAI` | `TRICH_XUATS.TX_NGAY_TRA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TX_TRICH_XUAT.MA_CQ_TX_VE` | `TRICH_XUATS.TX_DON_VI_VE_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.MA_DP_TX_VE` | `TRICH_XUATS.TX_DIA_PHUONG_VE_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_TX_TRICH_XUAT.MA_TINH_TRANG_TX` | `TRICH_XUATS.TX_TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_TRICH_XUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.MA_BAN_GIAO_TX` | `TRICH_XUATS.TX_BAN_GIAO_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_BAN_GIAO_TRICH_XUATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TX_TRICH_XUAT.GHI_CHU_TX` | `TRICH_XUATS.TX_THONG_TIN_KHAC` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db13-tamdinhchi"></a>

## Tạm đình chỉ (`DB13_TamDinhChi`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TDC_TAM_DINH_CHI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TAM_DINH_CHIS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD`, `NGAY_QD`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TDC_TAM_DINH_CHI.MA_LENH_TDC` | `TAM_DINH_CHIS.LOAI_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LOAI_QUYET_DINH_TAM_DINH_CHIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TDC_TAM_DINH_CHI.SO_QD` | `TAM_DINH_CHIS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_TDC_TAM_DINH_CHI.NGAY_QD` | `TAM_DINH_CHIS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TDC_TAM_DINH_CHI.MA_CQ_CUA_TOA` | `TAM_DINH_CHIS.TOA_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TDC_TAM_DINH_CHI.MA_DP_CUA_TOA` | `TAM_DINH_CHIS.DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_TDC_TAM_DINH_CHI.MA_LY_DO_TDC` | `TAM_DINH_CHIS.LY_DO_SUC_KHOE_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LY_DO_TAM_DINH_CHIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TDC_TAM_DINH_CHI.LY_DO_TDC` | `TAM_DINH_CHIS.LY_DO_CHI_TIET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TDC_TAM_DINH_CHI.MA_MUC_THOI_HAN_TDC` | `TAM_DINH_CHIS.THOI_HAN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TDC_TAM_DINH_CHI.TU_NGAY` | `TAM_DINH_CHIS.TU_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TDC_TAM_DINH_CHI.NOI_VE_XA` | `TAM_DINH_CHIS.NOI_VE_XA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_TDC_TAM_DINH_CHI.MA_DP_NOI_VE` | `TAM_DINH_CHIS.NOI_VE_DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_TDC_TAM_DINH_CHI.NGAY_TDC` | `TAM_DINH_CHIS.NGAY_TDC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TDC_TAM_DINH_CHI.NGAY_LAI` | `TAM_DINH_CHIS.NGAY_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TDC_TAM_DINH_CHI.NGAY_DE_NGHI` | `TAM_DINH_CHIS.NGAY_DE_NGHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_TDC_TAM_DINH_CHI.MA_TINH_TRANG_TDC` | `TAM_DINH_CHIS.TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TINH_TRANG_TAM_DINH_CHIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_TDC_TAM_DINH_CHI.NHAN_XET` | `TAM_DINH_CHIS.NHAN_XET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db14-hoantha"></a>

## Hoãn thi hành án (`DB14_HoanTHA`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_HOAN_THI_HANH_AN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `HOAN_THI_HANH_ANS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD_HOAN`, `NGAY_QD_HOAN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_HOAN_THI_HANH_AN.SO_QD_HOAN` | `HOAN_THI_HANH_ANS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_HOAN_THI_HANH_AN.NGAY_QD_HOAN` | `HOAN_THI_HANH_ANS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_HOAN_THI_HANH_AN.MA_CQ_TOA_QD_HOAN` | `HOAN_THI_HANH_ANS.TOA_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HOAN_THI_HANH_AN.MA_DP_TOA_QD_HOAN` | `HOAN_THI_HANH_ANS.DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_HOAN_THI_HANH_AN.LY_DO_HOAN` | `HOAN_THI_HANH_ANS.LY_DO_HOAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_HOAN_THI_HANH_AN.NGAY_HOAN` | `HOAN_THI_HANH_ANS.NGAY_HOAN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HOAN_THI_HANH_AN.DC_VE_CU_TRU` | `HOAN_THI_HANH_ANS.NOI_CU_TRU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_HOAN_THI_HANH_AN.NGAY_THI_HANH_AN` | `HOAN_THI_HANH_ANS.NGAY_THI_HANH_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HOAN_THI_HANH_AN.GHI_CHU_HTHA` | `HOAN_THI_HANH_ANS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db15-mienhp"></a>

## Miễn hình phạt (`DB15_MienHP`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_MIEN_HINH_PHAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `MIEN_HINH_PHATS` (liên kết phạm nhân: `PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `QD_MIEN_SO`, `QD_MIEN_NGAY`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_MIEN_HINH_PHAT.CV_DN_MIEN_SO` | `MIEN_HINH_PHATS.MHP_SO_DE_NGHI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_MIEN_HINH_PHAT.CV_DN_MIEN_NGAY` | `MIEN_HINH_PHATS.MHP_NGAY_DE_NGHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_MIEN_HINH_PHAT.QD_MIEN_SO` | `MIEN_HINH_PHATS.MHP_SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_MIEN_HINH_PHAT.QD_MIEN_NGAY` | `MIEN_HINH_PHATS.MHP_NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_MIEN_HINH_PHAT.MA_CQ_TOA_QD_MIEN` | `MIEN_HINH_PHATS.MHP_TOA_QUYET_DINH` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_MIEN_HINH_PHAT.MA_DP_TOA_QD_MIEN` | `MIEN_HINH_PHATS.MHP_DIA_PHUONG_QD` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_MIEN_HINH_PHAT.MA_TRUONG_HOP_MIEN` | `MIEN_HINH_PHATS.MHP_TRUONG_HOP_MIEN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_MIEN_HINH_PHATS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_MIEN_HINH_PHAT.MA_TOI_DANH_MIEN` | `MIEN_HINH_PHATS.MHP_TOI_DANH_MIEN` | Tách danh sách; DB cũ coi là mã, DB mới coi là ID; tra `DM_TOI_DANHS.ID` → mã `*_MA` từng phần tử, sắp xếp rồi so. |
| `PN_MIEN_HINH_PHAT.NGAY_TRA_TU_DO` | `MIEN_HINH_PHATS.MHP_NGAY_TU_DO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_MIEN_HINH_PHAT.DANH_GIA_CAI_TAO` | `MIEN_HINH_PHATS.MHP_NHAN_XET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db16-huyan"></a>

## Hủy án (`DB16_HuyAn`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_HUY_AN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `HUY_ANS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_QD_HUY`, `NGAY_QD_HUY`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_HUY_AN.SO_QD_HUY` | `HUY_ANS.SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_HUY_AN.NGAY_QD_HUY` | `HUY_ANS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_HUY_AN.MA_CQ_TOA_HUY` | `HUY_ANS.TOA_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HUY_AN.MA_DP_TOA_HUY` | `HUY_ANS.DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_HUY_AN.LY_DO_HUY` | `HUY_ANS.LY_DO_HUY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_HUY_AN.NGAY_TRA_TUDO` | `HUY_ANS.NGAY_TRA_TU_DO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HUY_AN.NGAY_LAI` | `HUY_ANS.NGAY_TRO_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HUY_AN.GHI_CHU` | `HUY_ANS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db17-tiencongldsx"></a>

## Tiền công lao động sản xuất (`DB17_TienCongLDSX`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TIEN_CONG_SX` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TIEN_LAO_DONG_SAN_XUATS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NAM_SX`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TIEN_CONG_SX.NAM_SX` | `TIEN_LAO_DONG_SAN_XUATS.NAM` | Chuẩn hóa giá trị số rồi so. **Khóa ghép dòng.** |
| `PN_TIEN_CONG_SX.TIEN_Q1` | `TIEN_LAO_DONG_SAN_XUATS.TIEN_Q1` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_CONG_SX.TIEN_Q2` | `TIEN_LAO_DONG_SAN_XUATS.TIEN_Q2` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_CONG_SX.TIEN_Q3` | `TIEN_LAO_DONG_SAN_XUATS.TIEN_Q3` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_CONG_SX.TIEN_Q4` | `TIEN_LAO_DONG_SAN_XUATS.TIEN_Q4` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_CONG_SX.TIEN_KHAC` | `TIEN_LAO_DONG_SAN_XUATS.TIEN_KHAC` | Chuẩn hóa giá trị số rồi so. |
| `PN_TIEN_CONG_SX.GHI_CHU` | `TIEN_LAO_DONG_SAN_XUATS.GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt01-ratrai"></a>

## Ra trại (`KT01_RaTrai`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_RA_TRAI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_KET_THUC_RA_TRAIS` (liên kết phạm nhân: `KTRT_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `NGAY_THA`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_RA_TRAI.MA_TH_THA` | `PN_KET_THUC_RA_TRAIS.KTRT_TRUONG_HOP_THA_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_THAS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_RA_TRAI.NGAY_THA` | `PN_KET_THUC_RA_TRAIS.KTRT_NGAY_THA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_RA_TRAI.NGAY_TRINH_DIEN` | `PN_KET_THUC_RA_TRAIS.KTRT_NGAY_TRINH_DIEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_RA_TRAI.GHI_CHU` | `PN_KET_THUC_RA_TRAIS.KTRT_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt02-chet"></a>

## Chết (`KT02_Chet`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_PNC_CHET` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_KET_THUC_CHETS` (liên kết phạm nhân: `KTC_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** Chưa khai báo khóa dòng riêng

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_PNC_CHET.NGAY_CHET` | `PN_KET_THUC_CHETS.KTC_NGAY_CHET` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PNC_CHET.MA_TH_CHET` | `PN_KET_THUC_CHETS.KTC_DM_TRUONG_HOP_CHET_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_CHETS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PNC_CHET.MA_NGUYEN_NHAN_CHET` | `PN_KET_THUC_CHETS.KTC_NGUYEN_NHAN_CHET_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_NGUYEN_NHAN_CHETS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PNC_CHET.NGUYEN_NHAN_CHET` | `PN_KET_THUC_CHETS.KTC_NGUYEN_NHAN_CHET_CHI_TIET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NOI_CHET` | `PN_KET_THUC_CHETS.KTC_NOI_CHET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.DIEN_BIEN_CHET` | `PN_KET_THUC_CHETS.KTC_DIEN_BIEN_CHET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NGAY_BDDT` | `PN_KET_THUC_CHETS.KTC_TU_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PNC_CHET.NGAY_KTDT` | `PN_KET_THUC_CHETS.KTC_DEN_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PNC_CHET.NOI_DIEU_TRI` | `PN_KET_THUC_CHETS.KTC_NOI_DIEU_TRI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NGAY_CHON` | `PN_KET_THUC_CHETS.KTC_NGAY_CHON` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PNC_CHET.MA_HINH_THUC_CHON` | `PN_KET_THUC_CHETS.KTC_DM_HINH_THUC_CHON_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HINH_THUC_CHONS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_PNC_CHET.NOI_CHON` | `PN_KET_THUC_CHETS.KTC_NOI_CHON` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.SO_MO` | `PN_KET_THUC_CHETS.KTC_SO_MO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.HANG_MO` | `PN_KET_THUC_CHETS.KTC_HANG_MO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.DAC_DIEM_MO` | `PN_KET_THUC_CHETS.KTC_DAC_DIEM_MO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.TAI_SAN_CON` | `PN_KET_THUC_CHETS.KTC_TAI_SAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NGUOI_GIU_TAI_SAN` | `PN_KET_THUC_CHETS.KTC_NGUOI_GIU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NGAY_BOC_MO` | `PN_KET_THUC_CHETS.KTC_NGAY_BOC_MO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_PNC_CHET.GHI_CHU_PNC` | `PN_KET_THUC_CHETS.KTC_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NGUOI_NHAN_THI_THE` | `PN_KET_THUC_CHETS.KTC_NGUOI_NHAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.DC_NGUOI_NHAN_THI_THE` | `PN_KET_THUC_CHETS.KTC_DIA_CHI_NGUOI_NHAN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.QUAN_HE` | `PN_KET_THUC_CHETS.KTC_QUAN_HE` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NOI_HOA_TANG` | `PN_KET_THUC_CHETS.KTC_NOI_HOA_TANG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_PNC_CHET.NOI_GUI_HAI_COT` | `PN_KET_THUC_CHETS.KTC_NOI_GUI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt03-thacodk"></a>

## Tha có điều kiện (`KT03_ThaCoDK`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_THA_CO_DK` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `THA_CO_DIEU_KIENS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_XET_TT`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_THA_CO_DK.NGAY_XET_TT` | `THA_CO_DIEU_KIENS.NGAY_XET` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_THA_CO_DK.MA_DUOC_TT` | `THA_CO_DIEU_KIENS.TINH_TRANG_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_THA_CO_DIEU_KIENS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_THA_CO_DK.NHAN_XET_TT` | `THA_CO_DIEU_KIENS.NHAN_XET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_THA_CO_DK.SO_QD_TT` | `THA_CO_DIEU_KIENS.SO_QUYET_DINH_THA` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_THA_CO_DK.NGAY_QD_TT` | `THA_CO_DIEU_KIENS.NGAY_QUYET_DINH_THA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.MA_CQ_TOA_QD_TT` | `THA_CO_DIEU_KIENS.TOA_QUYET_DINH_THA_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_THA_CO_DK.MA_DP_TOA_QD_TT` | `THA_CO_DIEU_KIENS.DIA_PHUONG_QUYET_DINH_THA_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_THA_CO_DK.NGAY_THA_TT` | `THA_CO_DIEU_KIENS.NGAY_THA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.NGAY_TRINH_DIEN_TT` | `THA_CO_DIEU_KIENS.NGAY_TRINH_DIEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.NGAY_QD_TRO_LAI` | `THA_CO_DIEU_KIENS.NGAY_QUYET_DINH_TRO_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.SO_QD_TL` | `THA_CO_DIEU_KIENS.SO_QUYET_DINH_LAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_THA_CO_DK.NGAY_QD_TL` | `THA_CO_DIEU_KIENS.NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.MA_CQ_TOA_QD_TL` | `THA_CO_DIEU_KIENS.TOA_QUYET_DINH_LAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_THA_CO_DK.MA_DP_TOA_QD_TL` | `THA_CO_DIEU_KIENS.DIA_PHUONG_QUYET_DINH_LAI_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_THA_CO_DK.MA_LY_DO_TRO_LAI` | `THA_CO_DIEU_KIENS.LY_DO_TRO_LAI_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LY_DO_TRO_LAIES.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_THA_CO_DK.LY_DO_TROLAI_CHITIET` | `THA_CO_DIEU_KIENS.LY_DO_CHI_TIET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_THA_CO_DK.NGAY_TRO_LAI_TRAI` | `THA_CO_DIEU_KIENS.NGAY_BAT_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_THA_CO_DK.KQCT_PHIEU_TT` | `THA_CO_DIEU_KIENS.QQCT_PHIEU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt04-dacxa"></a>

## Đặc xá (`KT04_DacXa`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_DX_DAC_XA` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_DAC_XAS` (liên kết phạm nhân: `PNLAI_LICH_ID`)
- **Khóa ghép dòng:** `NGAY_XET_DX`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_DX_DAC_XA.NGAY_XET_DX` | `PN_DAC_XAS.DX_NGAY_XET` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_DX_DAC_XA.MA_DUOC_DAC_XA` | `PN_DAC_XAS.DX_TINH_TRANG_DAC_XA` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_DUOC_DAC_XAS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_DX_DAC_XA.Y_KIEN_DOI_PN` | `PN_DAC_XAS.DX_YKIEN_DOI_PN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DX_DAC_XA.NHAN_XET_DE_NGHI` | `PN_DAC_XAS.DX_NHAN_XET_TRAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DX_DAC_XA.NGAY_THA_DX` | `PN_DAC_XAS.DX_NGAY_THA` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_DX_DAC_XA.NGAY_TRINH_DIEN_DX` | `PN_DAC_XAS.DX_NGAY_TRINH_DIEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_DX_DAC_XA.KQCT_PHIEU_DX` | `PN_DAC_XAS.DX_KQCT_PHIEU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_DX_DAC_XA.KQCT_DS_DX` | `PN_DAC_XAS.DX_KQCT_DS` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt05-chuyengiao"></a>

## Chuyển giao (`KT05_ChuyenGiao`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_CHUYEN_GIAO` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_CHUYEN_GIAO` (liên kết phạm nhân: `PNCG_LAI_LICH_ID`)
- **Khóa ghép dòng:** `SO_QD_CG`, `NGAY_QD_CG`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_CHUYEN_GIAO.SO_QD_CG` | `PN_CHUYEN_GIAO.PNCG_SO_QDCG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_CHUYEN_GIAO.NGAY_QD_CG` | `PN_CHUYEN_GIAO.PNCG_NGAY_QDCG` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_CHUYEN_GIAO.MA_CQ_TOA_CG` | `PN_CHUYEN_GIAO.PNCG_TOA_QDCG` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_GIAO.MA_DP_TOA_CG` | `PN_CHUYEN_GIAO.PNCG_DIA_PHUONG_QDCGID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_CHUYEN_GIAO.SO_QD_QDTH_CG` | `PN_CHUYEN_GIAO.PNCG_SO_QDTHQDCG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUYEN_GIAO.NGAY_QD_QDTH_CG` | `PN_CHUYEN_GIAO.PNCG_NGAY_QDTHQDCG` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUYEN_GIAO.MA_CQ_TOA_QDTH_CG` | `PN_CHUYEN_GIAO.PNCG_TOA_QDTHQDCG` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_GIAO.MA_DP_TOA_QDTH_CG` | `PN_CHUYEN_GIAO.PNCG_DIA_PHUONG_THQDCGID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_CHUYEN_GIAO.MA_QUOC_GIA_CG` | `PN_CHUYEN_GIAO.PNCG_NUOC_CHUYEN_GIAO_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_QUOC_TICHS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_GIAO.NGAY_CHUYEN_GIAO` | `PN_CHUYEN_GIAO.PNCG_NGAY_CHUYEN_GIAO` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUYEN_GIAO.GHI_CHU` | `PN_CHUYEN_GIAO.PNCG_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="kt06-chuyentrai"></a>

## Chuyển trại (`KT06_ChuyenTrai`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_CHUYEN_TRAI` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PHAM_NHAN_CHUYEN_TRAI` (liên kết phạm nhân: `PNCT_LAI_LICH_ID`)
- **Khóa ghép dòng:** `SO_QD_CHUYEN`, `NGAY_QD_CHUYEN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_CHUYEN_TRAI.SO_QD_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_SO_QDDIEU_CHUYEN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_CHUYEN_TRAI.NGAY_QD_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_NGAY_QDCHUYEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_CHUYEN_TRAI.MA_TRUONG_HOP_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_TRUONG_HOP_CHUYEN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRUONG_HOP_CHUYEN_TRAIS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_TRAI.NGAY_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_NGAY_CHUYEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUYEN_TRAI.MA_CQ_TRAI_DEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_TRAI_DEN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_TRAI_GIAMS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_TRAI.MA_DP_TRAI_DEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_TRAI_DEN_DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_CHUYEN_TRAI.GHI_CHU` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUYEN_TRAI.CV_DN_CHUYEN_SO` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_CONG_VAN_DE_NGHI_SO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUYEN_TRAI.CV_DN_CHUYEN_NGAY` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_CONG_VAN_DE_NGHI_NGAY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUYEN_TRAI.MA_CQ_DN_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_CO_QUAN_DE_NGHI_CHUYEN_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_CHUYEN_TRAI.MA_DP_DN_CHUYEN` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_CO_QUAN_DE_NGHI_DIA_PHUONG_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_CHUYEN_TRAI.NGAY_TRO_LAI` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_NGAY_TRO_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_CHUYEN_TRAI.QD_TRO_LAI_SO` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_SO_QDDIEU_CHUYEN_LAI` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_CHUYEN_TRAI.QD_TRO_LAI_NGAY` | `PHAM_NHAN_CHUYEN_TRAI.PNCT_NGAY_QDDIEU_CHUYEN_LAI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |

<a id="kt07-nopluu"></a>

## Nộp lưu hồ sơ (`KT07_NopLuu`)

- **Cụm:** `KET_THUC`
- **Bảng DB cũ:** `PN_HSPN_NOP_LUU` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `NOP_LUUS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `SO_DANG_KY`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_HSPN_NOP_LUU.HO_TEN_CB` | `NOP_LUUS.CAN_BO_NOP_LUU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_HSPN_NOP_LUU.CAP_BAC_CB` | `NOP_LUUS.CAP_BAC` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CAP_BACS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HSPN_NOP_LUU.CHUC_VU_CB` | `NOP_LUUS.CHUC_VU` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CHUC_VUS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HSPN_NOP_LUU.SO_DANG_KY` | `NOP_LUUS.SO_DANG_KY` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_HSPN_NOP_LUU.NGAY_LAP` | `NOP_LUUS.NGAY_DANG_KY` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HSPN_NOP_LUU.SO_DK_LUU_TRU` | `NOP_LUUS.SO_LUU_TRU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_HSPN_NOP_LUU.NOP_LUU_NGAY` | `NOP_LUUS.NGAY_NOP_LUU` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HSPN_NOP_LUU.MA_LOAI_TG_BQ` | `NOP_LUUS.THOI_GIAN_BAO_QUAN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_LOAI_THOI_GIAN_BAO_QUAN_HO_SO_PHAM_NHANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HSPN_NOP_LUU.SO_NAM_BAO_QUAN` | `NOP_LUUS.SO_NAM_BAO_QUAN` | Chuẩn hóa giá trị số rồi so. |
| `PN_HSPN_NOP_LUU.NGAY_KET_THUC_HS` | `NOP_LUUS.NGAY_KET_THUC` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_HSPN_NOP_LUU.BQ_DEN_NAM` | `NOP_LUUS.BAO_QUAN_DEN_NAM` | Chuẩn hóa giá trị số rồi so. |

<a id="ll12-tnds"></a>


## Trách nhiệm dân sự, HPBS (`LL12_TNDS`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_HPBS_HINH_PHAT` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_HINH_PHAT_BO_SUNGS` (liên kết phạm nhân: `HPBS_MA_PHAM_NHAN`)
- **Khóa ghép dòng:** `MA_HINH_PHAT`, `MA_MUC_THOI_HAN`, `TONG_TIEN_PHAT`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_HPBS_HINH_PHAT.MA_HINH_PHAT` | `PN_HINH_PHAT_BO_SUNGS.HPBS_HINH_PHAT` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HINH_PHAT_BO_SUNGS.ID` → cột mã `*_MA`, rồi so mã. **Khóa ghép dòng.** |
| `PN_HPBS_HINH_PHAT.MA_MUC_THOI_HAN` | `PN_HINH_PHAT_BO_SUNGS.HPBS_THOI_HAN` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_MA_THOI_GIANS.ID` → cột mã `*_MA`, rồi so mã. **Khóa ghép dòng.** |
| `PN_HPBS_HINH_PHAT.TONG_TIEN_PHAT` | `PN_HINH_PHAT_BO_SUNGS.HPBS_TONG_TIEN_PHAT` | Chuẩn hóa giá trị số rồi so. **Khóa ghép dòng.** |
| `PN_HPBS_HINH_PHAT.MA_HE_SO_TIEN` | `PN_HINH_PHAT_BO_SUNGS.HPBS_HE_SO` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_HE_SO_TIENS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HPBS_HINH_PHAT.MA_GHI_CHU_HPBS` | `PN_HINH_PHAT_BO_SUNGS.HPBS_GHI_CHU` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_GHI_CHU_HINH_PHAT_BO_SUNGS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_HPBS_HINH_PHAT.GHI_CHU_HPBS_HP` | `PN_HINH_PHAT_BO_SUNGS.HPBS_GHI_CHU_CHI_TIET` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll11b-phanbuong"></a>

## Phân buồng (`LL11b_PhanBuong`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_PHAN_BUONG` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PHAM_NHAN_PHAN_BUONG` (liên kết phạm nhân: `PNPB_LAI_LICH_ID`)
- **Khóa ghép dòng:** `NGAY_CHUYEN`, `SO_HIEU_BUONG`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_PHAN_BUONG.NGAY_CHUYEN` | `PHAM_NHAN_PHAN_BUONG.PNPB_NGAY_CHUYEN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_PHAN_BUONG.SO_HIEU_BUONG` | `PHAM_NHAN_PHAN_BUONG.PNPB_SO_BUONG` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_PHAN_BUONG.GHI_CHU` | `PHAM_NHAN_PHAN_BUONG.PNPB_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="ll06b-qdthihanhankhac"></a>

## Quyết định thi hành án khác (`LL06b_QDThiHanhAnKhac`)

- **Cụm:** `LAI_LICH`
- **Bảng DB cũ:** `PN_QD_THI_HANH_AN` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `PN_QUYET_DINH_BAN_AN_KHACS` (liên kết phạm nhân: `QDBAK_PN_LAI_LICH_ID`)
- **Khóa ghép dòng:** `SO_QDTH_AN`, `NGAY_QDTH_AN`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_QD_THI_HANH_AN.SO_QDTH_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_SO_QUYET_DINH` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |
| `PN_QD_THI_HANH_AN.NGAY_QDTH_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_NGAY_QUYET_DINH` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_QD_THI_HANH_AN.MA_CQ_TOA_QDTH_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_QUYET_DINH_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_QD_THI_HANH_AN.MA_DP_TOA_QDTH_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_QUYET_DINH_DP_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_QD_THI_HANH_AN.SO_BAN_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_SO_BAN_AN` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |
| `PN_QD_THI_HANH_AN.NGAY_BAN_AN` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_NGAY_BAN_AN` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. |
| `PN_QD_THI_HANH_AN.MA_CQ_TOA_XU` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_XU_ID` | DB cũ lưu mã; DB mới lưu ID. Tra `DM_CO_QUANS.ID` → cột mã `*_MA`, rồi so mã. |
| `PN_QD_THI_HANH_AN.MA_DP_TOA_XU` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_TOA_XU_DP_ID` | Mã tỉnh cũ → `MAPPING_PROVINCE` → `DM_TINH_THANH_PHO.TTP_MA` → ID; so với ID tỉnh DB mới. |
| `PN_QD_THI_HANH_AN.GHI_CHU_QDTHA` | `PN_QUYET_DINH_BAN_AN_KHACS.QDBAK_GHI_CHU` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. |

<a id="db17b-tienchildsx"></a>

## Tiền chi lao động sản xuất (`DB17b_TienChiLDSX`)

- **Cụm:** `DIEN_BIEN`
- **Bảng DB cũ:** `PN_TIEN_CHI_TIEU` (liên kết phạm nhân: `PN_ID`)
- **Bảng DB mới:** `TIEN_CHI_LAO_DONG_SAN_XUATS` (liên kết phạm nhân: `PHAM_NHAN_ID`)
- **Khóa ghép dòng:** `NGAY_CHI`, `SO_TIEN_CHI`, `MUC_DICH`

| DB cũ | DB mới | Logic chuyển / đối chiếu |
|---|---|---|
| `PN_TIEN_CHI_TIEU.NGAY_CHI` | `TIEN_CHI_LAO_DONG_SAN_XUATS.NGAY_CHI` | Chuẩn hóa ngày về `YYYY-MM-DD` rồi so. **Khóa ghép dòng.** |
| `PN_TIEN_CHI_TIEU.SO_TIEN_CHI` | `TIEN_CHI_LAO_DONG_SAN_XUATS.SO_TIEN` | Chuẩn hóa giá trị số rồi so. **Khóa ghép dòng.** |
| `PN_TIEN_CHI_TIEU.MUC_DICH` | `TIEN_CHI_LAO_DONG_SAN_XUATS.LY_DO` | Chuẩn hóa khoảng trắng, không phân biệt hoa/thường rồi so nội dung. **Khóa ghép dòng.** |

