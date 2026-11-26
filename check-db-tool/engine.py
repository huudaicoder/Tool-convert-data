"""Read-only Oracle comparison engine for the standalone C10 tool."""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace

import mapping as M

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
ASSET_DIR = ROOT / "assets"
AUDIT_DELETED = "IS_DELETED"


def load_schema():
    with (ASSET_DIR / "schema_old.json").open(encoding="utf-8") as f:
        old = json.load(f)
    with (ASSET_DIR / "schema_new.json").open(encoding="utf-8") as f:
        new = json.load(f)
    return old, new


def connect(dsn: str, user: str, password: str, schema: str = ""):
    import oracledb

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    # Enforce a read-only transaction for every tool session.
    cur = conn.cursor()
    cur.execute("SET TRANSACTION READ ONLY")
    cur.close()
    if schema:
        schema = schema.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_$#]+", schema):
            conn.close()
            raise ValueError("Tên schema chỉ được gồm chữ, số, _, $, #.")
    return conn


def qualified(schema: str, table: str) -> str:
    if not re.fullmatch(r"[A-Z0-9_$#]+", table.upper()):
        raise ValueError(f"Tên bảng không hợp lệ trong cấu hình: {table}")
    return f'"{schema.upper()}"."{table.upper()}"' if schema else f'"{table.upper()}"'


def fetch_all(conn, sql: str, binds=None, cancel=None):
    cur = conn.cursor()
    cur.arraysize = 2000
    cur.execute(sql, binds or {})
    names = [d[0] for d in cur.description]
    rows = []
    while True:
        if cancel and cancel.is_set():
            cur.close()
            raise InterruptedError("Đã hủy theo yêu cầu.")
        batch = cur.fetchmany(2000)
        if not batch:
            break
        for row in batch:
            rows.append(tuple(v.read() if hasattr(v, "read") else v for v in row))
    cur.close()
    return names, rows


def norm_text(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, float):
        return format(Decimal(repr(value)).normalize(), "f")
    if isinstance(value, bytes):
        return f"<BLOB {len(value)} bytes>"
    return " ".join(str(value).split())


def norm_hsld(value):
    # Only trim/collapse whitespace and normalize case. Do not remove punctuation
    # or leading zeroes; HSLĐ is the only matching key.
    return " ".join(norm_text(value).split()).upper()


def norm_value(value, kind, dm_map=None):
    if value is None:
        return ""
    if isinstance(kind, tuple) and kind[0] in ("dm", "dmlist"):
        if kind[0] == "dm":
            k = norm_text(value)
            if not k or k == "0":
                return ""
            return (dm_map or {}).get(k, f"?{k}")
        vals = [p.strip() for p in re.split(r"[,;|]", norm_text(value).strip("[] ")) if p.strip() and p.strip() != "0"]
        if dm_map is not None:
            vals = [dm_map.get(v, f"?{v}") for v in vals]
        return tuple(sorted(vals))
    if kind == M.D:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        raw = norm_text(value)
        return raw[:10] if len(raw) >= 10 else raw
    if kind == M.N:
        try:
            return format(Decimal(norm_text(value).replace(",", ".")).normalize(), "f")
        except InvalidOperation:
            return norm_text(value)
    return norm_text(value).casefold()


def dm_code_column(schema, table):
    names = [c[0] for c in schema.get(table, [])]
    return next((c for c in names if c != "ID" and c.endswith("_MA")), names[1] if len(names) > 1 else "ID")


