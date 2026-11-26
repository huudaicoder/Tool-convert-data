"""Standalone current-database province-ID merge utility."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import sys

import engine
import mapping as M


APP_TITLE = "Gộp mã tỉnh/thành trong DB hiện tại"
CSV_NAME = "province_fk_merge.csv"
AUDIT_NAME = "QLPNC10_gop_ma_tinh_audit.csv"
READY = "READY"

# Confirmed province-ID fields that are not yet part of the old→new mapping.
# Backup tables and report/RT tables are deliberately excluded.
EXTRA_CONFIRMED_TARGETS = (
    ("GTH_KY_GIAM_THOI_HANS", "KGTH_DIA_PHUONG_TOA_ID", "province"),
    ("PN_BIENLAIES", "BL_DIA_PHUONG", "province"),
    # Current-database merge needs no legacy source mapping; the target stores a province FK.
    ("PN_KET_THUC_RA_TRAIS", "KTRT_CONG_AN_TINH_THANH_PHO_ID", "province"),
)


def csv_path() -> Path:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / CSV_NAME


def configured_targets():
    targets = {}
    for screen in M.SCREENS:
        for _old_column, new_column, kind in screen["cols"]:
            if not (isinstance(kind, tuple) and kind[0] in {"province", "province_text_id"}):
                continue
            key = (screen["new_table"], new_column)
            target = targets.setdefault(key, {"table": screen["new_table"], "column": new_column,
                                               "kind": kind[0], "screens": set()})
            target["screens"].add(screen["name"])
    for table, column, kind in EXTRA_CONFIRMED_TARGETS:
        key = (table, column)
        target = targets.setdefault(key, {"table": table, "column": column, "kind": kind, "screens": set()})
        target["screens"].add("Bổ sung đã xác nhận")
    return [targets[key] for key in sorted(targets)]


def _hsld_join_for_table(table, schema, schema_name=""):
    """Return optional HSLD select expression and joins for a target table."""
    table = table.upper()
    target_cols = {name for name, _type in schema.get(table, [])}
    person_cols = {name for name, _type in schema.get("PN_LAI_LICHS", [])}
    if table == "PN_LAI_LICHS" and {"ID", "LL_SO_HO_SO_LAN_DAU"}.issubset(person_cols):
        return 'T."LL_SO_HO_SO_LAN_DAU"', ""

    if not {"ID", "LL_SO_HO_SO_LAN_DAU"}.issubset(person_cols):
        return "NULL", ""

    if table == "PN_BIENLAIES":
        receipt_cols = target_cols
        hpbs_cols = {name for name, _type in schema.get("PN_HINH_PHAT_BO_SUNGS", [])}
        if {"HPBS_ID"}.issubset(receipt_cols) and {"ID", "HPBS_MA_PHAM_NHAN"}.issubset(hpbs_cols):
            joins = (f' LEFT JOIN {engine.qualified(schema_name, "PN_HINH_PHAT_BO_SUNGS")} H ON H."ID"=T."HPBS_ID"'
                     f' LEFT JOIN {engine.qualified(schema_name, "PN_LAI_LICHS")} P ON P."ID"=H."HPBS_MA_PHAM_NHAN"')
            return 'P."LL_SO_HO_SO_LAN_DAU"', joins
        return "NULL", ""

    parent_fk = None
    for screen in M.SCREENS:
        if screen.get("new_table", "").upper() == table and screen.get("new_pn"):
            parent_fk = screen["new_pn"].upper()
            break
    if table == "PN_KET_THUC_RA_TRAIS":
        parent_fk = "KTRT_PN_LAI_LICH_ID"
    if parent_fk == "ID":
        return 'T."LL_SO_HO_SO_LAN_DAU"', ""
    if parent_fk and parent_fk in target_cols:
        joins = f' LEFT JOIN {engine.qualified(schema_name, "PN_LAI_LICHS")} P ON P."ID"=T."{parent_fk}"'
        return 'P."LL_SO_HO_SO_LAN_DAU"', joins
    return "NULL", ""


def _load_csv(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy CSV mapping: {path}")
    grouped = defaultdict(list)
    required = {"TTP_MA_CU", "TTP_MA_GIU", "TRANG_THAI", "GHI_CHU"}
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = {str(name or "").strip().upper() for name in (reader.fieldnames or [])}
        if not required.issubset(headers):
            raise ValueError("CSV cần header TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU.")
        lookup = {str(name).strip().upper(): name for name in reader.fieldnames}
        for line, row in enumerate(reader, start=2):
            old_code = engine.norm_text(row.get(lookup["TTP_MA_CU"])).strip()
            keep_code = engine.norm_text(row.get(lookup["TTP_MA_GIU"])).strip()
            status = engine.norm_text(row.get(lookup["TRANG_THAI"])).strip().upper()
            note = engine.norm_text(row.get(lookup["GHI_CHU"])).strip()
            if not any((old_code, keep_code, status, note)):
                continue
            item = {"old_code": old_code, "keep_code": keep_code, "status": status,
                    "note": note, "line": line, "invalid": not old_code or not keep_code}
            grouped[old_code or f"__LINE_{line}__"].append(item)
    return grouped


def _read_active_provinces(conn, schema_name, schema):
    table_cols = {name for name, _type in schema.get("DM_TINH_THANH_PHO", [])}
    required = {"ID", "TTP_MA", "TTP_TEN"}
    if not required.issubset(table_cols):
        raise ValueError("Schema snapshot thiếu DM_TINH_THANH_PHO.ID/TTP_MA/TTP_TEN.")
    active_filter = f' WHERE NVL("{engine.AUDIT_DELETED}",0)=0' if engine.AUDIT_DELETED in table_cols else ""
    _, rows = engine.fetch_all(conn,
        f'SELECT "ID","TTP_MA","TTP_TEN" FROM {engine.qualified(schema_name, "DM_TINH_THANH_PHO")}{active_filter}')
    by_code = defaultdict(list)
    for province_id, code, name in rows:
        normalized_code = engine.norm_text(code).strip()
        if normalized_code:
            by_code[normalized_code].append({"id": province_id, "name": engine.norm_text(name)})
    return by_code


def check_connection(cfg):
    """Verify login and access to the province catalog without reading business rows."""
    conn = None
    try:
        conn = engine.connect(cfg["dsn"], cfg["user"], cfg["password"], cfg.get("schema", ""), read_only=True)
        owner = cfg.get("schema", "").strip().upper()
        owner_filter = " AND OWNER=:owner" if owner else " AND OWNER=SYS_CONTEXT('USERENV','CURRENT_SCHEMA')"
        binds = {"owner": owner} if owner else {}
        _, rows = engine.fetch_all(conn,
            "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE TABLE_NAME='DM_TINH_THANH_PHO'" + owner_filter, binds)
        columns = {row[0] for row in rows}
        required = {"ID", "TTP_MA", "TTP_TEN"}
        if not required.issubset(columns):
            schema_label = owner or cfg["user"].strip().upper()
            raise ValueError(f"Đăng nhập DB thành công nhưng schema {schema_label} không thấy đủ bảng/cột DM_TINH_THANH_PHO (ID, TTP_MA, TTP_TEN).")
        engine.fetch_all(conn,
            f'SELECT "ID" FROM {engine.qualified(owner, "DM_TINH_THANH_PHO")} WHERE 1=0')
        return {"schema": owner or cfg["user"].strip().upper(), "catalog_columns": len(columns)}
    finally:
        if conn:
            conn.rollback()
            conn.close()


def _target_specs(schema, selected_tables=None):
    selected_tables = {table.upper() for table in selected_tables} if selected_tables is not None else None
    specs = [spec for spec in configured_targets()
             if selected_tables is None or spec["table"].upper() in selected_tables]
    available = defaultdict(dict)
    for table, fields in schema.items():
        available[table] = {column: data_type.upper() for column, data_type in fields}
    supported, issues = [], []
    for spec in specs:
        table, column = spec["table"], spec["column"]
        table_schema = available.get(table)
        if table_schema is None:
            issues.append({"table": table, "column": column, "status": "TABLE_NOT_IN_SCHEMA", "row_id": ""})
            continue
        if "ID" not in table_schema or column not in table_schema:
            issues.append({"table": table, "column": column, "status": "COLUMN_NOT_IN_SCHEMA", "row_id": ""})
            continue
        data_type = table_schema[column]
        if data_type.startswith("NUMBER"):
            spec["data_type"] = data_type
            supported.append(spec)
        elif spec["kind"] == "province_text_id" and data_type.startswith(("VARCHAR2", "NVARCHAR2")):
            spec["data_type"] = data_type
            supported.append(spec)
        else:
            issues.append({"table": table, "column": column, "status": f"UNSUPPORTED_TYPE:{data_type}", "row_id": ""})
    return supported, issues


def preview_current(cfg, mapping_path: Path, cancel=None, selected_tables=None):
    if selected_tables is None:
        selected_tables = {spec["table"] for spec in configured_targets()}
    selected_tables = {table.strip().upper() for table in selected_tables if table.strip()}
    if not selected_tables:
        raise ValueError("Chọn ít nhất một bảng để chạy preview.")
    _old_schema, new_schema = engine.load_schema()
    crosswalk = _load_csv(mapping_path)
    specs, issues = _target_specs(new_schema, selected_tables)
    conn = None
    try:
        conn = engine.connect(cfg["dsn"], cfg["user"], cfg["password"], cfg.get("schema", ""), read_only=True)
        owner = cfg.get("schema", "").strip().upper()
        owner_filter = " AND OWNER=:owner" if owner else " AND OWNER=SYS_CONTEXT('USERENV','CURRENT_SCHEMA')"
        binds = {"owner": owner} if owner else {}
        _, live_columns = engine.fetch_all(conn,
            "SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM ALL_TAB_COLUMNS WHERE 1=1" + owner_filter, binds)
        live = defaultdict(set)
        live_types = {}
        for table, column, data_type in live_columns:
            live[table].add(column)
            live_types[(table, column)] = engine.norm_text(data_type).upper()
        valid_specs = []
        for spec in specs:
            missing = {"ID", spec["column"]} - live.get(spec["table"], set())
            if missing:
                issues.append({"table": spec["table"], "column": spec["column"],
                               "status": "LIVE_SCHEMA_MISSING:" + ",".join(sorted(missing)), "row_id": ""})
            else:
                live_type = live_types.get((spec["table"], spec["column"]), "")
                type_ok = live_type.startswith("NUMBER") or (spec["kind"] == "province_text_id" and live_type in {"VARCHAR2", "NVARCHAR2"})
                if not type_ok:
                    issues.append({"table": spec["table"], "column": spec["column"],
                                   "status": "LIVE_UNSUPPORTED_TYPE:" + live_type, "row_id": ""})
                else:
                    spec["data_type"] = live_type
                    valid_specs.append(spec)
        provinces = _read_active_provinces(conn, cfg.get("schema", ""), new_schema)
        updates, rows, counts = [], [], defaultdict(int)
        target_id_by_source = {}
        references_by_source = defaultdict(int)
        query_errors_by_source = set()
        for source_code, entries in crosswalk.items():
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            entry = entries[0]
            status = ""
            if len(entries) != 1:
                status = "DUPLICATE_SOURCE_IN_CSV"
            elif entry["invalid"]:
                status = "INVALID_CSV_ROW"
            elif entry["status"] != "APPROVED":
                status = "MAPPING_NOT_APPROVED"
            else:
                old_matches = provinces.get(entry["old_code"], [])
                keep_matches = provinces.get(entry["keep_code"], [])
                if len(old_matches) != 1:
                    status = "SOURCE_CODE_NOT_UNIQUE" if old_matches else "SOURCE_CODE_NOT_FOUND"
                elif len(keep_matches) != 1:
                    status = "KEEP_CODE_NOT_UNIQUE" if keep_matches else "KEEP_CODE_NOT_FOUND"
                elif engine.norm_text(old_matches[0]["id"]) == engine.norm_text(keep_matches[0]["id"]):
                    status = "SOURCE_EQUALS_KEEP"
                else:
                    source_id = old_matches[0]["id"]
                    target_id_by_source[engine.norm_text(source_id)] = {
                        "id": keep_matches[0]["id"], "old_code": entry["old_code"],
                        "keep_code": entry["keep_code"], "name": keep_matches[0]["name"],
                        "source_name": old_matches[0]["name"], "source_id": source_id,
                    }
            if status:
                row = {"table": "DM_TINH_THANH_PHO", "column": "TTP_MA", "row_id": "",
                       "old_code": entry.get("old_code", ""), "keep_code": entry.get("keep_code", ""),
                       "old_id": "", "new_id": "", "status": status, "note": entry.get("note", "")}
                rows.append(row); counts[status] += 1

        for spec in valid_specs:
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            data_type = spec["data_type"]
            if data_type.startswith("NUMBER"):
                field_expr = f'T."{spec["column"]}"'
            else:
                field_expr = f'TRIM(T."{spec["column"]}")'
            deleted = f' AND NVL(T."{engine.AUDIT_DELETED}",0)=0' if engine.AUDIT_DELETED in {c[0] for c in new_schema.get(spec["table"], [])} else ""
            hsld_expr, hsld_joins = _hsld_join_for_table(spec["table"], new_schema, cfg.get("schema", ""))
            target_table = f'{engine.qualified(cfg.get("schema", ""), spec["table"])} T'
            for source_key, mapping in target_id_by_source.items():
                if cancel and cancel.is_set():
                    raise InterruptedError("Đã hủy theo yêu cầu.")
                source_id = mapping["source_id"]
                bind_source_id = source_id if data_type.startswith("NUMBER") else engine.norm_text(source_id)
                hsld_unavailable = False
                try:
                    _, found = engine.fetch_all(conn,
                        f'SELECT T."ID",T."{spec["column"]}",{hsld_expr} FROM {target_table}{hsld_joins} '
                        f'WHERE {field_expr}=:source_id{deleted}', {"source_id": bind_source_id}, cancel=cancel)
                except Exception as exc:
                    if not hsld_joins:
                        found = None
                    else:
                        try:
                            _, found = engine.fetch_all(conn,
                                f'SELECT T."ID",T."{spec["column"]}" FROM {target_table} '
                                f'WHERE {field_expr}=:source_id{deleted}', {"source_id": bind_source_id}, cancel=cancel)
                            hsld_unavailable = True
                        except Exception as query_exc:
                            found = None
                            exc = query_exc
                    if found is None:
                        rows.append({"table": spec["table"], "column": spec["column"], "row_id": "",
                            "old_code": mapping["old_code"], "keep_code": mapping["keep_code"], "old_id": source_id,
                            "new_id": mapping["id"], "status": "QUERY_ERROR:" + str(exc), "note": "Không đọc được field; field không được cập nhật."})
                        counts["QUERY_ERROR"] += 1
                        query_errors_by_source.add(source_key)
                        continue
                for found_row in found:
                    row_id, old_value = found_row[0], found_row[1]
                    hsld = engine.norm_text(found_row[2]) if len(found_row) > 2 else ""
                    references_by_source[source_key] += 1
                    old_id_text = engine.norm_text(old_value)
                    new_id_value = engine.norm_text(mapping["id"]) if spec["kind"] == "province_text_id" else mapping["id"]
                    rows.append({"table": spec["table"], "column": spec["column"], "row_id": engine.norm_text(row_id),
                        "hsld": hsld,
                        "old_code": mapping["old_code"], "keep_code": mapping["keep_code"],
                        "old_id": old_id_text, "new_id": engine.norm_text(mapping["id"]),
                        "status": READY, "note": (f'{mapping["source_name"]} → {mapping["name"]}' +
                            ("; không tra được HSLĐ" if hsld_unavailable else ""))})
                    updates.append({"table": spec["table"], "column": spec["column"], "row_id": row_id,
                        "old_value": old_value, "new_value": new_id_value, "old_code": mapping["old_code"],
                        "keep_code": mapping["keep_code"], "old_id": old_value, "new_id": mapping["id"]})
                    counts[READY] += 1
        for source_key, mapping in target_id_by_source.items():
            if references_by_source[source_key] == 0 and source_key not in query_errors_by_source:
                rows.append({"table": "(toàn phạm vi)", "column": "(các cột đã cấu hình)", "row_id": "",
                    "old_code": mapping["old_code"], "keep_code": mapping["keep_code"],
                    "old_id": source_key, "new_id": engine.norm_text(mapping["id"]),
                    "status": "NO_REFERENCES", "note": "Không có FK đang dùng ID mã cũ trong whitelist."})
                counts["NO_REFERENCES"] += 1
        for row in issues:
            rows.append({"table": row["table"], "column": row["column"], "row_id": row["row_id"],
                "old_code": "", "keep_code": "", "old_id": "", "new_id": "", "status": row["status"], "note": "Kiểm tra schema/cấu hình."})
            counts[row["status"].split(":", 1)[0]] += 1
        return {"mode": "current_db_all_province_fields", "rows": rows, "updates": updates,
                "counts": dict(counts), "mapping_file": str(mapping_path), "fields_scanned": len(valid_specs),
                "fields_configured": sum(1 for spec in configured_targets() if spec["table"].upper() in selected_tables),
                "selected_tables": sorted(selected_tables), "schema": cfg.get("schema", ""),
                "blocking_issues": len(issues) + counts.get("QUERY_ERROR", 0)}
    finally:
        if conn:
            conn.rollback()
            conn.close()


def apply_current(cfg, plan, selected_indices=None):
    if plan.get("mode") != "current_db_all_province_fields":
        raise ValueError("Preview không thuộc tool gộp mã tỉnh DB hiện tại.")
    if plan.get("blocking_issues", 0):
        raise ValueError("Preview có lỗi schema/truy vấn ở một số field; xử lý lỗi và chạy preview lại trước khi cập nhật để bảo đảm quét đủ phạm vi.")
    updates = plan.get("updates", [])
    if selected_indices is not None:
        updates = [update for index, update in enumerate(plan["updates"]) if index in selected_indices]
    if not updates:
        raise ValueError("Không có dòng READY được chọn.")
    allowed = {(spec["table"], spec["column"]) for spec in configured_targets()}
    if any((item["table"], item["column"]) not in allowed for item in updates):
        raise ValueError("Preview chứa bảng/cột ngoài whitelist mapping; từ chối ghi.")
    selected_tables = {table.upper() for table in plan.get("selected_tables", [])}
    if any(item["table"].upper() not in selected_tables for item in updates):
        raise ValueError("Preview chứa bảng ngoài phạm vi đã chọn; từ chối ghi.")
    _old_schema, new_schema = engine.load_schema()
    conn = None
    try:
        conn = engine.connect(cfg["dsn"], cfg["user"], cfg["password"], cfg.get("schema", ""), read_only=False)
        cursor = conn.cursor()
        for item in updates:
            deleted = f' AND NVL("{engine.AUDIT_DELETED}",0)=0' if engine.AUDIT_DELETED in {c[0] for c in new_schema.get(item["table"], [])} else ""
            sql = (f'UPDATE {engine.qualified(cfg.get("schema", ""), item["table"])} SET "{item["column"]}"=:new_value '
                   f'WHERE "ID"=:row_id AND ("{item["column"]}"=:old_value OR '
                   f'("{item["column"]}" IS NULL AND :old_is_null=1)){deleted}')
            cursor.execute(sql, {"new_value": item["new_value"], "row_id": item["row_id"],
                "old_value": item["old_value"], "old_is_null": int(item["old_value"] is None)})
            if cursor.rowcount != 1:
                raise RuntimeError(f'{item["table"]}.{item["column"]} row {item["row_id"]} đã đổi từ preview; toàn bộ transaction rollback.')
        conn.commit()
        run_id = uuid.uuid4().hex
        audit_path = Path.home() / "Documents" / AUDIT_NAME
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            exists = audit_path.exists()
            fields = ("run_id", "time", "schema", "table", "column", "row_id", "old_code", "keep_code", "old_id", "new_id", "status")
            with audit_path.open("a", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                if not exists:
                    writer.writeheader()
                for item in updates:
                    writer.writerow({"run_id": run_id, "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "schema": cfg.get("schema", ""), "table": item["table"], "column": item["column"],
                        "row_id": item["row_id"], "old_code": item["old_code"], "keep_code": item["keep_code"],
                        "old_id": item["old_id"], "new_id": item["new_id"], "status": "COMMITTED"})
            audit_error = ""
        except Exception as exc:
            audit_error = f"Đã commit DB nhưng không ghi được audit: {exc}"
        return {"updated": len(updates), "audit_path": str(audit_path), "audit_error": audit_error}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


class ProvinceMergeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1450x780")
        self.minsize(1000, 600)
        self.events = []
        self.busy = False
        self.plan = None
        self.update_row_ids = {}
        self.selected_rows = set()
        self.cancel_event = threading.Event()
        self.table_vars = {}
        self.table_checkbuttons = []
        self._build_ui()
        self.after(150, self._poll)

    def _build_ui(self):
        connection = ttk.LabelFrame(self, text="Kết nối DB mới (DB hiện tại)", padding=8)
        connection.pack(fill="x", padx=8, pady=8)
        self.vars = {key: tk.StringVar() for key in ("dsn", "user", "password", "schema")}
        labels = (("DSN", "dsn", 28), ("User", "user", 18), ("Mật khẩu", "password", 18), ("Schema (để trống nếu mặc định)", "schema", 24))
        for index, (label, key, width) in enumerate(labels):
            ttk.Label(connection, text=label).grid(row=0, column=index * 2, sticky="w", padx=(0, 4))
            entry = ttk.Entry(connection, textvariable=self.vars[key], width=width, show="*" if key == "password" else "")
            entry.grid(row=0, column=index * 2 + 1, sticky="ew", padx=(0, 10))
        for col in range(8): connection.columnconfigure(col, weight=1 if col % 2 else 0)

        mapping_frame = ttk.Frame(self)
        mapping_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.mapping_var = tk.StringVar(value=str(csv_path()))
        ttk.Label(mapping_frame, text="CSV mã cũ → mã giữ:").pack(side="left")
        ttk.Entry(mapping_frame, textvariable=self.mapping_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(mapping_frame, text="Chọn file...", command=self._choose_csv).pack(side="left")
        ttk.Label(self, text=(f"Tool quét {len(configured_targets())} cột FK tỉnh đã cấu hình trong mapping.py. "
            "Chỉ update FK đang trỏ tới ID của mã cũ; không xóa danh mục, không sửa xã/phường."),
            wraplength=1400, justify="left").pack(anchor="w", padx=8, pady=(0, 6))

        scope = ttk.LabelFrame(self, text="Bảng đưa vào preview (mặc định chọn tất cả)", padding=6)
        scope.pack(fill="x", padx=8, pady=(0, 4))
        scope_actions = ttk.Frame(scope)
        scope_actions.pack(fill="x", anchor="w")
        self.select_all_button = ttk.Button(scope_actions, text="Chọn tất cả", command=lambda: self._set_tables_selected(True))
        self.select_all_button.pack(side="left")
        self.select_none_button = ttk.Button(scope_actions, text="Bỏ chọn tất cả", command=lambda: self._set_tables_selected(False))
        self.select_none_button.pack(side="left", padx=5)
        self.table_scope_label = ttk.Label(scope_actions, text="")
        self.table_scope_label.pack(side="left", padx=8)
        tables_frame = ttk.Frame(scope)
        tables_frame.pack(fill="x", anchor="w", pady=(4, 0))
        table_names = sorted({spec["table"] for spec in configured_targets()})
        for index, table in enumerate(table_names):
            var = tk.BooleanVar(value=True)
            self.table_vars[table] = var
            check = ttk.Checkbutton(tables_frame, text=table, variable=var, command=self._update_table_count)
            check.grid(row=index // 4, column=index % 4, sticky="w", padx=(0, 18), pady=1)
            self.table_checkbuttons.append(check)
        for col in range(4): tables_frame.columnconfigure(col, weight=1)
        self._update_table_count()

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=8, pady=4)
        self.connection_button = ttk.Button(actions, text="Kiểm tra kết nối", command=self._check_connection)
        self.connection_button.pack(side="left")
        self.preview_button = ttk.Button(actions, text="Lấy preview", command=self._preview)
        self.preview_button.pack(side="left", padx=6)
        self.apply_selected = ttk.Button(actions, text="Cập nhật dòng chọn", command=lambda: self._apply(True), state="disabled")
        self.apply_selected.pack(side="left", padx=6)
        self.apply_all = ttk.Button(actions, text="Cập nhật tất cả dòng hợp lệ", command=lambda: self._apply(False), state="disabled")
        self.apply_all.pack(side="left")
        self.selected_label = ttk.Label(actions, text="Đã chọn: 0")
        self.selected_label.pack(side="left", padx=10)
        self.status = ttk.Label(actions, text="Chưa preview.")
        self.status.pack(side="left", padx=10)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        columns = ("pick", "table", "column", "row_id", "hsld", "old_code", "keep_code", "old_id", "new_id", "status", "note")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        headings = (("pick", "Chọn", 48), ("table", "Bảng", 210), ("column", "Cột", 260),
                    ("row_id", "Row ID", 115), ("hsld", "Số HSLĐ", 130),
                    ("old_code", "Mã cũ", 90), ("keep_code", "Mã giữ", 90),
                    ("old_id", "ID hiện tại", 105), ("new_id", "ID sau cập nhật", 110),
                    ("status", "Trạng thái", 190), ("note", "Ghi chú", 260))
        for column, title, width in headings:
            self.tree.heading(column, text=title); self.tree.column(column, width=width, anchor="w")
        self.tree.bind("<Button-1>", self._toggle_row)
        ybar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew"); ybar.grid(row=0, column=1, sticky="ns"); xbar.grid(row=1, column=0, sticky="ew")

    def _choose_csv(self):
        path = filedialog.askopenfilename(title="Chọn CSV mapping", filetypes=(("CSV", "*.csv"), ("Tất cả", "*.*")))
        if path: self.mapping_var.set(path)

    def _cfg(self):
        cfg = {key: value.get().strip() for key, value in self.vars.items()}
        if not cfg["dsn"] or not cfg["user"] or not self.vars["password"].get():
            messagebox.showwarning("Thiếu thông tin", "Nhập DSN, user và mật khẩu DB hiện tại."); return None
        if "/" not in cfg["dsn"]:
            messagebox.showwarning("DSN chưa đủ", "DSN cần dạng host:port/service."); return None
        cfg["password"] = self.vars["password"].get()
        return cfg

    def _selected_tables(self):
        return {table for table, var in self.table_vars.items() if var.get()}

    def _update_table_count(self):
        self.table_scope_label.configure(text=f"Đã chọn {len(self._selected_tables())}/{len(self.table_vars)} bảng")

    def _set_tables_selected(self, selected):
        if self.busy: return
        for var in self.table_vars.values(): var.set(selected)
        self._update_table_count()

    def _check_connection(self):
        if self.busy: return
        cfg = self._cfg()
        if not cfg: return
        self._set_busy(True, "Đang kiểm tra kết nối DB và danh mục tỉnh...")
        threading.Thread(target=self._connection_worker, args=(cfg,), daemon=True).start()

    def _connection_worker(self, cfg):
        try:
            self.events.append(("connection_ok", check_connection(cfg)))
        except Exception as exc:
            self.events.append(("connection_error", str(exc)))

    def _preview(self):
        if self.busy: return
        cfg = self._cfg()
        if not cfg: return
        selected_tables = self._selected_tables()
        if not selected_tables:
            messagebox.showwarning("Chưa chọn bảng", "Chọn ít nhất một bảng trước khi chạy preview."); return
        path = Path(self.mapping_var.get().strip())
        self._clear_preview(); self._set_busy(True, f"Đang quét các bảng đã chọn ({len(selected_tables)} bảng)...")
        threading.Thread(target=self._preview_worker, args=(cfg, path, selected_tables), daemon=True).start()

    def _preview_worker(self, cfg, path, selected_tables):
        try:
            plan = preview_current(cfg, path, self.cancel_event, selected_tables)
            self.events.append(("preview", plan))
        except Exception as exc:
            self.events.append(("error", str(exc)))

    def _clear_preview(self):
        self.plan = None; self.update_row_ids.clear(); self.selected_rows.clear()
        for item in self.tree.get_children(): self.tree.delete(item)
        self.selected_label.configure(text="Đã chọn: 0")

    def _toggle_row(self, event):
        if self.tree.identify_column(event.x) != "#1": return
        item = self.tree.identify_row(event.y)
        if not item or item not in self.update_row_ids: return
        if item in self.selected_rows:
            self.selected_rows.remove(item); self.tree.set(item, "pick", "☐")
        else:
            self.selected_rows.add(item); self.tree.set(item, "pick", "☑")
        self.selected_label.configure(text=f"Đã chọn: {len(self.selected_rows):,}")
        self._refresh_buttons()

    def _refresh_buttons(self):
        can_apply = bool(self.plan and self.plan.get("updates") and not self.plan.get("blocking_issues") and not self.busy)
        self.apply_selected.configure(state="normal" if can_apply and self.selected_rows else "disabled")
        self.apply_all.configure(state="normal" if can_apply else "disabled")

    def _apply(self, selected_only):
        if self.busy or not self.plan: return
        cfg = self._cfg()
        if not cfg: return
        selected = {self.update_row_ids[item] for item in self.selected_rows if item in self.update_row_ids} if selected_only else None
        if selected_only and not selected:
            messagebox.showwarning("Chưa chọn dòng", "Chọn ít nhất một dòng READY."); return
        count = len(selected) if selected is not None else len(self.plan["updates"])
        if not messagebox.askyesno("Xác nhận cập nhật", f"Sẽ cập nhật {count:,} FK tỉnh trong DB hiện tại. Danh mục tỉnh/xã không bị sửa. Tiếp tục?"):
            return
        plan = self.plan
        self._set_busy(True, "Đang cập nhật và kiểm tra giá trị cũ...")
        threading.Thread(target=self._apply_worker, args=(cfg, plan, selected), daemon=True).start()

    def _apply_worker(self, cfg, plan, selected):
        try: self.events.append(("done", apply_current(cfg, plan, selected)))
        except Exception as exc: self.events.append(("error", str(exc)))

    def _set_busy(self, busy, text):
        self.busy = busy
        self.connection_button.configure(state="disabled" if busy else "normal")
        self.preview_button.configure(state="disabled" if busy else "normal")
        self.select_all_button.configure(state="disabled" if busy else "normal")
        self.select_none_button.configure(state="disabled" if busy else "normal")
        for check in self.table_checkbuttons:
            check.configure(state="disabled" if busy else "normal")
        self.status.configure(text=text)
        self._refresh_buttons()

    def _poll(self):
        while self.events:
            event = self.events.pop(0)
            if event[0] == "preview":
                self.plan = event[1]; self.update_row_ids.clear()
                status_labels = {
                    READY: "Sẵn sàng cập nhật", "NO_REFERENCES": "Không có FK cần đổi",
                    "DUPLICATE_SOURCE_IN_CSV": "Mã cũ trùng trong CSV", "INVALID_CSV_ROW": "Dòng CSV thiếu mã",
                    "MAPPING_NOT_APPROVED": "Mapping chưa duyệt", "SOURCE_CODE_NOT_FOUND": "Không tìm thấy mã cũ",
                    "SOURCE_CODE_NOT_UNIQUE": "Mã cũ không duy nhất", "KEEP_CODE_NOT_FOUND": "Không tìm thấy mã giữ",
                    "KEEP_CODE_NOT_UNIQUE": "Mã giữ không duy nhất", "SOURCE_EQUALS_KEEP": "Hai mã cùng ID",
                }
                update_lookup = {(update["table"], update["column"], engine.norm_text(update["row_id"])): index
                                 for index, update in enumerate(self.plan["updates"])}
                for row in self.plan["rows"][:20000]:
                    update_index = update_lookup.get((row["table"], row["column"], row["row_id"])) if row["status"] == READY else None
                    status = row["status"].split(":", 1)[0]
                    status_label = status_labels.get(status, row["status"])
                    item = self.tree.insert("", "end", values=("☐" if update_index is not None else "", row["table"], row["column"], row["row_id"],
                        row.get("hsld", ""), row["old_code"], row["keep_code"], row["old_id"], row["new_id"], status_label, row["note"]))
                    if update_index is not None: self.update_row_ids[item] = update_index
                counts = self.plan["counts"]
                suffix = " (chỉ hiện 20.000 dòng đầu)" if len(self.plan["rows"]) > 20000 else ""
                blocked = self.plan.get("blocking_issues", 0)
                blocked_text = f" • {blocked} lỗi schema/truy vấn, nút cập nhật bị khóa" if blocked else ""
                scope_text = f'{len(self.plan["selected_tables"])} bảng'
                self._set_busy(False, f'{counts.get(READY, 0):,} FK READY; quét {self.plan["fields_scanned"]}/{self.plan["fields_configured"]} cột trong {scope_text}{blocked_text}. {self.plan["mapping_file"]}{suffix}')
            elif event[0] == "done":
                result = event[1]; self._clear_preview()
                self._set_busy(False, f'Đã cập nhật {result["updated"]:,} FK. Audit: {result["audit_path"]} {result["audit_error"]}')
                messagebox.showinfo("Hoàn tất", self.status.cget("text"))
            elif event[0] == "connection_ok":
                self._set_busy(False, f'Kết nối thành công. Schema: {event[1]["schema"]}; đọc được danh mục DM_TINH_THANH_PHO.')
                messagebox.showinfo("Kết nối thành công", self.status.cget("text"))
            elif event[0] == "connection_error":
                self._set_busy(False, "Kiểm tra kết nối không thành công.")
                messagebox.showerror("Không kết nối được", event[1])
            elif event[0] == "error":
                self._set_busy(False, "Có lỗi."); messagebox.showerror("Không xử lý được", event[1])
        self.after(150, self._poll)


if __name__ == "__main__":
    ProvinceMergeApp().mainloop()
