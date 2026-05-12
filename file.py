DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
WHERE TRUE;

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
(table_name, table_count, current_ts)
SELECT
  TABLE_NAME,
  TABLE_COUNT,
  CURRENT_TIMESTAMP()
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.rds_tables_summary_stg`;


=====



DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
WHERE DATE(current_ts) = CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
(table_name, table_count, current_ts)
SELECT
  table_name,
  table_count,
  current_ts
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`;



========


SELECT
  c.table_name,
  c.table_count AS today_count,
  h.table_count AS previous_count,
  c.table_count - IFNULL(h.table_count, 0) AS difference,
  CASE
    WHEN h.table_count IS NULL THEN 'FIRST_LOAD'
    WHEN c.table_count < h.table_count THEN 'COUNT_DECREASED'
    ELSE 'OK'
  END AS validation_status
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count` c
LEFT JOIN (
  SELECT * EXCEPT(rn)
  FROM (
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
  )
  WHERE rn = 1
) h
ON c.table_name = h.table_name
ORDER BY c.table_name;


