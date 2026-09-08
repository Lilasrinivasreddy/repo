-- =====================================================================
-- SCHEME_EMPLOYER - PRD READ-ONLY FAILURE VALIDATION
-- NO INSERT / UPDATE / DELETE / MERGE / CREATE
-- =====================================================================


-- =====================================================================
-- TEST 1: OVERALL SCD2 STATUS
-- Purpose:
-- Check total rows, latest records, historical records and business keys.
-- =====================================================================

SELECT
    COUNT(*) AS total_rows,
    COUNTIF(latest_rec_ind = TRUE) AS latest_true,
    COUNTIF(latest_rec_ind = FALSE) AS historical_false,

    COUNT(
        DISTINCT CONCAT(
            CAST(scheme_id AS STRING),
            '|',
            CAST(org_id AS STRING),
            '|',
            CAST(src_sys_id AS STRING)
        )
    ) AS distinct_business_keys

FROM `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

WHERE src_sys_id = 2;


-- =====================================================================
-- TEST 2: ODP MULTIPLE VERSIONS BUT FDP HAS FEWER ROWS
--
-- Purpose:
-- Find scenarios where ODP/source has multiple CURRENT_TS versions
-- for the same Scheme + Org + Hash, but FDP contains fewer rows.
--
-- This directly tests:
-- "There are scenarios where two rows are present on ODP
--  whereas there is only one row in FDP."
-- =====================================================================

WITH src_versions AS (

    SELECT
        SAFE_CAST(sch.ISC_POA_SCHEME_ID AS INT64) AS scheme_id,
        SAFE_CAST(prhm.IPY_PARTY_ID AS INT64) AS org_id,

        TO_HEX(
            SHA256(
                CONCAT(
                    COALESCE(
                        CAST(prhmd.IDD_ROLE_COMML_DATE AS STRING),
                        ''
                    ),
                    COALESCE(
                        CAST(prhmd.IDD_ROLE_EXP_DATE AS STRING),
                        ''
                    )
                )
            )
        ) AS hash_key_txt,

        prhmd.CURRENT_TS AS source_current_ts,

        DATE(prhmd.ODP_INGEST_TIMESTAMP) AS odp_ingest_date

    FROM
        `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_pty_map_dtl_stg`
        prhmd

    INNER JOIN
        `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_pty_map_stg`
        prhm

        ON prhmd.IRD_ROL_HDR_PTY_MAP_ID =
           prhm.IRD_ROL_HDR_PTY_MAP_ID

    INNER JOIN
        `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_stg`
        prh

        ON prh.IHR_ROLE_HDR_ID =
           prhm.IHR_ROLE_HDR_ID

        AND prh.IHR_ARRANGEMENT_REF_NO =
            prhm.IRD_ARRANGEMENT_REF_NO

    INNER JOIN
        `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_scheme_stg`
        sch

        ON sch.ISC_POA_SCHEME_ID =
           prh.IHR_ASSOC_TYPE_ID

    WHERE

        prhmd.IDD_DELETE_FLAG = 'N'

        AND prhmd.IDD_REC_END_DATE =
            '9999-01-01T00:00:00'

        AND prhmd.IDD_EFF_START_DATE <
            prhmd.IDD_EFF_END_DATE

        AND prhm.IRD_DELETE_FLAG = 'N'

        AND prhm.IRD_REC_END_DATE =
            '9999-01-01T00:00:00'

        AND prh.IHR_DELETE_FLAG = 'N'

        AND prh.IHR_REC_END_DATE =
            '9999-01-01T00:00:00'

        AND prh.IHR_ROLE_TYP = 'SEMP'

        AND prh.IHR_ASSOC_TYPE_CD = 'SCH'

        AND prh.IHR_ARRGMT_LEVEL_CD = 'SCH'

        AND sch.ISC_DELETE_FLAG = 'N'

        AND sch.ISC_REC_END_DATE =
            '9999-01-01T00:00:00'
),

src_cnt AS (

    SELECT
        scheme_id,
        org_id,
        hash_key_txt,

        COUNT(*) AS odp_rows,

        COUNT(
            DISTINCT source_current_ts
        ) AS odp_versions,

        MIN(source_current_ts)
            AS first_source_ts,

        MAX(source_current_ts)
            AS latest_source_ts

    FROM src_versions

    GROUP BY
        scheme_id,
        org_id,
        hash_key_txt
),

fdp_cnt AS (

    SELECT
        scheme_id,
        org_id,
        hash_key_txt,

        COUNT(*) AS fdp_rows

    FROM
        `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

    WHERE src_sys_id = 2

    GROUP BY
        scheme_id,
        org_id,
        hash_key_txt
)