def validate_mapping(old_schema, new_schema, screens):
    issues = []
    for screen in screens:
        old_cols = {c[0] for c in old_schema.get(screen["old_table"], [])}
        new_cols = {c[0] for c in new_schema.get(screen["new_table"], [])}
        if not old_cols:
            issues.append(f"{screen['code']}: thiếu bảng cũ {screen['old_table']}")
        if not new_cols:
            issues.append(f"{screen['code']}: thiếu bảng mới {screen['new_table']}")
        if screen["old_pn"] not in old_cols:
            issues.append(f"{screen['code']}: thiếu cột liên kết cũ {screen['old_pn']}")
        if screen["new_pn"] not in new_cols:
            issues.append(f"{screen['code']}: thiếu cột liên kết mới {screen['new_pn']}")
        for old, new, _kind in screen["cols"]:
            if old not in old_cols:
                issues.append(f"{screen['code']}: thiếu cột cũ {screen['old_table']}.{old}")
            if new not in new_cols:
                issues.append(f"{screen['code']}: thiếu cột mới {screen['new_table']}.{new}")
        for key in screen["key"]:
            if key not in {c[0] for c in screen["cols"]}:
                issues.append(f"{screen['code']}: khóa {key} không nằm trong danh sách cột so sánh")
    return issues


def validate_live_mapping(conn, schema_name, screens, side):
    tables = {s[f"{side}_table"] for s in screens if not s.get("unmapped")}
    owner = schema_name.strip().upper()
    if owner:
        _, rows = fetch_all(conn, "SELECT TABLE_NAME,COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER=:owner",
                            binds={"owner": owner})
    else:
        _, rows = fetch_all(conn, "SELECT TABLE_NAME,COLUMN_NAME FROM USER_TAB_COLUMNS")
    actual = defaultdict(set)
    for table, column in rows:
        if table in tables:
            actual[table].add(column)
    problems = []
    for screen in screens:
        if screen.get("unmapped"):
            continue
        table = screen[f"{side}_table"]
        names = {screen[f"{side}_pn"]}
        names.update(c[0 if side == "old" else 1] for c in screen["cols"])
        if table not in actual:
            problems.append(f"{screen['code']}: không đọc được bảng {table} trong schema {owner or '(user)'}")
            continue
        for name in sorted(names - actual[table]):
            problems.append(f"{screen['code']}: thiếu cột {table}.{name} trong DB {side}")
    return problems


def load_person_crosswalk(old_conn, new_conn, old_schema_name="", new_schema_name=""):
    old_master, new_master = M.PN_OLD, M.PN_NEW
    _, old_rows = fetch_all(old_conn, f'SELECT "{old_master["id"]}","{old_master["hsld"]}" FROM {qualified(old_schema_name, old_master["table"])}')
    _, new_cols = load_schema()
    has_deleted = AUDIT_DELETED in {c[0] for c in new_cols.get(new_master["table"], [])}
    where = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if has_deleted else ""
    _, new_rows = fetch_all(new_conn, f'SELECT "{new_master["id"]}","{new_master["hsld"]}" FROM {qualified(new_schema_name, new_master["table"])}{where}')

    old_by_key, new_by_key = defaultdict(list), defaultdict(list)
    old_info, new_info = {}, {}
    for pid, hsld in old_rows:
        key = norm_hsld(hsld)
        old_info[pid] = hsld
        if key:
            old_by_key[key].append(pid)
    for pid, hsld in new_rows:
        key = norm_hsld(hsld)
        new_info[pid] = hsld
        if key:
            new_by_key[key].append(pid)

    pairs, report, used_new = {}, [], set()
    for oid, hsld in old_rows:
        key = norm_hsld(hsld)
        matches = new_by_key.get(key, []) if key else []
        if not key:
            status, nid = "HSLĐ trống DB cũ", None
        elif len(old_by_key[key]) > 1:
            status, nid = f"Trùng HSLĐ DB cũ ({len(old_by_key[key])} hồ sơ)", None
        elif len(matches) > 1:
            status, nid = f"Trùng HSLĐ DB mới ({len(matches)} hồ sơ)", None
        elif not matches:
            status, nid = "Chỉ có ở DB cũ", None
        else:
            nid, status = matches[0], "Ghép theo HSLĐ"
            pairs[oid] = nid
            used_new.add(nid)
        report.append({"old_id": oid, "old_hsld": hsld, "new_id": nid,
                       "new_hsld": new_info.get(nid), "status": status})

    for nid, hsld in new_rows:
        if nid in used_new:
            continue
        key = norm_hsld(hsld)
        if not key:
            status = "HSLĐ trống DB mới"
        elif len(new_by_key[key]) > 1:
            status = f"Trùng HSLĐ DB mới ({len(new_by_key[key])} hồ sơ)"
        elif len(old_by_key.get(key, [])) > 1:
            status = f"Trùng HSLĐ DB cũ ({len(old_by_key[key])} hồ sơ)"
        else:
            status = "Chỉ có ở DB mới"
        report.append({"old_id": None, "old_hsld": None, "new_id": nid,
                       "new_hsld": hsld, "status": status})
    return pairs, report


