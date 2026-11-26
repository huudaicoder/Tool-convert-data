"""Preview/apply legacy province codes to current province IDs."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import csv
from pathlib import Path
import sys
import uuid

import engine
import mapping as M


MAPPING_FILE_NAME = "province_fk_merge.csv"
CURRENT_LAI_LICH_TABLE = "PN_LAI_LICHS"
CURRENT_LAI_LICH_FIELDS = (
    "LL_DIA_CHI_THUONG_TRU_PROVICE",
    "LL_NOI_OTRUOC_KHI_BAT_PROVICE",
    "LL_NOI_THA_VE_CU_TRU_PROVICE",
)


def mapping_file_path():
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / MAPPING_FILE_NAME


def _load_crosswalk():
    path = mapping_file_path()
    if not path.is_file():
        raise FileNotFoundError(f"Chưa có file mapping tỉnh: {path}")
    rows_by_source = defaultdict(list)
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"TTP_MA_CU", "TTP_MA_GIU", "TRANG_THAI", "GHI_CHU"}
        headers = {str(name or "").strip().upper() for name in (reader.fieldnames or [])}
        if not required.issubset(headers):
            raise ValueError("CSV mapping cần các cột: TTP_MA_CU,TTP_MA_GIU,TRANG_THAI,GHI_CHU.")
        # Resolve header casing/whitespace while preserving codes as text.
        header_lookup = {str(name).strip().upper(): name for name in reader.fieldnames}
        for line_no, row in enumerate(reader, start=2):
            source_code = engine.norm_text(row.get(header_lookup["TTP_MA_CU"])).strip()
            target_code = engine.norm_text(row.get(header_lookup["TTP_MA_GIU"])).strip()
            status = engine.norm_text(row.get(header_lookup["TRANG_THAI"])).strip().upper()
            note = engine.norm_text(row.get(header_lookup["GHI_CHU"])).strip()
            if not source_code and not target_code and not status and not note:
                continue
            if not source_code or not target_code:
                rows_by_source[source_code or f"__CSV_LINE_{line_no}__"].append({
                    "source_code": source_code, "target_code": target_code,
                    "status": status, "note": note, "line": line_no, "invalid": True,
                })
                continue
            rows_by_source[source_code].append({"source_code": source_code, "target_code": target_code,
                "status": status, "note": note, "line": line_no})
    return rows_by_source, path


def _key(value):
    if value is None:
        return ""
    return engine.norm_text(value).strip().casefold()


def _province_index(conn, schema_name, new_schema):
    columns = {c[0] for c in new_schema.get("DM_TINH_THANH_PHO", [])}
    required = {"ID", "TTP_MA", "TTP_TEN"}
    if not required.issubset(columns):
        raise ValueError("Schema thiếu DM_TINH_THANH_PHO.ID/TTP_MA/TTP_TEN.")
    deleted = f' WHERE NVL("{engine.AUDIT_DELETED}",0)=0' if engine.AUDIT_DELETED in columns else ""
    _, rows = engine.fetch_all(conn, f'SELECT "ID","TTP_MA","TTP_TEN" FROM {engine.qualified(schema_name, "DM_TINH_THANH_PHO")}{deleted}')
    by_code = defaultdict(list)
    by_id = {}
    for pid, code, name in rows:
        code = engine.norm_text(code).strip()
        by_id[engine.norm_text(pid)] = {"code": code, "name": engine.norm_text(name)}
        if code:
            by_code[code].append(pid)
    return by_code, by_id


def _resolve(code, by_code, province_by_id, crosswalk):
    code = engine.norm_text(code).strip()
    if not code:
        return "EMPTY_SOURCE", None, "", ""
    entries = crosswalk.get(code, [])
    if len(entries) > 1:
        return "AMBIGUOUS_MAPPING", None, "", ""
    if entries:
        entry = entries[0]
        if entry.get("invalid"):
            return "INVALID_MAPPING_ROW", None, "", entry.get("target_code", "")
        if entry.get("status") != "APPROVED":
            return "MAPPING_NOT_APPROVED", None, "", entry.get("target_code", "")
        target_code = engine.norm_text(entry.get("target_code")).strip()
    else:
        # Unchanged province codes can continue to resolve by exact code.
        target_code = code
    matches = by_code.get(target_code, [])
    if not matches:
        return "UNMAPPED_CODE", None, "", target_code
    if len(matches) != 1:
        return "AMBIGUOUS_CODE", None, "", target_code
    province_id = matches[0]
    return "READY", province_id, province_by_id.get(engine.norm_text(province_id), {}).get("name", ""), target_code


def _province_kind(kind):
    return isinstance(kind, tuple) and kind[0] in {"province", "province_text_id"}


def _screen_columns(screen, schemas):
    old_schema, new_schema = schemas
    old_table, new_table = screen["old_table"], screen["new_table"]
    old_cols = {c[0] for c in old_schema.get(old_table, [])}
    new_cols = {c[0] for c in new_schema.get(new_table, [])}
    provinces = [(o, n) for o, n, kind in screen["cols"] if _province_kind(kind)]
    if not provinces:
        return [], None
    needed_old = {screen["old_pn"], *[o for o, _ in provinces]}
    needed_new = {"ID", screen["new_pn"], *[n for _, n in provinces]}
    old_key_new = {}
    for key in screen.get("key", []):
        match = next(((o, n) for o, n, _kind in screen["cols"] if o == key), None)
        if match:
            needed_old.add(match[0]); needed_new.add(match[1])
            old_key_new[match[0]] = match[1]
    missing = ([f'{old_table}.{c}' for c in needed_old - old_cols] +
               [f'{new_table}.{c}' for c in needed_new - new_cols])
    if missing:
        return provinces, {"missing": missing}
    return provinces, {"old_key_new": old_key_new}


def _read_rows(conn, schema_name, table, columns, deleted=False, cancel=None):
    cols = list(dict.fromkeys(columns))
    where = f' WHERE NVL("{engine.AUDIT_DELETED}",0)=0' if deleted else ""
    names, rows = engine.fetch_all(
        conn, f'SELECT {",".join(chr(34)+c+chr(34) for c in cols)} FROM {engine.qualified(schema_name, table)}{where}', cancel=cancel)
    return [dict(zip(names, row)) for row in rows]


def preview(old_cfg, new_cfg, screen_codes=None, cancel=None):
    old_schema, new_schema = engine.load_schema()
    crosswalk, crosswalk_path = _load_crosswalk()
    old_conn = new_conn = None
    try:
        old_conn = engine.connect(old_cfg["dsn"], old_cfg["user"], old_cfg["password"], old_cfg.get("schema", ""), read_only=True)
        new_conn = engine.connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=True)
        screens = [s for s in M.SCREENS if any(_province_kind(k) for _, _, k in s["cols"])
                   and (screen_codes is None or s["code"] in screen_codes)]
        problems = engine.validate_live_mapping(old_conn, old_cfg.get("schema", ""), screens, "old")
        problems += engine.validate_live_mapping(new_conn, new_cfg.get("schema", ""), screens, "new")
        if problems:
            raise ValueError("Schema live không khớp mapping:\n" + "\n".join(problems[:50]))
        pairs, patients, prison_scope = engine.load_person_crosswalk(
            old_conn, new_conn, old_cfg.get("schema", ""), new_cfg.get("schema", ""), new_cfg.get("prison_code", ""))
        hsld_by_person = {p["old_id"]: engine.norm_text(p.get("old_hsld", "")) for p in patients if p.get("old_id") is not None}
        by_code, province_by_id = _province_index(new_conn, new_cfg.get("schema", ""), new_schema)
        result = {"mode": "legacy_to_current", "updates": [], "rows": [], "counts": defaultdict(int), "prison_scope": prison_scope,
                  "screens": [], "mapping_file": str(crosswalk_path),
                  "mapping_rule": "Mã nguồn → CSV TTP_MA_CU/TTP_MA_GIU (nếu có) → TTP_MA duy nhất → DM_TINH_THANH_PHO.ID; mã không đổi có thể khớp TTP_MA trực tiếp."}
        for screen in screens:
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            province_fields, key_config = _screen_columns(screen, (old_schema, new_schema))
            screen_result = {"code": screen["code"], "name": screen["name"], "eligible": False, "message": ""}
            target_types = {c[0]: c[1].upper() for c in new_schema.get(screen["new_table"], [])}
            kinds = {new_col: kind for _old_col, new_col, kind in screen["cols"] if _province_kind(kind)}
            unsafe_fields = [(old_col, new_col) for old_col, new_col in province_fields
                             if not (target_types.get(new_col, "").startswith("NUMBER") or
                                     (kinds.get(new_col, (None,))[0] == "province_text_id" and
                                      target_types.get(new_col, "").startswith(("NVARCHAR2", "VARCHAR2"))))]
            province_fields = [(old_col, new_col) for old_col, new_col in province_fields
                               if (target_types.get(new_col, "").startswith("NUMBER") or
                                   (kinds.get(new_col, (None,))[0] == "province_text_id" and
                                    target_types.get(new_col, "").startswith(("NVARCHAR2", "VARCHAR2"))))]
            if not province_fields:
                screen_result["message"] = "Cột đích không phải ID NUMBER; giữ preview-only, không cập nhật."
                if unsafe_fields:
                    result["counts"]["SCHEMA_UNCONFIRMED"] += len(unsafe_fields)
                result["screens"].append(screen_result)
                continue
            if key_config is None or "missing" in key_config:
                missing = key_config.get("missing", []) if key_config else []
                screen_result["message"] = "Thiếu cột schema: " + ", ".join(missing)
                result["screens"].append(screen_result)
                continue
            old_key_new = key_config["old_key_new"]
            if screen.get("key") and len(old_key_new) != len(screen["key"]):
                screen_result["message"] = "Không ghép đủ khóa sự kiện; chỉ kiểm kê, không cập nhật."
                result["screens"].append(screen_result)
                continue
            old_columns = [screen["old_pn"], *[o for o, _ in province_fields], *old_key_new.keys()]
            new_columns = ["ID", screen["new_pn"], *[n for _, n in province_fields], *old_key_new.values()]
            old_rows = _read_rows(old_conn, old_cfg.get("schema", ""), screen["old_table"], old_columns, cancel=cancel)
            new_has_deleted = engine.AUDIT_DELETED in {c[0] for c in new_schema.get(screen["new_table"], [])}
            new_rows = _read_rows(new_conn, new_cfg.get("schema", ""), screen["new_table"], new_columns, new_has_deleted, cancel)
            new_by_person = defaultdict(list)
            new_to_old = {engine.norm_text(new_id): old_id for old_id, new_id in pairs.items()}
            for row in new_rows:
                old_person = new_to_old.get(engine.norm_text(row[screen["new_pn"]]))
                if old_person is not None:
                    new_by_person[old_person].append(row)
            old_by_person = defaultdict(list)
            for row in old_rows:
                old_person = row[screen["old_pn"]]
                if old_person in pairs:
                    old_by_person[old_person].append(row)
            for old_person, src_rows in old_by_person.items():
                dst_rows = new_by_person.get(old_person, [])
                if old_key_new:
                    def event_key(row, cols):
                        return tuple(_key(row.get(c)) for c in cols)
                    dst_index = defaultdict(list)
                    for dst in dst_rows:
                        dst_index[event_key(dst, list(old_key_new.values()))].append(dst)
                    src_index = defaultdict(list)
                    for src in src_rows:
                        src_index[event_key(src, list(old_key_new.keys()))].append(src)
                    row_pairs = []
                    for ekey, source_group in src_index.items():
                        targets = dst_index.get(ekey, [])
                        if all(ekey) and len(source_group) == 1 and len(targets) == 1:
                            row_pairs.append((source_group[0], targets[0]))
                        else:
                            for src in source_group:
                                for old_col, new_col in province_fields:
                                    result["rows"].append(_issue_row(screen, old_person, ekey, old_col, new_col,
                                        src.get(old_col), "", "", "", "DUPLICATE_OR_MISSING_EVENT_KEY"))
                                    result["counts"]["DUPLICATE_OR_MISSING_EVENT_KEY"] += 1
                else:
                    if len(src_rows) == 1 and len(dst_rows) == 1:
                        row_pairs = [(src_rows[0], dst_rows[0])]
                    else:
                        row_pairs = []
                        for src in src_rows:
                            for old_col, new_col in province_fields:
                                result["rows"].append(_issue_row(screen, old_person, (), old_col, new_col,
                                    src.get(old_col), "", "", "", "NO_UNIQUE_ROW_KEY"))
                                result["counts"]["NO_UNIQUE_ROW_KEY"] += 1
                for src, dst in row_pairs:
                    ekey = event_key(src, list(old_key_new.keys())) if old_key_new else ()
                    for old_col, new_col in province_fields:
                        source_code = engine.norm_text(src.get(old_col)).strip()
                        target_id = dst.get(new_col)
                        status, desired_id, desired_name, desired_code = _resolve(source_code, by_code, province_by_id, crosswalk)
                        if desired_id is not None and kinds.get(new_col, (None,))[0] == "province_text_id":
                            desired_id = engine.norm_text(desired_id)
                        current_id = engine.norm_text(target_id)
                        if status == "READY" and current_id == engine.norm_text(desired_id):
                            status = "ALREADY_CORRECT"
                        row = _issue_row(screen, old_person, ekey, old_col, new_col, source_code,
                                         current_id, desired_id, desired_name, status, dst.get("ID"))
                        row["hsld"] = hsld_by_person.get(old_person, "")
                        row["target_code"] = desired_code
                        result["rows"].append(row); result["counts"][status] += 1
                        if status == "READY":
                            result["updates"].append({"id": dst["ID"], "column": new_col,
                                "old_value": target_id, "new_value": desired_id, "row_key": ekey,
                                "screen": screen["code"], "field": old_col, "target_code": desired_code})
            screen_result["eligible"] = True
            screen_result["message"] = f'{len(province_fields)} cột địa phương; event key: {", ".join(screen.get("key", [])) or "chỉ khi đúng một dòng/phạm nhân"}'
            result["screens"].append(screen_result)
        result["counts"] = dict(result["counts"])
        return result
    finally:
        if old_conn:
            old_conn.rollback(); old_conn.close()
        if new_conn:
            new_conn.rollback(); new_conn.close()


def _issue_row(screen, person_id, key, old_col, new_col, source_code, current_id,
               desired_id, desired_name, status, target_row_id=None):
    return {"screen": screen["code"], "screen_name": screen["name"], "person_id": engine.norm_text(person_id),
            "key": " | ".join(engine.norm_text(v) for v in key), "source_column": old_col,
            "target_column": new_col, "source_code": engine.norm_text(source_code),
            "current_id": engine.norm_text(current_id), "target_id": engine.norm_text(desired_id),
            "target_name": desired_name, "target_code": "", "status": status,
            "row_id": engine.norm_text(target_row_id)}


def preview_current(new_cfg, cancel=None):
    """Preview province-ID consolidation for three Lai lich fields in one DB."""
    _old_schema, new_schema = engine.load_schema()
    crosswalk, crosswalk_path = _load_crosswalk()
    conn = None
    try:
        conn = engine.connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"],
                              new_cfg.get("schema", ""), read_only=True)
        required_ttp = {"ID", "TTP_MA", "TTP_TEN"}
        ttp_cols = {column[0] for column in new_schema.get("DM_TINH_THANH_PHO", [])}
        ll_cols = {column[0] for column in new_schema.get(CURRENT_LAI_LICH_TABLE, [])}
        missing = ([f"DM_TINH_THANH_PHO.{col}" for col in required_ttp - ttp_cols] +
                   [f"{CURRENT_LAI_LICH_TABLE}.{col}" for col in {"ID", *CURRENT_LAI_LICH_FIELDS} - ll_cols])
        if missing:
            raise ValueError("Schema thiếu cột cần thiết: " + ", ".join(missing))
        by_code, province_by_id = _province_index(conn, new_cfg.get("schema", ""), new_schema)
        active = _read_rows(conn, new_cfg.get("schema", ""), CURRENT_LAI_LICH_TABLE,
                            ["ID", *CURRENT_LAI_LICH_FIELDS],
                            engine.AUDIT_DELETED in ll_cols, cancel=cancel)
        rows = []
        updates = []
        counts = defaultdict(int)
        screen = {"code": "CURRENT_LAI_LICH", "name": "Lai lịch (DB hiện tại)"}

        def add_issue(entry, status, source_id="", target_id="", target_name=""):
            row = _issue_row(screen, "", (), "DM_TINH_THANH_PHO.TTP_MA", "PN_LAI_LICHS.*",
                             entry.get("source_code", ""), source_id, target_id, target_name, status)
            row["target_code"] = entry.get("target_code", "")
            row["mapping_line"] = entry.get("line", "")
            rows.append(row)
            counts[status] += 1

        for source_code, entries in crosswalk.items():
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            if len(entries) != 1:
                add_issue(entries[0], "AMBIGUOUS_MAPPING")
                continue
            entry = entries[0]
            if entry.get("invalid"):
                add_issue(entry, "INVALID_MAPPING_ROW")
                continue
            if entry.get("status") != "APPROVED":
                add_issue(entry, "MAPPING_NOT_APPROVED")
                continue
            source_matches = by_code.get(source_code, [])
            target_code = entry["target_code"]
            target_matches = by_code.get(target_code, [])
            if len(source_matches) != 1:
                add_issue(entry, "SOURCE_CODE_NOT_UNIQUE" if source_matches else "SOURCE_CODE_NOT_FOUND")
                continue
            if len(target_matches) != 1:
                add_issue(entry, "TARGET_CODE_NOT_UNIQUE" if target_matches else "TARGET_CODE_NOT_FOUND")
                continue
            source_id, target_id = source_matches[0], target_matches[0]
            target_name = province_by_id.get(engine.norm_text(target_id), {}).get("name", "")
            if engine.norm_text(source_id) == engine.norm_text(target_id):
                add_issue(entry, "SOURCE_EQUALS_TARGET", source_id, target_id, target_name)
                continue
            found = 0
            for record in active:
                for field in CURRENT_LAI_LICH_FIELDS:
                    current_value = record.get(field)
                    if engine.norm_text(current_value) != engine.norm_text(source_id):
                        continue
                    found += 1
                    row = _issue_row(screen, "", (record["ID"],), "DM_TINH_THANH_PHO.TTP_MA",
                                     field, source_code, current_value, target_id, target_name, "READY", record["ID"])
                    row["target_code"] = target_code
                    row["mapping_line"] = entry.get("line", "")
                    rows.append(row)
                    counts["READY"] += 1
                    updates.append({"id": record["ID"], "column": field, "old_value": current_value,
                                    "new_value": target_id, "row_key": (record["ID"],),
                                    "screen": "CURRENT_LAI_LICH", "field": source_code,
                                    "source_code": source_code, "target_code": target_code,
                                    "source_id": source_id, "target_name": target_name})
            if not found:
                add_issue(entry, "NO_REFERENCES", source_id, target_id, target_name)

        result = {"mode": "current_db_merge", "updates": updates, "rows": rows,
                  "counts": dict(counts), "prison_scope": {"code": new_cfg.get("schema", "DB hiện tại")},
                  "screens": [{"code": screen["code"], "name": screen["name"], "eligible": True,
                               "message": f"Chỉ kiểm tra {len(CURRENT_LAI_LICH_FIELDS)} cột tỉnh Lai lịch."}],
                  "mapping_file": str(crosswalk_path),
                  "mapping_rule": "TTP_MA_CU → TTP_MA_GIU; chỉ khi cả hai mã tồn tại duy nhất trong DM_TINH_THANH_PHO."}
        return result
    finally:
        if conn:
            conn.rollback()
            conn.close()


def apply_current(new_cfg, preview, selected_keys=None):
    updates = preview.get("updates", [])
    if selected_keys is not None:
        updates = [item for index, item in enumerate(updates) if index in selected_keys]
    if not updates:
        raise ValueError("Không có dòng READY được chọn để cập nhật.")
    allowed = set(CURRENT_LAI_LICH_FIELDS)
    if preview.get("mode") != "current_db_merge" or any(item.get("column") not in allowed for item in updates):
        raise ValueError("Preview không đúng chế độ hoặc có cột ngoài whitelist Lai lịch; từ chối ghi DB.")
    conn = None
    try:
        conn = engine.connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"],
                              new_cfg.get("schema", ""), read_only=False)
        cursor = conn.cursor()
        target_schema = engine.load_schema()[1]
        soft_delete = (f' AND NVL("{engine.AUDIT_DELETED}",0)=0'
                       if engine.AUDIT_DELETED in {col[0] for col in target_schema.get(CURRENT_LAI_LICH_TABLE, [])}
                       else "")
        for item in updates:
            sql = (f'UPDATE {engine.qualified(new_cfg.get("schema", ""), CURRENT_LAI_LICH_TABLE)} '
                   f'SET "{item["column"]}"=:new_value WHERE "ID"=:row_id AND '
                   f'("{item["column"]}"=:old_value OR ("{item["column"]}" IS NULL AND :old_is_null=1)){soft_delete}')
            cursor.execute(sql, {"new_value": item["new_value"], "row_id": item["id"],
                                 "old_value": item["old_value"], "old_is_null": int(item["old_value"] is None)})
            if cursor.rowcount != 1:
                raise RuntimeError(f'Dữ liệu thay đổi hoặc không duy nhất: {CURRENT_LAI_LICH_TABLE} row {item["id"]} {item["column"]}; transaction đã rollback.')
        conn.commit()
        run_id = uuid.uuid4().hex
        audit_path = Path.home() / "Documents" / "QLPNC10_convert_dia_danh_audit.csv"
        audit_error = ""
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            exists = audit_path.exists()
            fields = ("run_id", "time", "schema", "screen", "field", "target_row_id",
                      "event_key", "old_id", "new_id", "status")
            with audit_path.open("a", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                if not exists:
                    writer.writeheader()
                for item in updates:
                    writer.writerow({"run_id": run_id, "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "schema": new_cfg.get("schema", ""), "screen": "CURRENT_LAI_LICH",
                        "field": item["column"], "target_row_id": item["id"],
                        "event_key": " | ".join(engine.norm_text(value) for value in item["row_key"]),
                        "old_id": item["old_value"], "new_id": item["new_value"], "status": "COMMITTED"})
        except Exception as exc:
            audit_error = f"Đã commit DB nhưng không ghi được audit CSV: {exc}"
        return {"mode": "current_db_merge", "updated": len(updates), "prison_scope": preview.get("prison_scope", {}),
                "audit_path": str(audit_path), "audit_error": audit_error}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def apply(new_cfg, preview, selected_keys=None):
    updates = preview.get("updates", [])
    if selected_keys is not None:
        updates = [u for i, u in enumerate(updates) if i in selected_keys]
    if not updates:
        raise ValueError("Không có dòng READY được chọn để cập nhật.")
    approved = {}
    for screen in M.SCREENS:
        approved[screen["code"]] = {new_col for _old_col, new_col, kind in screen["cols"]
                                    if _province_kind(kind)}
    for item in updates:
        if item.get("column") not in approved.get(item.get("screen"), set()):
            raise ValueError("Preview chứa cột ngoài whitelist mapping địa phương; từ chối ghi DB.")
    conn = None
    try:
        conn = engine.connect(new_cfg["dsn"], new_cfg["user"], new_cfg["password"], new_cfg.get("schema", ""), read_only=False)
        cursor = conn.cursor()
        target_schema = engine.load_schema()[1]
        for item in updates:
            table = next(s["new_table"] for s in M.SCREENS if s["code"] == item["screen"])
            soft_delete = (f' AND NVL("{engine.AUDIT_DELETED}",0)=0'
                           if engine.AUDIT_DELETED in {c[0] for c in target_schema.get(table, [])} else "")
            sql = (f'UPDATE {engine.qualified(new_cfg.get("schema", ""), table)} '
                   f'SET "{item["column"]}"=:new_value WHERE "ID"=:row_id AND '
                   f'("{item["column"]}"=:old_value OR ("{item["column"]}" IS NULL AND :old_is_null=1)){soft_delete}')
            cursor.execute(sql, {"new_value": item["new_value"], "row_id": item["id"],
                                 "old_value": item["old_value"], "old_is_null": int(item["old_value"] is None)})
            if cursor.rowcount != 1:
                raise RuntimeError(f'Dữ liệu đã thay đổi hoặc không duy nhất: {item["screen"]} row {item["id"]} {item["column"]}; toàn bộ transaction đã rollback.')
        conn.commit()
        run_id = uuid.uuid4().hex
        audit_path = Path.home() / "Documents" / "QLPNC10_convert_dia_danh_audit.csv"
        audit_error = ""
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            exists = audit_path.exists()
            with audit_path.open("a", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=("run_id", "time", "schema", "screen", "field",
                    "target_row_id", "event_key", "old_id", "new_id", "status"))
                if not exists:
                    writer.writeheader()
                for item in updates:
                    writer.writerow({"run_id": run_id, "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "schema": new_cfg.get("schema", ""), "screen": item["screen"], "field": item["field"],
                        "target_row_id": item["id"], "event_key": " | ".join(engine.norm_text(v) for v in item["row_key"]),
                        "old_id": item["old_value"], "new_id": item["new_value"], "status": "COMMITTED"})
        except Exception as exc:
            audit_error = f"Đã commit DB nhưng không ghi được audit CSV: {exc}"
        return {"mode": "legacy_to_current", "updated": len(updates), "prison_scope": preview.get("prison_scope", {}),
                "audit_path": str(audit_path), "audit_error": audit_error}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
