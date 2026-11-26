#!/usr/bin/env python3
"""Kiem tra dau vet di tru du lieu HPBS o DB MOI (QLPN). CHI SELECT, khong sua gi.

Chay:
  python check_hpbs_migration.py --dsn 10.0.229.237:1521/FREEPDB1 --user QLPN
Mat khau nhap khi chay, hoac dat bien moi truong NEW_PWD.
"""
import argparse
import getpass
import os
import sys

import oracledb


def q1(cur, sql):
    cur.execute(sql)
    return cur.fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--schema", default="")
    args = ap.parse_args()

    pwd = os.environ.get("NEW_PWD") or getpass.getpass(f"Mat khau DB moi ({args.user}): ")
    conn = oracledb.connect(user=args.user, password=pwd, dsn=args.dsn)
    cur = conn.cursor()
    pre = f'{args.schema}.' if args.schema else ""

    def count(table):
        try:
            return q1(cur, f'SELECT COUNT(*) FROM {pre}"{table}"')[0]
        except Exception as e:  # noqa: BLE001
            return f"LOI: {e}"

    print("== So dong cac bang lien quan ==")
    for t in ["PN_HINH_PHAT_BO_SUNGS", "PN_HINH_PHAT_BO_SUNGS_BAK20260924",
              "TMP_HPBS_MAP", "TMP_HPBS_DEDUP_MAP"]:
        print(f"  {t:36s} : {count(t)}")

    print("\n== 10 dong mau TMP_HPBS_MAP (OLD_ID -> NEW_ID) ==")
    try:
        cur.execute(f'SELECT * FROM {pre}"TMP_HPBS_MAP" FETCH FIRST 10 ROWS ONLY')
        for r in cur:
            print(" ", r)
    except Exception as e:  # noqa: BLE001
        print("  LOI:", e)

    print("\n== 10 dong mau TMP_HPBS_DEDUP_MAP (ID -> KEEP_ID, chi lay dong co ID != KEEP_ID) ==")
    try:
        cur.execute(f'SELECT * FROM {pre}"TMP_HPBS_DEDUP_MAP" WHERE "ID" != "KEEP_ID" FETCH FIRST 10 ROWS ONLY')
        rows = cur.fetchall()
        if not rows:
            print("  (khong co dong nao ID != KEEP_ID - co the bang rong hoac da dedup xong)")
        for r in rows:
            print(" ", r)
    except Exception as e:  # noqa: BLE001
        print("  LOI:", e)

    print("\n== Doi chieu nhanh: OLD_ID trong TMP_HPBS_MAP co giong MA_PN_HPBSHP ben DB CU khong? ==")
    try:
        cur.execute(f'SELECT "OLD_ID" FROM {pre}"TMP_HPBS_MAP" FETCH FIRST 5 ROWS ONLY')
        for r in cur:
            print("  OLD_ID mau:", r[0])
        print("  (ban tu doi chieu voi vai gia tri MA_PN_HPBSHP that o PN_HPBS_HINH_PHAT ben DB cu)")
    except Exception as e:  # noqa: BLE001
        print("  LOI:", e)

    conn.close()
    print("\nXong - gui lai toan bo output nay.")


if __name__ == "__main__":
    main()
