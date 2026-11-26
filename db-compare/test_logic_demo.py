#!/usr/bin/env python3
"""Test engine so sanh (run_screen, load_patients) bang du lieu gia - KHONG can Oracle that.
Chay:  python test_logic_demo.py
"""
import re
from collections import Counter
from types import SimpleNamespace

import compare as C
import mapping as M

# ----- du lieu gia, mo phong ket qua SELECT tu Oracle -----
FAKE_TABLES = {
    "PN_LAI_LICH": (  # DB cu - bang lai lich
        ["PN_ID", "SO_HSLD", "SO_CCCD", "SO_CMND", "HO_TEN"],
        [
            ("PN001", "HS0001", "001099001234", "", "Nguyễn Văn A"),
            ("PN002", "HS0002", "001099005678", "", "Trần Thị B"),
        ],
    ),
    "PN_LAI_LICHS": (  # DB moi - bang lai lich
        ["ID", "LL_SO_HO_SO_LAN_DAU", "LL_CCCD", "LL_HO_TEN"],
        [
            (1001, "HS0001", "001099001234", "Nguyễn Văn A"),
            (1002, "HS0002", "001099005678", "Trần Thị B"),
        ],
    ),
    "PN_TIEN_SU": (  # DB cu - man dang test: LL05_TienSu
        ["PN_ID", "NGAY_THANG", "QD_SO", "QD_NGAY", "HANH_VI_VP", "DON_VI_XL", "HINH_THUC_XL",
         "NOI_CHAP_HANH", "NGAY_BAT_DAU", "NGAY_KET_THUC", "GHI_CHU_TS"],
        [
            # PN001: 1 dong khop hoan toan + 1 dong chi co o DB cu
            ("PN001", "01/01/2020", "QD-01/2020", "01/01/2020", "Gây rối trật tự",
             "CA Phường X", "Cảnh cáo", "Địa phương", "01/01/2020", "01/02/2020", "Ghi chú A"),
            ("PN001", "05/05/2020", "QD-02/2020", "05/05/2020", "Trộm cắp vặt",
             "CA Phường Y", "Phạt tiền", "Địa phương", "05/05/2020", "05/06/2020", "chỉ có ở cũ"),
            # PN002: 1 dong lech gia tri (HANH_VI_VP khac)
            ("PN002", "10/03/2021", "QD-09/2021", "10/03/2021", "Đánh bạc",
             "CA Phường Z", "Cảnh cáo", "Địa phương", "10/03/2021", "10/04/2021", "Ghi chú B"),
        ],
    ),
    "PN_TIEN_SUS": (  # DB moi - man dang test
        ["TS_PN_LAI_LICH_ID", "TS_THOI_GIAN", "TS_SO_QUYET_DINH", "TS_NGAY_QUYET_DINH", "TS_HANH_VI_VI_PHAM",
         "TS_DON_VI_XU_LY", "TS_HINH_THUC_XU_LY", "TS_NOI_CHAP_HANH", "TS_NGAY_BAT_DAU", "TS_NGAY_KET_THUC",
         "TS_GHI_CHU"],
        [
            (1001, "2020-01-01", "QD-01/2020", "2020-01-01", "Gây rối trật tự",
             "CA Phường X", "Cảnh cáo", "Địa phương", "2020-01-01", "2020-02-01", "Ghi chú A"),
            (1002, "2021-03-10", "QD-09/2021", "2021-03-10", "Đánh bạc (đã sửa sai)",
             "CA Phường Z", "Cảnh cáo", "Địa phương", "2021-03-10", "2021-04-10", "Ghi chú B"),
            # chi co o DB moi
            (1002, "2022-07-07", "QD-77/2022", "2022-07-07", "Mới thêm ở DB mới",
             "CA Phường T", "Cảnh cáo", "Địa phương", "2022-07-07", "2022-08-07", ""),
        ],
    ),
}


def fake_fetch(_conn, sql, _binds=None):
    m = re.search(r'FROM\s+("?[A-Z0-9_."]+)', sql, re.IGNORECASE)
    table = m.group(1).strip('"').split(".")[-1]
    names, rows = FAKE_TABLES[table]
    return names, rows


def main():
    C.fetch = fake_fetch  # ghi de ham doc DB bang ham doc du lieu gia

    args = SimpleNamespace(old_schema="", new_schema="", ignore_case=False,
                            new_schema_json={"PN_LAI_LICHS": [["ID", "x"]], "PN_TIEN_SUS": [["TS_PN_LAI_LICH_ID", "x"]]})

    print("== Ghep pham nhan ==")
    pairs, pat_report, ident = C.load_patients(None, None, args, args.new_schema_json)
    for r in pat_report:
        print(" ", r)
    assert pairs == {"PN001": 1001, "PN002": 1002}, f"Ghep pham nhan SAI: {pairs}"
    print("-> Ghep pham nhan dung nhu ky vong.\n")

    screen = next(s for s in M.SCREENS if s["code"] == "LL05_TienSu")
    nm = C.Norm(ignore_case=False)
    stats_cols = Counter()
    st, diffs = C.run_screen(screen, None, None, args, pairs, ident, {}, nm, stats_cols)

    print("== Ket qua man", screen["code"], "==")
    print(st)
    for d in diffs:
        print(" ", d)

    assert st["match"] == 1, "Phai co 1 dong khop hoan toan (PN001 QD-01/2020)"
    assert st["diff"] == 1, "Phai co 1 dong lech gia tri (PN002 QD-09/2021 HANH_VI_VP)"
    assert st["old_only"] == 1, "Phai co 1 dong chi co o DB cu (PN001 QD-02/2020)"
    assert st["new_only"] == 1, "Phai co 1 dong chi co o DB moi (PN002 QD-77/2022)"
    assert st["conclusion"] == "Trùng một phần"
    print("\n*** TAT CA ASSERT DEU PASS - logic ghep/so sanh dang chay dung nhu thiet ke. ***")


if __name__ == "__main__":
    main()
