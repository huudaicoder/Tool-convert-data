"""Oracle ID conversion for PN_TIEN_AN.PNTA_DIA_PHUONG_ID."""
from __future__ import annotations
import hashlib, json, os, re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import cryptography  # PyInstaller includes Oracle Thin-mode crypto.

def connect(dsn, user, password, schema="", read_only=True):
    import oracledb
    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    if read_only:
        cur=conn.cursor(); cur.execute("SET TRANSACTION READ ONLY"); cur.close()
    if schema and not re.fullmatch(r"[A-Z0-9_$#]+", schema.strip().upper()):
        conn.close(); raise ValueError("Tên schema chỉ được gồm chữ, số, _, $, #.")
    return conn

def qualified(schema, table):
    if not re.fullmatch(r"[A-Z0-9_$#]+", table.upper()): raise ValueError("Tên bảng không hợp lệ.")
    return f'"{schema.upper()}"."{table.upper()}"' if schema else f'"{table.upper()}"'

def fetch_all(conn, sql, binds=None):
    cur=conn.cursor(); cur.arraysize=2000; cur.execute(sql, binds or {})
    names=[d[0] for d in cur.description]; rows=[]
    while True:
        batch=cur.fetchmany(2000)
        if not batch: break
        rows.extend(tuple(v.read() if hasattr(v,"read") else v for v in row) for row in batch)
    cur.close(); return names, rows

def norm_text(value):
    if value is None: return ""
    if isinstance(value,(datetime,date)): return value.strftime("%Y-%m-%d")
    if isinstance(value,Decimal): return format(value.normalize(),"f")
    if isinstance(value,float): return format(Decimal(repr(value)).normalize(),"f")
    if isinstance(value,bytes): return f"<BLOB {len(value)} bytes>"
    return " ".join(str(value).split())

def _oracle_table_columns(conn, schema, table):
    owner = (schema or "").strip().upper()
    if owner:
        _, rows = fetch_all(conn, "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER=:p_owner AND TABLE_NAME=:p_table",
                            {"p_owner": owner, "p_table": table.upper()})
    else:
        _, rows = fetch_all(conn, "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME=:p_table",
                            {"p_table": table.upper()})
    return {row[0] for row in rows}




def _ledger_path():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "QLPNTienAnDiaPhuong"
    return base / "conversion_ledger.json"

def _scope(cfg):
    raw = "|".join((cfg.get("dsn", "").strip().upper(), cfg.get("user", "").strip().upper(), cfg.get("schema", "").strip().upper()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _read_ledger():
    path = _ledger_path()
    if not path.exists(): return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}

def _write_ledger(data):
    path = _ledger_path(); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)

def preview_tien_an_dia_phuong_conversion(cfg):
    """Build an in-memory plan without modifying Oracle."""
    conn = connect(cfg["dsn"], cfg["user"], cfg["password"], cfg.get("schema", ""), read_only=True)
    try:
        required = {
            "PN_TIEN_AN": {"ID", "PNTA_DIA_PHUONG_ID"},
            "DM_DIA_PHUONG": {"ID", "DP_MA", "DP_TEN"},
            "DM_TINH_THANH_PHO": {"ID", "TTP_MA", "TTP_TEN"},
        }
        columns = {t: _oracle_table_columns(conn, cfg.get("schema", ""), t) for t in required}
        missing = [f"{t}.{c}" for t, needed in required.items() for c in sorted(needed-columns[t])]
        if missing: raise ValueError("Schema DB thiếu: " + ", ".join(missing))
        def active(alias, table):
            return f' AND NVL({alias}."IS_DELETED",0)=0' if "IS_DELETED" in columns[table] else ""
        dp_active, ttp_active = active("D", "DM_DIA_PHUONG"), active("T", "DM_TINH_THANH_PHO")
        _, dp_rows = fetch_all(conn, f'SELECT D."ID",D."DP_MA",D."DP_TEN" FROM {qualified(cfg.get("schema", ""), "DM_DIA_PHUONG")} D WHERE 1=1{dp_active}')
        _, ttp_rows = fetch_all(conn, f'SELECT T."ID",T."TTP_MA",T."TTP_TEN" FROM {qualified(cfg.get("schema", ""), "DM_TINH_THANH_PHO")} T WHERE 1=1{ttp_active}')
        dp_by_id = {norm_text(r[0]): (r[1], r[2]) for r in dp_rows}
        target_by_code = defaultdict(list)
        for tid, code, name in ttp_rows:
            key = norm_text(code).strip().upper()
            if key: target_by_code[key].append({"id": tid, "code": code, "name": name})
        _, people = fetch_all(conn,
            f'SELECT P."ID",P."PNTA_DIA_PHUONG_ID" FROM {qualified(cfg.get("schema", ""), "PN_TIEN_AN")} P '
            f'WHERE P."PNTA_DIA_PHUONG_ID" IS NOT NULL{active("P", "PN_TIEN_AN")}')
        ledger = _read_ledger().get(_scope(cfg), {})
        rows = []
        for row_id, old_id in people:
            rid, oid = norm_text(row_id), norm_text(old_id)
            journal = ledger.get(rid)
            if journal:
                if oid == norm_text(journal.get("new_id")): continue
                if oid != norm_text(journal.get("old_id")):
                    rows.append({"row_id":row_id,"old_id":old_id,"status":"LEDGER_CONFLICT","ready":False}); continue
            source = dp_by_id.get(oid)
            if not source:
                rows.append({"row_id":row_id,"old_id":old_id,"status":"NOT_IN_DP_CATALOG","ready":False}); continue
            code, name = source; matches = target_by_code.get(norm_text(code).strip().upper(), [])
            base = {"row_id":row_id,"old_id":old_id,"old_code":code,"old_name":name}
            if not matches: rows.append({**base,"status":"NO_TTP_CODE","ready":False})
            elif len(matches)>1: rows.append({**base,"status":"DUPLICATE_TTP_CODE","ready":False})
            elif oid == norm_text(matches[0]["id"]): continue
            else:
                target=matches[0]
                rows.append({**base,"new_id":target["id"],"new_code":target["code"],"new_name":target["name"],"status":"READY","ready":True})
        counts=Counter(r["status"] for r in rows)
        return {"rows":rows,"counts":dict(counts),"ready_count":counts.get("READY",0),"issue_count":len(rows)-counts.get("READY",0),"unchanged_count":len(people)-len(rows),"total_rows":len(people)}
    finally:
        conn.rollback(); conn.close()

