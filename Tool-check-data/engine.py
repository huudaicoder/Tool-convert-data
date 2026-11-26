"""Read-only Oracle comparison engine for the standalone C10 tool."""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace

import cryptography  # Explicit import so PyInstaller includes Oracle Thin-mode crypto.
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


def connect(dsn: str, user: str, password: str, schema: str = "", read_only: bool = True):
    import oracledb

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    if read_only:
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


def _oracle_table_columns(conn, schema, table):
    owner = (schema or "").strip().upper()
    if owner:
        _, rows = fetch_all(conn, "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER=:p_owner AND TABLE_NAME=:p_table",
                            {"p_owner": owner, "p_table": table.upper()})
    else:
        _, rows = fetch_all(conn, "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME=:p_table",
                            {"p_table": table.upper()})
    return {row[0] for row in rows}


def _same_schema_units_plan(old_conn, new_conn, old_schema_name, new_schema_name, prison_code):
    """Compare identical PN_LAI_LICHS structures in two databases."""
    table = "PN_LAI_LICHS"
    old_columns = _oracle_table_columns(old_conn, old_schema_name, table)
    new_columns = _oracle_table_columns(new_conn, new_schema_name, table)
    required = {"ID", "LL_SO_HO_SO_LAN_DAU", "LL_TRAI_GIAM_ID", "LL_PHAN_DOI_ID", "LL_PHAN_TRAI_ID"}
    if not required <= old_columns or not required <= new_columns:
        raise ValueError("Cả hai DB phải có PN_LAI_LICHS với cùng các cột: ID, LL_SO_HO_SO_LAN_DAU, LL_TRAI_GIAM_ID, LL_PHAN_DOI_ID, LL_PHAN_TRAI_ID.")

    def prison(conn, schema):
        dm_cols = _oracle_table_columns(conn, schema, "DM_TRAI_GIAMS")
        if not {"ID", "TG_MA"} <= dm_cols:
            raise ValueError(f"DB {schema or '(mặc định)'} thiếu DM_TRAI_GIAMS.ID/TG_MA.")
        _, rows = fetch_all(conn,
            f'SELECT "ID","TG_MA","TG_TEN" FROM {qualified(schema, "DM_TRAI_GIAMS")} WHERE UPPER(TRIM("TG_MA"))=:p_code',
            {"p_code": norm_text(prison_code).strip().upper()})
        if len(rows) != 1:
            raise ValueError(f"TG_MA '{prison_code}' khớp {len(rows)} trại trong DB {schema or '(mặc định)'}; cần đúng một trại.")
        return rows[0]

    old_prison, new_prison = prison(old_conn, old_schema_name), prison(new_conn, new_schema_name)
    old_code, new_code = norm_text(old_prison[1]).strip().upper(), norm_text(new_prison[1]).strip().upper()
    if old_code != new_code:
        raise ValueError(f"TG_MA hai DB không trùng nhau ({old_code} / {new_code}).")
    scope = {"old_code": old_code, "code": new_code, "name": norm_text(new_prison[2]), "new_id": new_prison[0]}
    old_deleted = f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in old_columns else ""
    new_deleted = f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in new_columns else ""
    select = '"ID","LL_SO_HO_SO_LAN_DAU","LL_PHAN_DOI_ID","LL_PHAN_TRAI_ID"'
    _, old_rows = fetch_all(old_conn, f'SELECT {select} FROM {qualified(old_schema_name, table)} WHERE "LL_TRAI_GIAM_ID"=:p_prison{old_deleted}', {"p_prison": old_prison[0]})
    _, new_rows = fetch_all(new_conn, f'SELECT {select} FROM {qualified(new_schema_name, table)} WHERE "LL_TRAI_GIAM_ID"=:p_prison{new_deleted}', {"p_prison": new_prison[0]})

    old_by_hsld, new_by_hsld = defaultdict(list), defaultdict(list)
    old_by_id = {row[0]: row for row in old_rows}
    for row in old_rows:
        key = norm_hsld(row[1])
        if key: old_by_hsld[key].append(row)
    for row in new_rows:
        key = norm_hsld(row[1])
        if key: new_by_hsld[key].append(row)
    pairs, issues = {}, []
    for key, sources in old_by_hsld.items():
        targets = new_by_hsld.get(key, [])
        if len(sources) == 1 and len(targets) == 1:
            pairs[sources[0][0]] = targets[0]
        elif len(sources) != 1:
            issues.append({"hsld": norm_text(sources[0][1]), "status": f"Trùng HSLĐ DB cũ ({len(sources)})"})
        elif len(targets) > 1:
            issues.append({"hsld": norm_text(sources[0][1]), "status": f"Trùng HSLĐ DB mới ({len(targets)})"})
        else:
            issues.append({"hsld": norm_text(sources[0][1]), "status": "Không có HSLĐ tương ứng trong DB mới"})

    # Fetch each catalog once. Per-ID and per-preview-row round trips made the
    # previous implementation very slow on large prisons.
    def read_catalog(conn, schema, table, id_col, code_col, name_col, parent_col=None, parent_id=None):
        columns = _oracle_table_columns(conn, schema, table)
        needed = {id_col, code_col, name_col}
        if parent_col:
            needed.add(parent_col)
        if not needed <= columns:
            raise ValueError(f"{schema or '(mặc định)'}.{table} thiếu cột " + ", ".join(sorted(needed - columns)))
        select_cols = [id_col, code_col, name_col] + ([parent_col] if parent_col else [])
        clauses, binds = [], {}
        if "IS_DELETED" in columns:
            clauses.append('NVL("IS_DELETED",0)=0')
        if parent_col and parent_id is not None:
            clauses.append(f'"{parent_col}"=:p_parent')
            binds["p_parent"] = parent_id
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        _, rows = fetch_all(conn, f'SELECT {",".join(chr(34)+c+chr(34) for c in select_cols)} '
                            f'FROM {qualified(schema, table)}{where}', binds)
        by_id = {row[0]: row for row in rows}
        by_code = defaultdict(list)
        for row in rows:
            key = norm_hsld(row[1])
            if key:
                by_code[key].append(row)
        return by_id, by_code

    old_team_by_id, _ = read_catalog(old_conn, old_schema_name, "DM_PHAN_DOIS", "ID", "PD_MA", "PD_TEN")
    old_branch_by_id, _ = read_catalog(old_conn, old_schema_name, "DM_PHAN_TRAIS", "ID", "PT_MA", "PT_TEN")
    new_branch_by_id, new_branch_by_code = read_catalog(
        new_conn, new_schema_name, "DM_PHAN_TRAIS", "ID", "PT_MA", "PT_TEN", "PT_DM_TRAI_GIAM_ID", new_prison[0])
    new_team_by_id, new_team_by_code = read_catalog(
        new_conn, new_schema_name, "DM_PHAN_DOIS", "ID", "PD_MA", "PD_TEN", "PD_DM_PHAN_TRAI_ID")

    def catalog_label(row):
        if row is None:
            return "(trống)"
        catalog_id = norm_text(row[0])
        code, name = norm_text(row[1]), norm_text(row[2])
        return f"ID {catalog_id} · mã {code} · {name}" if name else f"ID {catalog_id} · mã {code}"

    def target_label(catalog, value):
        if value is None:
            return "(trống)"
        row = catalog.get(value)
        return catalog_label(row) if row else f"ID {value} (không có trong danh mục trại)"

    updates = []
    for source_id, target in pairs.items():
        source = old_by_id[source_id]
        fields, expected = {}, {}
        source_team_id, source_branch_id = source[2], source[3]
        target_team_id, target_branch_id = target[2], target[3]
        old_team_row = old_team_by_id.get(source_team_id) if source_team_id is not None else None
        old_branch_row = old_branch_by_id.get(source_branch_id) if source_branch_id is not None else None
        mapped_team_id = mapped_branch_id = None
        # Empty old values mean "no source value" and must never clear target.
        if source_branch_id is not None:
            if old_branch_row is None:
                issues.append({"hsld": norm_text(source[1]), "status": "Không tra được duy nhất mã phân trại từ ID DB cũ; bỏ qua hồ sơ"})
                continue
            new_branch_matches = new_branch_by_code.get(norm_hsld(old_branch_row[1]), [])
            if len(new_branch_matches) != 1:
                issues.append({"hsld": norm_text(source[1]), "status": f"Mã phân trại {old_branch_row[1]} không khớp duy nhất trong DB mới của trại; bỏ qua hồ sơ"})
                continue
            mapped_branch_id = new_branch_matches[0][0]

        if source_team_id is not None:
            if old_team_row is None:
                issues.append({"hsld": norm_text(source[1]), "status": "Không tra được duy nhất mã phân đội từ ID DB cũ; bỏ qua hồ sơ"})
                continue
            team_candidates = new_team_by_code.get(norm_hsld(old_team_row[1]), [])
            if mapped_branch_id is not None:
                team_candidates = [row for row in team_candidates if row[3] == mapped_branch_id]
            if len(team_candidates) != 1:
                issues.append({"hsld": norm_text(source[1]), "status": f"Mã phân đội {old_team_row[1]} không khớp duy nhất trong phân trại DB mới; bỏ qua hồ sơ"})
                continue
            mapped_team_id = team_candidates[0][0]
            if mapped_team_id != target_team_id:
                fields["LL_PHAN_DOI_ID"] = mapped_team_id
                expected["LL_PHAN_DOI_ID"] = target_team_id
        if mapped_branch_id is not None and mapped_branch_id != target_branch_id:
            fields["LL_PHAN_TRAI_ID"] = mapped_branch_id
            expected["LL_PHAN_TRAI_ID"] = target_branch_id
        if fields:
            desired_team_id = mapped_team_id if mapped_team_id is not None else target_team_id
            desired_branch_id = mapped_branch_id if mapped_branch_id is not None else target_branch_id
            updates.append({"id": target[0], "hsld": norm_text(source[1]), "fields": fields, "expected": expected,
                            "team_old": catalog_label(old_team_row),
                            "team_new": (target_label(new_team_by_id, target_team_id) +
                                         (f" → {target_label(new_team_by_id, desired_team_id)}" if desired_team_id != target_team_id else "")),
                            "branch_old": catalog_label(old_branch_row),
                            "branch_new": (target_label(new_branch_by_id, target_branch_id) +
                                           (f" → {target_label(new_branch_by_id, desired_branch_id)}" if desired_branch_id != target_branch_id else ""))})
    return {"updates": updates, "issues": issues, "prison_scope": scope,
            "field_count": sum(len(row["fields"]) for row in updates)}

def preview_same_schema_units(old_cfg, new_cfg):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _same_schema_units_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try: conn.rollback(); conn.close()
                except Exception: pass


