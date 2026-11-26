"""Old database to new database locality/court conversion engine."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import csv
import re
import sys
import uuid

import oracledb
import mapping as M

AUDIT_DELETED = "IS_DELETED"


def norm(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return " ".join(str(value).split())


def code_key(value):
    return norm(value).strip().casefold()


def ward_name_key(value):
    value = norm(value).strip().casefold()
    return re.sub(r'^(?:xã|phường|thị trấn)\s+', '', value)


def hsld_key(value):
    return " ".join(norm(value).split()).upper()


def qualified(schema, table):
    if not re.fullmatch(r"[A-Z0-9_$#]+", table.upper()):
        raise ValueError(f"Tên bảng không hợp lệ trong cấu hình: {table}")
    schema = (schema or "").strip().upper()
    if schema and not re.fullmatch(r"[A-Z0-9_$#]+", schema):
        raise ValueError("Tên schema chỉ được gồm chữ, số, _, $, #.")
    return f'"{schema}"."{table.upper()}"' if schema else f'"{table.upper()}"'


def connect(cfg, read_only=True):
    if not cfg.get("dsn", "").strip() or not cfg.get("user", "").strip():
        raise ValueError("Cần nhập DSN và user.")
    conn = oracledb.connect(user=cfg["user"].strip(), password=cfg.get("password", ""), dsn=cfg["dsn"].strip())
    if read_only:
        cur = conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        cur.close()
    return conn


def fetch_all(conn, sql, binds=None, cancel=None):
    cur = conn.cursor()
    cur.arraysize = 1000
    cur.execute(sql, binds or {})
    names = [item[0] for item in cur.description]
    rows = []
    while True:
        if cancel and cancel.is_set():
            cur.close()
            raise InterruptedError("Đã hủy theo yêu cầu.")
        batch = cur.fetchmany(1000)
        if not batch:
            break
        rows.extend(tuple(value.read() if hasattr(value, "read") else value for value in row) for row in batch)
    cur.close()
    return names, rows


def live_schema(conn, schema):
    owner = (schema or "").strip().upper()
    if owner:
        _, records = fetch_all(conn,
            "SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM ALL_TAB_COLUMNS WHERE OWNER=:owner",
            {"owner": owner})
    else:
        _, records = fetch_all(conn,
            "SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM USER_TAB_COLUMNS")
    tables = defaultdict(dict)
    for table, column, data_type in records:
        tables[table][column] = norm(data_type).upper()
    return tables


def _missing(schema, table, needed):
    return sorted(set(needed) - set(schema.get(table, {})))


def test_connection(cfg, side):
    conn = None
    try:
        conn = connect(cfg, read_only=True)
        schema = live_schema(conn, cfg.get("schema", ""))
        if side == "old":
            needed = {M.PERSON_OLD["id"], M.PERSON_OLD["hsld"]}
            missing = _missing(schema, M.PERSON_OLD["table"], needed)
            for table in ("MA_CQ", "MA_DP"):
                missing.extend(f"{table}.{col}" for col in _missing(schema, table, {"MA", "ND"}))
            missing.extend(f"MA_DP_XA_PHUONG.{col}" for col in
                           _missing(schema, "MA_DP_XA_PHUONG", {"MA", "ND", "MA_QH"}))
            if missing:
                raise ValueError("Kết nối được nhưng DB cũ thiếu: " + ", ".join(missing))
        else:
            needed = {M.PERSON_NEW["id"], M.PERSON_NEW["hsld"], M.PERSON_NEW["trai"]}
            missing = _missing(schema, M.PERSON_NEW["table"], needed)
            for table, cols in (("DM_CO_QUANS", {"ID", "CQ_MA", "CQ_TEN"}),
                                ("DM_TINH_THANH_PHO", {"ID", "TTP_MA", "TTP_TEN"}),
                                ("DM_XA_PHUONG", {"ID", "XP_MA", "XP_MA_TINH_THANH_PHO", "XP_TEN"}),
                                ("DM_TRAI_GIAMS", {"ID", "TG_MA", "TG_TEN"})):
                missing.extend(f"{table}.{col}" for col in _missing(schema, table, cols))
            if missing:
                raise ValueError("Kết nối được nhưng DB mới thiếu: " + ", ".join(missing))
        _, who = fetch_all(conn, "SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM DUAL")
        return norm(who[0][0]) if who else cfg.get("user", "").upper()
    finally:
        if conn:
            conn.rollback()
            conn.close()


def _deleted(schema, table, alias=None):
    if AUDIT_DELETED not in schema.get(table, {}):
        return ""
    prefix = f'{alias}.' if alias else ""
    return f' AND NVL({prefix}"{AUDIT_DELETED}",0)=0'


def _person_rows(conn, schema_name, schema, master):
    table = master["table"]
    cols = schema.get(table, {})
    needed = {master["id"], master["hsld"]}
    missing = _missing(schema, table, needed)
    if missing:
        raise ValueError(f"{table} thiếu cột: {', '.join(missing)}")
    deleted = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in cols else ""
    sql = (f'SELECT "{master["id"]}","{master["hsld"]}" '
           f'FROM {qualified(schema_name, table)}{deleted}')
    _, rows = fetch_all(conn, sql)
    return rows


def _new_prison(conn, schema_name, schema, prison_code):
    if not prison_code:
        raise ValueError("Cần nhập mã trại DB mới (TG_MA) để giới hạn dữ liệu.")
    cols = schema.get("DM_TRAI_GIAMS", {})
    missing = _missing(schema, "DM_TRAI_GIAMS", {"ID", "TG_MA", "TG_TEN"})
    if missing:
        raise ValueError("DM_TRAI_GIAMS thiếu cột: " + ", ".join(missing))
    deleted = f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in cols else ""
    _, rows = fetch_all(conn,
        f'SELECT "ID","TG_MA","TG_TEN" FROM {qualified(schema_name,"DM_TRAI_GIAMS")} '
        f'WHERE UPPER(TRIM("TG_MA"))=:code{deleted}', {"code": norm(prison_code).strip().upper()})
    if len(rows) != 1:
        raise ValueError(f"Mã trại DB mới '{prison_code}' khớp {len(rows)} dòng; cần đúng một DM_TRAI_GIAMS.TG_MA.")
    return rows[0]


def _fetch_new_people(conn, schema_name, schema, prison_id):
    m = M.PERSON_NEW
    cols = schema.get(m["table"], {})
    deleted = f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in cols else ""
    _, rows = fetch_all(conn,
        f'SELECT "{m["id"]}","{m["hsld"]}" FROM {qualified(schema_name,m["table"])} '
        f'WHERE "{m["trai"]}"=:prison_id{deleted}', {"prison_id": prison_id})
    return rows


def _person_pairs(old_rows, new_rows):
    old_by, new_by = defaultdict(list), defaultdict(list)
    for row in old_rows:
        key = hsld_key(row[1])
        if key:
            old_by[key].append(row)
    for row in new_rows:
        key = hsld_key(row[1])
        if key:
            new_by[key].append(row)
    pairs, issues = {}, []
    for key, sources in old_by.items():
        targets = new_by.get(key, [])
        if len(sources) == 1 and len(targets) == 1:
            pairs[sources[0][0]] = targets[0][0]
        else:
            reason = (f"HSLĐ trùng DB cũ ({len(sources)})" if len(sources) != 1 else
                      f"HSLĐ trùng DB mới ({len(targets)})" if len(targets) > 1 else "Không có hồ sơ DB mới")
            issues.append({"hsld": norm(sources[0][1]), "old_person_id": norm(sources[0][0]),
                           "new_person_id": "", "status": reason})
    for row in old_rows:
        if not hsld_key(row[1]):
            issues.append({"hsld": "", "old_person_id": norm(row[0]), "new_person_id": "", "status": "HSLĐ trống DB cũ"})
    paired_new = set(pairs.values())
    for row in new_rows:
        if row[0] not in paired_new and not hsld_key(row[1]):
            issues.append({"hsld": "", "old_person_id": "", "new_person_id": norm(row[0]), "status": "HSLĐ trống DB mới"})
    return pairs, issues


def _catalog(conn, schema_name, schema, table, code_col, name_col):
    cols = schema.get(table, {})
    missing = _missing(schema, table, {"ID", code_col, name_col})
    if missing:
        raise ValueError(f"{table} thiếu cột: {', '.join(missing)}")
    deleted = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in cols else ""
    _, records = fetch_all(conn,
        f'SELECT "ID","{code_col}","{name_col}" FROM {qualified(schema_name,table)}{deleted}')
    index = defaultdict(list)
    by_id = {}
    for row_id, code, name in records:
        key = code_key(code)
        if key:
            item={"id": row_id, "code": norm(code), "name": norm(name)}
            index[key].append(item)
            by_id[norm(row_id)]=norm(name)
    return {"by_code": index, "by_id": by_id}


def _old_catalog_names(conn, schema_name, schema, table):
    missing=_missing(schema,table,{"MA","ND"})
    if missing:
        raise ValueError(f"DB cũ {table} thiếu cột: {', '.join(missing)}")
    _, records=fetch_all(conn,
        f'SELECT "MA","ND" FROM {qualified(schema_name,table)}')
    index=defaultdict(list)
    for code,name in records:
        key=code_key(code)
        if key:index[key].append(norm(name))
    return index


def _old_ward_catalog(conn, schema_name, schema):
    table = "MA_DP_XA_PHUONG"
    missing = _missing(schema, table, {"MA", "ND", "MA_QH"})
    if missing:
        raise ValueError(f"DB cũ {table} thiếu cột: {', '.join(missing)}")
    _, records = fetch_all(conn,
        f'SELECT "MA","ND","MA_QH" FROM {qualified(schema_name, table)}')
    index = defaultdict(list)
    for ward_code, ward_name, parent_code in records:
        key = (code_key(parent_code), ward_name_key(ward_name))
        if all(key):
            index[key].append({"code": norm(ward_code), "name": norm(ward_name),
                               "parent_code": norm(parent_code)})
    return index


def _new_ward_catalog(conn, schema_name, schema):
    table = "DM_XA_PHUONG"
    missing = _missing(schema, table, {"ID", "XP_MA", "XP_MA_TINH_THANH_PHO", "XP_TEN"})
    if missing:
        raise ValueError(f"DB mới {table} thiếu cột: {', '.join(missing)}")
    deleted = f' WHERE NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in schema.get(table, {}) else ""
    _, records = fetch_all(conn,
        f'SELECT "ID","XP_MA","XP_MA_TINH_THANH_PHO","XP_TEN" '
        f'FROM {qualified(schema_name, table)}{deleted}')
    by_code = defaultdict(list)
    by_id = {}
    for ward_id, ward_code, parent_code, ward_name in records:
        item = {"id": ward_id, "code": norm(ward_code), "parent_code": norm(parent_code),
                "name": norm(ward_name)}
        by_code[code_key(ward_code)].append(item)
        by_id[norm(ward_id)] = item["name"]
    return {"by_code": by_code, "by_id": by_id}


def _query_person_rows(conn, schema_name, schema, screen, side, person_ids, cancel=None):
    table = screen[f"{side}_table"]
    parent_col = screen[f"{side}_pn"]
    fields = []
    for field in screen["fields"]:
        fields.append(field["source"] if side == "old" else field["target"])
        parent_key = "parent_source" if side == "old" else "parent_target"
        if field.get(parent_key):
            fields.append(field[parent_key])
    key_pairs = _key_pairs(screen)
    keys = [pair[0] if side == "old" else pair[1] for pair in key_pairs]
    select = [parent_col, *fields, *keys]
    if side == "new":
        select.insert(0, "ID")
    select = list(dict.fromkeys(select))
    result = []
    values = list(person_ids)
    for start in range(0, len(values), 500):
        if cancel and cancel.is_set():
            raise InterruptedError("Đã hủy theo yêu cầu.")
        chunk = values[start:start+500]
        binds = {f"p{i}": value for i, value in enumerate(chunk)}
        placeholders = ",".join(f":p{i}" for i in range(len(chunk)))
        if screen["code"] == "LL12_BienLai":
            if side == "old":
                sql = (f'SELECT hp."PN_ID" AS "PN_ID",h."MA_CQ_THU_NOP",h."MA_DP_THU_NOP",'
                       f'h."BIEN_LAI_SO",h."NGAY_NOP",h."SO_TIEN_NOP" '
                       f'FROM {qualified(schema_name,"PN_HPBS_THUC_HIEN")} h '
                       f'JOIN {qualified(schema_name,"PN_HPBS_HINH_PHAT")} hp '
                       f'ON hp."MA_PN_HPBSHP"=h."MA_PN_HPBSHP" '
                       f'WHERE hp."PN_ID" IN ({placeholders})')
            else:
                deleted_receipt = _deleted(schema, "PN_BIENLAIES", "b")
                deleted_hpbs = _deleted(schema, "PN_HINH_PHAT_BO_SUNGS", "hp")
                sql = (f'SELECT b."ID",hp."HPBS_MA_PHAM_NHAN" AS "PHAM_NHAN_ID",'
                       f'b."BL_NOP_TAI_CO_QUAN",b."BL_DIA_PHUONG",'
                       f'b."BL_SO_BIEN_LAI",b."BL_NGAY_NOP",b."BL_SO_TIEN" '
                       f'FROM {qualified(schema_name,"PN_BIENLAIES")} b '
                       f'JOIN {qualified(schema_name,"PN_HINH_PHAT_BO_SUNGS")} hp ON hp."ID"=b."HPBS_ID" '
                       f'WHERE hp."HPBS_MA_PHAM_NHAN" IN ({placeholders}){deleted_receipt}{deleted_hpbs}')
            _, rows = fetch_all(conn, sql, binds, cancel)
            result.extend(dict(zip(select, row)) for row in rows)
            continue
        deleted = _deleted(schema, table) if side == "new" else ""
        sql = (f'SELECT {",".join(chr(34)+col+chr(34) for col in select)} '
               f'FROM {qualified(schema_name,table)} WHERE "{parent_col}" IN ({placeholders}){deleted}')
        _, rows = fetch_all(conn, sql, binds, cancel)
        result.extend(dict(zip(select, row)) for row in rows)
    return result


def _event_key(row, keys):
    return tuple(norm(row.get(key)).casefold() for key in keys)


def _key_pairs(screen):
    return screen.get("key_pairs", [(key, key) for key in screen["key"]])


def _append_issue(rows, screen, old_row, hsld, old_pid, new_pid, source_field,
                  target_field, old_code, status, note=""):
    key_pairs = _key_pairs(screen)
    source_row_key = repr(sorted((str(k), norm(v)) for k, v in old_row.items())) if old_row else ""
    rows.append({"screen": screen["code"], "screen_name": screen["name"], "hsld": hsld,
        "old_person_id": norm(old_pid), "new_person_id": norm(new_pid), "old_row_id": "",
        "row_id": "", "source_row_key": source_row_key,
        "event_key": " | ".join(norm(old_row.get(pair[0])) for pair in key_pairs), "source_field": source_field,
        "old_code": norm(old_code), "target_field": target_field, "current_id": "",
        "target_id": "", "target_code": "", "target_name": "", "status": status, "note": note})


def preview(old_cfg, new_cfg, selected_codes, new_prison_code="", cancel=None):
    if not selected_codes:
        raise ValueError("Chọn ít nhất một màn/bảng.")
    old_conn = new_conn = None
    try:
        old_conn = connect(old_cfg, read_only=True)
        new_conn = connect(new_cfg, read_only=True)
        old_schema = live_schema(old_conn, old_cfg.get("schema", ""))
        new_schema = live_schema(new_conn, new_cfg.get("schema", ""))
        old_persons = _person_rows(old_conn, old_cfg.get("schema", ""), old_schema, M.PERSON_OLD)
        prison = _new_prison(new_conn, new_cfg.get("schema", ""), new_schema, new_prison_code)
        new_persons = _fetch_new_people(new_conn, new_cfg.get("schema", ""), new_schema, prison[0])
        person_map, person_issues = _person_pairs(old_persons, new_persons)
        if not person_map:
            raise ValueError("Không ghép được hồ sơ nào theo HSLĐ duy nhất trong phạm vi đã chọn.")
        court_index = _catalog(new_conn, new_cfg.get("schema", ""), new_schema,
                               "DM_CO_QUANS", "CQ_MA", "CQ_TEN")
        province_index = _catalog(new_conn, new_cfg.get("schema", ""), new_schema,
                                  "DM_TINH_THANH_PHO", "TTP_MA", "TTP_TEN")
        indexes = {"court": court_index, "province": province_index}
        if any(field.get("catalog") == "ward" for selected in M.SCREENS
               if selected["code"] in selected_codes for field in selected["fields"]):
            indexes["ward"] = _new_ward_catalog(new_conn, new_cfg.get("schema", ""), new_schema)
            old_ward_index = _old_ward_catalog(old_conn, old_cfg.get("schema", ""), old_schema)
        else:
            old_ward_index = {}
        old_name_indexes = {
            "court": _old_catalog_names(old_conn, old_cfg.get("schema", ""), old_schema, "MA_CQ"),
            "province": _old_catalog_names(old_conn, old_cfg.get("schema", ""), old_schema, "MA_DP"),
        }
        person_hsld = {row[0]: norm(row[1]) for row in old_persons}
        reverse = {new_id: old_id for old_id, new_id in person_map.items()}
        result = {"updates": [], "rows": [], "blocking_issues": 0,
                  "prison_scope": {"old_code": "Toàn bộ DB cũ (một trại)", "new_code": norm(prison[1]), "new_name": norm(prison[2])},
                  "screens": [], "old_schema": old_cfg.get("schema", ""), "new_schema": new_cfg.get("schema", "")}
        for issue in person_issues:
            result["rows"].append({"screen":"Ghép hồ sơ", "screen_name":"Ghép hồ sơ", "hsld":issue["hsld"],
                "old_person_id":issue["old_person_id"], "new_person_id":issue["new_person_id"],
                "old_row_id":"", "row_id":"", "event_key":"", "source_field":"", "old_code":"",
                "target_field":"", "current_id":"", "target_id":"", "target_code":"", "target_name":"",
                "status":issue["status"], "note":"Chỉ ghép hồ sơ theo HSLĐ duy nhất."})
        screen_lookup = {screen["code"]: screen for screen in M.SCREENS}
        for code in selected_codes:
            screen = screen_lookup.get(code)
            if not screen:
                continue
            if cancel and cancel.is_set():
                raise InterruptedError("Đã hủy theo yêu cầu.")
            key_pairs = _key_pairs(screen)
            required_old = {*(pair[0] for pair in key_pairs), *(f["source"] for f in screen["fields"])}
            required_new = {"ID", *(pair[1] for pair in key_pairs), *(f["target"] for f in screen["fields"])}
            required_old.update(f["parent_source"] for f in screen["fields"] if f.get("parent_source"))
            required_new.update(f["parent_target"] for f in screen["fields"] if f.get("parent_target"))
            if not screen.get("join_required"):
                required_old.add(screen["old_pn"])
                required_new.add(screen["new_pn"])
            miss_old = _missing(old_schema, screen["old_table"], required_old)
            miss_new = _missing(new_schema, screen["new_table"], required_new)
            for join_table, join_cols in screen.get("join_required", {}).get("old", {}).items():
                miss_old.extend(f"{join_table}.{column}" for column in _missing(old_schema, join_table, join_cols))
            for join_table, join_cols in screen.get("join_required", {}).get("new", {}).items():
                miss_new.extend(f"{join_table}.{column}" for column in _missing(new_schema, join_table, join_cols))
            if miss_old or miss_new:
                error = "; ".join([*(f"DB cũ {screen['old_table']}.{c}" for c in miss_old),
                                    *(f"DB mới {screen['new_table']}.{c}" for c in miss_new)])
                result["blocking_issues"] += 1
                result["rows"].append({"screen":code,"screen_name":screen["name"],"hsld":"","old_person_id":"",
                    "new_person_id":"","old_row_id":"","row_id":"","event_key":"","source_field":"",
                    "old_code":"","target_field":"","current_id":"","target_id":"","target_code":"",
                    "target_name":"","status":"SCHEMA_MISSING","note":error})
                result["screens"].append({"code":code,"name":screen["name"],"eligible":False,"message":error})
                continue
            old_rows = _query_person_rows(old_conn, old_cfg.get("schema", ""), old_schema, screen,
                                          "old", person_map.keys(), cancel)
            new_rows = _query_person_rows(new_conn, new_cfg.get("schema", ""), new_schema, screen,
                                          "new", person_map.values(), cancel)
            old_by_person, new_by_person = defaultdict(list), defaultdict(list)
            for row in old_rows:
                pid = row.get(screen["old_pn"])
                if pid in person_map:
                    old_by_person[pid].append(row)
            for row in new_rows:
                pid = reverse.get(row.get(screen["new_pn"]))
                if pid is not None:
                    new_by_person[pid].append(row)
            before_count = len(result["rows"])
            for old_pid in person_map:
                src_group, dst_group = old_by_person.get(old_pid, []), new_by_person.get(old_pid, [])
                if not src_group:
                    continue
                matched=[]
                key_pairs = _key_pairs(screen)
                if key_pairs:
                    old_key_cols = [pair[0] for pair in key_pairs]
                    new_key_cols = [pair[1] for pair in key_pairs]
                    old_index, new_index = defaultdict(list), defaultdict(list)
                    for row in src_group: old_index[_event_key(row, old_key_cols)].append(row)
                    for row in dst_group: new_index[_event_key(row, new_key_cols)].append(row)
                    for ekey, candidates in old_index.items():
                        targets = new_index.get(ekey, [])
                        if all(ekey) and len(candidates)==1 and len(targets)==1:
                            matched.append((candidates[0],targets[0],ekey))
                        else:
                            for source_row in candidates:
                                for field in screen["fields"]:
                                    _append_issue(result["rows"],screen,source_row,person_hsld.get(old_pid,""),
                                        old_pid,person_map[old_pid],field["source"],field["target"],
                                        source_row.get(field["source"]),"EVENT_KEY_NOT_UNIQUE",
                                        "Khóa sự kiện trống, thiếu hoặc trùng ở một trong hai DB.")
                                    result["blocking_issues"] += 1
                else:
                    if len(src_group)==1 and len(dst_group)==1:
                        matched.append((src_group[0],dst_group[0],()))
                    else:
                        for source_row in src_group:
                            for field in screen["fields"]:
                                _append_issue(result["rows"],screen,source_row,person_hsld.get(old_pid,""),
                                    old_pid,person_map[old_pid],field["source"],field["target"],
                                    source_row.get(field["source"]),"ROW_NOT_UNIQUE",
                                    f"Cần đúng 1 dòng mỗi bên; DB cũ={len(src_group)}, DB mới={len(dst_group)}.")
                                result["blocking_issues"] += 1
                for source_row,target_row,ekey in matched:
                    for field in screen["fields"]:
                        source_code=norm(source_row.get(field["source"])).strip()
                        old_names=(old_name_indexes[field["catalog"]].get(code_key(source_code),[])
                                   if source_code and field["catalog"] in old_name_indexes else [])
                        old_name=old_names[0] if len(old_names)==1 else ("Mã cũ trùng danh mục" if len(old_names)>1 else "")
                        current_id=norm(target_row.get(field["target"]))
                        current_name=indexes[field["catalog"]]["by_id"].get(current_id, "") if current_id else ""
                        row={"screen":code,"screen_name":screen["name"],"hsld":person_hsld.get(old_pid,""),
                            "old_person_id":norm(old_pid),"new_person_id":norm(person_map[old_pid]),
                            "old_row_id":"","row_id":norm(target_row.get("ID")),
                            "source_row_key":repr(sorted((str(k), norm(v)) for k, v in source_row.items())),
                            "event_key":" | ".join(norm(source_row.get(pair[0])) for pair in key_pairs),
                            "source_field":field["source"],"old_code":source_code,"old_name":old_name,
                            "source_kind":field["catalog"],
                            "target_field":field["target"],"current_id":current_id,"current_name":current_name,
                            "target_id":"","target_code":"",
                            "target_name":"","status":"","note":""}
                        if not source_code:
                            row["status"]="EMPTY_SOURCE"; row["note"]="Nguồn trống; giữ nguyên DB mới."
                        elif field["catalog"] == "ward":
                            row["old_code"] = ""
                            row["old_name"] = source_code
                            old_parent_code = norm(source_row.get(field["parent_source"])).strip()
                            old_ward_matches = old_ward_index.get(
                                (code_key(old_parent_code), ward_name_key(source_code)), [])
                            if not old_parent_code:
                                row["status"] = "WARD_PARENT_EMPTY"
                                row["note"] = f"Mã địa phương nguồn {field['parent_source']} trống; không thể lọc MA_QH."
                            elif not old_ward_matches:
                                row["status"] = "WARD_NAME_NOT_FOUND"
                                row["note"] = (f"Không tìm thấy ND='{source_code}' với "
                                               f"MA_QH='{old_parent_code}' trong MA_DP_XA_PHUONG.")
                                row["old_name"] = source_code
                            elif len(old_ward_matches) > 1:
                                row["status"] = "WARD_NAME_NOT_UNIQUE"
                                row["note"] = (f"Tên xã/phường và MA_QH khớp {len(old_ward_matches)} dòng "
                                               "trong MA_DP_XA_PHUONG.")
                                row["old_name"] = source_code
                            else:
                                old_ward = old_ward_matches[0]
                                row["old_code"] = old_ward["code"]
                                row["old_name"] = source_code
                                ward_matches = indexes["ward"]["by_code"].get(code_key(old_ward["code"]), [])
                                if not ward_matches:
                                    row["status"] = "WARD_CODE_NOT_FOUND"
                                    row["note"] = (f"MA='{old_ward['code']}' không khớp XP_MA trong "
                                                   "DM_XA_PHUONG.")
                                elif len(ward_matches) > 1:
                                    row["status"] = "WARD_CODE_NOT_UNIQUE"
                                    row["note"] = (f"MA='{old_ward['code']}' khớp {len(ward_matches)} "
                                                   "xã/phường trong DM_XA_PHUONG.")
                                else:
                                    dest = ward_matches[0]
                                    row.update({"target_id": norm(dest["id"]), "target_code": dest["code"],
                                                "target_name": dest["name"]})
                                    desired = dest["id"]
                                    if norm(target_row.get(field["target"])) == norm(desired):
                                        row["status"] = "ALREADY_CORRECT"
                                        row["note"] = "ID xã/phường đích đã đúng."
                                    else:
                                        row["status"] = "READY"
                                        result["updates"].append({"table": screen["new_table"],
                                            "row_id": target_row["ID"], "column": field["target"],
                                            "old_value": target_row.get(field["target"]), "new_value": desired,
                                            "text_id": False, "screen": code, "source_field": field["source"],
                                            "old_code": old_ward["code"], "target_code": dest["code"],
                                            "target_name": dest["name"], "hsld": person_hsld.get(old_pid, ""),
                                            "event_key": row["event_key"]})
                                        row["update_index"] = len(result["updates"]) - 1
                        else:
                            matches=indexes[field["catalog"]]["by_code"].get(code_key(source_code),[])
                            if not matches:
                                row["status"]="CODE_NOT_FOUND"; row["note"]="Không có mã này trong danh mục DB mới."
                            elif len(matches)>1:
                                row["status"]="CODE_NOT_UNIQUE"; row["note"]=f"Mã khớp {len(matches)} dòng active trong danh mục DB mới."
                            else:
                                dest=matches[0]
                                row.update({"target_id":norm(dest["id"]),"target_code":dest["code"],"target_name":dest["name"]})
                                target_type=new_schema[screen["new_table"]][field["target"]]
                                desired=norm(dest["id"]) if target_type.startswith(("VARCHAR2","NVARCHAR2","CHAR","NCHAR")) else dest["id"]
                                if norm(target_row.get(field["target"]))==norm(desired):
                                    row["status"]="ALREADY_CORRECT"; row["note"]="ID đích đã đúng."
                                else:
                                    row["status"]="READY"
                                    result["updates"].append({"table":screen["new_table"],"row_id":target_row["ID"],
                                        "column":field["target"],"old_value":target_row.get(field["target"]),
                                        "new_value":desired,"text_id":target_type.startswith(("VARCHAR2","NVARCHAR2","CHAR","NCHAR")),
                                        "screen":code,"source_field":field["source"],"old_code":source_code,
                                        "target_code":dest["code"],"target_name":dest["name"],
                                        "hsld":person_hsld.get(old_pid,""),"event_key":row["event_key"]})
                                    row["update_index"]=len(result["updates"])-1
                        result["rows"].append(row)
            screen_rows=result["rows"][before_count:]
            result["screens"].append({"code":code,"name":screen["name"],"eligible":True,
                "rows":len(screen_rows),"message":f"Đã kiểm tra {len(screen_rows):,} trường địa danh."})
        return result
    finally:
        for conn in (old_conn,new_conn):
            if conn:
                conn.rollback(); conn.close()


def apply_updates(new_cfg, plan, selected_indexes=None):
    updates=plan.get("updates",[])
    if selected_indexes is not None:
        updates=[item for index,item in enumerate(updates) if index in selected_indexes]
    if not updates:
        raise ValueError("Không có dòng READY được chọn.")
    # Every write target must come from the fixed whitelist.
    allowed={(s["new_table"],f["target"]) for s in M.SCREENS for f in s["fields"]}
    if any((item["table"],item["column"]) not in allowed for item in updates):
        raise ValueError("Preview chứa bảng/cột ngoài whitelist; từ chối cập nhật.")
    conn=None
    try:
        conn=connect(new_cfg,read_only=False)
        schema=live_schema(conn,new_cfg.get("schema",""))
        cursor=conn.cursor()
        for item in updates:
            table=item["table"]
            if "ID" not in schema.get(table,{}) or item["column"] not in schema.get(table,{}):
                raise RuntimeError(f"Schema thay đổi: không còn {table}.ID/{item['column']}.")
            deleted=f' AND NVL("{AUDIT_DELETED}",0)=0' if AUDIT_DELETED in schema[table] else ""
            sql=(f'UPDATE {qualified(new_cfg.get("schema",""),table)} SET "{item["column"]}"=:new_value '
                 f'WHERE "ID"=:row_id AND ("{item["column"]}"=:old_value OR '
                 f'("{item["column"]}" IS NULL AND :old_is_null=1)){deleted}')
            binds={"new_value":item["new_value"],"row_id":item["row_id"],
                   "old_value":item["old_value"],"old_is_null":int(item["old_value"] is None)}
            cursor.execute(sql,binds)
            if cursor.rowcount!=1:
                raise RuntimeError(f"Dòng đích đã thay đổi hoặc không duy nhất: {table} ID={norm(item['row_id'])} {item['column']}; đã rollback toàn bộ.")
        conn.commit()
        run_id=uuid.uuid4().hex
        path=Path.home()/"Documents"/"QLPNC10_convert_dia_danh_cu_moi_audit.csv"
        audit_error=""
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            exists=path.exists()
            fields=("run_id","time","schema_new","screen","table","row_id","hsld","event_key",
                    "source_field","old_code","target_field","old_id","new_id","target_code","status")
            with path.open("a",newline="",encoding="utf-8-sig") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                if not exists: writer.writeheader()
                stamp=datetime.now().astimezone().isoformat(timespec="seconds")
                for item in updates:
                    writer.writerow({"run_id":run_id,"time":stamp,"schema_new":new_cfg.get("schema",""),
                        "screen":item["screen"],"table":item["table"],"row_id":norm(item["row_id"]),
                        "hsld":item["hsld"],"event_key":item["event_key"],"source_field":item["source_field"],
                        "old_code":item["old_code"],"target_field":item["column"],"old_id":norm(item["old_value"]),
                        "new_id":norm(item["new_value"]),"target_code":item["target_code"],"status":"COMMITTED"})
        except Exception as exc:
            audit_error=f"DB đã commit nhưng không ghi được audit: {exc}"
        return {"updated":len(updates),"audit_path":str(path),"audit_error":audit_error}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