def load_dm_maps(conn, schema_name, new_schema, screens):
    tables = {kind[1] for s in screens for _o, _n, kind in s["cols"] if isinstance(kind, tuple)}
    maps = {}
    for table in tables:
        code_col = dm_code_column(new_schema, table)
        try:
            _, rows = fetch_all(conn, f'SELECT "ID","{code_col}" FROM {qualified(schema_name, table)}')
            maps[table] = {norm_text(i): norm_text(code).strip() for i, code in rows}
        except Exception:
            maps[table] = {}
    return maps


def _rows_by_key(rows, key_indexes):
    grouped = defaultdict(list)
    for row in rows:
        key = tuple(row[i] for i in key_indexes)
        grouped[key].append(row)
    return grouped


def _sql_read(conn, schema, screen, side, schema_json, cancel):
    table = screen[f"{side}_table"]
    person_col = screen[f"{side}_pn"]
    cols = [c[0 if side == "old" else 1] for c in screen["cols"]]
    select_cols = list(dict.fromkeys([person_col] + cols))
    sql = f'SELECT {",".join(chr(34) + c + chr(34) for c in select_cols)} FROM {qualified(schema, table)}'
    if side == "new" and AUDIT_DELETED in {c[0] for c in schema_json.get(table, [])}:
        sql += f' WHERE NVL("{AUDIT_DELETED}",0)=0'
    _, rows = fetch_all(conn, sql, cancel=cancel)
    return rows, select_cols