def apply_same_schema_units(old_cfg, new_cfg, preview, selected_ids=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _same_schema_units_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        expected = [(r["id"], r["fields"], r["expected"]) for r in preview["updates"]]
        actual = [(r["id"], r["fields"], r["expected"]) for r in fresh["updates"]]
        if expected != actual:
            raise ValueError("Dữ liệu hai DB đã thay đổi so với xem trước. Không ghi gì; hãy tải lại xem trước.")
        if selected_ids is not None:
            selected_ids = set(selected_ids)
            if not selected_ids or not selected_ids <= {r["id"] for r in fresh["updates"]}:
                raise ValueError("Danh sách hồ sơ chọn không còn hợp lệ; hãy tải lại xem trước.")
            fresh["updates"] = [r for r in fresh["updates"] if r["id"] in selected_ids]
        cursor = new_conn.cursor()
        table = qualified(new_cfg.get("schema", ""), "PN_LAI_LICHS")
        prison_id = fresh["prison_scope"].get("new_id")
        new_columns = _oracle_table_columns(new_conn, new_cfg.get("schema", ""), "PN_LAI_LICHS")
        deleted_filter = ' AND NVL(T."IS_DELETED",0)=0' if "IS_DELETED" in new_columns else ""
        for row in fresh["updates"]:
            assignments, conditions, binds = [], [], {"id": row["id"]}
            for i, (column, value) in enumerate(row["fields"].items()):
                assignments.append(f'"{column}"=:v{i}'); binds[f"v{i}"] = value
                old_value = row["expected"][column]
                if old_value is None: conditions.append(f'T."{column}" IS NULL')
                else: conditions.append(f'T."{column}"=:e{i}'); binds[f"e{i}"] = old_value
            binds["prison_id"] = prison_id
            cursor.execute(f'UPDATE {table} T SET {",".join(assignments)} WHERE T."ID"=:id '
                           f'{deleted_filter} AND T."LL_TRAI_GIAM_ID"=:prison_id '
                           f'AND {" AND ".join(conditions)}', binds)
            if cursor.rowcount != 1:
                raise RuntimeError("Lai lịch DB mới đã đổi trong lúc cập nhật; toàn bộ transaction rollback.")
        cursor.close(); new_conn.commit()
        return {"updated_rows": len(fresh["updates"]), "updated_fields": sum(len(r["fields"]) for r in fresh["updates"]), "prison_scope": fresh["prison_scope"]}
    except Exception:
        if new_conn: new_conn.rollback()
        raise
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try: conn.rollback(); conn.close()
                except Exception: pass


def norm_value(value, kind, dm_map=None):
    if value is None:
        return ""
    if isinstance(kind, tuple) and kind[0] in ("dm", "dmlist"):
        if kind[0] == "dm":
            k = norm_text(value)
            if not k or k == "0":
                return ""
            # Old-side value is already the legacy code. New-side value is an
            # ID and must be translated through the target DM table.
            if dm_map is None:
                return k.strip().casefold()
            return (dm_map.get(k, f"?{k}") or "").casefold()
        vals = [p.strip() for p in re.split(r"[,;|]", norm_text(value).strip("[] ")) if p.strip() and p.strip() != "0"]
        if dm_map is not None:
            vals = [dm_map.get(v, f"?{v}").casefold() for v in vals]
        else:
            vals = [v.casefold() for v in vals]
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
    # User-entered Vietnamese text can look identical while using composed vs.
    # decomposed Unicode, or contain common zero-width copy/paste characters.
    # Normalize these before comparing free-text fields such as LL02_HanhVi.
    text = unicodedata.normalize("NFC", str(value))
    for invisible in ("\u200b", "\ufeff", "\u00ad", "\u2060"):
        text = text.replace(invisible, "")
    return " ".join(text.split()).casefold()


def dm_code_column(schema, table):
    names = [c[0] for c in schema.get(table, [])]
    # The application exports DM_TRAI_GIAMS.TG_MA back to legacy MA_TRAI_GIAM,
    # so *_MA is the business code used for the comparison. Do not substitute
    # *_MA_XAC_THUC without a field-specific migration rule.
    return next((c for c in names if c != "ID" and c.endswith("_MA")),
                names[1] if len(names) > 1 else "ID")


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


def load_person_crosswalk(old_conn, new_conn, old_schema_name="", new_schema_name="", new_prison_code=""):
    old_master, new_master = M.PN_OLD, M.PN_NEW
    old_sql = (f'SELECT "{old_master["id"]}","{old_master["hsld"]}","{old_master["trai"]}" '
               f'FROM {qualified(old_schema_name, old_master["table"])}')
    _, old_rows = fetch_all(old_conn, old_sql)
    _, new_cols = load_schema()
    has_deleted = AUDIT_DELETED in {c[0] for c in new_cols.get(new_master["table"], [])}
    old_codes = {norm_text(row[2]).strip().upper() for row in old_rows if norm_text(row[2]).strip()}
    old_code_valid = len(old_codes) == 1 and all(norm_text(row[2]).strip() for row in old_rows)
    manual_prison_code = norm_text(new_prison_code).strip().upper()
    if not old_code_valid and not manual_prison_code:
        raise ValueError("Không xác định được duy nhất mã trại trong DB cũ. Cần mọi hồ sơ có cùng một MA_TRAI_GIAM trước khi đối soát.")
    old_prison_code = next(iter(old_codes)) if old_code_valid else "Không duy nhất / có giá trị trống"
    prison_code = manual_prison_code or old_prison_code

    dm_table = "DM_TRAI_GIAMS"
    dm_columns = {c[0] for c in new_cols.get(dm_table, [])}
    if not {"ID", "TG_MA", "TG_TEN"}.issubset(dm_columns):
        raise ValueError("Schema DB mới thiếu DM_TRAI_GIAMS.ID, TG_MA hoặc TG_TEN; không thể xác định trại tương ứng an toàn.")
    dm_deleted = f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in dm_columns else ""
    dm_sql = (f'SELECT "ID","TG_TEN" FROM {qualified(new_schema_name, dm_table)} '
              f'WHERE UPPER(TRIM("TG_MA"))=:prison_code{dm_deleted}')
    _, prison_rows = fetch_all(new_conn, dm_sql, {"prison_code": prison_code})
    if len(prison_rows) != 1:
        raise ValueError(f"Mã trại DB mới '{prison_code}' khớp {len(prison_rows)} trại trong DB mới. Cần đúng một dòng DM_TRAI_GIAMS.TG_MA để tiếp tục.")
    new_prison_id, prison_name = prison_rows[0]

    where = f' AND NVL("{AUDIT_DELETED}",0)=0' if has_deleted else ""
    new_sql = (f'SELECT "{new_master["id"]}","{new_master["hsld"]}" '
               f'FROM {qualified(new_schema_name, new_master["table"])} '
               f'WHERE "{new_master["trai"]}"=:prison_id{where}')
    _, new_rows = fetch_all(new_conn, new_sql, {"prison_id": new_prison_id})

    old_by_key, new_by_key = defaultdict(list), defaultdict(list)
    old_info, new_info = {}, {}
    for pid, hsld, _prison_code in old_rows:
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
    for oid, hsld, _prison_code in old_rows:
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
    return pairs, report, {"old_code": old_prison_code, "code": prison_code,
                           "name": norm_text(prison_name), "new_id": new_prison_id}


def load_dm_maps(conn, schema_name, new_schema, screens):
    tables = {kind[1] for s in screens for _o, _n, kind in s["cols"]
              if isinstance(kind, tuple) and kind[0] in ("dm", "dmlist", "dm_legacy")}
    maps = {}
    for table in tables:
        if table not in new_schema:
            continue
        code_col = dm_code_column(new_schema, table)
        deleted = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in {c[0] for c in new_schema.get(table, [])} else ""
        _, rows = fetch_all(conn, f'SELECT "ID","{code_col}" FROM {qualified(schema_name, table)}{deleted}')
        maps[table] = {norm_text(i): norm_text(code).strip() for i, code in rows}

    # These two legacy catalogs have explicit migration tables. Resolve the old
    # code through the imported *_OLD row ID and its mapping to the current DM ID.
    bridge_specs = {
        kind for s in screens for _o, _n, kind in s["cols"]
        if isinstance(kind, tuple) and kind[0] == "dm_legacy"
    }
    legacy_maps = {}
    for _tag, current_table, legacy_table, mapping_table, old_id_col, new_id_col in bridge_specs:
        current_code_col = dm_code_column(new_schema, current_table)
        legacy_cols = {c[0] for c in new_schema.get(legacy_table, [])}
        mapping_cols = {c[0] for c in new_schema.get(mapping_table, [])}
        current_cols = {c[0] for c in new_schema.get(current_table, [])}
        if not {"ID", current_code_col}.issubset(current_cols):
            raise ValueError(f"Schema thiếu {current_table}.ID hoặc {current_code_col}.")
        legacy_code_col = current_code_col
        if not {"ID", legacy_code_col}.issubset(legacy_cols):
            # The imported legacy catalog uses the same business code column name.
            raise ValueError(f"Schema thiếu bảng danh mục cũ {legacy_table} hoặc cột mã tương ứng.")
        required_mapping = {old_id_col, new_id_col}
        if not required_mapping.issubset(mapping_cols):
            raise ValueError(f"Schema thiếu cột {mapping_table}.{old_id_col}/{new_id_col}.")
        legacy_deleted = f' AND NVL(L."{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in legacy_cols else ""
        current_deleted = f' AND NVL(N."{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in current_cols else ""
        sql = (f'SELECT L."{legacy_code_col}",N."{current_code_col}" '
               f'FROM {qualified(schema_name, legacy_table)} L '
               f'JOIN {qualified(schema_name, mapping_table)} X ON X."{old_id_col}"=L."ID" '
               f'JOIN {qualified(schema_name, current_table)} N ON N."ID"=X."{new_id_col}" '
               f'WHERE L."{legacy_code_col}" IS NOT NULL{legacy_deleted}{current_deleted}')
        _, rows = fetch_all(conn, sql)
        candidates = defaultdict(set)
        for old_code, current_code in rows:
            old_key = norm_text(old_code).strip().casefold()
            if old_key:
                candidates[old_key].add(norm_text(current_code).strip().casefold())
        legacy_maps[kind] = {code: next(iter(values)) if len(values) == 1 else None
                             for code, values in candidates.items()}
    maps["__legacy_dm_maps__"] = legacy_maps
    return maps


def load_province_map(conn, schema_name, new_schema):
    """Map legacy province codes to the new DM_TINH_THANH_PHO IDs."""
    mapping_cols = {c[0] for c in new_schema.get("MAPPING_PROVINCE", [])}
    province_cols = {c[0] for c in new_schema.get("DM_TINH_THANH_PHO", [])}
    if not {"MA_TINH_OLD", "MA_TINH_NEW"}.issubset(mapping_cols) or not {"ID", "TTP_MA"}.issubset(province_cols):
        raise ValueError("Không thể đối chiếu mã tỉnh: DB mới thiếu MAPPING_PROVINCE hoặc DM_TINH_THANH_PHO.")
    ttp_deleted = f' AND NVL(T."{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in province_cols else ""
    sql = (f'SELECT MP."MA_TINH_OLD",T."ID" FROM {qualified(schema_name, "MAPPING_PROVINCE")} MP '
           f'JOIN {qualified(schema_name, "DM_TINH_THANH_PHO")} T '
           f'ON TRIM(MP."MA_TINH_NEW")=TRIM(T."TTP_MA"){ttp_deleted}')
    _, rows = fetch_all(conn, sql)
    found = defaultdict(set)
    for old_code, province_id in rows:
        key = norm_hsld(old_code)
        if key:
            found[key].add(norm_text(province_id))
    return {code: next(iter(ids)) if len(ids) == 1 else None for code, ids in found.items()}


def _rows_by_key(rows, key_indexes):
    grouped = defaultdict(list)
    for row in rows:
        key = tuple(row[i] for i in key_indexes)
        grouped[key].append(row)
    return grouped


def _sql_read(conn, schema, screen, side, schema_json, cancel, prison_id=None):
    table = screen[f"{side}_table"]
    person_col = screen[f"{side}_pn"]
    cols = [c[0 if side == "old" else 1] for c in screen["cols"]]
    select_cols = list(dict.fromkeys([person_col] + cols))
    sql = f'SELECT {",".join(chr(34) + c + chr(34) for c in select_cols)} FROM {qualified(schema, table)}'
    conditions, binds = [], {}
    if side == "new" and AUDIT_DELETED in {c[0] for c in schema_json.get(table, [])}:
        conditions.append(f'NVL("{AUDIT_DELETED}",0)=0')
    if side == "new" and prison_id is not None:
        person_table = qualified(schema, M.PN_NEW["table"])
        person_deleted = (f' AND NVL(P."{AUDIT_DELETED}",0)=0'
                          if AUDIT_DELETED in {c[0] for c in schema_json.get(M.PN_NEW["table"], [])} else "")
        conditions.append(
            f'EXISTS (SELECT 1 FROM {person_table} P WHERE P."{M.PN_NEW["id"]}"="{table}"."{person_col}" '
            f'AND P."{M.PN_NEW["trai"]}"=:prison_id{person_deleted})'
        )
        binds["prison_id"] = prison_id
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    _, rows = fetch_all(conn, sql, binds=binds, cancel=cancel)
    return rows, select_cols


def compare_screen(screen, old_conn, new_conn, schemas, old_schema_name, new_schema_name,
                   pairs, hsld_by_old, dm_maps, province_map=None, prison_id=None, cancel=None):
    old_schema, new_schema = schemas
    old_rows, old_select = _sql_read(old_conn, old_schema_name, screen, "old", old_schema, cancel)
    new_rows, new_select = _sql_read(new_conn, new_schema_name, screen, "new", new_schema, cancel, prison_id)
    old_person_col = screen["old_pn"]
    new_person_col = screen["new_pn"]
    old_person_index, new_person_index = old_select.index(old_person_col), new_select.index(new_person_col)
    old_people_with_data = len({raw[old_person_index] for raw in old_rows
                                if raw[old_person_index] is not None})
    new_people_with_data = len({raw[new_person_index] for raw in new_rows
                                if raw[new_person_index] is not None})
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
        normalized = []
        for i, col in zip(old_value_indexes, screen["cols"]):
            kind = col[2]
            if isinstance(kind, tuple) and kind[0] == "province":
                code = norm_hsld(raw[i])
                mapped = (province_map or {}).get(code) if code else ""
                normalized.append(mapped if mapped is not None else (f"?{code}" if code else ""))
            elif isinstance(kind, tuple) and kind[0] == "dm_legacy":
                code = norm_text(raw[i]).strip().casefold()
                if not code or code == "0":
                    normalized.append("")
                else:
                    mapped = (dm_maps.get("__legacy_dm_maps__", {}).get(kind, {}).get(code))
                    normalized.append(mapped if mapped is not None else f"?{code}")
            else:
                normalized.append(norm_value(raw[i], kind, None))
        row = tuple(normalized)
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
            if isinstance(kind, tuple) and kind[0] == "province":
                raw_value = raw[i]
                values.append("" if raw_value is None else norm_text(raw_value).strip())
            else:
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
               "old_people_with_data": old_people_with_data,
               "new_people_with_data": new_people_with_data,
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
        pairs, patients, prison_scope = load_person_crosswalk(
            old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        old_id_to_hsld = {r["old_id"]: r["old_hsld"] or "" for r in patients if r["old_id"] is not None}
        dm_maps = load_dm_maps(new_conn, new_cfg.get("schema", ""), new_schema, screens)
        province_map = load_province_map(new_conn, new_cfg.get("schema", ""), new_schema)
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
                                  "old_people_with_data": "", "new_people_with_data": "",
                                  "old_only": 0, "new_only": 0, "duplicates": 0,
                                  "unmapped_old_person_rows": 0, "unmapped_new_person_rows": 0,
                                  "status": "Chưa có mapping nguồn legacy"})
                continue
            try:
                summary, rows = compare_screen(screen, old_conn, new_conn, (old_schema, new_schema),
                                               old_cfg.get("schema", ""), new_cfg.get("schema", ""),
                                               pairs, old_id_to_hsld, dm_maps, province_map,
                                               prison_scope["new_id"], cancel)
                summaries.append(summary)
                details.extend(rows)
            except Exception as exc:
                summaries.append({"code": screen["code"], "group": screen["group"], "name": screen["name"],
                                  "old_table": screen["old_table"], "new_table": screen["new_table"],
                                  "old_total": "", "new_total": "", "matched": 0, "diff": 0,
                                  "old_people_with_data": "", "new_people_with_data": "",
                                  "old_only": 0, "new_only": 0, "duplicates": 0,
                                  "unmapped_old_person_rows": 0, "unmapped_new_person_rows": 0,
                                  "status": f"Lỗi truy vấn: {exc}"})
        return {"patients": patients, "summaries": summaries, "details": details,
                "prison_scope": prison_scope,
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


def preview_province_catalog_audit(old_cfg, new_cfg):
    """Compare MA_DP.MA directly with DM_TINH_THANH_PHO.TTP_MA."""
    old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
    new_conn = None
    try:
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        old_schema, new_schema = load_schema()
        old_tables = {"MA_DP": {c[0] for c in old_schema.get("MA_DP", [])}}
        new_tables = {"DM_TINH_THANH_PHO": {c[0] for c in new_schema.get("DM_TINH_THANH_PHO", [])}}
        required = {"MA_DP": {"MA", "ND"}, "DM_TINH_THANH_PHO": {"TTP_MA", "TTP_TEN"}}
        actual = {"MA_DP": old_tables["MA_DP"], **new_tables}
        missing = [f"{table}.{column}" for table, columns in required.items()
                   for column in columns if column not in actual.get(table, set())]
        if missing:
            raise ValueError("Schema đóng gói thiếu cột cần đối chiếu: " + ", ".join(missing))

        old_sql = (f'SELECT "MA", "ND" FROM {qualified(old_cfg.get("schema", ""), "MA_DP")} '
                   'ORDER BY "MA"')
        try:
            _, old_rows = fetch_all(old_conn, old_sql)
        except Exception as exc:
            raise RuntimeError(
                f"Đăng nhập DB cũ được nhưng không đọc được bảng "
                f"{qualified(old_cfg.get('schema', ''), 'MA_DP')}. "
                f"Kiểm tra owner/schema và quyền SELECT. Oracle: {exc}"
            ) from exc
        new_sql = (f'SELECT "TTP_MA", "TTP_TEN" '
                   f'FROM {qualified(new_cfg.get("schema", ""), "DM_TINH_THANH_PHO")} '
                   'WHERE NVL("IS_DELETED",0)=0 ORDER BY "TTP_MA"')
        try:
            _, new_rows = fetch_all(new_conn, new_sql)
        except Exception as exc:
            raise RuntimeError(
                f"Đăng nhập DB mới được nhưng không đọc được bảng "
                f"{qualified(new_cfg.get('schema', ''), 'DM_TINH_THANH_PHO')}. "
                f"Kiểm tra owner/schema và quyền SELECT. Oracle: {exc}"
            ) from exc
        # Codes are compared as trimmed strings. In particular, preserve leading
        # zeroes: code "01" must not be treated as the same code as "1" or "10101".
        new_by_code = defaultdict(list)
        for new_code, new_name in new_rows:
            code = norm_text(new_code).strip()
            if code:
                new_by_code[code].append(norm_text(new_name))

        rows = []
        counts = Counter()
        normalize_name = lambda value: "".join(
            ch for ch in unicodedata.normalize("NFD", norm_text(value)).casefold()
            if not unicodedata.combining(ch) and ch.isalnum())
        for old_code, old_name in old_rows:
            key = norm_text(old_code).strip()
            candidates = new_by_code.get(key, [])
            if not key:
                status, new_code, new_name = "Mã cũ trống", "", ""
            elif not candidates:
                status, new_code, new_name = "Mã cũ không có ở DB mới", "", ""
            elif len(candidates) > 1:
                status, new_code, new_name = "Mã DB mới bị trùng", key, " | ".join(candidates)
            else:
                new_code, new_name = key, candidates[0]
                status = "Cùng mã nhưng khác tên" if normalize_name(old_name) != normalize_name(new_name) else "Khớp"
            counts[status] += 1
            if status != "Khớp":
                rows.append({"old_code": norm_text(old_code), "old_name": norm_text(old_name),
                             "new_code": new_code, "new_name": new_name, "status": status})
        return {"rows": rows, "counts": dict(counts), "old_count": len(old_rows)}
    finally:
        old_conn.close()
        if new_conn:
            new_conn.close()


def _ward_catalog_plan(old_conn, new_conn, old_schema_name, new_schema_name):
    old_required = {"MA", "ND", "MA_QH"}
    new_required = {"ID", "XP_MA", "XP_MA_TINH_THANH_PHO", "XP_TEN", "XP_TRANG_THAI", "CREATION_TIME", "IS_DELETED"}
    old_cols = _oracle_table_columns(old_conn, old_schema_name, "MA_DP_XA_PHUONG")
    new_cols = _oracle_table_columns(new_conn, new_schema_name, "DM_XA_PHUONG")
    missing_old, missing_new = old_required - old_cols, new_required - new_cols
    if missing_old or missing_new:
        details = []
        if missing_old: details.append("DB cũ thiếu MA_DP_XA_PHUONG." + ", ".join(sorted(missing_old)))
        if missing_new: details.append("DB mới thiếu DM_XA_PHUONG." + ", ".join(sorted(missing_new)))
        raise ValueError("; ".join(details))

    _, old_rows = fetch_all(old_conn, f'SELECT "MA","ND","MA_QH" FROM {qualified(old_schema_name, "MA_DP_XA_PHUONG")} ORDER BY "MA"')
    new_deleted = ' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in new_cols else ""
    _, new_rows = fetch_all(new_conn, f'SELECT "XP_MA" FROM {qualified(new_schema_name, "DM_XA_PHUONG")}{new_deleted}')
    new_codes = {norm_text(row[0]).strip() for row in new_rows if norm_text(row[0]).strip()}

    # Verify every MA_QH can be used as a province code in the target catalog.
    ttp_cols = _oracle_table_columns(new_conn, new_schema_name, "DM_TINH_THANH_PHO")
    if not {"TTP_MA"} <= ttp_cols:
        raise ValueError("DB mới thiếu DM_TINH_THANH_PHO.TTP_MA để kiểm tra MA_QH.")
    ttp_deleted = ' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in ttp_cols else ""
    _, ttp_rows = fetch_all(new_conn, f'SELECT "TTP_MA" FROM {qualified(new_schema_name, "DM_TINH_THANH_PHO")}{ttp_deleted}')
    ttp_codes = {norm_text(row[0]).strip() for row in ttp_rows if norm_text(row[0]).strip()}

    seen, rows = set(), []
    for code_value, name_value, province_value in old_rows:
        code, name = norm_text(code_value).strip(), norm_text(name_value).strip()
        source_province = norm_text(province_value).strip()
        # The target column is NOT NULL. Use the agreed sentinel for legacy rows
        # without a district/province code instead of attempting to insert NULL.
        province = source_province or "00"
        if not code or code in new_codes:
            continue
        if code in seen:
            rows.append({"code": code, "province_code": province, "name": name, "status": 1,
                         "deleted": 0, "result": "Mã MA bị trùng trong DB cũ", "insertable": False,
                         "province_warning": False})
            continue
        seen.add(code)
        issues = []
        if not code: issues.append("Mã MA trống")
        if not name: issues.append("Tên ND trống")
        if province and province not in ttp_codes: issues.append("MA_QH không có trong TTP_MA DB mới")
        required_issue = not code or not name
        rows.append({"code": code, "province_code": province, "name": name, "status": 1,
                     "deleted": 0, "result": "; ".join(issues) if issues else "Sẵn sàng insert",
                     "insertable": not required_issue,
                     "province_warning": province not in ttp_codes,
                     "province_null": not source_province})
    return {"rows": rows, "old_count": len(old_rows), "ready_count": sum(r["insertable"] for r in rows),
            "issue_count": sum(not r["insertable"] for r in rows)}


def preview_ward_catalog_sync(old_cfg, new_cfg):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _ward_catalog_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""))
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try: conn.rollback(); conn.close()
                except Exception: pass


