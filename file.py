-- ============================================================
-- 1. DECLARE / GET LAST EXECUTION TIMESTAMP
-- ============================================================

DECLARE last_exec_ts DATETIME
DEFAULT DATETIME('2000-01-01 00:00:00');

SET last_exec_ts = (
    SELECT
        COALESCE(
            MAX(previous_execution_timestamp),
            DATETIME('2000-01-01 00:00:00')
        )
    FROM `{project_id}.gid_mfb_audit.mfb_odp_execution_tracking`
    WHERE table_name = 'rds_addnl_support'
);


-- ============================================================
-- 2. CREATE TEMP TABLE
--    Store ranked delta records once and reuse them
-- ============================================================

CREATE TEMP TABLE tmp_rds_addnl_support AS
SELECT
    ASM_ADD_SUPP_NO,
    ASM_CSTMR_INSTRN_POS_ID,
    ASM_USER_ID,
    ASM_CSTMR_REF,
    ASM_SUPPORT_CODE,
    ASM_EFFECTIVE_DT,
    ASM_EXPLICIT_CNSNT_REQ,
    ASM_SPCFC_SUPPORT,
    ASM_EXPIRY_DT,
    ASM_STATUS,
    ODP_INGEST_TIMESTAMP,
    OPTYPE,
    SRC_FILENAME,
    CURRENT_TS,

    ROW_NUMBER() OVER (
        PARTITION BY ASM_ADD_SUPP_NO
        ORDER BY
            ODP_INGEST_TIMESTAMP DESC,
            CURRENT_TS DESC
    ) AS rn

FROM `{project_id}.gid_mfb_staging.rds_addnl_support_stg`

WHERE ODP_INGEST_TIMESTAMP > last_exec_ts
  AND OPTYPE IN ('I', 'U', 'D');


-- ============================================================
-- 3. START TRANSACTION
-- ============================================================

BEGIN TRANSACTION;


-- ============================================================
-- 4. CDC AUDIT
-- ============================================================

INSERT INTO
`{project_id}.gid_mfb_odp_cdc_audit.rds_addnl_support_odp_cdc_audit`
(
    ASM_ADD_SUPP_NO,
    ASM_CSTMR_INSTRN_POS_ID,
    ASM_USER_ID,
    ASM_CSTMR_REF,
    ASM_SUPPORT_CODE,
    ASM_EFFECTIVE_DT,
    ASM_EXPLICIT_CNSNT_REQ,
    ASM_SPCFC_SUPPORT,
    ASM_EXPIRY_DT,
    ASM_STATUS,
    ODP_INGEST_TIMESTAMP,
    OPTYPE,
    SRC_FILENAME,
    CURRENT_TS,
    INGESTION_TS,
    OPTYPE_STG
)

-- ============================================================
-- 4A. EXISTING AUDIT LOGIC
--     Capture current ODP record before change
-- ============================================================

SELECT
    act.ASM_ADD_SUPP_NO,
    act.ASM_CSTMR_INSTRN_POS_ID,
    act.ASM_USER_ID,
    act.ASM_CSTMR_REF,
    act.ASM_SUPPORT_CODE,
    act.ASM_EFFECTIVE_DT,
    act.ASM_EXPLICIT_CNSNT_REQ,
    act.ASM_SPCFC_SUPPORT,
    act.ASM_EXPIRY_DT,
    act.ASM_STATUS,
    act.ODP_INGEST_TIMESTAMP,
    act.OPTYPE,
    act.SRC_FILENAME,
    act.CURRENT_TS,
    CURRENT_DATETIME() AS INGESTION_TS,
    stg.OPTYPE AS OPTYPE_STG

FROM tmp_rds_addnl_support AS stg

INNER JOIN
`{project_id}.gid_mfb_odp.rds_addnl_support_odp` AS act

ON act.ASM_ADD_SUPP_NO = stg.ASM_ADD_SUPP_NO

WHERE stg.rn = 1

  AND act.ODP_INGEST_TIMESTAMP
      < stg.ODP_INGEST_TIMESTAMP


-- ============================================================
-- 4B. NEW AUDIT LOGIC
--     rn != 1 records are not sent to ODP,
--     so preserve them in CDC audit
-- ============================================================

UNION ALL

SELECT
    stg.ASM_ADD_SUPP_NO,
    stg.ASM_CSTMR_INSTRN_POS_ID,
    stg.ASM_USER_ID,
    stg.ASM_CSTMR_REF,
    stg.ASM_SUPPORT_CODE,
    stg.ASM_EFFECTIVE_DT,
    stg.ASM_EXPLICIT_CNSNT_REQ,
    stg.ASM_SPCFC_SUPPORT,
    stg.ASM_EXPIRY_DT,
    stg.ASM_STATUS,
    stg.ODP_INGEST_TIMESTAMP,
    stg.OPTYPE,
    stg.SRC_FILENAME,
    stg.CURRENT_TS,
    CURRENT_DATETIME() AS INGESTION_TS,
    stg.OPTYPE AS OPTYPE_STG

FROM tmp_rds_addnl_support AS stg

WHERE stg.rn != 1;


-- ============================================================
-- 5. CDC MERGE INTO ODP
--    Only latest row rn = 1 is used
-- ============================================================

MERGE INTO
`{project_id}.gid_mfb_odp.rds_addnl_support_odp` AS T

