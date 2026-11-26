#!/usr/bin/env python3
"""So sanh du lieu pham nhan giua DB cu (QLPN_SUOI_HAI) va DB moi (QLPN). CHI DUNG SELECT.

Vi du:
  python compare.py --old-dsn 10.0.0.1:1521/OLDPDB --old-user QLPN_SUOI_HAI \
                    --new-dsn 10.0.229.237:1521/FREEPDB1 --new-user QLPN \
                    --screens LL01,DB08 --out ket_qua.xlsx
Mat khau: nhap khi chay (hoac bien moi truong OLD_PWD / NEW_PWD).
Kiem tra file mapping (khong can ket noi DB):  python compare.py --check-mapping
"""
import argparse
import getpass
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import mapping as M

HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
AUDIT_DELETED = "IS_DELETED"


# ----------------------------------------------------------------------------- schema / check
def load_schema():
    with open(os.path.join(HERE, "schema_old.json"), encoding="utf-8") as f:
        old = json.load(f)
    with open(os.path.join(HERE, "schema_new.json"), encoding="utf-8") as f:
        new = json.load(f)
    return old, new


def dm_code_col(new_schema, table):
    cols = [c[0] for c in new_schema[table]]
    for c in cols:
        if c != "ID" and c.endswith("_MA"):
            return c
    return cols[1]


def check_mapping():
    old, new = load_schema()
    bad = 0
    for s in M.SCREENS:
        oc, nc = {c[0] for c in old.get(s["old_table"], [])}, {c[0] for c in new.get(s["new_table"], [])}
        if not oc:
            print(f"[{s['code']}] thieu bang cu {s['old_table']}"); bad += 1
        if not nc:
            print(f"[{s['code']}] thieu bang moi {s['new_table']}"); bad += 1
        if s["old_pn"] not in oc:
            print(f"[{s['code']}] cot cu {s['old_pn']} khong ton tai"); bad += 1
        if s["new_pn"] not in nc:
            print(f"[{s['code']}] cot moi {s['new_pn']} khong ton tai"); bad += 1
        oldcols = [c[0] for c in s["cols"]]
        for k in s["key"]:
            if k not in oldcols:
                print(f"[{s['code']}] key {k} khong nam trong cols"); bad += 1
        for o, n, kind in s["cols"]:
            if o not in oc:
                print(f"[{s['code']}] cot cu {o} khong ton tai trong {s['old_table']}"); bad += 1
            if n not in nc:
                print(f"[{s['code']}] cot moi {n} khong ton tai trong {s['new_table']}"); bad += 1
            if isinstance(kind, tuple) and kind[1] not in new:
                print(f"[{s['code']}] bang danh muc {kind[1]} khong ton tai"); bad += 1
    print(f"Kiem tra xong: {len(M.SCREENS)} man, {bad} loi.")
    return bad


# ----------------------------------------------------------------------------- normalize
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d", "%d.%m.%Y")


def to_text(v):
    if v is None:
        return ""
    if hasattr(v, "read"):  # LOB
        v = v.read()
    if isinstance(v, bytes):
        return f"<blob {len(v)}B>"
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, Decimal):
        return format(v.normalize(), "f")
    if isinstance(v, float):
        return format(Decimal(repr(v)).normalize(), "f")
    return str(v)


class Norm:
    def __init__(self, ignore_case=False):
        self.ic = ignore_case

    def text(self, v):
        s = " ".join(to_text(v).split())
        return s.casefold() if self.ic else s

    def date(self, v):
        if v is None:
            return ""
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, date):
            return v.isoformat()
        s = self.text(v)
        if not s:
            return ""
        base = s.split(" ")[0].split("T")[0]
        for f in DATE_FORMATS:
            try:
                return datetime.strptime(base, f).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return s

    def num(self, v):
        s = self.text(v)
        if not s:
            return ""
        try:
            return format(Decimal(s.replace(",", ".")).normalize(), "f")
        except InvalidOperation:
            return s

    def dm(self, v, mp):
        """mp: None (DB cu, giu nguyen ma) hoac dict ID->MA (DB moi).
        ID=0 o DB moi nghia la "chua chon" (khong co dong ID=0 trong bang danh muc, bat dau tu 1) -
        coi nhu rong, khong tra danh muc de tranh bao "?0" sai."""
        s = self.text(v)
        if not s:
            return ""
        if mp is None:
            return s
        if s == "0":
            return ""
        return mp.get(s, f"?{s}")

    def dmlist(self, v, mp):
        s = self.text(v).strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1].strip()
        if not s:
            return ""
        parts = [p.strip() for p in re.split(r"[,;|]", s) if p.strip()]
        if mp is not None:
            parts = [p for p in parts if p != "0"]
            parts = [mp.get(p, f"?{p}") for p in parts]
        return ",".join(sorted(parts))

    def value(self, v, kind, mp):
        if kind == M.T:
            return self.text(v)
        if kind == M.D:
            return self.date(v)
        if kind == M.N:
            return self.num(v)
        if kind[0] == "dm":
            return self.dm(v, mp)
        return self.dmlist(v, mp)


