-- Copy rows that exist in the legacy lookup tables but are missing from
-- the current tables. IDs and audit columns are preserved.
-- Oracle Database; safe to run repeatedly because matching IDs are skipped.

SET SERVEROUTPUT ON;

DECLARE
    v_dan_toc_inserted PLS_INTEGER := 0;
    v_ton_giao_inserted PLS_INTEGER := 0;
BEGIN
    INSERT INTO QLPN.DM_DAN_TOCS (
        ID,
        DT_MA,
        DT_TEN,
        DT_TRANG_THAI,
        DT_MO_TA,
        CREATION_TIME,
        CREATOR_USER_ID,
        LAST_MODIFICATION_TIME,
        LAST_MODIFIER_USER_ID,
        IS_DELETED,
        DELETER_USER_ID,
        DELETION_TIME
    )
    SELECT
        old.ID,
        old.DT_MA,
        old.DT_TEN,
        old.DT_TRANG_THAI,
        old.DT_MO_TA,
        old.CREATION_TIME,
        old.CREATOR_USER_ID,
        old.LAST_MODIFICATION_TIME,
        old.LAST_MODIFIER_USER_ID,
        old.IS_DELETED,
        old.DELETER_USER_ID,
        old.DELETION_TIME
    FROM QLPN.DM_DAN_TOCS_OLD old
    WHERE NOT EXISTS (
        SELECT 1
        FROM QLPN.DM_DAN_TOCS current_row
        WHERE current_row.ID = old.ID
    );

    v_dan_toc_inserted := SQL%ROWCOUNT;

    INSERT INTO QLPN.DM_TON_GIAOS (
        ID,
        TG_MA,
        TG_TEN,
        TG_TRANG_THAI,
        TG_MO_TA,
        CREATION_TIME,
        CREATOR_USER_ID,
        LAST_MODIFICATION_TIME,
        LAST_MODIFIER_USER_ID,
        IS_DELETED,
        DELETER_USER_ID,
        DELETION_TIME
    )
    SELECT
        old.ID,
        old.TG_MA,
        old.TG_TEN,
        old.TG_TRANG_THAI,
        old.TG_MO_TA,
        old.CREATION_TIME,
        old.CREATOR_USER_ID,
        old.LAST_MODIFICATION_TIME,
        old.LAST_MODIFIER_USER_ID,
        old.IS_DELETED,
        old.DELETER_USER_ID,
        old.DELETION_TIME
    FROM QLPN.DM_TON_GIAOS_OLD old
    WHERE NOT EXISTS (
        SELECT 1
        FROM QLPN.DM_TON_GIAOS current_row
        WHERE current_row.ID = old.ID
    );

    v_ton_giao_inserted := SQL%ROWCOUNT;

    DBMS_OUTPUT.PUT_LINE('DM_DAN_TOCS inserted: ' || v_dan_toc_inserted);
    DBMS_OUTPUT.PUT_LINE('DM_TON_GIAOS inserted: ' || v_ton_giao_inserted);
END;
/

-- Review the resulting ID coverage.
SELECT old.ID AS MISSING_ID_IN_CURRENT
FROM QLPN.DM_DAN_TOCS_OLD old
WHERE NOT EXISTS (
    SELECT 1 FROM QLPN.DM_DAN_TOCS current_row WHERE current_row.ID = old.ID
)
ORDER BY old.ID;

SELECT old.ID AS MISSING_ID_IN_CURRENT
FROM QLPN.DM_TON_GIAOS_OLD old
WHERE NOT EXISTS (
    SELECT 1 FROM QLPN.DM_TON_GIAOS current_row WHERE current_row.ID = old.ID
)
ORDER BY old.ID;

COMMIT;
