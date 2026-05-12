CREATE TABLE IF NOT EXISTS
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
(
    table_name STRING,
    table_count INT64,
    load_date DATE,
    last_updt TIMESTAMP
);

--------


CREATE TABLE IF NOT EXISTS
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
(
    table_name STRING,
    table_count INT64,
    load_date DATE,
    last_updt TIMESTAMP
);

---------

CREATE TABLE IF NOT EXISTS
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
(
    load_date DATE,
    table_name STRING,
    today_count INT64,
    previous_count INT64,
    difference INT64,
    status STRING,
    remarks STRING,
    created_ts TIMESTAMP
);



----------

DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
WHERE TRUE;

---------


INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`
(
    table_name,
    table_count,
    load_date,
    last_updt
)

SELECT
'rds_addnl_support_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_addnl_support_stg`

UNION ALL

SELECT
'rds_addresses_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_addresses_stg`

UNION ALL

SELECT
'rds_bancs_codes_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_bancs_codes_stg`

UNION ALL

SELECT
'rds_case_workflow_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_case_workflow_details_stg`

UNION ALL

SELECT
'rds_case_workflow_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_case_workflow_stg`

UNION ALL

SELECT
'rds_contact_hist_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_contact_hist_stg`

UNION ALL

SELECT
'rds_country_list_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_country_list_stg`

UNION ALL

SELECT
'rds_cust_details_corporate_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_cust_details_corporate_stg`

UNION ALL

SELECT
'rds_cust_details_individual_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_cust_details_individual_stg`

UNION ALL

SELECT
'rds_customer_instruction_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_customer_instruction_stg`

UNION ALL

SELECT
'rds_document_submitted_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_document_submitted_stg`

UNION ALL

SELECT
'rds_instructions_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_instructions_stg`

UNION ALL

SELECT
'rds_intrstd_pty_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_intrstd_pty_stg`

UNION ALL

SELECT
'rds_portfolio_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_portfolio_details_stg`

UNION ALL

SELECT
'rds_q_user_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_q_user_stg`

UNION ALL

SELECT
'rds_qc_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_qc_details_stg`

UNION ALL

SELECT
'rds_qz_dates_back_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_qz_dates_back_stg`

UNION ALL

SELECT
'rds_qz_dates_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_qz_dates_stg`

UNION ALL

SELECT
'rds_shareclass_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_shareclass_details_stg`

UNION ALL

SELECT
'rds_txn_deal_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_txn_deal_details_stg`

UNION ALL

SELECT
'rds_txn_transfer_details_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_txn_transfer_details_stg`

UNION ALL

SELECT
'rds_user_group_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_user_group_stg`

UNION ALL

SELECT
'rds_user_user_group_stg',
COUNT(*),
CURRENT_DATE(),
CURRENT_TIMESTAMP()
FROM `iw-gid-bld-01-7904.gid_mfb_staging.rds_user_user_group_stg`;

---------



DELETE FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
WHERE load_date = CURRENT_DATE();

INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`

SELECT *
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count`;


-----
INSERT INTO
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`

SELECT
    c.load_date,
    c.table_name,
    c.table_count AS today_count,
    h.table_count AS previous_count,

    c.table_count - IFNULL(h.table_count,0) AS difference,

    CASE
        WHEN h.table_count IS NULL THEN 'BASELINE'
        WHEN c.table_count < h.table_count THEN 'ALERT'
        ELSE 'PASS'
    END AS status,

    CASE
        WHEN h.table_count IS NULL
        THEN 'First time load'

        WHEN c.table_count < h.table_count
        THEN 'Count decreased'

        ELSE 'Validation successful'
    END AS remarks,

    CURRENT_TIMESTAMP()

FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count` c

LEFT JOIN
(
    SELECT * EXCEPT(rn)
    FROM
    (
        SELECT *,
               ROW_NUMBER() OVER
               (
                   PARTITION BY table_name
                   ORDER BY load_date DESC
               ) rn
        FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_count_hist`
        WHERE load_date < CURRENT_DATE()
    )
    WHERE rn = 1
) h

ON c.table_name = h.table_name;


------


SELECT *
FROM
`iw-gid-bld-01-7904.gid_mfb_staging.reconciliation_validation_result`
ORDER BY table_name;