def norm_key(v):
    return re.sub(r"[\s\-_.]", "", (to_text(v) or "")).upper()


# ----------------------------------------------------------------------------- db access
def connect(dsn, user, pwd):
    import oracledb
    return oracledb.connect(user=user, password=pwd, dsn=dsn)


def q(prefix, table):
    return f'{prefix + "." if prefix else ""}"{table}"'


def fetch(conn, sql, binds=None):
    cur = conn.cursor()
    cur.arraysize = 5000
    cur.execute(sql, binds or {})
    names = [d[0] for d in cur.description]
    out = []
    for r in cur:
        out.append(tuple(x.read() if hasattr(x, "read") else x for x in r))
    cur.close()
    return names, out


def load_patients(conn_old, conn_new, args, new_schema):
    po, pn = M.PN_OLD, M.PN_NEW
    _, orows = fetch(conn_old, f'SELECT "{po["id"]}","{po["hsld"]}","{po["cccd"]}","{po["cmnd"]}","{po["name"]}" '
                               f'FROM {q(args.old_schema, po["table"])}')
    where = f' WHERE NVL("{AUDIT_DELETED}",0)=0'
    _, nrows = fetch(conn_new, f'SELECT "{pn["id"]}","{pn["hsld"]}","{pn["cccd"]}","{pn["name"]}" '
                               f'FROM {q(args.new_schema, pn["table"])}{where}')
    new_by_hsld, new_by_cccd = defaultdict(list), defaultdict(list)
    new_info = {}
    for nid, hsld, cccd, name in nrows:
        k, c = norm_key(hsld), norm_key(cccd)
        new_info[nid] = dict(hsld=hsld, cccd=cccd, name=name)
        if k:
            new_by_hsld[k].append(nid)
        if c:
            new_by_cccd[c].append(nid)

    pairs, used_new, report = {}, set(), []
    for oid, hsld, cccd, cmnd, name in orows:
        k, c = norm_key(hsld), norm_key(cccd) or norm_key(cmnd)
        status, nid = None, None
        cand = [n for n in new_by_hsld.get(k, []) if n not in used_new] if k else []
        if len(cand) == 1:
            nid = cand[0]
        elif len(cand) > 1:
            same = [n for n in cand if c and norm_key(new_info[n]["cccd"]) == c]
            if same:
                nid = same[0]
            else:
                status = f"Trùng HSLĐ ở DB mới ({len(cand)} bản ghi), không phân biệt được"
        if nid is None and status is None and c:
            cand = [n for n in new_by_cccd.get(c, []) if n not in used_new]
            if len(cand) == 1:
                nid, status = cand[0], "Chỉ khớp CCCD (HSLĐ khác/thiếu)"
            elif len(cand) > 1:
                status = f"Trùng CCCD ở DB mới ({len(cand)} bản ghi)"
        if nid is not None:
            used_new.add(nid)
            pairs[oid] = nid
            if status is None:
                same_c = (not c) or norm_key(new_info[nid]["cccd"]) == c
                status = "Khớp HSLĐ + CCCD" if same_c else "Khớp HSLĐ, lệch CCCD"
        else:
            status = status or "Chỉ có ở DB cũ"
        report.append([oid, hsld, cccd or cmnd, name, nid, new_info.get(nid, {}).get("hsld"),
                       new_info.get(nid, {}).get("cccd"), new_info.get(nid, {}).get("name"), status])
    for nid, info in new_info.items():
        if nid not in used_new:
            report.append([None, None, None, None, nid, info["hsld"], info["cccd"], info["name"], "Chỉ có ở DB mới"])
    ident = {oid: (hsld, name) for oid, hsld, _, _, name in orows}
    return pairs, report, ident