USING
(
    SELECT
        ASM_ADD_SUPP_NO,
        ASM_CSTMR_INSTRN_POS_ID,
        ASM_USER_ID,
        ASM_CSTMR_REF,
        ASM_SUPPORT_CODE,
        ASM_EFFECTIVE_DT,
        ASM_EXPLICIT_CNSNT_REQ,
        ASM_SPCFC_SUPPORT,
        ASM_EXPIRY_DT,
        ASM_STATUS,
        ODP_INGEST_TIMESTAMP,
        OPTYPE,
        SRC_FILENAME,
        CURRENT_TS

    FROM tmp_rds_addnl_support

    WHERE rn = 1

) AS S

ON T.ASM_ADD_SUPP_NO = S.ASM_ADD_SUPP_NO


-- ============================================================
-- DELETE CASE
-- ============================================================

WHEN MATCHED
    AND S.OPTYPE = 'D'
    AND T.ODP_INGEST_TIMESTAMP <= S.ODP_INGEST_TIMESTAMP
THEN
    DELETE


-- ============================================================
-- UPDATE EXISTING RECORD
-- I/U both refresh the existing ODP row
-- ============================================================

WHEN MATCHED
    AND S.OPTYPE IN ('I', 'U')
    AND T.ODP_INGEST_TIMESTAMP < S.ODP_INGEST_TIMESTAMP
THEN

UPDATE SET

    T.ASM_CSTMR_INSTRN_POS_ID =
        S.ASM_CSTMR_INSTRN_POS_ID,

    T.ASM_USER_ID =
        S.ASM_USER_ID,

    T.ASM_CSTMR_REF =
        S.ASM_CSTMR_REF,

    T.ASM_SUPPORT_CODE =
        S.ASM_SUPPORT_CODE,

    T.ASM_EFFECTIVE_DT =
        S.ASM_EFFECTIVE_DT,

    T.ASM_EXPLICIT_CNSNT_REQ =
        S.ASM_EXPLICIT_CNSNT_REQ,

    T.ASM_SPCFC_SUPPORT =
        S.ASM_SPCFC_SUPPORT,

    T.ASM_EXPIRY_DT =
        S.ASM_EXPIRY_DT,

    T.ASM_STATUS =
        S.ASM_STATUS,

    T.ODP_INGEST_TIMESTAMP =
        S.ODP_INGEST_TIMESTAMP,

    T.OPTYPE =
        S.OPTYPE,

    T.SRC_FILENAME =
        S.SRC_FILENAME,

    T.CURRENT_TS =
        S.CURRENT_TS,

    T.UPDATED_TS =
        CURRENT_DATETIME()


-- ============================================================
-- INSERT NEW RECORD
-- U is also allowed as insert for missed-day recovery
-- ============================================================

WHEN NOT MATCHED
    AND S.OPTYPE IN ('I', 'U')
THEN

INSERT
(
    ASM_ADD_SUPP_NO,
    ASM_CSTMR_INSTRN_POS_ID,
    ASM_USER_ID,
    ASM_CSTMR_REF,
    ASM_SUPPORT_CODE,
    ASM_EFFECTIVE_DT,
    ASM_EXPLICIT_CNSNT_REQ,
    ASM_SPCFC_SUPPORT,
    ASM_EXPIRY_DT,
    ASM_STATUS,
    ODP_INGEST_TIMESTAMP,
    OPTYPE,
    SRC_FILENAME,
    CURRENT_TS,
    CREATED_TS,
    UPDATED_TS
)

VALUES
(
    S.ASM_ADD_SUPP_NO,
    S.ASM_CSTMR_INSTRN_POS_ID,
    S.ASM_USER_ID,
    S.ASM_CSTMR_REF,
    S.ASM_SUPPORT_CODE,
    S.ASM_EFFECTIVE_DT,
    S.ASM_EXPLICIT_CNSNT_REQ,
    S.ASM_SPCFC_SUPPORT,
    S.ASM_EXPIRY_DT,
    S.ASM_STATUS,
    S.ODP_INGEST_TIMESTAMP,
    S.OPTYPE,
    S.SRC_FILENAME,
    S.CURRENT_TS,
    CURRENT_DATETIME(),
    CURRENT_DATETIME()
);


-- ============================================================
-- 6. 90-DAY STAGING RETENTION
-- ============================================================

DELETE FROM
`{project_id}.gid_mfb_staging.rds_addnl_support_stg`

WHERE ODP_INGEST_TIMESTAMP
    < DATETIME(
        TIMESTAMP_SUB(
            CURRENT_TIMESTAMP(),
            INTERVAL 90 DAY
        )
    );


-- ============================================================
-- 7. UPDATE EXECUTION TRACKING
-- ============================================================

MERGE
`{project_id}.gid_mfb_audit.mfb_odp_execution_tracking` AS T

USING
(
    SELECT
        'rds_addnl_support' AS table_name,
        CURRENT_DATETIME() AS previous_execution_timestamp
) AS S

ON T.table_name = S.table_name


WHEN MATCHED THEN

UPDATE SET

    T.previous_execution_timestamp =
        S.previous_execution_timestamp


WHEN NOT MATCHED THEN

INSERT
(
    table_name,
    previous_execution_timestamp
)

VALUES
(
    S.table_name,
    S.previous_execution_timestamp
);


-- ============================================================
-- 8. COMMIT
-- ============================================================

COMMIT TRANSACTION;