def apply_tien_an_dia_phuong_conversion(cfg, plan, selected_row_ids=None):
    selected={norm_text(x) for x in selected_row_ids} if selected_row_ids is not None else None
    eligible={norm_text(r["row_id"]):r for r in plan["rows"] if r.get("ready")}
    updates=[r for key,r in eligible.items() if selected is None or key in selected]
    if not updates: return {"updated":0,"skipped":0}
    # Re-preview immediately before write to reject stale data or mappings.
    fresh=preview_tien_an_dia_phuong_conversion(cfg)
    fresh_by_id={norm_text(r["row_id"]):r for r in fresh["rows"] if r.get("ready")}
    for row in updates:
        current=fresh_by_id.get(norm_text(row["row_id"]))
        if not current or norm_text(current["old_id"])!=norm_text(row["old_id"]) or norm_text(current["new_id"])!=norm_text(row["new_id"]):
            raise ValueError(f'Dữ liệu đã thay đổi từ lúc preview tại PN_TIEN_AN.ID={row["row_id"]}; hãy preview lại.')
    scope=_scope(cfg); journal=_read_ledger(); scope_rows=journal.setdefault(scope,{})
    for r in updates: scope_rows[norm_text(r["row_id"]) ]={"old_id":norm_text(r["old_id"]),"new_id":norm_text(r["new_id"]),"state":"pending"}
    _write_ledger(journal)
    conn=connect(cfg["dsn"],cfg["user"],cfg["password"],cfg.get("schema",""),read_only=False); count=0
    try:
        table=qualified(cfg.get("schema",""),"PN_TIEN_AN"); dp=qualified(cfg.get("schema",""),"DM_DIA_PHUONG"); ttp=qualified(cfg.get("schema",""),"DM_TINH_THANH_PHO")
        cur=conn.cursor()
        for r in updates:
            cur.execute(f'UPDATE {table} SET "PNTA_DIA_PHUONG_ID"=:new_id WHERE "ID"=:row_id AND "PNTA_DIA_PHUONG_ID"=:old_id AND EXISTS (SELECT 1 FROM {dp} D WHERE D."ID"=:old_id AND UPPER(TRIM(D."DP_MA"))=:code) AND EXISTS (SELECT 1 FROM {ttp} T WHERE T."ID"=:new_id AND UPPER(TRIM(T."TTP_MA"))=:code)',
                {"new_id":r["new_id"],"row_id":r["row_id"],"old_id":r["old_id"],"code":norm_text(r["old_code"]).strip().upper()})
            if cur.rowcount!=1: raise ValueError(f'Dòng PN_TIEN_AN.ID={r["row_id"]} thay đổi hoặc mapping không còn đúng; toàn bộ transaction rollback.')
            count+=1
        conn.commit(); cur.close()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
    for r in updates: scope_rows[norm_text(r["row_id"])]["state"]="committed"
    _write_ledger(journal)
    return {"updated":count,"skipped":len(eligible)-count}
