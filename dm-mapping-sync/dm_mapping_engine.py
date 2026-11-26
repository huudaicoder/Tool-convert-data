"""Preview and synchronize the two fixed QLPN lookup-table pairs."""
from __future__ import annotations

import re


TABLES = {
    "Dân tộc": {
        "old": "DM_DAN_TOCS_OLD",
        "current": "DM_DAN_TOCS",
        "columns": (
            "ID", "DT_MA", "DT_TEN", "DT_TRANG_THAI", "DT_MO_TA",
            "CREATION_TIME", "CREATOR_USER_ID", "LAST_MODIFICATION_TIME",
            "LAST_MODIFIER_USER_ID", "IS_DELETED", "DELETER_USER_ID", "DELETION_TIME",
        ),
    },
    "Tôn giáo": {
        "old": "DM_TON_GIAOS_OLD",
        "current": "DM_TON_GIAOS",
        "columns": (
            "ID", "TG_MA", "TG_TEN", "TG_TRANG_THAI", "TG_MO_TA",
            "CREATION_TIME", "CREATOR_USER_ID", "LAST_MODIFICATION_TIME",
            "LAST_MODIFIER_USER_ID", "IS_DELETED", "DELETER_USER_ID", "DELETION_TIME",
        ),
    },
}


def _schema_name(value: str) -> str:
    name = (value or "QLPN").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_$#]+", name):
        raise ValueError("Schema chỉ được gồm chữ, số, _, $, #.")
    return name


def _connect(cfg):
    import oracledb

    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])


def _missing_rows(conn, schema: str, spec):
    cols = spec["columns"]
    col_sql = ", ".join(f'old."{col}"' for col in cols)
    sql = (
        f'SELECT {col_sql} FROM "{schema}"."{spec["old"]}" old '
        f'WHERE NOT EXISTS (SELECT 1 FROM "{schema}"."{spec["current"]}" cur '
        'WHERE cur."ID" = old."ID") ORDER BY old."ID"'
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = [tuple(value.read() if hasattr(value, "read") else value for value in row)
            for row in cursor.fetchall()]
    cursor.close()
    return rows


def preview(cfg):
    schema = _schema_name(cfg.get("schema", "QLPN"))
    conn = _connect(cfg)
    try:
        result = {label: _missing_rows(conn, schema, spec) for label, spec in TABLES.items()}
        conn.rollback()
        return result
    finally:
        conn.close()


def synchronize(cfg, expected_ids=None):
    """Recheck and insert both pairs atomically; never update existing IDs."""
    schema = _schema_name(cfg.get("schema", "QLPN"))
    conn = _connect(cfg)
    inserted = {}
    try:
        cursor = conn.cursor()
        for label, spec in TABLES.items():
            rows = _missing_rows(conn, schema, spec)
            if expected_ids is not None:
                live_ids = [row[0] for row in rows]
                if live_ids != expected_ids.get(label, []):
                    raise RuntimeError(f"Danh sách ID {label} đã thay đổi sau preview. Hãy kiểm tra lại trước khi chèn.")
            if not rows:
                inserted[label] = 0
                continue
            cols = spec["columns"]
            target_cols = ", ".join(f'"{col}"' for col in cols)
            binds = ", ".join(f":{i}" for i in range(1, len(cols) + 1))
            sql = f'INSERT INTO "{schema}"."{spec["current"]}" ({target_cols}) VALUES ({binds})'
            cursor.executemany(sql, rows)
            inserted[label] = len(rows)
        conn.commit()
        cursor.close()
        return inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_connection(cfg):
    _schema_name(cfg.get("schema", "QLPN"))
    conn = _connect(cfg)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SYS_CONTEXT('USERENV','DB_NAME'), SYS_CONTEXT('USERENV','CURRENT_SCHEMA'), SYSDATE FROM DUAL")
        result = cursor.fetchone()
        cursor.close()
        conn.rollback()
        return result
    finally:
        conn.close()
