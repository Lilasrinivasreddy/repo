DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
WHERE TRUE;

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
(
  table_name,
  table_count,
  current_ts
)
SELECT
  TABLE_NAME,
  TABLE_COUNT,
  CURRENT_TIMESTAMP()
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.rds_tables_summary_stg`;
===========================================



DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
WHERE DATE(current_ts) = CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
(
  table_name,
  table_count,
  current_ts
)
SELECT
  table_name,
  table_count,
  current_ts
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`;


=====================




DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
WHERE DATE(created_ts) = CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
(
  table_name,
  today_count,
  previous_count,
  difference,
  created_ts
)
SELECT
  c.table_name,
  c.table_count AS today_count,
  h.table_count AS previous_count,
  c.table_count - IFNULL(h.table_count, 0) AS difference,
  CURRENT_TIMESTAMP() AS created_ts
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count` c
LEFT JOIN (
  SELECT
    table_name,
    table_count,
    current_ts,
    ROW_NUMBER() OVER (
      PARTITION BY table_name
      ORDER BY current_ts DESC
    ) AS rn
  FROM
  `iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
  WHERE DATE(current_ts) < CURRENT_DATE()
) h
ON c.table_name = h.table_name
AND h.rn = 1;


================
-- =========================================================
-- STEP 1 : REFRESH TODAY SNAPSHOT
-- =========================================================

DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
WHERE TRUE;

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
(
  table_name,
  table_count,
  current_ts
)

SELECT
  TABLE_NAME,
  TABLE_COUNT,
  CURRENT_TIMESTAMP()

FROM
`iw-gid-bld-01-7904.gid_mfb_staging.rds_tables_summary_stg`;



-- =========================================================
-- STEP 2 : LOAD INTO HISTORY TABLE
-- =========================================================

DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
WHERE DATE(current_ts)=CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
(
  table_name,
  table_count,
  current_ts
)

SELECT
  table_name,
  table_count,
  current_ts

FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`;



-- =========================================================
-- STEP 3 : GENERATE VALIDATION RESULT
-- =========================================================

DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
WHERE DATE(created_ts)=CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
(
  table_name,
  today_count,
  previous_count,
  difference,
  created_ts
)

SELECT
    c.table_name,

    c.table_count AS today_count,

    h.table_count AS previous_count,

    c.table_count - IFNULL(h.table_count,0) AS difference,

    CURRENT_TIMESTAMP()

FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count` c

LEFT JOIN (

SELECT
    table_name,
    table_count,
    current_ts,

    ROW_NUMBER() OVER
    (
        PARTITION BY table_name
        ORDER BY current_ts DESC
    ) rn

FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`

WHERE DATE(current_ts) < CURRENT_DATE()

) h

ON c.table_name = h.table_name
AND h.rn = 1;