def insert_ward_catalog_missing(old_cfg, new_cfg, preview):
    old_conn = new_conn = cursor = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _ward_catalog_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""))
        expected = [(r["code"], r["province_code"], r["name"], r["insertable"], r.get("province_warning", False), r.get("province_null", False)) for r in preview["rows"]]
        actual = [(r["code"], r["province_code"], r["name"], r["insertable"], r.get("province_warning", False), r.get("province_null", False)) for r in fresh["rows"]]
        if expected != actual:
            raise ValueError("Dữ liệu danh mục đã thay đổi so với preview. Chưa ghi gì; hãy preview lại.")
        cursor = new_conn.cursor()
        target = qualified(new_cfg.get("schema", ""), "DM_XA_PHUONG")
        sql = (f'INSERT INTO {target} ("XP_MA","XP_MA_TINH_THANH_PHO","XP_TEN",'
               '"XP_TRANG_THAI","CREATION_TIME","IS_DELETED") '
               'SELECT :code,:province,:name,1,SYSTIMESTAMP,0 FROM DUAL '
               f'WHERE NOT EXISTS (SELECT 1 FROM {target} WHERE TRIM("XP_MA")=:code)')
        inserted = skipped = 0
        for row in fresh["rows"]:
            if not row["insertable"]:
                continue
            cursor.execute(sql, {"code": row["code"], "province": row["province_code"], "name": row["name"]})
            if cursor.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        new_conn.commit()
        return {"inserted": inserted, "skipped": skipped}
    except Exception:
        if new_conn: new_conn.rollback()
        raise
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        for conn in (old_conn, new_conn):
            if conn:
                try: conn.rollback(); conn.close()
                except Exception: pass


REDUCTION_FIELDS = [
    ("SO_QD_GIAM", "SO_QUYET_DINH", M.T),
    ("NGAY_QD_GIAM", "NGAY_QUYET_DINH", M.D),
    ("MA_MUC_QD_GIAM_TOA_AN", "MUC_GIAM_ID", M.dm(M.MTG)),
    ("MA_CQ_TOA_QD_GIAM", "TOA_QUYET_DINH_ID", M.dm(M.CQ)),
    # This legacy code is a province code (e.g. 40300 = Nghệ An), not a
    # ward/district code from DM_DIA_PHUONG. Resolve through MAPPING_PROVINCE
    # and store the matched DM_TINH_THANH_PHO.ID.
    ("MA_DP_TOA_QD_GIAM", "DIA_PHUONG_ID", ("province", "MAPPING_PROVINCE")),
    ("NGAY_THA_GIAM_HET_AN", "NGAY_THA_GIAM_HET_AN", M.D),
]


def _reduction_plan(old_conn, new_conn, old_schema_name, new_schema_name, prison_code):
    pairs, patients, prison_scope = load_person_crosswalk(
        old_conn, new_conn, old_schema_name, new_schema_name, prison_code)
    old_table = next(s["old_table"] for s in M.SCREENS if s["code"] == "DB01_GiamThoiHan")
    old_select = ["PN_ID", "NGAY_XET", *[field[0] for field in REDUCTION_FIELDS]]
    new_select = ["ID", "PHAM_NHAN_ID", "NGAY_XET", *[field[1] for field in REDUCTION_FIELDS]]
    _, old_rows = fetch_all(old_conn, f'SELECT {",".join(chr(34)+c+chr(34) for c in old_select)} FROM {qualified(old_schema_name, old_table)}')

    _, new_schema = load_schema()
    dm_tables = {kind[1] for _, _, kind in REDUCTION_FIELDS
                 if isinstance(kind, tuple) and kind[0] == "dm"}
    dm_by_code = {}
    dm_ambiguous = set()
    for table in dm_tables:
        code_col = dm_code_column(new_schema, table)
        dm_where = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in {c[0] for c in new_schema.get(table, [])} else ""
        _, rows = fetch_all(new_conn, f'SELECT "ID","{code_col}" FROM {qualified(new_schema_name, table)}{dm_where}')
        index = defaultdict(list)
        for dm_id, code in rows:
            key = norm_hsld(code)
            if key:
                index[key].append(dm_id)
        dm_by_code[table] = index
        dm_ambiguous.update((table, key) for key, ids in index.items() if len(set(ids)) > 1)

    # Legacy MA_DP_TOA_QD_GIAM values use old province codes. Convert them
    # through the explicit old->new province mapping, then resolve the new
    # code against DM_TINH_THANH_PHO. The destination column stores that
    # table's ID (for Nghệ An in the user's database, ID 29).
    province_by_old_code = defaultdict(list)
    mapping_table = "MAPPING_PROVINCE"
    if mapping_table in new_schema and "DM_TINH_THANH_PHO" in new_schema:
        _, province_rows = fetch_all(
            new_conn,
            f'SELECT MP."MA_TINH_OLD", TTP."ID" '
            f'FROM {qualified(new_schema_name, mapping_table)} MP '
            f'JOIN {qualified(new_schema_name, "DM_TINH_THANH_PHO")} TTP '
            f'ON TRIM(MP."MA_TINH_NEW")=TRIM(TTP."TTP_MA") '
            f'AND NVL(TTP."IS_DELETED",0)=0'
        )
        for old_code, province_id in province_rows:
            key = norm_hsld(old_code)
            if key:
                province_by_old_code[key].append(province_id)

    old_by_new_person_date = defaultdict(list)
    for row in old_rows:
        old_person = row[0]
        new_person = pairs.get(old_person)
        day = norm_value(row[1], M.D)
        if new_person is not None and day:
            old_by_new_person_date[(new_person, day)].append(row)

    dest_cols = [field[1] for field in REDUCTION_FIELDS]
    target_sql = (
        f'SELECT T."ID",T."PHAM_NHAN_ID",T."NGAY_XET",{",".join("T."+chr(34)+c+chr(34) for c in dest_cols)} '
        f'FROM {qualified(new_schema_name, "GIAM_THOI_HANS")} T '
        f'WHERE NVL(T."IS_DELETED",0)=0 AND EXISTS '
        f'(SELECT 1 FROM {qualified(new_schema_name, M.PN_NEW["table"])} P '
        f'WHERE P."{M.PN_NEW["id"]}"=T."PHAM_NHAN_ID" '
        f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0)'
    )
    _, target_rows = fetch_all(new_conn, target_sql, {"prison_id": prison_scope["new_id"]})
    target_by_new_person_date = defaultdict(list)
    for row in target_rows:
        day = norm_value(row[2], M.D)
        if day:
            target_by_new_person_date[(row[1], day)].append(row)

    patient_hsld = {r["new_id"]: r["old_hsld"] for r in patients if r.get("new_id") is not None}
    updates, issues = [], []
    considered = 0
    for row in old_rows:
        if row[0] not in pairs:
            issues.append({"hsld": "", "ngay_xet": "", "status": "Không ghép được phạm nhân theo HSLĐ",
                           "old_count": 1, "new_count": 0})
        elif not norm_value(row[1], M.D):
            issues.append({"hsld": patient_hsld.get(pairs[row[0]], ""), "ngay_xet": "", "status": "Thiếu ngày xét",
                           "old_count": 1, "new_count": 0})
    for key, old_group in old_by_new_person_date.items():
        new_group = target_by_new_person_date.get(key, [])
        hsld = patient_hsld.get(key[0], "")
        if len(old_group) != 1 or len(new_group) != 1:
            considered += 1
            issue = "Trùng khóa nguồn" if len(old_group) != 1 else "Không tìm thấy dòng đích" if not new_group else "Trùng khóa đích"
            issues.append({"hsld": hsld, "ngay_xet": key[1], "status": issue,
                           "old_count": len(old_group), "new_count": len(new_group)})
            continue
        source, target = old_group[0], new_group[0]
        change = {"id": target[0], "new_person_id": key[0], "hsld": hsld,
                  "ngay_xet": key[1], "fields": {}, "expected": {}, "display": []}
        for offset, (old_col, new_col, kind) in enumerate(REDUCTION_FIELDS):
            source_value = source[2 + offset]
            target_value = target[3 + offset]
            source_present = source_value is not None and norm_text(source_value) != ""
            target_present = target_value is not None and norm_text(target_value) != ""
            mapped_value = source_value
            is_province = isinstance(kind, tuple) and kind[0] == "province"
            is_correctable = is_province or new_col == "MUC_GIAM_ID"
            province_resolved = False
            can_update = source_present and (not target_present or is_correctable)
            if can_update and isinstance(kind, tuple):
                code = norm_hsld(source_value)
                if kind[0] == "province":
                    matches = province_by_old_code.get(code, [])
                    ambiguous = len(set(matches)) > 1
                else:
                    dm_table = kind[1]
                    matches = dm_by_code.get(dm_table, {}).get(code, [])
                    ambiguous = (dm_table, code) in dm_ambiguous
                if len(set(matches)) != 1 or ambiguous:
                    issues.append({"hsld": hsld, "ngay_xet": key[1], "status": f"Không ánh xạ duy nhất {old_col} sang {new_col}",
                                   "old_count": 1, "new_count": 1, "target_id": target[0],
                                   "field": new_col, "source_value": norm_text(source_value),
                                   "target_value": norm_text(target_value)})
                    can_update = False
                else:
                    mapped_value = next(iter(set(matches)))
                    province_resolved = is_province
            # Other fields only fill blanks. Province and court-reduction
            # amount also repair a non-null value when it differs from the
            # uniquely mapped destination ID.
            if can_update and target_present and is_correctable:
                can_update = norm_text(target_value) != norm_text(mapped_value)
            elif can_update and target_present:
                can_update = False
            if can_update:
                change["fields"][new_col] = mapped_value
                change["expected"][new_col] = target_value if target_present else None
            # Keep one row per reduction ID. Hide already-correct province
            # IDs; show an incorrect value and its replacement inline.
            if is_province and target_present and province_resolved and not can_update:
                display_new = ""
                display_old = ""
            elif is_correctable and target_present and can_update:
                display_new = f"{norm_text(target_value)} → {norm_text(mapped_value)}"
                display_old = norm_text(source_value)
            else:
                display_new = mapped_value if can_update else target_value if target_present else None
                display_old = norm_text(source_value)
            change["display"].append({"field": new_col, "old": display_old,
                                      "new": norm_text(display_new)})
        if change["fields"]:
            updates.append(change)
    return {"updates": updates, "issues": issues, "prison_scope": prison_scope,
            "matched_rows": len(updates), "field_count": sum(len(row["fields"]) for row in updates),
            "ambiguous_rows": sum(1 for issue in issues if issue["status"] in ("Trùng khóa nguồn", "Trùng khóa đích")),
            "unmatched_rows": sum(1 for issue in issues if issue["status"] == "Không tìm thấy dòng đích"),
            "considered_rows": considered}


