"""Whitelist for institution/court FK and its province FK in the current DB."""

# Each entry is an explicitly paired FK: a row is eligible only if COURT_COLUMN
# currently contains the ID resolved from CQ_MA_CU in the mapping CSV.
PAIRS = [
    ("Thi hành án - Cơ quan bắt", "PN_THI_HANH_AN", "THA_CO_QUAN_BAT_ID", "THA_DIA_PHUONG_CO_QUAN_BAT_ID"),
    ("Thi hành án - Tòa quyết định", "PN_THI_HANH_AN", "THA_TOA_QD_ID", "THA_DIA_PHUONG_TOA_QD_THA_ID"),
    ("Thi hành án - Đơn vị đề nghị", "PN_THI_HANH_AN", "THA_DON_VI_DE_NGHI_ID", "THA_DIA_PHUONG_DON_VI_DE_NGHI_ID"),
    ("Thi hành án - Cơ quan lập", "PN_THI_HANH_AN", "THA_CO_QUAN_LAP_ID", "THA_DIA_PHUONG_DON_CO_QUAN_LAP_ID"),
    ("Bản án khác - Tòa xử", "PN_BAN_AN_KHACS", "BAK_TOA_XU_ID", "BAK_TOA_XU_DP_ID"),
    ("Giảm thời hạn - Tòa quyết định", "GIAM_THOI_HANS", "TOA_QUYET_DINH_ID", "DIA_PHUONG_ID"),
    ("Chữa bệnh bắt buộc - Cơ quan quyết định", "CHUA_BENH_BAT_BUOCS", "CO_QUAN_QUYET_DINH_ID", "DIA_PHUONG_QUYET_DINH_ID"),
    ("Tăng giảm hình phạt - Đơn vị quyết định", "TANG_GIAM_HINH_PHATS", "DON_VI_QUYET_DINH_ID", "DIA_PHUONG_QUYET_DINH_ID"),
    ("Trích xuất - Đơn vị đề nghị", "TRICH_XUATS", "TX_DON_VI_DE_NGHI_ID", "TX_DIA_PHUONG_DE_NGHI_ID"),
    ("Trích xuất - Đơn vị về", "TRICH_XUATS", "TX_DON_VI_VE_ID", "TX_DIA_PHUONG_VE_ID"),
    ("Tạm đình chỉ - Tòa quyết định", "TAM_DINH_CHIS", "TOA_QUYET_DINH_ID", "DIA_PHUONG_ID"),
    ("Hoãn thi hành án - Tòa quyết định", "HOAN_THI_HANH_ANS", "TOA_QUYET_DINH_ID", "DIA_PHUONG_ID"),
    ("Miễn hình phạt - Tòa quyết định", "MIEN_HINH_PHATS", "MHP_TOA_QUYET_DINH", "MHP_DIA_PHUONG_QD"),
    ("Hủy án - Tòa quyết định", "HUY_ANS", "TOA_QUYET_DINH_ID", "DIA_PHUONG_ID"),
    ("Tha có điều kiện - Tòa quyết định tha", "THA_CO_DIEU_KIENS", "TOA_QUYET_DINH_THA_ID", "DIA_PHUONG_QUYET_DINH_THA_ID"),
    ("Tha có điều kiện - Tòa quyết định lại", "THA_CO_DIEU_KIENS", "TOA_QUYET_DINH_LAI_ID", "DIA_PHUONG_QUYET_DINH_LAI_ID"),
    ("Chuyển giao - Tòa quyết định chuyển giao", "PN_CHUYEN_GIAO", "PNCG_TOA_QDCG", "PNCG_DIA_PHUONG_QDCGID"),
    ("Chuyển giao - Tòa QĐ thi hành", "PN_CHUYEN_GIAO", "PNCG_TOA_QDTHQDCG", "PNCG_DIA_PHUONG_THQDCGID"),
    ("Chuyển trại - Cơ quan đề nghị", "PHAM_NHAN_CHUYEN_TRAI", "PNCT_CO_QUAN_DE_NGHI_CHUYEN_ID", "PNCT_CO_QUAN_DE_NGHI_DIA_PHUONG_ID"),
    ("Quyết định thi hành án khác - Tòa QĐTH", "PN_QUYET_DINH_BAN_AN_KHACS", "QDBAK_TOA_QUYET_DINH_ID", "QDBAK_TOA_QUYET_DINH_DP_ID"),
    ("Quyết định thi hành án khác - Tòa xử", "PN_QUYET_DINH_BAN_AN_KHACS", "QDBAK_TOA_XU_ID", "QDBAK_TOA_XU_DP_ID"),
]

CSV_NAME = "court_location_mapping.csv"
CSV_COLUMNS = ("CQ_MA_CU", "CQ_MA_MOI", "TTP_MA_MOI")
AUDIT_NAME = "QLPNC10_chuan_hoa_co_quan_audit.csv"
