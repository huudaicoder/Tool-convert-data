#!/usr/bin/env python3
"""Doi chieu thuc te: voi moi cot dm()/dmlist() trong mapping.py (cac man dang bat),
kiem tra bao nhieu % gia tri ID thuc te o DB moi tra duoc trong dung bang danh muc da khai bao.
Ty le thap => nghi van khai bao sai bang danh muc dich. CHI SELECT, khong sua gi.

Chay:
  python audit_dm_mapping.py --dsn 192.168.120.55:1521/freepdb1 --user QLPN
"""
import argparse
import getpass
import os
import re
import sys

import oracledb

import mapping as M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--schema", default="")
    args = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    pwd = os.environ.get("NEW_PWD") or getpass.getpass(f"Mat khau DB moi ({args.user}): ")
    conn = oracledb.connect(user=args.user, password=pwd, dsn=args.dsn)
    cur = conn.cursor()
    pre = f'{args.schema}.' if args.schema else ""

    dm_id_cache = {}

    def dm_ids(table):
        if table not in dm_id_cache:
            try:
                cur.execute(f'SELECT "ID" FROM {pre}"{table}"')
                dm_id_cache[table] = {str(r[0]) for r in cur}
            except Exception as e:  # noqa: BLE001
                print(f"  ! khong doc duoc bang danh muc {table}: {e}")
                dm_id_cache[table] = None
        return dm_id_cache[table]

    def split_val(v):
        s = str(v).strip() if v is not None else ""
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        return [p.strip() for p in re.split(r"[,;|]", s) if p.strip() and p.strip() != "0"]

    problems = []
    checked = 0
    for s in M.SCREENS:
        for old_c, new_c, kind in s["cols"]:
            if not isinstance(kind, tuple):
                continue
            target = kind[1]
            ids = dm_ids(target)
            if ids is None:
                continue
            try:
                cur.execute(f'SELECT DISTINCT "{new_c}" FROM {pre}"{s["new_table"]}" '
                            f'WHERE "{new_c}" IS NOT NULL FETCH FIRST 500 ROWS ONLY')
                rows = [r[0] for r in cur]
            except Exception as e:  # noqa: BLE001
                print(f"[{s['code']}] {new_c}: LOI doc du lieu - {e}")
                continue
            vals = []
            for r in rows:
                vals.extend(split_val(r))
            vals = list(set(vals))
            checked += 1
            if not vals:
                continue
            ok = sum(1 for v in vals if v in ids)
            rate = ok / len(vals)
            status = "OK" if rate >= 0.9 else ("NGHI VAN" if rate < 0.5 else "CANH BAO")
            if rate < 0.9:
                problems.append((s["code"], old_c, new_c, target, rate, len(vals)))
            print(f"[{s['code']}] {old_c} <-> {new_c} -> {target}: {ok}/{len(vals)} tra duoc ({rate:.0%}) [{status}]")

    print(f"\n== Tong ket: kiem tra {checked} cot, {len(problems)} cot nghi van (ty le tra duoc < 90%) ==")
    for code, old_c, new_c, target, rate, n in sorted(problems, key=lambda x: x[4]):
        print(f"  [{code}] {old_c} <-> {new_c} -> {target}: chi {rate:.0%} tra duoc ({n} gia tri mau)")
    conn.close()


if __name__ == "__main__":
    main()