def preview_reduction_update(old_cfg, new_cfg):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _reduction_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


def apply_reduction_update(old_cfg, new_cfg, preview, selected_fields=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _reduction_plan(old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        expected = [(r["id"], r["fields"], r.get("expected", {})) for r in preview["updates"]]
        actual = [(r["id"], r["fields"], r.get("expected", {})) for r in fresh["updates"]]
        if expected != actual:
            raise ValueError("Dữ liệu đã thay đổi so với xem trước. Không ghi gì; hãy tải lại xem trước rồi xác nhận lại.")
        if selected_fields is not None:
            allowed_fields = {(row["id"], column) for row in preview["updates"] for column in row["fields"]}
            selected_fields = set(selected_fields)
            if not selected_fields or not selected_fields.issubset(allowed_fields):
                raise ValueError("Danh sách trường được chọn không còn hợp lệ. Hãy tải lại xem trước.")
            for row in fresh["updates"]:
                row["fields"] = {column: value for column, value in row["fields"].items()
                                 if (row["id"], column) in selected_fields}
                row["expected"] = {column: value for column, value in row.get("expected", {}).items()
                                    if (row["id"], column) in selected_fields}
            fresh["updates"] = [row for row in fresh["updates"] if row["fields"]]
            fresh["field_count"] = sum(len(row["fields"]) for row in fresh["updates"])
        if not fresh["updates"]:
            raise ValueError("Không còn trường nào cần cập nhật trong lựa chọn hiện tại.")
        cursor = new_conn.cursor()
        table = qualified(new_cfg.get("schema", ""), "GIAM_THOI_HANS")
        for row in fresh["updates"]:
            fields = row["fields"]
            assignments = ",".join(f'"{column}"=:v_{i}' for i, column in enumerate(fields))
            conditions = []
            binds = {f"v_{i}": value for i, value in enumerate(fields.values())}
            for i, column in enumerate(fields):
                expected_value = row.get("expected", {}).get(column)
                if expected_value is None:
                    conditions.append(f'"{column}" IS NULL')
                else:
                    conditions.append(f'"{column}"=:expected_{i}')
                    binds[f"expected_{i}"] = expected_value
            binds.update({"target_id": row["id"], "prison_id": fresh["prison_scope"]["new_id"]})
            cursor.execute(
                f'UPDATE {table} SET {assignments} WHERE "ID"=:target_id AND NVL("IS_DELETED",0)=0 '
                f'AND "PHAM_NHAN_ID"=:person_id AND EXISTS '
                f'(SELECT 1 FROM {qualified(new_cfg.get("schema", ""), M.PN_NEW["table"])} P '
                f'WHERE P."{M.PN_NEW["id"]}"=:person_id AND P."{M.PN_NEW["trai"]}"=:prison_id '
                f'AND NVL(P."IS_DELETED",0)=0) AND {" AND ".join(conditions)}',
                {**binds, "person_id": row["new_person_id"]})
            if cursor.rowcount != 1:
                raise RuntimeError("Có dòng đích đã thay đổi hoặc không còn thuộc trại đã chọn; toàn bộ cập nhật sẽ được rollback.")
        cursor.close()
        new_conn.commit()
        return {"updated_rows": len(fresh["updates"]), "updated_fields": fresh["field_count"],
                "prison_scope": fresh["prison_scope"]}
    except Exception:
        if new_conn:
            new_conn.rollback()
        raise
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


REDUCTION_INSERT_SPECS = [
    # Source, target, conversion, required. A non-empty source that cannot be
    # mapped uniquely blocks insertion of the whole row.
    ("NGAY_XET", "NGAY_XET", M.D, True),
    ("MA_MUC_DN_GIAM_TG", "MUC_DE_NGHI_ID", ("dm_id", M.MTG), True),
    ("MA_MUC_DN_GIAM_V26", "CAP_TREN_DUYET_ID", ("dm_id", M.MTG), False),
    ("MA_MUC_TG_CHAP_HANH", "DA_CHAP_HANH", ("dm_title", M.MTG), False),
    ("MA_MUC_TG_CON_LAI", "CON_LAI", ("dm_title", M.MTG), False),
    ("SO_QD_GIAM", "SO_QUYET_DINH", M.T, False),
    ("NGAY_QD_GIAM", "NGAY_QUYET_DINH", M.D, False),
    ("MA_MUC_QD_GIAM_TOA_AN", "MUC_GIAM_ID", ("dm_id", M.MTG), False),
    ("MA_CQ_TOA_QD_GIAM", "TOA_QUYET_DINH_ID", ("dm_id", M.CQ), False),
    ("MA_DP_TOA_QD_GIAM", "DIA_PHUONG_ID", ("province_id", "MAPPING_PROVINCE"), False),
    ("NGAY_THA_GIAM_HET_AN", "NGAY_THA_GIAM_HET_AN", M.D, False),
    ("NHAN_XET_TG", "NHAN_XET", M.T, False),
    ("KQCT_PHIEU_GIAM", "KQCT_PHIEU", M.T, False),
    ("KQCT_DS_GIAM", "KQCT_DANHSACH", M.T, False),
]


def _reduction_supplement_plan(old_conn, new_conn, old_schema_name, new_schema_name, prison_code):
    pairs, patients, prison_scope = load_person_crosswalk(
        old_conn, new_conn, old_schema_name, new_schema_name, prison_code)
    old_schema, new_schema = load_schema()
    old_columns = {column[0] for column in old_schema.get("PN_GIAM_THOI_HAN", [])}
    new_columns = {column[0] for column in new_schema.get("GIAM_THOI_HANS", [])}
    missing_old = [source for source, _target, _kind, _required in REDUCTION_INSERT_SPECS
                   if source not in old_columns]
    if missing_old:
        raise ValueError("Schema DB cũ thiếu cột giảm thời hạn cần cho bổ sung: " + ", ".join(missing_old))
    missing_new = [target for _source, target, _kind, _required in REDUCTION_INSERT_SPECS
                   if target not in new_columns]
    if missing_new or not {"ID", "PHAM_NHAN_ID", "CREATION_TIME", "IS_DELETED"}.issubset(new_columns):
        required_columns = sorted(set(missing_new) | ({"ID", "PHAM_NHAN_ID", "CREATION_TIME", "IS_DELETED"} - new_columns))
        raise ValueError("Schema DB mới thiếu cột giảm thời hạn cần cho bổ sung: " + ", ".join(required_columns))

    old_select = ["PN_ID", *dict.fromkeys(source for source, _target, _kind, _required
                                           in REDUCTION_INSERT_SPECS)]
    _, old_rows = fetch_all(
        old_conn,
        f'SELECT {",".join(chr(34)+column+chr(34) for column in old_select)} '
        f'FROM {qualified(old_schema_name, "PN_GIAM_THOI_HAN")}')

    dm_tables = {kind[1] for _source, _target, kind, _required in REDUCTION_INSERT_SPECS
                 if isinstance(kind, tuple) and kind[0] in ("dm_id", "dm_title")}
    dm_by_code = defaultdict(lambda: defaultdict(list))
    for table in dm_tables:
        code_col = dm_code_column(new_schema, table)
        columns = {column[0] for column in new_schema.get(table, [])}
        title_col = "MTG_TITLE" if table == M.MTG else None
        if title_col and title_col not in columns:
            raise ValueError(f"Schema DB mới thiếu {table}.{title_col} để đổi mã thời gian sang tên hiển thị.")
        selected = f'"ID","{code_col}"' + (f',"{title_col}"' if title_col else "")
        deleted = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in columns else ""
        _, rows = fetch_all(new_conn, f'SELECT {selected} FROM {qualified(new_schema_name, table)}{deleted}')
        for row in rows:
            dm_by_code[table][norm_hsld(row[1])].append((row[0], row[2] if title_col else None))

    province_by_old_code = defaultdict(list)
    if "MAPPING_PROVINCE" in new_schema and "DM_TINH_THANH_PHO" in new_schema:
        province_columns = {column[0] for column in new_schema["MAPPING_PROVINCE"]}
        ttp_columns = {column[0] for column in new_schema["DM_TINH_THANH_PHO"]}
        if not {"MA_TINH_OLD", "MA_TINH_NEW"}.issubset(province_columns) or not {"ID", "TTP_MA"}.issubset(ttp_columns):
            raise ValueError("Schema DB mới thiếu cột trong MAPPING_PROVINCE/DM_TINH_THANH_PHO để ánh xạ tỉnh.")
        ttp_deleted = f' AND NVL(TTP."{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in ttp_columns else ""
        _, rows = fetch_all(
            new_conn,
            f'SELECT MP."MA_TINH_OLD",TTP."ID" '
            f'FROM {qualified(new_schema_name, "MAPPING_PROVINCE")} MP '
            f'JOIN {qualified(new_schema_name, "DM_TINH_THANH_PHO")} TTP '
            f'ON TRIM(MP."MA_TINH_NEW")=TRIM(TTP."TTP_MA"){ttp_deleted}')
        for old_code, province_id in rows:
            key = norm_hsld(old_code)
            if key:
                province_by_old_code[key].append(province_id)

    new_table = qualified(new_schema_name, "GIAM_THOI_HANS")
    person_table = qualified(new_schema_name, M.PN_NEW["table"])
    _, target_rows = fetch_all(
        new_conn,
        f'SELECT T."PHAM_NHAN_ID",T."NGAY_XET" FROM {new_table} T '
        f'WHERE NVL(T."IS_DELETED",0)=0 AND EXISTS '
        f'(SELECT 1 FROM {person_table} P WHERE P."{M.PN_NEW["id"]}"=T."PHAM_NHAN_ID" '
        f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0)',
        {"prison_id": prison_scope["new_id"]})
    target_by_key = defaultdict(list)
    for person_id, review_date in target_rows:
        day = norm_value(review_date, M.D)
        if day:
            target_by_key[(person_id, day)].append(review_date)

    old_to_hsld = {row.get("old_id"): row.get("old_hsld", "") for row in patients
                   if row.get("old_id") is not None}
    old_groups = defaultdict(list)
    issues = []
    for source in old_rows:
        old_person_id = source[0]
        new_person_id = pairs.get(old_person_id)
        day = norm_value(source[old_select.index("NGAY_XET")], M.D)
        hsld = old_to_hsld.get(old_person_id, "")
        if new_person_id is None:
            issues.append({"hsld": norm_text(hsld), "ngay_xet": day,
                           "status": "Không ghép được phạm nhân theo HSLĐ"})
            continue
        if not day:
            issues.append({"hsld": norm_text(hsld), "ngay_xet": "", "status": "Thiếu ngày xét"})
            continue
        old_groups[(new_person_id, day)].append(source)

    inserts = []
    for (new_person_id, day), source_group in old_groups.items():
        hsld = norm_text(old_to_hsld.get(source_group[0][0], ""))
        if len(source_group) != 1:
            issues.append({"hsld": hsld, "ngay_xet": day, "status": "Trùng khóa nguồn",
                           "old_count": len(source_group), "new_count": len(target_by_key.get((new_person_id, day), []))})
            continue
        target_group = target_by_key.get((new_person_id, day), [])
        if len(target_group) == 1:
            continue
        if len(target_group) > 1:
            issues.append({"hsld": hsld, "ngay_xet": day, "status": "Trùng khóa đích",
                           "old_count": 1, "new_count": len(target_group)})
            continue

        source = source_group[0]
        source_values = dict(zip(old_select, source))
        target_values = {}
        display, mapping_errors = [], []
        for source_col, target_col, kind, required in REDUCTION_INSERT_SPECS:
            value = source_values[source_col]
            is_present = value is not None and norm_text(value) != ""
            mapped = value if is_present else None
            if is_present and isinstance(kind, tuple):
                code = norm_hsld(value)
                if kind[0] in ("dm_id", "dm_title"):
                    matches = dm_by_code[kind[1]].get(code, [])
                    unique_ids = {item[0] for item in matches}
                    if len(unique_ids) != 1:
                        mapping_errors.append(f"{source_col} → {target_col}: mã '{norm_text(value)}' khớp {len(unique_ids)} danh mục")
                        mapped = None
                    else:
                        match = next(item for item in matches if item[0] in unique_ids)
                        mapped = match[0] if kind[0] == "dm_id" else match[1]
                        if mapped is None or norm_text(mapped) == "":
                            mapping_errors.append(f"{source_col} → {target_col}: danh mục '{norm_text(value)}' thiếu tên hiển thị")
                            mapped = None
                elif kind[0] == "province_id":
                    matches = set(province_by_old_code.get(code, []))
                    if len(matches) != 1:
                        mapping_errors.append(f"{source_col} → {target_col}: mã tỉnh '{norm_text(value)}' khớp {len(matches)} tỉnh")
                        mapped = None
                    else:
                        mapped = next(iter(matches))
            if required and (mapped is None or norm_text(mapped) == ""):
                if not any(source_col in error for error in mapping_errors):
                    mapping_errors.append(f"Thiếu giá trị bắt buộc {target_col} từ {source_col}")
            target_values[target_col] = mapped
            display.append({"field": target_col, "old": norm_text(value), "new": norm_text(mapped)})

        if mapping_errors:
            issues.append({"hsld": hsld, "ngay_xet": day,
                           "status": "Không thể bổ sung: " + "; ".join(mapping_errors),
                           "old_count": 1, "new_count": 0})
            continue
        source_person_id = source_values["PN_ID"]
        insert_key = (source_person_id, day)
        inserts.append({"insert_key": insert_key, "old_person_id": source_person_id,
                        "new_person_id": new_person_id, "hsld": hsld, "ngay_xet": day,
                        "fields": target_values, "display": display})

    inserts.sort(key=lambda row: (not bool(row["hsld"]), row["hsld"].casefold(), row["ngay_xet"], str(row["old_person_id"])))
    issues.sort(key=lambda row: (not bool(row.get("hsld")), str(row.get("hsld", "")).casefold(),
                                 str(row.get("ngay_xet", "")), row["status"]))
    return {"inserts": inserts, "issues": issues, "prison_scope": prison_scope,
            "insert_count": len(inserts)}


def preview_reduction_supplement(old_cfg, new_cfg):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _reduction_supplement_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                                          new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


def apply_reduction_supplement(old_cfg, new_cfg, preview, selected_keys=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _reduction_supplement_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                                           new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        expected = [(row["insert_key"], row["new_person_id"], row["fields"]) for row in preview["inserts"]]
        actual = [(row["insert_key"], row["new_person_id"], row["fields"]) for row in fresh["inserts"]]
        if (expected != actual or preview.get("issues") != fresh.get("issues")
                or preview.get("prison_scope") != fresh.get("prison_scope")):
            raise ValueError("Dữ liệu hoặc danh mục đã thay đổi so với xem trước. Không ghi gì; hãy tải lại xem trước rồi xác nhận lại.")
        if selected_keys is not None:
            allowed = {row["insert_key"] for row in preview["inserts"]}
            selected_keys = set(selected_keys)
            if not selected_keys or not selected_keys.issubset(allowed):
                raise ValueError("Danh sách dòng được chọn không còn hợp lệ. Hãy tải lại xem trước.")
            fresh["inserts"] = [row for row in fresh["inserts"] if row["insert_key"] in selected_keys]
        if not fresh["inserts"]:
            raise ValueError("Không còn dòng nào đủ điều kiện bổ sung trong lựa chọn hiện tại.")

        table = qualified(new_cfg.get("schema", ""), "GIAM_THOI_HANS")
        person_table = qualified(new_cfg.get("schema", ""), M.PN_NEW["table"])
        cursor = new_conn.cursor()
        for row in fresh["inserts"]:
            # Omit optional NULL columns from the INSERT. This lets Oracle use
            # the destination column type directly rather than infer a bind
            # type for a NULL selected from DUAL.
            fields = {column: value for column, value in row["fields"].items() if value is not None}
            columns = list(fields)
            binds = {f"v_{index}": value for index, value in enumerate(fields.values())}
            bind_columns = [f":v_{index}" for index in range(len(columns))]
            columns.extend(("CREATION_TIME", "IS_DELETED", "PHAM_NHAN_ID"))
            bind_columns.extend(("SYSTIMESTAMP", "0", ":person_id"))
            binds.update({"person_id": row["new_person_id"], "review_date": fields["NGAY_XET"],
                          "prison_id": fresh["prison_scope"]["new_id"]})
            cursor.execute(
                f'INSERT INTO {table} ({",".join(chr(34)+column+chr(34) for column in columns)}) '
                f'SELECT {",".join(bind_columns)} FROM DUAL WHERE EXISTS '
                f'(SELECT 1 FROM {person_table} P WHERE P."{M.PN_NEW["id"]}"=:person_id '
                f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0) '
                f'AND NOT EXISTS (SELECT 1 FROM {table} T WHERE NVL(T."IS_DELETED",0)=0 '
                f'AND T."PHAM_NHAN_ID"=:person_id AND TRUNC(T."NGAY_XET")=TRUNC(:review_date))', binds)
            if cursor.rowcount != 1:
                raise RuntimeError("Dòng đích cùng phạm nhân/ngày xét vừa xuất hiện hoặc insert không thành công; toàn bộ lượt bổ sung sẽ rollback.")
        cursor.close()
        new_conn.commit()
        return {"inserted_rows": len(fresh["inserts"]), "prison_scope": fresh["prison_scope"]}
    except Exception:
        if new_conn:
            new_conn.rollback()
        raise
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


BIOGRAPHY_FIELDS = [
    ("TOM_TAT_HV", "LL_TOM_TAT_HV"),
    ("CHI_TIET_HV", "LL_CHI_TIET_HV"),
    ("SO_TIEN_AN", "LL_SO_TIEN_AN"),
    ("NHAN_THAN", "LL_NHAN_THAN"),
]
BIOGRAPHY_DIRECT_DM_FIELDS = [
    {"old": "MA_TAI_PHAM", "new": "LL_TAI_PHAM", "old_table": "MA_TAI_PHAM",
     "new_table": "DM_TAI_PHAMS", "code": "TP_MA", "name": "TP_TEN", "label": "Tái phạm"},
]
BIOGRAPHY_LEGACY_DM_FIELDS = [
    {"old": "MA_DAN_TOC", "new": "LL_DM_DAN_TOC_ID", "old_table": "MA_DAN_TOC",
     "legacy_table": "DM_DAN_TOCS_OLD", "current_table": "DM_DAN_TOCS",
     "code": "DT_MA", "name": "DT_TEN", "label": "Dân tộc"},
    {"old": "MA_TON_GIAO", "new": "LL_DM_TON_GIAO_ID", "old_table": "MA_TON_GIAO",
     "legacy_table": "DM_TON_GIAOS_OLD", "current_table": "DM_TON_GIAOS",
     "code": "TG_MA", "name": "TG_TEN", "label": "Tôn giáo"},
]
BIOGRAPHY_DURATION_FIELDS = [
    ("MA_MUC_TAM_GIAM", "THA_THOI_GIAN_TAM_GIAM", "Thời gian tạm giam"),
    ("MA_MUC_TAM_GIU", "THA_THOI_GIAN_TAM_GIU", "Thời gian tạm giữ"),
]
def _duration_key(value):
    value = norm_text(value).casefold()
    return "".join(char for char in unicodedata.normalize("NFD", value)
                   if unicodedata.category(char) != "Mn")


def _biography_legacy_dm_maps(old_conn, new_conn, old_schema_name, new_schema_name, selected_fields):
    """Resolve legacy person codes through new DB *_OLD and explicit mapping tables."""
    maps = {}
    for spec in BIOGRAPHY_LEGACY_DM_FIELDS:
        if spec["new"] not in selected_fields:
            continue
        old_columns = _oracle_table_columns(old_conn, old_schema_name, spec["old_table"])
        if not {"MA", "ND"}.issubset(old_columns):
            raise ValueError(f'DB cũ thiếu {spec["old_table"]}.MA/ND để hiển thị {spec["label"]}.')
        _, source_rows = fetch_all(old_conn,
            f'SELECT "MA","ND" FROM {qualified(old_schema_name, spec["old_table"])}')
        source_names = defaultdict(list)
        for code, name in source_rows:
            key = norm_hsld(code)
            if key:
                source_names[key].append(norm_text(name))

        legacy_columns = _oracle_table_columns(new_conn, new_schema_name, spec["legacy_table"])
        current_columns = _oracle_table_columns(new_conn, new_schema_name, spec["current_table"])
        required = {
            spec["legacy_table"]: {"ID", spec["code"]},
            spec["current_table"]: {"ID", spec["code"], spec["name"]},
        }
        actual = {spec["legacy_table"]: legacy_columns,
                  spec["current_table"]: current_columns}
        missing = [f"{table}.{column}" for table, columns in required.items()
                   for column in columns - actual[table]]
        if missing:
            raise ValueError("DB mới thiếu cột để ánh xạ " + spec["label"] + ": " + ", ".join(missing))
        legacy_deleted = (f' AND NVL(L."IS_DELETED",0)=0'
                          if "IS_DELETED" in legacy_columns else "")
        current_deleted = (f' AND NVL(N."IS_DELETED",0)=0'
                           if "IS_DELETED" in current_columns else "")
        sql = (f'SELECT L."{spec["code"]}",N."ID",N."{spec["code"]}",N."{spec["name"]}" '
               f'FROM {qualified(new_schema_name, spec["legacy_table"])} L '
               f'JOIN {qualified(new_schema_name, spec["current_table"])} N '
               'ON N."ID"=L."ID" '
               f'WHERE L."{spec["code"]}" IS NOT NULL{legacy_deleted}{current_deleted}')
        _, mapped_rows = fetch_all(new_conn, sql)
        candidates = defaultdict(dict)
        current_labels = {}
        for old_code, current_id, current_code, current_name in mapped_rows:
            key = norm_hsld(old_code)
            if not key:
                continue
            item = {"id": current_id, "code": norm_text(current_code), "name": norm_text(current_name)}
            candidates[key][norm_text(current_id)] = item
            current_labels[norm_text(current_id)] = " — ".join(
                part for part in (item["code"], item["name"]) if part)
        maps[spec["new"]] = {
            "spec": spec,
            "source_names": source_names,
            "candidates": {code: list(values.values()) for code, values in candidates.items()},
            "current_labels": current_labels,
        }
    return maps


def _biography_direct_dm_maps(old_conn, new_conn, old_schema_name, new_schema_name, selected_fields):
    """Map an old catalog code directly to the matching current catalog code."""
    maps = {}
    for spec in BIOGRAPHY_DIRECT_DM_FIELDS:
        if spec["new"] not in selected_fields:
            continue
        old_columns = _oracle_table_columns(old_conn, old_schema_name, spec["old_table"])
        if not {"MA", "ND"}.issubset(old_columns):
            raise ValueError(f'DB cũ thiếu {spec["old_table"]}.MA/ND để hiển thị {spec["label"]}.')
        _, source_rows = fetch_all(old_conn,
            f'SELECT "MA","ND" FROM {qualified(old_schema_name, spec["old_table"])}')
        source_names = defaultdict(list)
        for code, name in source_rows:
            key = norm_hsld(code)
            if key:
                source_names[key].append(norm_text(name))

        new_columns = _oracle_table_columns(new_conn, new_schema_name, spec["new_table"])
        required = {"ID", spec["code"], spec["name"]}
        if not required.issubset(new_columns):
            raise ValueError(f'DB mới thiếu cột {spec["new_table"]}: '
                             + ", ".join(sorted(required - new_columns)))
        deleted = f' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in new_columns else ""
        _, target_rows = fetch_all(new_conn,
            f'SELECT "ID","{spec["code"]}","{spec["name"]}" '
            f'FROM {qualified(new_schema_name, spec["new_table"])}{deleted}')
        candidates = defaultdict(list)
        current_labels = {}
        for row_id, code, name in target_rows:
            key = norm_hsld(code)
            item = {"id": row_id, "code": norm_text(code), "name": norm_text(name)}
            current_labels[norm_text(row_id)] = " — ".join(
                part for part in (item["code"], item["name"]) if part)
            if key:
                candidates[key].append(item)
        maps[spec["new"]] = {"spec": spec, "source_names": source_names,
                              "candidates": candidates, "current_labels": current_labels}
    return maps


def _biography_plan(old_conn, new_conn, old_schema_name, new_schema_name, prison_code, selected_fields=None):
    all_biography_fields = {new for _old, new in BIOGRAPHY_FIELDS}
    all_direct_dm_fields = {spec["new"] for spec in BIOGRAPHY_DIRECT_DM_FIELDS}
    all_legacy_dm_fields = {spec["new"] for spec in BIOGRAPHY_LEGACY_DM_FIELDS}
    all_duration_fields = {new for _old, new, _label in BIOGRAPHY_DURATION_FIELDS}
    valid_fields = all_biography_fields | all_direct_dm_fields | all_legacy_dm_fields | all_duration_fields | {"LL_PHAN_DOI_ID", "LL_PHAN_TRAI_ID"}
    selected_fields = valid_fields if selected_fields is None else set(selected_fields) & valid_fields
    if not selected_fields:
        raise ValueError("Hãy chọn ít nhất một cột cần kiểm tra.")
    selected_durations = selected_fields & all_duration_fields
    selected_units = selected_fields & {"LL_PHAN_DOI_ID", "LL_PHAN_TRAI_ID"}
    selected_direct_dm = selected_fields & all_direct_dm_fields
    selected_legacy_dm = selected_fields & all_legacy_dm_fields
    pairs, patients, prison_scope = load_person_crosswalk(
        old_conn, new_conn, old_schema_name, new_schema_name, prison_code)
    old_columns = ["PN_ID", "SO_HSLD", *(old for old, _new in BIOGRAPHY_FIELDS),
                   *(old for old, _new, _label in BIOGRAPHY_DURATION_FIELDS), "MA_PHAN_DOI"]
    new_columns = ["ID", "LL_SO_HO_SO_LAN_DAU", *(new for _old, new in BIOGRAPHY_FIELDS),
                   "LL_PHAN_DOI_ID", "LL_PHAN_TRAI_ID"]
    old_columns.extend(spec["old"] for spec in BIOGRAPHY_DIRECT_DM_FIELDS
                       if spec["new"] in selected_direct_dm)
    new_columns.extend(spec["new"] for spec in BIOGRAPHY_DIRECT_DM_FIELDS
                       if spec["new"] in selected_direct_dm)
    old_columns.extend(spec["old"] for spec in BIOGRAPHY_LEGACY_DM_FIELDS if spec["new"] in selected_legacy_dm)
    new_columns.extend(spec["new"] for spec in BIOGRAPHY_LEGACY_DM_FIELDS if spec["new"] in selected_legacy_dm)
    _, old_rows = fetch_all(
        old_conn,
        f'SELECT {",".join(chr(34)+c+chr(34) for c in old_columns)} '
        f'FROM {qualified(old_schema_name, "PN_LAI_LICH")}')

    _, schema_new = load_schema()
    table_columns = {c[0] for c in schema_new.get("PN_LAI_LICHS", [])}
    deleted_filter = f' AND NVL("IS_DELETED",0)=0' if "IS_DELETED" in table_columns else ""
    target_sql = (
        f'SELECT {",".join("T."+chr(34)+c+chr(34) for c in new_columns)} '
        f'FROM {qualified(new_schema_name, "PN_LAI_LICHS")} T '
        f'WHERE T."LL_TRAI_GIAM_ID"=:prison_id{deleted_filter}')
    _, new_rows = fetch_all(new_conn, target_sql, {"prison_id": prison_scope["new_id"]})
    legacy_dm_maps = _biography_legacy_dm_maps(
        old_conn, new_conn, old_schema_name, new_schema_name, selected_legacy_dm)
    direct_dm_maps = _biography_direct_dm_maps(
        old_conn, new_conn, old_schema_name, new_schema_name, selected_direct_dm)
    old_column_indexes = {column: index for index, column in enumerate(old_columns)}
    new_column_indexes = {column: index for index, column in enumerate(new_columns)}
    # The legacy columns contain codes. The new UI stores the catalog title
    # (MTG_TITLE) as text in PN_THI_HANH_AN, so resolve old MA -> old ND and
    # match ND to a unique new title before comparing/updating.
    old_duration_titles = defaultdict(list)
    new_duration_titles = defaultdict(list)
    if selected_durations:
        old_dm_columns = {c[0] for c in load_schema()[0].get("MA_MUC_THOI_GIAN", [])}
        new_dm_columns = {c[0] for c in load_schema()[1].get("DM_MA_THOI_GIANS", [])}
        if not {"MA", "ND"}.issubset(old_dm_columns):
            raise ValueError("DB cũ thiếu MA_MUC_THOI_GIAN (MA, ND) để đọc thời gian tạm giam/tạm giữ.")
        if not {"ID", "MTG_TITLE", "IS_DELETED"}.issubset(new_dm_columns):
            raise ValueError("DB mới thiếu DM_MA_THOI_GIANS (ID, MTG_TITLE, IS_DELETED).")
        _, old_duration_rows = fetch_all(
            old_conn, f'SELECT "MA","ND" FROM {qualified(old_schema_name, "MA_MUC_THOI_GIAN")}')
        for code, title in old_duration_rows:
            key = norm_hsld(code)
            if key:
                old_duration_titles[key].append(norm_text(title))
        _, new_duration_rows = fetch_all(
            new_conn, f'SELECT "MTG_TITLE" FROM {qualified(new_schema_name, "DM_MA_THOI_GIANS")} '
            'WHERE NVL("IS_DELETED",0)=0')
        for (title,) in new_duration_rows:
            key = _duration_key(title)
            if key:
                new_duration_titles[key].append(norm_text(title))

    old_unit_names = defaultdict(list)
    new_units_by_code = defaultdict(list)
    new_branches_by_code = defaultdict(list)
    new_units_by_id = {}
    new_branches_by_id = {}
    if selected_units:
        old_unit_columns = {c[0] for c in load_schema()[0].get("MA_PHAN_DOI_PN", [])}
        new_team_columns = {c[0] for c in load_schema()[1].get("DM_PHAN_DOIS", [])}
        new_branch_columns = {c[0] for c in load_schema()[1].get("DM_PHAN_TRAIS", [])}
        if not {"MA", "ND", "TEN_DOI"}.issubset(old_unit_columns):
            raise ValueError("DB cũ thiếu MA_PHAN_DOI_PN (MA, ND, TEN_DOI) để tra mã phân đội.")
        if not {"ID", "PD_MA", "PD_TEN", "PD_DM_PHAN_TRAI_ID", "IS_DELETED"}.issubset(new_team_columns):
            raise ValueError("DB mới thiếu cột DM_PHAN_DOIS cần để ánh xạ phân đội.")
        if not {"ID", "PT_MA", "PT_TEN", "PT_DM_TRAI_GIAM_ID", "IS_DELETED"}.issubset(new_branch_columns):
            raise ValueError("DB mới thiếu cột DM_PHAN_TRAIS cần để ánh xạ mã phân trại và phân trại.")
        _, old_unit_rows = fetch_all(
            old_conn, f'SELECT "MA","ND","TEN_DOI" FROM {qualified(old_schema_name, "MA_PHAN_DOI_PN")}')
        for code, name, team_name in old_unit_rows:
            key = norm_hsld(code)
            if key:
                label = " — ".join(part for part in (norm_text(name), norm_text(team_name)) if part)
                old_unit_names[key].append(label)
        _, new_branch_rows = fetch_all(
            new_conn,
            f'SELECT "ID","PT_MA","PT_TEN" FROM {qualified(new_schema_name, "DM_PHAN_TRAIS")} '
            'WHERE "PT_DM_TRAI_GIAM_ID"=:prison_id AND NVL("IS_DELETED",0)=0',
            {"prison_id": prison_scope["new_id"]})
        for branch_id, code, name in new_branch_rows:
            key = norm_hsld(code)
            item = {"id": branch_id, "code": norm_text(code), "name": norm_text(name)}
            if key:
                new_branches_by_code[key].append(item)
            new_branches_by_id[branch_id] = item["name"]
        _, new_unit_rows = fetch_all(
            new_conn,
            f'SELECT D."ID",D."PD_MA",D."PD_TEN",D."PD_DM_PHAN_TRAI_ID",B."PT_TEN",B."ID" '
            f'FROM {qualified(new_schema_name, "DM_PHAN_DOIS")} D '
            f'JOIN {qualified(new_schema_name, "DM_PHAN_TRAIS")} B '
            'ON B."ID"=D."PD_DM_PHAN_TRAI_ID" '
            'WHERE B."PT_DM_TRAI_GIAM_ID"=:prison_id AND NVL(B."IS_DELETED",0)=0 '
            'AND NVL(D."IS_DELETED",0)=0', {"prison_id": prison_scope["new_id"]})
        for team_id, code, name, branch_id, branch_name, _branch_actual_id in new_unit_rows:
            key = norm_hsld(code)
            item = {"id": team_id, "code": norm_text(code), "name": norm_text(name),
                    "branch_id": branch_id, "branch_name": norm_text(branch_name)}
            if key:
                new_units_by_code[key].append(item)
            new_units_by_id[team_id] = item

    tha_by_person = defaultdict(list)
    if selected_durations:
        tha_columns = {c[0] for c in load_schema()[1].get("PN_THI_HANH_AN", [])}
        needed_tha = {"ID", "THA_PNLAI_LICH_ID", "IS_DELETED", *selected_durations}
        if not needed_tha.issubset(tha_columns):
            raise ValueError("DB mới thiếu cột PN_THI_HANH_AN cần cho thời gian tạm giam/tạm giữ: "
                             + ", ".join(sorted(needed_tha - tha_columns)))
        tha_select = ["ID", "THA_PNLAI_LICH_ID",
                      *(new for _old, new, _label in BIOGRAPHY_DURATION_FIELDS)]
        _, tha_rows = fetch_all(
            new_conn,
            f'SELECT {",".join("T."+chr(34)+c+chr(34) for c in tha_select)} '
            f'FROM {qualified(new_schema_name, "PN_THI_HANH_AN")} T '
            f'JOIN {qualified(new_schema_name, "PN_LAI_LICHS")} L '
            'ON L."ID"=T."THA_PNLAI_LICH_ID" '
            'WHERE L."LL_TRAI_GIAM_ID"=:prison_id AND NVL(L."IS_DELETED",0)=0 '
            'AND NVL(T."IS_DELETED",0)=0', {"prison_id": prison_scope["new_id"]})
        for row in tha_rows:
            tha_by_person[row[1]].append(row)
    old_by_id = {row[0]: row for row in old_rows}
    target_by_id = {row[0]: row for row in new_rows}
    patient_hsld = {row["old_id"]: row.get("old_hsld") for row in patients if row.get("old_id") is not None}
    patient_status = {row["old_id"]: row.get("status", "Không ghép duy nhất theo HSLĐ")
                      for row in patients if row.get("old_id") is not None}

    updates, issues = [], []
    for old_id, new_id in pairs.items():
        source = old_by_id.get(old_id)
        target = target_by_id.get(new_id)
        hsld = patient_hsld.get(old_id, "")
        if source is None or target is None:
            issues.append({"hsld": norm_text(hsld), "status": "Không tìm thấy hồ sơ lai lịch tương ứng"})
            continue
        fields, field_expected, unit_fields, tha_fields, unit_expected, tha_expected, display, warnings = {}, {}, {}, {}, {}, {}, [], []
        for offset, (old_col, new_col) in enumerate(BIOGRAPHY_FIELDS):
            if new_col not in selected_fields:
                continue
            source_value, target_value = source[2 + offset], target[2 + offset]
            source_present = source_value is not None and bool(norm_text(source_value))
            target_present = target_value is not None and bool(norm_text(target_value))
            if new_col == "LL_NHAN_THAN":
                source_normalized = norm_text(source_value).strip()
                target_normalized = norm_text(target_value).strip()
                if source_normalized != target_normalized:
                    fields[new_col] = source_value
            elif new_col == "LL_SO_TIEN_AN":
                source_normalized = norm_text(source_value).strip()
                target_normalized = norm_text(target_value).strip()
                if source_present and source_normalized != target_normalized:
                    fields[new_col] = source_value
                    field_expected[new_col] = target_value
            elif source_present and not target_present:
                fields[new_col] = source_value
            if new_col == "LL_SO_TIEN_AN":
                old_display = norm_text(source_value)
                current_display = norm_text(target_value) or "(trống)"
                if source_present and norm_text(source_value).strip() != norm_text(target_value).strip():
                    new_display = f"{current_display} → {old_display}"
                else:
                    new_display = norm_text(target_value)
                display.append({"field": new_col, "old": old_display, "new": new_display})
            else:
                display.append({"field": new_col, "old": norm_text(source_value),
                                "new": norm_text(target_value if new_col == "LL_NHAN_THAN" or target_present
                                                 else source_value if source_present else None)})
        for spec in BIOGRAPHY_LEGACY_DM_FIELDS:
            new_col = spec["new"]
            if new_col not in selected_legacy_dm:
                continue
            source_code = norm_text(source[old_column_indexes[spec["old"]]]).strip()
            current_id = target[new_column_indexes[new_col]]
            catalog = legacy_dm_maps[new_col]
            code_key = norm_hsld(source_code)
            source_names = catalog["source_names"].get(code_key, []) if code_key else []
            old_label = source_code
            if len(source_names) == 1:
                old_label = f"{source_code} — {source_names[0]}"
            elif len(source_names) > 1:
                warnings.append(f'{spec["label"]}: mã {source_code} trùng trong danh mục DB cũ')
            if not code_key or code_key == "0":
                current_label = catalog["current_labels"].get(
                    norm_text(current_id), f"ID {norm_text(current_id)}" if current_id is not None else "(trống)")
                display.append({"field": new_col, "old": old_label, "new": current_label})
                continue
            if len(source_names) != 1:
                if not source_names:
                    warnings.append(f'{spec["label"]}: mã cũ {source_code} không có trong {spec["old_table"]}')
                current_label = catalog["current_labels"].get(
                    norm_text(current_id), f"ID {norm_text(current_id)}" if current_id is not None else "(trống)")
                display.append({"field": new_col, "old": old_label, "new": f"{current_label} (không ánh xạ)"})
                continue
            candidates = catalog["candidates"].get(code_key, [])
            if len(candidates) != 1:
                reason = "không có mapping" if not candidates else "mapping đến nhiều giá trị"
                warnings.append(f'{spec["label"]}: mã cũ {source_code} {reason}; không cập nhật')
                current_label = catalog["current_labels"].get(
                    norm_text(current_id), f"ID {norm_text(current_id)}" if current_id is not None else "(trống)")
                display.append({"field": new_col, "old": old_label, "new": f"{current_label} (không ánh xạ)"})
                continue
            mapped = candidates[0]
            current_label = catalog["current_labels"].get(
                norm_text(current_id), f"ID {norm_text(current_id)}" if current_id is not None else "(trống)")
            mapped_label = " — ".join(part for part in (mapped["code"], mapped["name"]) if part)
            if str(current_id) != str(mapped["id"]):
                fields[new_col] = mapped["id"]
                field_expected[new_col] = current_id
                new_label = f"{current_label} → {mapped_label}"
            else:
                new_label = mapped_label
            display.append({"field": new_col, "old": old_label, "new": new_label})
        for spec in BIOGRAPHY_DIRECT_DM_FIELDS:
            new_col = spec["new"]
            if new_col not in selected_direct_dm:
                continue
            source_code = norm_text(source[old_column_indexes[spec["old"]]]).strip()
            current_id = target[new_column_indexes[new_col]]
            catalog = direct_dm_maps[new_col]
            code_key = norm_hsld(source_code)
            source_names = catalog["source_names"].get(code_key, []) if code_key else []
            old_label = source_code
            if len(source_names) == 1:
                old_label = f"{source_code} — {source_names[0]}"
            elif len(source_names) > 1:
                warnings.append(f'{spec["label"]}: mã {source_code} trùng trong danh mục DB cũ')
            current_label = catalog["current_labels"].get(
                norm_text(current_id), f"ID {norm_text(current_id)}" if current_id is not None else "(trống)")
            candidates = catalog["candidates"].get(code_key, []) if code_key and code_key != "0" else []
            if not code_key or code_key == "0":
                display.append({"field": new_col, "old": old_label, "new": current_label})
                continue
            if len(source_names) != 1:
                if not source_names:
                    warnings.append(f'{spec["label"]}: mã cũ {source_code} không có trong {spec["old_table"]}')
                display.append({"field": new_col, "old": old_label,
                                "new": f"{current_label} (không ánh xạ)"})
                continue
            if len(candidates) != 1:
                reason = "không có mã tương ứng" if not candidates else "mã đích bị trùng"
                warnings.append(f'{spec["label"]}: mã cũ {source_code} {reason}; không cập nhật')
                display.append({"field": new_col, "old": old_label,
                                "new": f"{current_label} (không ánh xạ)"})
                continue
            mapped = candidates[0]
            mapped_label = " — ".join(part for part in (mapped["code"], mapped["name"]) if part)
            if norm_text(current_id) != norm_text(mapped["id"]):
                fields[new_col] = mapped["id"]
                field_expected[new_col] = current_id
                new_label = f"{current_label} → {mapped_label}"
            else:
                new_label = mapped_label
            display.append({"field": new_col, "old": old_label, "new": new_label})
        old_unit_code = (norm_hsld(source[2 + len(BIOGRAPHY_FIELDS) + len(BIOGRAPHY_DURATION_FIELDS)])
                         if selected_units else "")
        current_team_id = target[new_column_indexes["LL_PHAN_DOI_ID"]]
        current_branch_id = target[new_column_indexes["LL_PHAN_TRAI_ID"]]
        source_team = None
        source_unit_name = ""
        if old_unit_code and old_unit_code != "0":
            old_names = old_unit_names.get(old_unit_code, [])
            if len(old_names) != 1:
                warnings.append(f"Phân đội: mã cũ {norm_text(source[2 + len(BIOGRAPHY_FIELDS) + len(BIOGRAPHY_DURATION_FIELDS)])} không tra được duy nhất trong MA_PHAN_DOI_PN")
            else:
                source_unit_name = old_names[0]
                old_branch_code = old_unit_code[:3] if len(old_unit_code) >= 3 else ""
                branch_candidates = new_branches_by_code.get(old_branch_code, [])
                if not old_branch_code or len(branch_candidates) != 1:
                    warnings.append(
                        f"Phân trại: mã đầu {old_branch_code or '(thiếu)'} của MA_PHAN_DOI "
                        "không khớp duy nhất với PT_MA trong danh mục DB mới của trại này")
                    branch_candidates = []
                source_branch = branch_candidates[0] if branch_candidates else None
                candidates = [team for team in new_units_by_code.get(old_unit_code, [])
                              if source_branch and team["branch_id"] == source_branch["id"]]
                if len(candidates) != 1:
                    if source_branch:
                        warnings.append(
                            f"Phân đội: PD_MA {old_unit_code} không khớp duy nhất dưới phân trại "
                            f"{source_branch['name']} (PT_MA {old_branch_code})")
                else:
                    source_team = candidates[0]
                    if ("LL_PHAN_DOI_ID" in selected_fields
                            and current_team_id != source_team["id"]):
                        unit_fields["LL_PHAN_DOI_ID"] = source_team["id"]
                        unit_expected["LL_PHAN_DOI_ID"] = current_team_id
                    if current_team_id is not None and current_team_id not in new_units_by_id:
                        warnings.append("Phân đội hiện có trên DB mới không tìm thấy trong danh mục của trại")
                    # The old schema has no separate branch column. The
                    # expected branch must follow the old code's mapped team,
                    # including when the current team/branch pair is wrong.
                    if ("LL_PHAN_TRAI_ID" in selected_fields and source_branch
                            and current_branch_id != source_branch["id"]):
                        unit_fields["LL_PHAN_TRAI_ID"] = source_branch["id"]
                        unit_expected["LL_PHAN_TRAI_ID"] = current_branch_id
        if old_unit_code and old_unit_code != "0" and "LL_PHAN_DOI_ID" in selected_fields:
            if "LL_PHAN_DOI_ID" in unit_fields and source_team:
                current_value = (new_units_by_id.get(current_team_id, {}).get(
                    "name", f"ID {current_team_id} (không có trong danh mục trại)")
                    if current_team_id is not None else "(trống)")
                current_team_label = f"{current_value} → {source_team['name']}"
            elif current_team_id is not None:
                current_team_label = new_units_by_id.get(current_team_id, {}).get(
                    "name", f"ID {current_team_id} (không có trong danh mục trại)")
            else:
                current_team_label = "(trống)"
            display.append({"field": "LL_PHAN_DOI_ID",
                            "old": f"{norm_text(source[2 + len(BIOGRAPHY_FIELDS) + len(BIOGRAPHY_DURATION_FIELDS)])} — {source_unit_name}".strip(" —"),
                            "new": current_team_label})
        if old_unit_code and old_unit_code != "0" and "LL_PHAN_TRAI_ID" in selected_fields:
            if "LL_PHAN_TRAI_ID" in unit_fields and source_team:
                current_value = (new_branches_by_id.get(
                    current_branch_id, f"ID {current_branch_id} (không có trong danh mục trại)")
                    if current_branch_id is not None else "(trống)")
                current_branch_label = f"{current_value} → {source_team['branch_name']}"
            elif current_branch_id is not None:
                current_branch_label = new_branches_by_id.get(
                    current_branch_id, f"ID {current_branch_id} (không có trong danh mục trại)")
            else:
                current_branch_label = "(trống)"
            display.append({"field": "LL_PHAN_TRAI_ID", "old": "Theo phân đội DB cũ",
                            "new": current_branch_label})
        tha_matches = tha_by_person.get(new_id, []) if selected_durations else []
        tha = tha_matches[0] if len(tha_matches) == 1 else None
        if selected_durations and len(tha_matches) != 1:
            warnings.append("Không tìm thấy duy nhất bản ghi thi hành án DB mới" if not tha_matches
                            else "Có nhiều bản ghi thi hành án DB mới")
        elif selected_durations:
            for offset, (old_col, new_col, label) in enumerate(BIOGRAPHY_DURATION_FIELDS):
                if new_col not in selected_fields:
                    continue
                old_code = source[2 + len(BIOGRAPHY_FIELDS) + offset]
                current_value = tha[2 + offset]
                old_code_key = norm_hsld(old_code)
                desired_value = None
                if old_code_key and old_code_key != "0":
                    old_titles = old_duration_titles.get(old_code_key, [])
                    if len(old_titles) != 1:
                        warnings.append(f"{label}: mã cũ {norm_text(old_code)} không ánh xạ duy nhất qua MA_MUC_THOI_GIAN")
                        display.append({"field": new_col, "old": f"{norm_text(old_code)} (không ánh xạ)",
                                        "new": norm_text(current_value)})
                        continue
                    title_matches = new_duration_titles.get(_duration_key(old_titles[0]), [])
                    if len(title_matches) != 1:
                        warnings.append(f"{label}: không tìm thấy duy nhất tên '{old_titles[0]}' trong DM_MA_THOI_GIANS")
                        display.append({"field": new_col, "old": old_titles[0], "new": norm_text(current_value)})
                        continue
                    desired_value = title_matches[0]
                # Treat the displayed sentinel "Không" identically on both
                # sides. Previously only the new value was collapsed to an
                # empty key, causing old="Không" and new="Không" to look
                # different and be incorrectly scheduled for update.
                current_normalized = _duration_key(current_value)
                desired_normalized = _duration_key(desired_value)
                if current_normalized in ("", "khong"):
                    current_normalized = ""
                if desired_normalized in ("", "khong"):
                    desired_normalized = ""
                if current_normalized != desired_normalized:
                    tha_fields[new_col] = desired_value
                    tha_expected[new_col] = current_value
                display.append({"field": new_col, "old": norm_text(desired_value) or "Không",
                                "new": norm_text(current_value) or "Không"})
        if fields or unit_fields or tha_fields:
            updates.append({"id": new_id, "old_person_id": old_id, "hsld": norm_text(hsld),
                            "fields": fields, "field_expected": field_expected, "unit_fields": unit_fields,
                            "unit_expected": unit_expected, "tha_id": tha[0] if tha else None,
                            "tha_fields": tha_fields, "tha_expected": tha_expected,
                            "warnings": warnings, "display": display})
        elif warnings:
            issues.append({"hsld": norm_text(hsld), "status": "; ".join(warnings), "display": display})

    paired_old = set(pairs)
    for old_id, row in old_by_id.items():
        if old_id not in paired_old:
            issues.append({"hsld": norm_text(row[1]),
                           "status": patient_status.get(old_id, "Không ghép duy nhất theo HSLĐ")})
    updates.sort(key=lambda row: (not bool(row["hsld"]), row["hsld"].casefold(), str(row["id"])))
    return {"updates": updates, "issues": issues, "prison_scope": prison_scope,
            "selected_fields": sorted(selected_fields),
            "field_count": sum(len(row["fields"]) + len(row["unit_fields"]) + len(row["tha_fields"])
                               for row in updates)}


def preview_biography_update(old_cfg, new_cfg, selected_fields=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _biography_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                               new_cfg.get("schema", ""), new_cfg.get("prison_code", ""), selected_fields)
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


def apply_biography_update(old_cfg, new_cfg, preview, selected_ids=None, selected_fields=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _biography_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                                new_cfg.get("schema", ""), new_cfg.get("prison_code", ""),
                                selected_fields if selected_fields is not None else preview.get("selected_fields"))
        expected = [(row["id"], row["fields"], row.get("field_expected", {}), row["unit_fields"], row["unit_expected"],
                     row["tha_id"], row["tha_fields"], row["tha_expected"], row.get("display", []), row.get("warnings", []))
                    for row in preview["updates"]]
        actual = [(row["id"], row["fields"], row.get("field_expected", {}), row["unit_fields"], row["unit_expected"],
                   row["tha_id"], row["tha_fields"], row["tha_expected"], row.get("display", []), row.get("warnings", []))
                  for row in fresh["updates"]]
        if expected != actual:
            raise ValueError("Dữ liệu đã thay đổi so với xem trước. Không ghi gì; hãy tải lại xem trước rồi xác nhận lại.")
        if selected_ids is not None:
            selected_ids = set(selected_ids)
            allowed_ids = {row["id"] for row in preview["updates"]}
            if not selected_ids or not selected_ids.issubset(allowed_ids):
                raise ValueError("Danh sách hồ sơ được chọn không còn hợp lệ. Hãy tải lại xem trước.")
            fresh["updates"] = [row for row in fresh["updates"] if row["id"] in selected_ids]
        if not fresh["updates"]:
            raise ValueError("Không còn trường nào đủ điều kiện cập nhật trong lựa chọn này.")

        cursor = new_conn.cursor()
        table = qualified(new_cfg.get("schema", ""), "PN_LAI_LICHS")
        tha_table = qualified(new_cfg.get("schema", ""), "PN_THI_HANH_AN")
        patient_table = qualified(new_cfg.get("schema", ""), M.PN_NEW["table"])
        for row in fresh["updates"]:
            prison_id = fresh["prison_scope"]["new_id"]
            if row["fields"]:
                fields = row["fields"]
                assignments = ",".join(f'"{column}"=:v_{i}' for i, column in enumerate(fields))
                compare_conditions = []
                binds = {f"v_{i}": value for i, value in enumerate(fields.values())}
                binds.update({"target_id": row["id"], "person_id": row["id"], "prison_id": prison_id})
                for i, (column, value) in enumerate(fields.items()):
                    if column in row.get("field_expected", {}):
                        expected_value = row["field_expected"][column]
                        if expected_value is None:
                            compare_conditions.append(f'T."{column}" IS NULL')
                        else:
                            binds[f"expected_{i}"] = expected_value
                            compare_conditions.append(f'T."{column}"=:expected_{i}')
                    elif column == "LL_NHAN_THAN":
                        if value is None:
                            compare_conditions.append(f'T."{column}" IS NOT NULL')
                        else:
                            binds[f"expected_{i}"] = value
                            compare_conditions.append(f'(T."{column}" IS NULL OR T."{column}"<>:expected_{i})')
                    else:
                        compare_conditions.append(f'(T."{column}" IS NULL OR TRIM(T."{column}") IS NULL)')
                cursor.execute(
                    f'UPDATE {table} T SET {assignments} WHERE T."ID"=:target_id '
                    f'AND T."LL_TRAI_GIAM_ID"=:prison_id AND NVL(T."IS_DELETED",0)=0 '
                    f'AND EXISTS (SELECT 1 FROM {patient_table} P WHERE P."{M.PN_NEW["id"]}"=:person_id '
                    f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0) '
                    f'AND {" AND ".join(compare_conditions)}', binds)
                if cursor.rowcount != 1:
                    raise RuntimeError("Có hồ sơ đích đã thay đổi hoặc không còn thuộc trại đã chọn; toàn bộ cập nhật sẽ được rollback.")
            if row["unit_fields"]:
                assignments = ",".join(f'"{column}"=:v_{i}' for i, column in enumerate(row["unit_fields"]))
                compare_conditions = []
                binds = {f"v_{i}": value for i, value in enumerate(row["unit_fields"].values())}
                binds.update({"target_id": row["id"], "prison_id": prison_id,
                              "person_id": row["id"]})
                for i, (column, expected_value) in enumerate(row["unit_expected"].items()):
                    if expected_value is None:
                        compare_conditions.append(f'T."{column}" IS NULL')
                    else:
                        binds[f"old_{i}"] = expected_value
                        compare_conditions.append(f'T."{column}"=:old_{i}')
                cursor.execute(
                    f'UPDATE {table} T SET {assignments} WHERE T."ID"=:target_id '
                    f'AND T."LL_TRAI_GIAM_ID"=:prison_id AND NVL(T."IS_DELETED",0)=0 '
                    f'AND EXISTS (SELECT 1 FROM {patient_table} P WHERE P."{M.PN_NEW["id"]}"=:person_id '
                    f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0) '
                    f'AND ({" AND ".join(compare_conditions)})', binds)
                if cursor.rowcount != 1:
                    raise RuntimeError("Phân đội/phân trại đã thay đổi hoặc hồ sơ không còn thuộc trại đã chọn; toàn bộ cập nhật sẽ được rollback.")
            if row["tha_fields"]:
                assignments = ",".join(f'"{column}"=:v_{i}' for i, column in enumerate(row["tha_fields"]))
                binds = {f"v_{i}": value for i, value in enumerate(row["tha_fields"].values())}
                binds.update({"tha_id": row["tha_id"], "person_id": row["id"], "prison_id": prison_id})
                compare_conditions = []
                for i, (column, expected_value) in enumerate(row["tha_expected"].items()):
                    if expected_value is None:
                        compare_conditions.append(f'T."{column}" IS NULL')
                    else:
                        binds[f"old_{i}"] = expected_value
                        compare_conditions.append(f'T."{column}"=:old_{i}')
                cursor.execute(
                    f'UPDATE {tha_table} T SET {assignments} WHERE T."ID"=:tha_id '
                    'AND T."THA_PNLAI_LICH_ID"=:person_id AND NVL(T."IS_DELETED",0)=0 '
                    f'AND EXISTS (SELECT 1 FROM {table} L WHERE L."ID"=:person_id '
                    'AND L."LL_TRAI_GIAM_ID"=:prison_id AND NVL(L."IS_DELETED",0)=0) '
                    f'AND ({" OR ".join(compare_conditions)})', binds)
                if cursor.rowcount != 1:
                    raise RuntimeError("Bản ghi thi hành án đã thay đổi hoặc không còn thuộc hồ sơ/trại đã chọn; toàn bộ cập nhật sẽ được rollback.")
        cursor.close()
        new_conn.commit()
        return {"updated_rows": len(fresh["updates"]),
                "updated_fields": sum(len(row["fields"]) + len(row["unit_fields"]) + len(row["tha_fields"])
                                       for row in fresh["updates"]),
                "prison_scope": fresh["prison_scope"]}
    except Exception:
        if new_conn:
            new_conn.rollback()
        raise
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