def load_dm(conn_new, args, new_schema, tables):
    maps = {}
    for t in sorted(tables):
        col = dm_code_col(new_schema, t)
        try:
            _, rows = fetch(conn_new, f'SELECT "ID","{col}" FROM {q(args.new_schema, t)}')
            maps[t] = {to_text(i): to_text(c).strip() for i, c in rows}
        except Exception as e:  # noqa: BLE001
            print(f"  ! Khong doc duoc danh muc {t}: {e}")
            maps[t] = {}
    return maps


# ----------------------------------------------------------------------------- compare
def conclude(n_match, n_diff, n_old_only, n_new_only):
    total = n_match + n_diff + n_old_only + n_new_only
    if total == 0:
        return "Không có dữ liệu"
    if n_diff == 0 and n_old_only == 0 and n_new_only == 0:
        return "Trùng khớp toàn bộ"
    if n_old_only == 0 and n_new_only == 0:
        return "Trùng key (lệch giá trị)"
    if n_match + n_diff == 0:
        return "Không trùng"
    return "Trùng một phần"


def run_screen(s, conn_old, conn_new, args, pairs, ident, dmmaps, nm, stats_cols):
    old_cols = [c[0] for c in s["cols"]]
    new_cols = [c[1] for c in s["cols"]]
    kinds = [c[2] for c in s["cols"]]
    mps = [dmmaps.get(k[1]) if isinstance(k, tuple) else None for k in kinds]
    key_idx = [old_cols.index(k) for k in s["key"]]

    sel_old = ",".join(f'"{c}"' for c in [s["old_pn"]] + old_cols)
    sel_new = ",".join(f'"{c}"' for c in [s["new_pn"]] + new_cols)
    _, orows = fetch(conn_old, f'SELECT {sel_old} FROM {q(args.old_schema, s["old_table"])}')
    has_del = AUDIT_DELETED in {c[0] for c in args.new_schema_json[s["new_table"]]}
    where = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if has_del else ""
    _, nrows = fetch(conn_new, f'SELECT {sel_new} FROM {q(args.new_schema, s["new_table"])}{where}')

    new_to_old = {v: k for k, v in pairs.items()}
    old_by, new_by = defaultdict(list), defaultdict(list)
    for r in orows:
        pid = r[0]
        if pid in pairs:
            old_by[pid].append([nm.value(v, k, None) for v, k in zip(r[1:], kinds)])
    for r in nrows:
        oid = new_to_old.get(r[0])
        if oid is not None:
            new_by[oid].append([nm.value(v, k, m) for v, k, m in zip(r[1:], kinds, mps)])

    n_match = n_diff = n_oo = n_no = 0
    diffs = []

    def make_keys(rows):
        rows.sort(key=lambda r: ([r[i] for i in key_idx], r))
        cnt, out = Counter(), {}
        for r in rows:
            k = tuple(r[i] for i in key_idx)
            cnt[k] += 1
            out[(k, cnt[k])] = r
        return out

    for pid in sorted(set(old_by) | set(new_by), key=str):
        hsld, name = ident.get(pid, ("", ""))
        nid = pairs.get(pid)
        o, n = make_keys(old_by.get(pid, [])), make_keys(new_by.get(pid, []))
        for kk, orow in o.items():
            keytxt = " | ".join(kk[0]) + (f" (#{kk[1]})" if kk[1] > 1 else "")
            nrow = n.pop(kk, None)
            if nrow is None:
                n_oo += 1
                diffs.append(["Chỉ có ở DB cũ", pid, nid, hsld, name, keytxt, "", "", ""])
                continue
            if getattr(args, "only_missing", False):
                n_match += 1
                continue
            bad = [i for i in range(len(old_cols)) if orow[i] != nrow[i]]
            if not bad:
                n_match += 1
                continue
            n_diff += 1
            for i in bad:
                stats_cols[(s["code"], old_cols[i] + " ↔ " + new_cols[i])] += 1
                diffs.append(["Lệch giá trị", pid, nid, hsld, name, keytxt, old_cols[i] + " ↔ " + new_cols[i],
                              orow[i], nrow[i]])
        for kk, nrow in n.items():
            n_no += 1
            diffs.append(["Chỉ có ở DB mới", pid, nid, hsld, name, " | ".join(kk[0]), "", "", ""])
    return dict(match=n_match, diff=n_diff, old_only=n_oo, new_only=n_no,
                old_total=len(orows), new_total=len(nrows),
                conclusion=conclude(n_match, n_diff, n_oo, n_no)), diffs