def compare_screen(screen, old_conn, new_conn, schemas, old_schema_name, new_schema_name,
                   pairs, hsld_by_old, dm_maps, cancel=None):
    old_schema, new_schema = schemas
    old_rows, old_select = _sql_read(old_conn, old_schema_name, screen, "old", old_schema, cancel)
    new_rows, new_select = _sql_read(new_conn, new_schema_name, screen, "new", new_schema, cancel)
    old_person_col = screen["old_pn"]
    new_person_col = screen["new_pn"]
    old_person_index, new_person_index = old_select.index(old_person_col), new_select.index(new_person_col)
    old_value_indexes = [old_select.index(c[0]) for c in screen["cols"]]
    new_value_indexes = [new_select.index(c[1]) for c in screen["cols"]]
    keys = screen["key"]
    key_indexes = [next(i for i, c in enumerate(screen["cols"]) if c[0] == k) for k in keys]
    old_to_new = {old_id: new_id for old_id, new_id in pairs.items()}
    new_to_old = {v: k for k, v in pairs.items()}

    old_by, new_by = defaultdict(list), defaultdict(list)
    excluded_old = excluded_new = 0
    for raw in old_rows:
        person = raw[old_person_index]
        if person not in old_to_new:
            excluded_old += 1
            continue
        row = tuple(norm_value(raw[i], c[2], None) for i, c in zip(old_value_indexes, screen["cols"]))
        old_by[person].append(row)
    for raw in new_rows:
        person = raw[new_person_index]
        old_person = new_to_old.get(person)
        if old_person is None:
            excluded_new += 1
            continue
        values = []
        for i, col in zip(new_value_indexes, screen["cols"]):
            kind = col[2]
            dm_map = dm_maps.get(kind[1]) if isinstance(kind, tuple) else None
            values.append(norm_value(raw[i], kind, dm_map))
        new_by[old_person].append(tuple(values))

    match_count = diff_count = old_only = new_only = duplicate_count = 0
    detail = []
    for old_pid in set(old_by) | set(new_by):
        old_values = old_by.get(old_pid, [])
        new_values = new_by.get(old_pid, [])
        ogroups = _rows_by_key(old_values, key_indexes) if keys else {(): list(old_values)}
        ngroups = _rows_by_key(new_values, key_indexes) if keys else {(): list(new_values)}
        for key in set(ogroups) | set(ngroups):
            olds, news = list(ogroups.get(key, [])), list(ngroups.get(key, []))
            if len(olds) > 1 or len(news) > 1:
                duplicate_count += max(0, len(olds) - 1) + max(0, len(news) - 1)
            # Cancel exact multiset matches first, independent of query order.
            old_counter, new_counter = Counter(olds), Counter(news)
            exact = sum((old_counter & new_counter).values())
            match_count += exact
            old_remaining, new_remaining = [], []
            for row, n in (old_counter - new_counter).items():
                old_remaining.extend([row] * n)
            for row, n in (new_counter - old_counter).items():
                new_remaining.extend([row] * n)
            key_text = " | ".join(norm_text(v) for v in key) if keys else ""
            if len(old_remaining) == 1 and len(new_remaining) == 1 and not (len(olds) > 1 or len(news) > 1):
                before, after = old_remaining[0], new_remaining[0]
                bad = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
                if bad:
                    diff_count += 1
                    hsld = hsld_by_old.get(old_pid, "")
                    for i in bad:
                        detail.append({"dataset": screen["name"], "code": screen["code"],
                                       "status": "Lệch giá trị", "hsld": hsld,
                                       "old_person_id": old_pid, "new_person_id": old_to_new[old_pid],
                                       "key": key_text, "old_column": screen["cols"][i][0],
                                       "new_column": screen["cols"][i][1],
                                       "old_value": before[i], "new_value": after[i]})
                else:
                    match_count += 1
                continue
            if len(old_remaining) > 1 or len(new_remaining) > 1:
                status = "Trùng khóa cần rà soát"
                for row in old_remaining:
                    detail.append({"dataset": screen["name"], "code": screen["code"], "status": status,
                                   "hsld": hsld_by_old.get(old_pid, ""), "old_person_id": old_pid,
                                   "new_person_id": old_to_new[old_pid], "key": key_text,
                                   "old_column": "", "new_column": "", "old_value": repr(row), "new_value": ""})
                for row in new_remaining:
                    detail.append({"dataset": screen["name"], "code": screen["code"], "status": status,
                                   "hsld": hsld_by_old.get(old_pid, ""), "old_person_id": old_pid,
                                   "new_person_id": old_to_new[old_pid], "key": key_text,
                                   "old_column": "", "new_column": "", "old_value": "", "new_value": repr(row)})
                continue
            for row in old_remaining:
                old_only += 1
                detail.append({"dataset": screen["name"], "code": screen["code"],
                               "status": "Chỉ có ở DB cũ (thiếu ở DB mới)",
                               "hsld": hsld_by_old.get(old_pid, ""), "old_person_id": old_pid,
                               "new_person_id": old_to_new[old_pid], "key": key_text,
                               "old_column": "", "new_column": "", "old_value": json.dumps(dict(zip([c[0] for c in screen["cols"]], row)), ensure_ascii=False, default=str), "new_value": ""})
            for row in new_remaining:
                new_only += 1
                detail.append({"dataset": screen["name"], "code": screen["code"],
                               "status": "Chỉ có ở DB mới (thiếu ở DB cũ)",
                               "hsld": hsld_by_old.get(old_pid, ""), "old_person_id": old_pid,
                               "new_person_id": old_to_new[old_pid], "key": key_text,
                                   "old_column": "", "new_column": "", "old_value": "", "new_value": json.dumps(dict(zip([c[1] for c in screen["cols"]], row)), ensure_ascii=False, default=str)})

    if not old_rows and not new_rows:
        status = "Không có dữ liệu"
    elif diff_count or old_only or new_only or duplicate_count or excluded_old or excluded_new:
        status = "Có sai lệch hoặc hồ sơ chưa đối soát"
    else:
        status = "Khớp"
    if screen["code"] == "LL12_TNDS":
        status = "Chưa đối soát phân loại TNDS/HPBS (đang gộp dữ liệu)"
    summary = {"code": screen["code"], "group": screen["group"], "name": screen["name"],
               "old_table": screen["old_table"], "new_table": screen["new_table"],
               "old_total": len(old_rows), "new_total": len(new_rows), "matched": match_count,
               "diff": diff_count, "old_only": old_only, "new_only": new_only,
               "duplicates": duplicate_count, "unmapped_old_person_rows": excluded_old,
               "unmapped_new_person_rows": excluded_new, "status": status}
    return summary, detail