CLASSIFICATION_YEAR = 2026


CLASSIFICATION_PERIODS = (
    {"quarter": 3, "old_column": "MA_XEP_LOAI_Q3", "new_column": "XEP_LOAI_QUY_III", "label": "quý III"},
    {"quarter": 4, "old_column": "MA_XEP_LOAI_Q4", "new_column": "XEP_LOAI_QUY_IV", "label": "quý IV"},
)


def _classification_update_plan(old_conn, new_conn, old_schema_name, new_schema_name, prison_code):
    pairs, patients, prison_scope = load_person_crosswalk(
        old_conn, new_conn, old_schema_name, new_schema_name, prison_code)
    old_schema, new_schema = load_schema()
    old_result_columns = {c[0] for c in old_schema.get("PN_KET_QUA_CAI_TAO", [])}
    target_columns = {c[0] for c in new_schema.get("XEP_LOAIS", [])}
    category_columns = {c[0] for c in new_schema.get("DM_XEP_LOAIES", [])}
    old_category_columns = {c[0] for c in old_schema.get("MA_XEP_LOAI", [])}
    required = {"PN_ID", "NAM_XL", *(period["old_column"] for period in CLASSIFICATION_PERIODS)}
    if not required.issubset(old_result_columns):
        raise ValueError("DB cũ thiếu cột trong PN_KET_QUA_CAI_TAO: " + ", ".join(sorted(required - old_result_columns)))
    required_target = {"ID", "PHAM_NHAN_ID", "XEP_LOAI_NAM", "IS_DELETED",
                      *(period["new_column"] for period in CLASSIFICATION_PERIODS)}
    if not required_target.issubset(target_columns):
        raise ValueError("DB mới thiếu cột trong XEP_LOAIS: " + ", ".join(sorted(required_target - target_columns)))
    if not {"ID", "XL_MA", "XL_TEN"}.issubset(category_columns):
        raise ValueError("DB mới thiếu cột trong DM_XEP_LOAIES (ID, XL_MA, XL_TEN).")
    if not {"MA", "ND"}.issubset(old_category_columns):
        raise ValueError("DB cũ thiếu bảng/cột MA_XEP_LOAI (MA, ND) để hiển thị kết quả nguồn.")

    _, old_rows = fetch_all(
        old_conn,
        f'SELECT R."PN_ID",R."MA_XEP_LOAI_Q3",R."MA_XEP_LOAI_Q4" '
        f'FROM {qualified(old_schema_name, "PN_KET_QUA_CAI_TAO")} R '
        f'WHERE R."NAM_XL"=:year AND EXISTS '
        f'(SELECT 1 FROM {qualified(old_schema_name, M.PN_OLD["table"])} P '
        f'WHERE P."{M.PN_OLD["id"]}"=R."PN_ID" AND UPPER(TRIM(P."{M.PN_OLD["trai"]}"))=:old_prison_code)',
        {"year": CLASSIFICATION_YEAR, "old_prison_code": prison_scope["old_code"]})
    source_by_person = defaultdict(list)
    for old_person_id, q3_code, q4_code in old_rows:
        source_by_person[old_person_id].append((q3_code, q4_code))

    _, old_names = fetch_all(
        old_conn,
        f'SELECT "MA","ND" FROM {qualified(old_schema_name, "MA_XEP_LOAI")}')
    old_name_by_code = defaultdict(list)
    for code, title in old_names:
        key = norm_text(code).strip().upper()
        if key:
            old_name_by_code[key].append(norm_text(title))

    category_deleted = f' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in category_columns else ""
    _, category_rows = fetch_all(
        new_conn,
        f'SELECT "ID","XL_MA","XL_TEN" FROM {qualified(new_schema_name, "DM_XEP_LOAIES")}{category_deleted}')
    new_category_by_code = defaultdict(list)
    for category_id, code, title in category_rows:
        key = norm_text(code).strip().upper()
        if key:
            new_category_by_code[key].append((category_id, norm_text(title)))

    person_table = qualified(new_schema_name, M.PN_NEW["table"])
    _, target_rows = fetch_all(
        new_conn,
        f'SELECT T."ID",T."PHAM_NHAN_ID",T."XEP_LOAI_QUY_III",T."XEP_LOAI_QUY_IV" '
        f'FROM {qualified(new_schema_name, "XEP_LOAIS")} T '
        f'WHERE T."XEP_LOAI_NAM"=:year AND NVL(T."IS_DELETED",0)=0 AND EXISTS '
        f'(SELECT 1 FROM {person_table} P WHERE P."{M.PN_NEW["id"]}"=T."PHAM_NHAN_ID" '
        f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0)',
        {"year": CLASSIFICATION_YEAR, "prison_id": prison_scope["new_id"]})
    target_by_person = defaultdict(list)
    for target_id, new_person_id, q3_value, q4_value in target_rows:
        target_by_person[new_person_id].append({"id": target_id, "q3": q3_value, "q4": q4_value})

    hsld_by_old_id = {row.get("old_id"): row.get("old_hsld", "") for row in patients
                      if row.get("old_id") is not None}
    patient_status = {row.get("old_id"): row.get("status", "Không ghép duy nhất theo HSLĐ")
                      for row in patients if row.get("old_id") is not None}
    updates, issues = [], []
    for old_person_id, new_person_id in pairs.items():
        hsld = norm_text(hsld_by_old_id.get(old_person_id, ""))
        source_rows = source_by_person.get(old_person_id, [])
        if not source_rows:
            issues.append({"hsld": hsld, "status": "DB cũ không có bản ghi xếp loại năm 2026"})
            continue
        if len(source_rows) != 1:
            issues.append({"hsld": hsld, "old_count": len(source_rows),
                           "status": "DB cũ có nhiều bản ghi xếp loại năm 2026; không tự chọn"})
            continue
        source_values = dict(zip((p["quarter"] for p in CLASSIFICATION_PERIODS), source_rows[0]))
        targets = target_by_person.get(new_person_id, [])
        if not targets:
            issues.append({"hsld": hsld,
                           "status": "DB mới chưa có bản ghi xếp loại năm 2026"})
            continue
        if len(targets) != 1:
            issues.append({"hsld": hsld, "target_count": len(targets),
                           "status": "DB mới có nhiều bản ghi xếp loại năm 2026; không tự chọn"})
            continue
        target = targets[0]
        for period in CLASSIFICATION_PERIODS:
            quarter = period["quarter"]
            source_code = norm_text(source_values[quarter]).strip()
            label = period["label"]
            if not source_code:
                continue
            if target[f"q{quarter}"] is not None:
                issues.append({"hsld": hsld, "quarter": quarter, "old_code": source_code,
                               "new_value": norm_text(target[f"q{quarter}"]), "target_id": target["id"],
                               "status": f"DB mới đã có {label}; giữ nguyên"})
                continue
            key = source_code.upper()
            old_titles = old_name_by_code.get(key, [])
            if len(old_titles) != 1:
                issues.append({"hsld": hsld, "quarter": quarter, "old_code": source_code,
                               "status": ("Mã xếp loại không có trong danh mục DB cũ"
                                          if not old_titles else "Mã xếp loại trùng trong danh mục DB cũ")})
                continue
            categories = new_category_by_code.get(key, [])
            if len(categories) != 1:
                issues.append({"hsld": hsld, "quarter": quarter, "old_code": source_code,
                               "status": ("Mã xếp loại DB cũ không có trong DM_XEP_LOAIES DB mới"
                                          if not categories else "Mã xếp loại DB mới không duy nhất trong DM_XEP_LOAIES")})
                continue
            category_id, category_title = categories[0]
            updates.append({"id": target["id"], "person_id": new_person_id,
                            "old_person_id": old_person_id, "hsld": hsld, "quarter": quarter,
                            "new_column": period["new_column"], "quarter_label": label,
                            "old_code": source_code, "old_title": old_titles[0],
                            "new_value": category_id, "new_code": source_code,
                            "new_title": category_title})

    for old_person_id in source_by_person:
        if old_person_id not in pairs:
            codes = source_by_person[old_person_id][0]
            issues.append({"hsld": norm_text(hsld_by_old_id.get(old_person_id, "")),
                           "old_code": "/".join(norm_text(code) for code in codes if code),
                           "status": patient_status.get(old_person_id, "Không ghép duy nhất theo HSLĐ")})
    for person in patients:
        new_person_id = person.get("new_id")
        if person.get("old_id") is not None or new_person_id is None:
            continue
        missing_periods = [(row, p) for row in target_by_person.get(new_person_id, [])
                           for p in CLASSIFICATION_PERIODS if row[f"q{p['quarter']}"] is None]
        if missing_periods:
            issues.append({"hsld": norm_text(person.get("new_hsld", "")),
                           "status": person.get("status", "Không ghép được với DB cũ theo HSLĐ")})
    updates.sort(key=lambda row: (not bool(row["hsld"]), row["hsld"].casefold(), str(row["id"])))
    issues.sort(key=lambda row: (not bool(row.get("hsld")), str(row.get("hsld", "")).casefold(), row["status"]))
    return {"updates": updates, "issues": issues, "prison_scope": prison_scope}