SELECT
    s.scheme_id,
    s.org_id,
    s.hash_key_txt,

    s.odp_rows,
    s.odp_versions,

    COALESCE(
        f.fdp_rows,
        0
    ) AS fdp_rows,

    s.first_source_ts,
    s.latest_source_ts

FROM src_cnt s

LEFT JOIN fdp_cnt f

    ON s.scheme_id = f.scheme_id
    AND s.org_id = f.org_id
    AND s.hash_key_txt = f.hash_key_txt

WHERE
    s.odp_versions >
    COALESCE(f.fdp_rows, 0)

ORDER BY
    s.odp_versions -
    COALESCE(f.fdp_rows, 0) DESC;


-- =====================================================================
-- TEST 3: SAME HASH + MULTIPLE SOURCE VERSIONS
--
-- Purpose:
-- Check whether same Scheme + Org + Hash exists with multiple
-- source CURRENT_TS values.
--
-- If rows are returned, this proves that multiple source versions
-- can have the same hash.
-- =====================================================================

SELECT
    SAFE_CAST(
        sch.ISC_POA_SCHEME_ID AS INT64
    ) AS scheme_id,

    SAFE_CAST(
        prhm.IPY_PARTY_ID AS INT64
    ) AS org_id,

    TO_HEX(
        SHA256(
            CONCAT(
                COALESCE(
                    CAST(
                        prhmd.IDD_ROLE_COMML_DATE
                        AS STRING
                    ),
                    ''
                ),

                COALESCE(
                    CAST(
                        prhmd.IDD_ROLE_EXP_DATE
                        AS STRING
                    ),
                    ''
                )
            )
        )
    ) AS hash_key_txt,

    COUNT(*) AS source_rows,

    COUNT(
        DISTINCT prhmd.CURRENT_TS
    ) AS different_source_versions,

    MIN(prhmd.CURRENT_TS)
        AS first_current_ts,

    MAX(prhmd.CURRENT_TS)
        AS latest_current_ts

FROM
    `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_pty_map_dtl_stg`
    prhmd

INNER JOIN
    `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_pty_map_stg`
    prhm

    ON prhmd.IRD_ROL_HDR_PTY_MAP_ID =
       prhm.IRD_ROL_HDR_PTY_MAP_ID

INNER JOIN
    `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_role_hdr_stg`
    prh

    ON prh.IHR_ROLE_HDR_ID =
       prhm.IHR_ROLE_HDR_ID

    AND prh.IHR_ARRANGEMENT_REF_NO =
        prhm.IRD_ARRANGEMENT_REF_NO

INNER JOIN
    `iw-gid-prd-01-c683.gid_brd_staging.ta_poa_scheme_stg`
    sch

    ON sch.ISC_POA_SCHEME_ID =
       prh.IHR_ASSOC_TYPE_ID

WHERE

    prhmd.IDD_DELETE_FLAG = 'N'

    AND prhmd.IDD_REC_END_DATE =
        '9999-01-01T00:00:00'

    AND prhmd.IDD_EFF_START_DATE <
        prhmd.IDD_EFF_END_DATE

    AND prhm.IRD_DELETE_FLAG = 'N'

    AND prhm.IRD_REC_END_DATE =
        '9999-01-01T00:00:00'

    AND prh.IHR_DELETE_FLAG = 'N'

    AND prh.IHR_REC_END_DATE =
        '9999-01-01T00:00:00'

    AND prh.IHR_ROLE_TYP = 'SEMP'

    AND prh.IHR_ASSOC_TYPE_CD = 'SCH'

    AND prh.IHR_ARRGMT_LEVEL_CD = 'SCH'

    AND sch.ISC_DELETE_FLAG = 'N'

    AND sch.ISC_REC_END_DATE =
        '9999-01-01T00:00:00'

GROUP BY
    scheme_id,
    org_id,
    hash_key_txt

HAVING
    COUNT(DISTINCT prhmd.CURRENT_TS) > 1

ORDER BY
    different_source_versions DESC;


-- =====================================================================
-- TEST 4: MORE OR LESS THAN ONE LATEST RECORD
--
-- Expected result: 0 rows
--
-- Every Scheme + Org + Source System should have exactly
-- one latest_rec_ind = TRUE.
-- =====================================================================

SELECT
    scheme_id,
    org_id,
    src_sys_id,

    COUNT(*) AS total_versions,

    COUNTIF(
        latest_rec_ind = TRUE
    ) AS latest_true_count,

    COUNTIF(
        latest_rec_ind = FALSE
    ) AS historical_count

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