def run_comparison(old_cfg, new_cfg, screens, progress=None, cancel=None):
    old_schema, new_schema = load_schema()
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""))
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""))
        problems = validate_mapping(old_schema, new_schema, screens)
        problems += validate_live_mapping(old_conn, old_cfg.get("schema", ""), screens, "old")
        problems += validate_live_mapping(new_conn, new_cfg.get("schema", ""), screens, "new")
        if problems:
            raise ValueError("Mapping/schema không hợp lệ:\n" + "\n".join(problems[:80]))
        pairs, patients = load_person_crosswalk(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""))
        old_id_to_hsld = {r["old_id"]: r["old_hsld"] or "" for r in patients if r["old_id"] is not None}
        dm_maps = load_dm_maps(new_conn, new_cfg.get("schema", ""), new_schema, screens)
        summaries, details = [], []
        for index, screen in enumerate(screens, 1):
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            if progress:
                progress(index, len(screens), screen["name"])
            if screen.get("unmapped"):
                summaries.append({"code": screen["code"], "group": screen["group"], "name": screen["name"],
                                  "old_table": "Chưa xác định", "new_table": screen.get("new_table", ""),
                                  "old_total": "", "new_total": "", "matched": 0, "diff": 0,
                                  "old_only": 0, "new_only": 0, "duplicates": 0,
                                  "unmapped_old_person_rows": 0, "unmapped_new_person_rows": 0,
                                  "status": "Chưa có mapping nguồn legacy"})
                continue
            try:
                summary, rows = compare_screen(screen, old_conn, new_conn, (old_schema, new_schema),
                                               old_cfg.get("schema", ""), new_cfg.get("schema", ""),
                                               pairs, old_id_to_hsld, dm_maps, cancel)
                summaries.append(summary)
                details.extend(rows)
            except Exception as exc:
                summaries.append({"code": screen["code"], "group": screen["group"], "name": screen["name"],
                                  "old_table": screen["old_table"], "new_table": screen["new_table"],
                                  "old_total": "", "new_total": "", "matched": 0, "diff": 0,
                                  "old_only": 0, "new_only": 0, "duplicates": 0,
                                  "unmapped_old_person_rows": 0, "unmapped_new_person_rows": 0,
                                  "status": f"Lỗi truy vấn: {exc}"})
        return {"patients": patients, "summaries": summaries, "details": details,
                "matched_people": len(pairs)}
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


def test_connection(cfg):
    conn = None
    try:
        conn = connect(cfg["dsn"], cfg["user"], cfg["password"], cfg.get("schema", ""))
        _, rows = fetch_all(conn, "SELECT SYS_CONTEXT('USERENV','DB_NAME'), SYS_CONTEXT('USERENV','CURRENT_SCHEMA'), SYSDATE FROM DUAL")
        return rows[0] if rows else ("", "", "")
    finally:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