def preview_classification_update(old_cfg, new_cfg):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        return _classification_update_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                                           new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass


def apply_classification_update(old_cfg, new_cfg, preview, selected_ids=None):
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        fresh = _classification_update_plan(old_conn, new_conn, old_cfg.get("schema", ""),
                                            new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        signature = lambda rows: [(r["id"], r["person_id"], r["new_value"], r["old_code"], r["quarter"])
                                  for r in rows]
        if signature(preview["updates"]) != signature(fresh["updates"]):
            raise ValueError("Dữ liệu đã thay đổi so với xem trước. Không ghi gì; hãy tải lại xem trước rồi xác nhận lại.")
        if selected_ids is not None:
            selected_keys = set(selected_ids)
            allowed = {(row["id"], row["quarter"]) for row in fresh["updates"]}
            if not selected_keys or not selected_keys.issubset(allowed):
                raise ValueError("Danh sách dòng chọn không còn hợp lệ. Hãy tải lại xem trước.")
            fresh["updates"] = [row for row in fresh["updates"]
                                if (row["id"], row["quarter"]) in selected_keys]
        if not fresh["updates"]:
            raise ValueError("Không có dòng xếp loại quý III hoặc quý IV nào đủ điều kiện cập nhật trong lựa chọn này.")

        table = qualified(new_cfg.get("schema", ""), "XEP_LOAIS")
        person_table = qualified(new_cfg.get("schema", ""), M.PN_NEW["table"])
        cursor = new_conn.cursor()
        for row in fresh["updates"]:
            cursor.execute(
                f'UPDATE {table} T SET "{row["new_column"]}"=:category_id '
                f'WHERE T."ID"=:target_id AND T."PHAM_NHAN_ID"=:person_id '
                f'AND T."XEP_LOAI_NAM"=:year AND T."{row["new_column"]}" IS NULL '
                f'AND NVL(T."IS_DELETED",0)=0 AND EXISTS '
                f'(SELECT 1 FROM {person_table} P WHERE P."{M.PN_NEW["id"]}"=:person_id '
                f'AND P."{M.PN_NEW["trai"]}"=:prison_id AND NVL(P."IS_DELETED",0)=0)',
                {"category_id": row["new_value"], "target_id": row["id"],
                 "person_id": row["person_id"], "year": CLASSIFICATION_YEAR,
                 "prison_id": fresh["prison_scope"]["new_id"]})
            if cursor.rowcount != 1:
                raise RuntimeError("Bản ghi đích đã thay đổi hoặc không còn thuộc trại đã chọn; toàn bộ cập nhật sẽ được rollback.")
        cursor.close()
        new_conn.commit()
        return {"updated_rows": len(fresh["updates"]), "prison_scope": fresh["prison_scope"]}
    except Exception:
        if new_conn:
            new_conn.rollback()
        raise
    finally:
        for conn in (old_conn, new_conn):
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
