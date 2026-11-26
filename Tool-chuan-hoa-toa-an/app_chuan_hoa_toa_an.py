"""Standalone current-database court/institution and province FK normalizer."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import uuid

import oracledb
import mapping as M


APP_TITLE = "Chuẩn hóa mã cơ quan/tòa án và địa phương"


def csv_path() -> Path:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / M.CSV_NAME


def norm(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def qualified(schema: str, table: str) -> str:
    if not re.fullmatch(r"[A-Z0-9_$#]+", table.upper()):
        raise ValueError(f"Tên bảng không hợp lệ: {table}")
    return f'"{schema.upper()}"."{table.upper()}"' if schema else f'"{table.upper()}"'


def connect(cfg, read_only=True):
    schema = cfg.get("schema", "").strip().upper()
    if schema and not re.fullmatch(r"[A-Z0-9_$#]+", schema):
        raise ValueError("Tên schema chỉ được gồm chữ, số, _, $, #.")
    conn = oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])
    if read_only:
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.close()
    return conn


def fetch_all(conn, sql, binds=None):
    cursor = conn.cursor()
    cursor.arraysize = 2000
    cursor.execute(sql, binds or {})
    columns = [col[0] for col in cursor.description]
    result = []
    while True:
        chunk = cursor.fetchmany(2000)
        if not chunk:
            break
        result.extend(chunk)
    cursor.close()
    return columns, result


def _owner_clause(schema):
    if schema:
        return "OWNER=:owner", {"owner": schema.upper()}
    return "OWNER=SYS_CONTEXT('USERENV','CURRENT_SCHEMA')", {}


def _live_schema(conn, schema):
    owner_filter, binds = _owner_clause(schema)
    _, records = fetch_all(conn,
        f"SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM ALL_TAB_COLUMNS WHERE {owner_filter}", binds)
    columns = defaultdict(dict)
    for table, column, data_type in records:
        columns[table][column] = norm(data_type).upper()
    return columns


def check_connection(cfg):
    conn = None
    try:
        conn = connect(cfg, read_only=True)
        schema = cfg.get("schema", "").strip().upper()
        _, records = fetch_all(conn, "SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM DUAL")
        current_schema = schema or (norm(records[0][0]) if records else cfg["user"].upper())
        live = _live_schema(conn, schema)
        for table, required in (("DM_CO_QUANS", {"ID", "CQ_MA", "CQ_TEN"}),
                                ("DM_TINH_THANH_PHO", {"ID", "TTP_MA", "TTP_TEN"})):
            if not required.issubset(live.get(table, {})):
                raise ValueError(f"Kết nối được nhưng thiếu bảng/cột bắt buộc {table} ({', '.join(sorted(required))}).")
            fetch_all(conn, f'SELECT "ID" FROM {qualified(schema, table)} WHERE 1=0')
        return current_schema
    finally:
        if conn:
            conn.rollback()
            conn.close()


def _load_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file mapping: {path}")
    items = []
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = {str(col or "").strip().upper() for col in (reader.fieldnames or [])}
        if not set(M.CSV_COLUMNS).issubset(headers):
            raise ValueError("CSV cần đủ header CQ_MA_CU,CQ_MA_MOI,TTP_MA_MOI.")
        lookup = {str(col).strip().upper(): col for col in reader.fieldnames}
        for line, row in enumerate(reader, start=2):
            item = {key: norm(row.get(lookup[key])) for key in M.CSV_COLUMNS}
            if not any(item.values()):
                continue
            item["line"] = line
            item["invalid"] = not all(item[key] for key in M.CSV_COLUMNS)
            items.append(item)
    if not items:
        raise ValueError("CSV chưa có mapping nào. Hãy nhập các cặp mã đã xác nhận rồi preview lại.")
    return items


def _active_catalogs(conn, schema, live):
    cq_cols = live["DM_CO_QUANS"]
    ttp_cols = live["DM_TINH_THANH_PHO"]
    cq_deleted = f' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in cq_cols else ""
    ttp_deleted = f' WHERE NVL("IS_DELETED",0)=0' if "IS_DELETED" in ttp_cols else ""
    _, courts = fetch_all(conn,
        f'SELECT "ID","CQ_MA","CQ_TEN" FROM {qualified(schema, "DM_CO_QUANS")}{cq_deleted}')
    _, provinces = fetch_all(conn,
        f'SELECT "ID","TTP_MA","TTP_TEN" FROM {qualified(schema, "DM_TINH_THANH_PHO")}{ttp_deleted}')
    by_court_code, by_province_code, province_by_id = defaultdict(list), defaultdict(list), {}
    for row_id, code, name in courts:
        code = norm(code)
        if code:
            by_court_code[code].append({"id": row_id, "name": norm(name)})
    for row_id, code, name in provinces:
        code = norm(code)
        value = {"id": row_id, "name": norm(name)}
        if code:
            by_province_code[code].append(value)
        province_by_id[norm(row_id)] = value
    return by_court_code, by_province_code, province_by_id


def preview(cfg, path, selected_tables):
    selected_tables = {name.upper() for name in selected_tables if name}
    if not selected_tables:
        raise ValueError("Chọn ít nhất một bảng trước khi preview.")
    entries = _load_csv(path)
    conn = None
    try:
        conn = connect(cfg, read_only=True)
        schema_name = cfg.get("schema", "").strip().upper()
        live = _live_schema(conn, schema_name)
        court_by_code, province_by_code, province_by_id = _active_catalogs(conn, schema_name, live)
        issues, valid_entries = [], []
        seen_sources = set()
        for entry in entries:
            error = ""
            source, target, location = (entry[key] for key in M.CSV_COLUMNS)
            if entry["invalid"]:
                error = "CSV thiếu mã"
            elif source in seen_sources:
                error = "Mã cơ quan cũ bị lặp trong CSV"
            else:
                seen_sources.add(source)
                old_courts, new_courts = court_by_code.get(source, []), court_by_code.get(target, [])
                new_locations = province_by_code.get(location, [])
                if len(old_courts) != 1:
                    error = "Không tìm thấy mã cơ quan cũ" if not old_courts else "Mã cơ quan cũ không duy nhất"
                elif len(new_courts) != 1:
                    error = "Không tìm thấy mã cơ quan mới" if not new_courts else "Mã cơ quan mới không duy nhất"
                elif len(new_locations) != 1:
                    error = "Không tìm thấy mã tỉnh/thành mới" if not new_locations else "Mã tỉnh/thành mới không duy nhất"
            if error:
                issues.append({"table": "CSV/DANH MỤC", "label": f'Dòng {entry["line"]}', "row_id": "",
                    "old_code": source, "old_name": "", "new_code": target, "new_name": "",
                    "old_location": "", "new_location_code": location, "new_location": "",
                    "status": "ERROR", "note": error})
            else:
                valid_entries.append({**entry, "old_court": old_courts[0], "new_court": new_courts[0],
                                      "new_province": new_locations[0]})

        updates, rows, issues_count = [], list(issues), len(issues)
        references_by_line = defaultdict(int)
        query_errors_by_line = set()
        for label, table, court_col, location_col in M.PAIRS:
            if table not in selected_tables:
                continue
            table_cols = live.get(table, {})
            missing = {"ID", court_col, location_col} - set(table_cols)
            if missing:
                issues_count += 1
                rows.append({"table": table, "label": label, "row_id": "", "old_code": "", "old_name": "",
                    "new_code": "", "new_name": "", "old_location": "", "new_location_code": "",
                    "new_location": "", "status": "ERROR", "note": "Thiếu cột/schema: " + ", ".join(sorted(missing))})
                continue
            court_type, location_type = table_cols[court_col], table_cols[location_col]
            court_is_text_id = court_type.startswith(("VARCHAR2", "NVARCHAR2"))
            if not (court_type.startswith("NUMBER") or court_is_text_id) or not (location_type.startswith("NUMBER") or location_type.startswith(("VARCHAR2", "NVARCHAR2"))):
                issues_count += 1
                rows.append({"table": table, "label": label, "row_id": "", "old_code": "", "old_name": "",
                    "new_code": "", "new_name": "", "old_location": "", "new_location_code": "",
                    "new_location": "", "status": "ERROR", "note": f"Kiểu dữ liệu không hỗ trợ: {court_col}={court_type}, {location_col}={location_type}"})
                continue
            deleted = f' AND NVL(T."IS_DELETED",0)=0' if "IS_DELETED" in table_cols else ""
            qualified_table = f'{qualified(schema_name, table)} T'
            for entry in valid_entries:
                old_court, new_court, new_province = entry["old_court"], entry["new_court"], entry["new_province"]
                old_bind = norm(old_court["id"]) if court_is_text_id else old_court["id"]
                new_court_value = norm(new_court["id"]) if court_is_text_id else new_court["id"]
                new_location_value = norm(new_province["id"]) if location_type.startswith(("VARCHAR2", "NVARCHAR2")) else new_province["id"]
                try:
                    _, found = fetch_all(conn,
                        f'SELECT T."ID",T."{court_col}",T."{location_col}" FROM {qualified_table} '
                        f'WHERE T."{court_col}"=:old_id{deleted}', {"old_id": old_bind})
                except Exception as exc:
                    issues_count += 1
                    query_errors_by_line.add(entry["line"])
                    rows.append({"table": table, "label": label, "row_id": "", "old_code": entry["CQ_MA_CU"],
                        "old_name": old_court["name"], "new_code": entry["CQ_MA_MOI"], "new_name": new_court["name"],
                        "old_location": "", "new_location_code": entry["TTP_MA_MOI"], "new_location": new_province["name"],
                        "status": "ERROR", "note": "Không đọc được dữ liệu: " + str(exc)})
                    continue
                for row_id, current_court_id, current_location_id in found:
                    references_by_line[entry["line"]] += 1
                    change_court = norm(current_court_id) != norm(new_court["id"])
                    change_location = norm(current_location_id) != norm(new_province["id"])
                    status = "READY" if change_court or change_location else "NO_CHANGE"
                    old_location = province_by_id.get(norm(current_location_id), {}).get("name", "")
                    row = {"table": table, "label": label, "row_id": norm(row_id),
                        "old_code": entry["CQ_MA_CU"], "old_name": old_court["name"],
                        "new_code": entry["CQ_MA_MOI"], "new_name": new_court["name"],
                        "old_location": old_location or ("ID " + norm(current_location_id) if current_location_id is not None else "(NULL)"),
                        "new_location_code": entry["TTP_MA_MOI"], "new_location": new_province["name"],
                        "status": status, "note": "Tỉnh/thành đích được áp theo CSV."}
                    rows.append(row)
                    if status == "READY":
                        updates.append({"table": table, "court_column": court_col, "location_column": location_col,
                            "row_id": row_id, "old_court_id": current_court_id, "new_court_id": new_court_value,
                            "old_location_id": current_location_id, "new_location_id": new_location_value,
                            "old_code": entry["CQ_MA_CU"], "new_code": entry["CQ_MA_MOI"],
                            "new_location_code": entry["TTP_MA_MOI"], "label": label})
        for entry in valid_entries:
            if references_by_line[entry["line"]] == 0 and entry["line"] not in query_errors_by_line:
                rows.append({"table": "(các bảng đã chọn)", "label": "Không có bản ghi tham chiếu", "row_id": "",
                    "old_code": entry["CQ_MA_CU"], "old_name": entry["old_court"]["name"],
                    "new_code": entry["CQ_MA_MOI"], "new_name": entry["new_court"]["name"],
                    "old_location": "", "new_location_code": entry["TTP_MA_MOI"],
                    "new_location": entry["new_province"]["name"], "status": "NO_REFERENCES",
                    "note": "Không có dòng nào đang dùng mã cơ quan cũ trong phạm vi đã chọn."})
        return {"rows": rows, "updates": updates, "blocking_issues": issues_count,
            "selected_tables": sorted(selected_tables), "pairs_scanned": sum(1 for p in M.PAIRS if p[1] in selected_tables),
            "mapping_file": str(path), "schema": schema_name}
    finally:
        if conn:
            conn.rollback()
            conn.close()


def apply(cfg, plan, selected_indices=None):
    if plan.get("blocking_issues"):
        raise ValueError("Preview có lỗi CSV/schema/truy vấn; xử lý lỗi rồi preview lại trước khi cập nhật.")
    updates = plan.get("updates", [])
    if selected_indices is not None:
        updates = [item for index, item in enumerate(plan["updates"]) if index in selected_indices]
    if not updates:
        raise ValueError("Không có dòng READY được chọn.")
    allowed = {(table, court, location) for _label, table, court, location in M.PAIRS}
    selected_tables = set(plan.get("selected_tables", []))
    if any((item["table"], item["court_column"], item["location_column"]) not in allowed or item["table"] not in selected_tables for item in updates):
        raise ValueError("Preview có cột ngoài whitelist hoặc ngoài bảng đã chọn; từ chối cập nhật.")

    conn = None
    try:
        conn = connect(cfg, read_only=False)
        cursor = conn.cursor()
        schema = cfg.get("schema", "").strip().upper()
        live = _live_schema(conn, schema)
        for item in updates:
            deleted = f' AND NVL("IS_DELETED",0)=0' if "IS_DELETED" in live.get(item["table"], {}) else ""
            sql = (f'UPDATE {qualified(schema, item["table"])} SET "{item["court_column"]}"=:new_court, '
                   f'"{item["location_column"]}"=:new_location WHERE "ID"=:row_id '
                   f'AND "{item["court_column"]}"=:old_court AND '
                   f'(("{item["location_column"]}"=:old_location) OR '
                   f'("{item["location_column"]}" IS NULL AND :old_location_null=1)){deleted}')
            cursor.execute(sql, {"new_court": item["new_court_id"], "new_location": item["new_location_id"],
                "row_id": item["row_id"], "old_court": item["old_court_id"],
                "old_location": item["old_location_id"], "old_location_null": int(item["old_location_id"] is None)})
            if cursor.rowcount != 1:
                raise RuntimeError(f'{item["table"]} row {norm(item["row_id"])} đã đổi so với preview; toàn bộ transaction rollback.')
        conn.commit()
        audit_path = Path.home() / "Documents" / M.AUDIT_NAME
        run_id = uuid.uuid4().hex
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            exists = audit_path.exists()
            fields = ("run_id", "time", "schema", "table", "pair", "row_id", "cq_ma_cu", "cq_ma_moi", "ttp_ma_moi", "old_court_id", "new_court_id", "old_location_id", "new_location_id")
            with audit_path.open("a", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                if not exists:
                    writer.writeheader()
                for item in updates:
                    writer.writerow({"run_id": run_id, "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "schema": cfg.get("schema", ""), "table": item["table"], "pair": item["label"],
                        "row_id": item["row_id"], "cq_ma_cu": item["old_code"], "cq_ma_moi": item["new_code"],
                        "ttp_ma_moi": item["new_location_code"], "old_court_id": item["old_court_id"],
                        "new_court_id": item["new_court_id"], "old_location_id": item["old_location_id"],
                        "new_location_id": item["new_location_id"]})
            audit_error = ""
        except Exception as exc:
            audit_error = f"DB đã commit nhưng audit không ghi được: {exc}"
        return {"count": len(updates), "audit_path": str(audit_path), "audit_error": audit_error}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


class CourtNormalizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1600x850")
        self.minsize(1100, 650)
        self.events, self.busy, self.plan = [], False, None
        self.row_update_index, self.selected_rows = {}, set()
        self.table_vars, self.table_checks = {}, []
        self._build_ui()
        self.after(150, self._poll)

    def _build_ui(self):
        frame = ttk.LabelFrame(self, text="Kết nối DB hiện tại", padding=8)
        frame.pack(fill="x", padx=8, pady=8)
        self.vars = {key: tk.StringVar() for key in ("dsn", "user", "password", "schema")}
        labels = (("DSN", "dsn", 28), ("User", "user", 18), ("Mật khẩu", "password", 18), ("Schema (để trống nếu mặc định)", "schema", 24))
        for idx, (label, key, width) in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=0, column=idx * 2, sticky="w", padx=(0, 4))
            ttk.Entry(frame, textvariable=self.vars[key], width=width, show="*" if key == "password" else "").grid(row=0, column=idx * 2 + 1, sticky="ew", padx=(0, 10))
        for col in range(8): frame.columnconfigure(col, weight=1 if col % 2 else 0)

        mapping_frame = ttk.Frame(self)
        mapping_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.csv_var = tk.StringVar(value=str(csv_path()))
        ttk.Label(mapping_frame, text="CSV mã cơ quan cũ → mới + tỉnh/thành:").pack(side="left")
        ttk.Entry(mapping_frame, textvariable=self.csv_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(mapping_frame, text="Chọn file...", command=self._choose_csv).pack(side="left")
        ttk.Label(self, text="Tool tra mã trong DM_CO_QUANS/DM_TINH_THANH_PHO rồi cập nhật ID ở các cặp FK đã cấu hình. Địa phương đích trong CSV sẽ được áp kể cả khi địa phương hiện tại đã có giá trị.",
            wraplength=1500, justify="left").pack(anchor="w", padx=8, pady=(0, 6))

        scope = ttk.LabelFrame(self, text="Bảng đưa vào preview (mặc định chọn tất cả)", padding=6)
        scope.pack(fill="x", padx=8, pady=(0, 4))
        controls = ttk.Frame(scope); controls.pack(fill="x")
        self.select_all_button = ttk.Button(controls, text="Chọn tất cả", command=lambda: self._set_tables(True)); self.select_all_button.pack(side="left")
        self.select_none_button = ttk.Button(controls, text="Bỏ chọn tất cả", command=lambda: self._set_tables(False)); self.select_none_button.pack(side="left", padx=5)
        self.scope_label = ttk.Label(controls, text=""); self.scope_label.pack(side="left", padx=8)
        tables = ttk.Frame(scope); tables.pack(fill="x", pady=(4, 0))
        names = sorted({item[1] for item in M.PAIRS})
        for i, table in enumerate(names):
            var = tk.BooleanVar(value=True); self.table_vars[table] = var
            check = ttk.Checkbutton(tables, text=table, variable=var, command=self._update_scope_label)
            check.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=1); self.table_checks.append(check)
        for col in range(4): tables.columnconfigure(col, weight=1)
        self._update_scope_label()

        actions = ttk.Frame(self); actions.pack(fill="x", padx=8, pady=4)
        self.check_button = ttk.Button(actions, text="Kiểm tra kết nối", command=self._check_connection); self.check_button.pack(side="left")
        self.preview_button = ttk.Button(actions, text="Lấy preview", command=self._preview); self.preview_button.pack(side="left", padx=6)
        self.apply_selected_button = ttk.Button(actions, text="Cập nhật dòng chọn", command=lambda: self._apply(True), state="disabled"); self.apply_selected_button.pack(side="left", padx=6)
        self.apply_all_button = ttk.Button(actions, text="Cập nhật tất cả dòng hợp lệ", command=lambda: self._apply(False), state="disabled"); self.apply_all_button.pack(side="left")
        self.selected_label = ttk.Label(actions, text="Đã chọn: 0"); self.selected_label.pack(side="left", padx=10)
        self.status = ttk.Label(actions, text="Chưa preview."); self.status.pack(side="left", padx=10)

        result_frame = ttk.Frame(self); result_frame.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self.columns = ("pick", "table", "pair", "row_id", "old_code", "old_name", "new_code", "new_name", "old_location", "new_location_code", "new_location", "status", "note")
        self.tree = ttk.Treeview(result_frame, columns=self.columns, show="headings", selectmode="none")
        headings = (("pick", "Chọn", 45), ("table", "Bảng", 190), ("pair", "Trường", 230), ("row_id", "Row ID", 100),
            ("old_code", "Mã CQ cũ", 85), ("old_name", "Tên CQ cũ", 220), ("new_code", "Mã CQ mới", 85), ("new_name", "Tên CQ chuẩn", 220),
            ("old_location", "Địa phương hiện tại", 160), ("new_location_code", "Mã tỉnh mới", 90), ("new_location", "Địa phương chuẩn", 160),
            ("status", "Trạng thái", 100), ("note", "Ghi chú", 220))
        for col, title, width in headings:
            self.tree.heading(col, text=title); self.tree.column(col, width=width, anchor="w")
        self.tree.bind("<Button-1>", self._toggle_row)
        ybar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(result_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        result_frame.rowconfigure(0, weight=1); result_frame.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew"); ybar.grid(row=0, column=1, sticky="ns"); xbar.grid(row=1, column=0, sticky="ew")

    def _config(self):
        cfg = {key: var.get().strip() for key, var in self.vars.items()}
        if not cfg["dsn"] or not cfg["user"] or not self.vars["password"].get():
            messagebox.showwarning("Thiếu thông tin", "Nhập DSN, user và mật khẩu DB."); return None
        if "/" not in cfg["dsn"]:
            messagebox.showwarning("DSN chưa đủ", "DSN cần dạng host:port/service."); return None
        cfg["password"] = self.vars["password"].get()
        return cfg

    def _choose_csv(self):
        path = filedialog.askopenfilename(title="Chọn CSV mapping", filetypes=(("CSV", "*.csv"), ("Tất cả", "*.*")))
        if path: self.csv_var.set(path)

    def _selected_tables(self):
        return {table for table, var in self.table_vars.items() if var.get()}

    def _update_scope_label(self):
        self.scope_label.configure(text=f"Đã chọn {len(self._selected_tables())}/{len(self.table_vars)} bảng")

    def _set_tables(self, value):
        if self.busy: return
        for var in self.table_vars.values(): var.set(value)
        self._update_scope_label()

    def _busy(self, state, message):
        self.busy = state
        for button in (self.check_button, self.preview_button, self.select_all_button, self.select_none_button):
            button.configure(state="disabled" if state else "normal")
        for check in self.table_checks: check.configure(state="disabled" if state else "normal")
        self.status.configure(text=message)
        can_apply = bool(self.plan and self.plan["updates"] and not self.plan["blocking_issues"] and not state)
        self.apply_selected_button.configure(state="normal" if can_apply and self.selected_rows else "disabled")
        self.apply_all_button.configure(state="normal" if can_apply else "disabled")

    def _check_connection(self):
        if self.busy: return
        cfg = self._config()
        if cfg:
            self._busy(True, "Đang kiểm tra kết nối và danh mục...")
            threading.Thread(target=self._check_worker, args=(cfg,), daemon=True).start()

    def _check_worker(self, cfg):
        try: self.events.append(("connected", check_connection(cfg)))
        except Exception as exc: self.events.append(("error", str(exc)))

    def _preview(self):
        if self.busy: return
        cfg = self._config()
        if not cfg: return
        tables = self._selected_tables()
        if not tables:
            messagebox.showwarning("Chưa chọn bảng", "Chọn ít nhất một bảng để preview."); return
        self._clear_result()
        self._busy(True, f"Đang preview {len(tables)} bảng...")
        threading.Thread(target=self._preview_worker, args=(cfg, Path(self.csv_var.get().strip()), tables), daemon=True).start()

    def _preview_worker(self, cfg, path, tables):
        try: self.events.append(("preview", preview(cfg, path, tables)))
        except Exception as exc: self.events.append(("error", str(exc)))

    def _clear_result(self):
        self.plan = None; self.row_update_index.clear(); self.selected_rows.clear()
        for item in self.tree.get_children(): self.tree.delete(item)
        self.selected_label.configure(text="Đã chọn: 0")

    def _toggle_row(self, event):
        if self.tree.identify_column(event.x) != "#1": return
        item = self.tree.identify_row(event.y)
        if not item or item not in self.row_update_index: return
        if item in self.selected_rows:
            self.selected_rows.remove(item); self.tree.set(item, "pick", "☐")
        else:
            self.selected_rows.add(item); self.tree.set(item, "pick", "☑")
        self.selected_label.configure(text=f"Đã chọn: {len(self.selected_rows):,}")
        self._busy(False, self.status.cget("text"))

    def _apply(self, selected_only):
        if self.busy or not self.plan: return
        cfg = self._config()
        if not cfg: return
        indices = {self.row_update_index[item] for item in self.selected_rows if item in self.row_update_index} if selected_only else None
        if selected_only and not indices:
            messagebox.showwarning("Chưa chọn dòng", "Chọn ít nhất một dòng READY."); return
        count = len(indices) if indices is not None else len(self.plan["updates"])
        if not messagebox.askyesno("Xác nhận cập nhật", f"Sẽ cập nhật {count:,} cặp FK cơ quan/địa phương. Địa phương sẽ được đặt theo mapping CSV. Tiếp tục?"):
            return
        self._busy(True, "Đang cập nhật và đối chiếu giá trị cũ...")
        threading.Thread(target=self._apply_worker, args=(cfg, self.plan, indices), daemon=True).start()

    def _apply_worker(self, cfg, plan, indices):
        try: self.events.append(("done", apply(cfg, plan, indices)))
        except Exception as exc: self.events.append(("error", str(exc)))

    def _poll(self):
        while self.events:
            kind, result = self.events.pop(0)
            if kind == "connected":
                self._busy(False, f"Kết nối thành công. Schema: {result}.")
                messagebox.showinfo("Kết nối thành công", self.status.cget("text"))
            elif kind == "preview":
                self.plan = result; self.row_update_index.clear(); self.selected_rows.clear()
                ready_index = 0
                for row in result["rows"][:20000]:
                    index = None
                    if row["status"] == "READY":
                        index = ready_index
                        ready_index += 1
                    values = ("☐" if index is not None else "", row.get("table", ""), row.get("label", ""), row.get("row_id", ""),
                        row.get("old_code", ""), row.get("old_name", ""), row.get("new_code", ""), row.get("new_name", ""),
                        row.get("old_location", ""), row.get("new_location_code", ""), row.get("new_location", ""), row.get("status", ""), row.get("note", ""))
                    item = self.tree.insert("", "end", values=values)
                    if index is not None: self.row_update_index[item] = index
                ready = sum(1 for row in result["rows"] if row["status"] == "READY")
                suffix = " (hiển thị tối đa 20.000 dòng)" if len(result["rows"]) > 20000 else ""
                blocked = f' • {result["blocking_issues"]} lỗi, khóa cập nhật' if result["blocking_issues"] else ""
                self._busy(False, f'{ready:,} dòng READY; quét {result["pairs_scanned"]} cặp trong {len(result["selected_tables"])} bảng{blocked}. {result["mapping_file"]}{suffix}')
            elif kind == "done":
                self._clear_result()
                self._busy(False, f'Đã cập nhật {result["count"]:,} cặp FK. Audit: {result["audit_path"]} {result["audit_error"]}')
                messagebox.showinfo("Hoàn tất", self.status.cget("text"))
            else:
                self._busy(False, "Có lỗi.")
                messagebox.showerror("Không xử lý được", result)
        self.after(150, self._poll)


if __name__ == "__main__":
    CourtNormalizerApp().mainloop()