# ----------------------------------------------------------------------------- excel
def write_excel(path, summary, pat_report, col_stats, details, limit):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="DDEBF7")

    def sheet(title, header, rows, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title[:31]
        ws.append(header)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True), head_fill
        for r in rows:
            ws.append([("'" + x if isinstance(x, str) and x and x[0] in "=+-@" else x) for x in r])
        ws.freeze_panes = "A2"
        for i, h in enumerate(header, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(60, max(12, len(str(h)) + 4))
        return ws

    sheet("Tong_hop",
          ["Mã", "Nhóm", "Màn", "Bảng cũ", "Bảng mới", "Số dòng DB cũ", "Số dòng DB mới", "Khớp hoàn toàn",
           "Chỉ trùng key (lệch giá trị)", "Chỉ có ở DB cũ", "Chỉ có ở DB mới", "Kết luận", "Ghi chú"],
          summary, first=True)
    sheet("PhamNhan", ["PN_ID cũ", "Số HSLĐ cũ", "CCCD cũ", "Họ tên cũ", "ID mới", "Số HSLĐ mới", "CCCD mới",
                       "Họ tên mới", "Kết quả ghép"], pat_report)
    sheet("Cot_lech", ["Mã màn", "Cột (cũ ↔ mới)", "Số dòng lệch"],
          [[a, b, n] for (a, b), n in sorted(col_stats.items(), key=lambda x: (x[0][0], -x[1]))])
    full_header = ["Trạng thái", "PN_ID cũ", "ID phạm nhân mới", "Số HSLĐ", "Họ tên", "Key dòng", "Cột lệch",
                   "Giá trị DB cũ", "Giá trị DB mới"]
    for code, rows in details.items():
        cut = rows[:limit]
        ws = sheet(code, full_header, cut)
        if len(rows) > limit:
            ws.append([f"... cắt bớt: còn {len(rows) - limit} dòng nữa (tăng --limit để xem thêm)"])
    wb.save(path)


def write_excel_single(path, code, diffs, limit, only_missing=False):
    """Chi 1 man: xuat mot sheet duy nhat, chi gom cac dong CHUA trung khop
    (Lech gia tri / Chi co o DB cu / Chi co o DB moi). only_missing=True: bo 3 cot
    Cot lech/Gia tri DB cu/Gia tri DB moi (luon rong trong che do chi kiem tra thieu ban ghi)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = code[:31]
    header = ["Trạng thái", "PN_ID cũ", "ID phạm nhân mới", "Số HSLĐ", "Họ tên", "Key dòng"]
    if not only_missing:
        header += ["Cột lệch", "Giá trị DB cũ", "Giá trị DB mới"]
    if only_missing:
        diffs = [r[:6] for r in diffs]
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDEBF7")
    for r in diffs[:limit]:
        ws.append([("'" + x if isinstance(x, str) and x and x[0] in "=+-@" else x) for x in r])
    if len(diffs) > limit:
        ws.append([f"... cắt bớt: còn {len(diffs) - limit} dòng nữa (tăng --limit để xem thêm)"])
    if not diffs:
        ws.append(["Không có dòng lệch — toàn bộ phạm nhân đã ghép được đều khớp dữ liệu."])
    ws.freeze_panes = "A2"
    for i, h in enumerate(header, 1):
        ws.column_dimensions[get_column_letter(i)].width = min(60, max(12, len(str(h)) + 4))
    wb.save(path)


def run_compare(args, screens):
    """args can giu: old_dsn, old_user, old_pwd, old_schema, new_dsn, new_user, new_pwd,
    new_schema, out, limit, ignore_case. Dung chung cho CLI va GUI. Tra ve duong dan file Excel."""
    _, new_schema = load_schema()
    args.new_schema_json = new_schema

    print("Ket noi DB cu...");  co = connect(args.old_dsn, args.old_user, args.old_pwd)
    print("Ket noi DB moi..."); cn = connect(args.new_dsn, args.new_user, args.new_pwd)
    try:
        nm = Norm(args.ignore_case)

        print("Ghep pham nhan (HSLD, CCCD)...")
        pairs, pat_report, ident = load_patients(co, cn, args, new_schema)
        cnt = Counter(r[-1] for r in pat_report)
        for k, v in cnt.most_common():
            print(f"  {k}: {v}")

        dm_tables = {k[1] for s in screens for _, _, k in s["cols"] if isinstance(k, tuple)}
        print(f"Doc {len(dm_tables)} bang danh muc DB moi...")
        dmmaps = load_dm(cn, args, new_schema, dm_tables)

        summary, details, col_stats, errors = [], {}, Counter(), {}
        for s in screens:
            print(f"[{s['code']}] {s['name']} ...", end=" ", flush=True)
            try:
                st, diffs = run_screen(s, co, cn, args, pairs, ident, dmmaps, nm, col_stats)
            except Exception as e:  # noqa: BLE001
                print(f"LOI: {e}")
                errors[s["code"]] = str(e)
                summary.append([s["code"], s["group"], s["name"], s["old_table"], s["new_table"], "", "", "", "",
                                "", "", "LỖI", str(e)[:300]])
                continue
            print(st["conclusion"])
            summary.append([s["code"], s["group"], s["name"], s["old_table"], s["new_table"], st["old_total"],
                            st["new_total"], st["match"], st["diff"], st["old_only"], st["new_only"],
                            st["conclusion"], "chỉ tính phạm nhân đã ghép được"])
            if diffs:
                details[s["code"]] = diffs
    finally:
        co.close()
        cn.close()
    if len(screens) == 1:
        code = screens[0]["code"]
        if code in errors:
            raise RuntimeError(f"Loi khi chay man {code}: {errors[code]}")
        write_excel_single(args.out, code, details.get(code, []), args.limit,
                            only_missing=getattr(args, "only_missing", False))
    else:
        write_excel(args.out, summary, pat_report, col_stats, details, args.limit)
    print(f"Da ghi {args.out}")
    return args.out


def select_screens(screens_arg):
    screens = M.SCREENS
    if screens_arg:
        want = [x.strip().upper() for x in screens_arg.split(",") if x.strip()]
        screens = [s for s in screens if any(s["code"].upper().startswith(w) for w in want)]
    return screens


# ----------------------------------------------------------------------------- main
def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check-mapping", action="store_true", help="chi kiem tra file mapping, khong ket noi DB")
    ap.add_argument("--old-dsn"), ap.add_argument("--old-user"), ap.add_argument("--old-schema", default="")
    ap.add_argument("--new-dsn"), ap.add_argument("--new-user"), ap.add_argument("--new-schema", default="")
    ap.add_argument("--screens", default="", help="vd: LL01,DB08,KT01 (mac dinh: tat ca)")
    ap.add_argument("--out", default="ket_qua_so_sanh.xlsx")
    ap.add_argument("--limit", type=int, default=50000, help="so dong lech toi da moi sheet")
    ap.add_argument("--ignore-case", action="store_true", help="bo qua hoa/thuong khi so chuoi")
    ap.add_argument("--only-missing", action="store_true",
                    help="chi bao dong thieu ban ghi (bo qua so lech gia tri tung cot)")
    args = ap.parse_args()

    if args.check_mapping:
        sys.exit(1 if check_mapping() else 0)
    for a in ("old_dsn", "old_user", "new_dsn", "new_user"):
        if not getattr(args, a):
            ap.error(f"thieu --{a.replace('_', '-')}")
    args.old_pwd = os.environ.get("OLD_PWD") or getpass.getpass(f"Mat khau DB cu ({args.old_user}): ")
    args.new_pwd = os.environ.get("NEW_PWD") or getpass.getpass(f"Mat khau DB moi ({args.new_user}): ")

    screens = select_screens(args.screens)
    if not screens:
        sys.exit("Khong co man nao khop --screens")
    run_compare(args, screens)


if __name__ == "__main__":
    main()