WHERE src_sys_id = 2

GROUP BY
    scheme_id,
    org_id,
    src_sys_id

HAVING
    COUNTIF(latest_rec_ind = TRUE) != 1

ORDER BY
    total_versions DESC;


-- =====================================================================
-- TEST 5: LATEST RECORD MUST HAVE EFF_TO_DT = 9999-01-01
--
-- Expected result: 0 rows
-- =====================================================================

SELECT
    scheme_emplyr_key_id,
    scheme_id,
    org_id,
    src_sys_id,
    eff_from_dt,
    eff_to_dt,
    latest_rec_ind

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

WHERE
    src_sys_id = 2

    AND latest_rec_ind = TRUE

    AND eff_to_dt != DATE '9999-01-01'

ORDER BY
    scheme_id,
    org_id;


-- =====================================================================
-- TEST 6: EFF_FROM_DT MUST BE BEFORE EFF_TO_DT
--
-- Expected result: 0 rows
-- =====================================================================

SELECT
    scheme_emplyr_key_id,
    scheme_id,
    org_id,
    src_sys_id,
    eff_from_dt,
    eff_to_dt,
    latest_rec_ind

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

WHERE
    src_sys_id = 2

    AND eff_from_dt >= eff_to_dt

ORDER BY
    scheme_id,
    org_id,
    eff_from_dt;


-- =====================================================================
-- TEST 7: CHECK FOR OVERLAPPING SCD2 DATE RANGES
--
-- Expected result: 0 rows
--
-- Example of failure:
--
-- Version 1 : 2025-01-01 -> 2025-10-01
-- Version 2 : 2025-09-01 -> 9999-01-01
--
-- These overlap.
-- =====================================================================

WITH scd_check AS (

    SELECT
        scheme_emplyr_key_id,
        scheme_id,
        org_id,
        src_sys_id,
        eff_from_dt,
        eff_to_dt,
        latest_rec_ind,

        LAG(eff_to_dt) OVER (

            PARTITION BY
                scheme_id,
                org_id,
                src_sys_id

            ORDER BY
                eff_from_dt

        ) AS previous_eff_to_dt

    FROM
        `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

    WHERE src_sys_id = 2
)

SELECT
    *

FROM scd_check

WHERE
    previous_eff_to_dt IS NOT NULL

    AND eff_from_dt < previous_eff_to_dt

ORDER BY
    scheme_id,
    org_id,
    eff_from_dt;


-- =====================================================================
-- TEST 8A: REFERENTIAL INTEGRITY
--
-- scheme_employer contains scheme_id
-- but corresponding scheme does NOT exist.
-- =====================================================================

SELECT
    se.scheme_id,

    COUNT(*) AS employer_rows

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`
    se

LEFT JOIN
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme`
    s

    ON se.scheme_id = s.scheme_id

WHERE
    s.scheme_id IS NULL

GROUP BY
    se.scheme_id

ORDER BY
    employer_rows DESC;


-- =====================================================================
-- TEST 8B: REVERSE REFERENTIAL CHECK
--
-- Scheme exists but Scheme Employer does not exist.
--
-- NOTE:
-- This does not automatically mean a defect.
-- It needs to be interpreted according to the business/design rules.
-- =====================================================================

SELECT
    s.scheme_id

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme`
    s

LEFT JOIN
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`
    se

    ON s.scheme_id = se.scheme_id

WHERE
    se.scheme_id IS NULL

ORDER BY
    s.scheme_id;


-- =====================================================================
-- TEST 9: FIND BUSINESS KEYS HAVING REAL SCD2 HISTORY
--
-- Purpose:
-- Show Scheme/Org combinations having more than one FDP version.
-- Useful for manually inspecting historical records.
-- =====================================================================

SELECT
    scheme_id,
    org_id,
    src_sys_id,

    COUNT(*) AS total_versions,

    COUNTIF(
        latest_rec_ind = TRUE
    ) AS latest_records,

    COUNTIF(
        latest_rec_ind = FALSE
    ) AS historical_records,

    MIN(eff_from_dt) AS first_eff_from_dt,

    MAX(eff_from_dt) AS latest_eff_from_dt

FROM
    `iw-gid-prd-01-c683.gid_brd_scheme_fdp.scheme_employer`

WHERE src_sys_id = 2

GROUP BY
    scheme_id,
    org_id,
    src_sys_id

HAVING COUNT(*) > 1

ORDER BY
    total_versions DESC;


-- =====================================================================
-- END OF READ-ONLY PRD VALIDATION
-- =====================================================================