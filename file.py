-- Customer late-arrival changes for the two supplied screenshots.
-- TEST SCRIPT: all customer/tracking writes below affect TEMPORARY copies.
-- PREREQUISITE: customer must contain src_current_ts TIMESTAMP and src_odp_ts TIMESTAMP.
-- Suggested schema statements, intentionally NOT executed in this test script:
-- ALTER TABLE gid_brd_customer_fdp.customer ADD COLUMN IF NOT EXISTS src_current_ts TIMESTAMP;
-- ALTER TABLE gid_brd_customer_fdp.customer ADD COLUMN IF NOT EXISTS src_odp_ts TIMESTAMP;
-- Backfill these from authoritative source lineage before incremental testing.
-- Do NOT backfill src_current_ts from rec_upd_ts (FDP processing time).
-- Assumptions: source timestamps can be CAST to TIMESTAMP; DATETIME tracking is UTC.
-- CURRENT_TS identifies source versions; person CURRENT_TS remains the customer
-- ordering timestamp, matching the original query. Non-person-only changes use
-- src_odp_ts as a tie-breaker when the person source timestamp is unchanged.
-- Existing source joins/business filters are retained. This does not reconstruct
-- as-of historical joins or repair all existing SCD effective-date intervals.

DECLARE run_cutoff TIMESTAMP DEFAULT CURRENT_TIMESTAMP();
BEGIN TRANSACTION;

-- CHANGED: copy existing state so run 2 can compare with run 1.
CREATE TEMP TABLE brd_fdp_execution_tracking AS
SELECT * FROM gid_brd_audit.brd_fdp_execution_tracking
WHERE table_name = 'customer';
CREATE TEMP TABLE customer AS
SELECT * FROM gid_brd_customer_fdp.customer WHERE src_sys_id = 2;

ASSERT NOT EXISTS (
  SELECT 1 FROM customer
  WHERE src_current_ts IS NULL OR src_odp_ts IS NULL
) AS 'Backfill source timestamps on existing customer history before running.';
ASSERT NOT EXISTS (
  SELECT 1 FROM customer WHERE latest_rec_ind IS TRUE
  GROUP BY customer_id, src_sys_id HAVING COUNT(*) > 1
) AS 'More than one existing latest customer row: reconcile before running.';

CREATE TEMP TABLE src AS
WITH last_run AS (
  SELECT COALESCE(MAX(CAST(previous_execution_timestamp AS TIMESTAMP)),
                  TIMESTAMP '1990-01-01 00:00:00+00') AS ts
  FROM brd_fdp_execution_tracking WHERE table_name = 'customer'
),
per_latest AS (
  SELECT DISTINCT
    PER_PERSON_ID, IPY_PARTY_ID, PER_TITLE_CD, PER_FIRST_NAME, PER_SURNAME,
    PER_DOB, PER_SEX_CD, PER_NI_NO, PER_MARITAL_STAT_CD, PER_SMOKER_STATUS,
    PER_DEATH_DATE, PER_DEATH_NOTIFIED_DATE, PER_PRY_EMP_STAT,
    PER_NET_INCOME, PER_GROSS_INCOME, PER_INCOME_CURRENCY_CD,
    PER_OCCUPATION_CD, PER_EFF_START_DATE, PER_EFF_END_DATE,
    PER_REC_START_DATE, PER_REC_END_DATE, CURRENT_TS, ODP_INGEST_TIMESTAMP
  FROM gid_brd_staging.ta_prt_person_stg
  WHERE DATE(PER_REC_END_DATE) = DATE '9999-01-01'
    AND COALESCE(DATE(PER_EFF_START_DATE), DATE '0001-01-01')
      < COALESCE(DATE(PER_EFF_END_DATE), DATE '9999-01-01')
    AND UPPER(TRIM(PER_FIRST_NAME)) NOT IN ('ERASED')
    AND PER_REC_DELETED_BY IS NULL
    AND CAST(ODP_INGEST_TIMESTAMP AS TIMESTAMP) <= run_cutoff
  -- CHANGED: preserve distinct source versions, even if ingested together.
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY PER_PERSON_ID, CURRENT_TS
    ORDER BY ODP_INGEST_TIMESTAMP DESC
  ) = 1
),
prt_latest AS (
  SELECT DISTINCT IPY_PARTY_ID, IPY_TMP_CUST_NO, IPY_CUST_NO,
    IPY_PARTY_TYP_CD, CURRENT_TS, ODP_INGEST_TIMESTAMP
  FROM gid_brd_staging.ta_prt_party_stg
  WHERE CAST(ODP_INGEST_TIMESTAMP AS TIMESTAMP) <= run_cutoff
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY IPY_PARTY_ID, CURRENT_TS
    ORDER BY ODP_INGEST_TIMESTAMP DESC
  ) = 1
),
prtdtl_latest AS (
  SELECT PDT_PARTY_DTL_ID, IPY_PARTY_ID, PDT_COL_1, PDT_COL_10,
    PDT_REC_START_DATE, CURRENT_TS, ODP_INGEST_TIMESTAMP
  FROM gid_brd_staging.ta_prt_party_detail_stg
  WHERE DATE(PDT_REC_END_DATE) = DATE '9999-01-01'
    AND PDT_REC_DELETED_BY IS NULL
    AND CAST(ODP_INGEST_TIMESTAMP AS TIMESTAMP) <= run_cutoff
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY PDT_PARTY_DTL_ID, CURRENT_TS
    ORDER BY ODP_INGEST_TIMESTAMP DESC
  ) = 1
),
rolhld_latest AS (
  SELECT IRD_ROL_HDR_PTY_MAP_ID, IPY_PARTY_ID, IRD_ROLE_CD,
    IRD_REC_END_DATE, CURRENT_TS, ODP_INGEST_TIMESTAMP
  FROM gid_brd_staging.ta_poa_role_hdr_pty_map_stg
  WHERE DATE(IRD_REC_END_DATE) = DATE '9999-01-01'
    AND IRD_DELETE_FLAG = 'N'
    AND CAST(ODP_INGEST_TIMESTAMP AS TIMESTAMP) <= run_cutoff
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY IRD_ROL_HDR_PTY_MAP_ID, CURRENT_TS
    ORDER BY ODP_INGEST_TIMESTAMP DESC
  ) = 1
),
base AS (
  SELECT
    FARM_FINGERPRINT(CONCAT(CAST(per.PER_PERSON_ID AS STRING),
      CAST(per.IPY_PARTY_ID AS STRING), STRING(per.CURRENT_TS), 'BANCS'))
      AS customer_key_id,
    occ.occupation_id, nat.nationality_id,
    COALESCE(life.life_status_id, 4) AS life_status_id,
    2 AS src_sys_id, prt.IPY_PARTY_ID AS customer_id,
    prt.IPY_TMP_CUST_NO AS customer_internal_ref_num,
    prt.IPY_CUST_NO AS cust_ref_id,
    TRIM(per.PER_TITLE_CD) AS title_cd,
    TRIM(per.PER_FIRST_NAME) AS given_nm,
    TRIM(per.PER_SURNAME) AS sur_nm,
    per.PER_DOB AS birth_dt,
    CASE per.PER_SEX_CD WHEN 'M' THEN 'Male' WHEN 'F' THEN 'Female'
      WHEN 'U' THEN 'Unknown' ELSE NULL END AS gender_cd,
    per.PER_NI_NO AS doc_id_typ_txt,
    per.PER_MARITAL_STAT_CD AS marital_status_cd,
    per.PER_SMOKER_STATUS AS smoker_status_cd,
    per.PER_DEATH_DATE AS death_dt,
    CASE WHEN per.PER_DEATH_NOTIFIED_DATE < per.PER_DEATH_DATE THEN NULL
      ELSE per.PER_DEATH_NOTIFIED_DATE END AS death_notified_dt,
    per.PER_PRY_EMP_STAT AS employment_status_cd,
    per.PER_NET_INCOME AS net_incm_amt,
    per.PER_GROSS_INCOME AS gross_incm_amt,
    per.PER_INCOME_CURRENCY_CD AS incm_curncy_cd,
    TO_HEX(SHA256(CONCAT(
      COALESCE(CAST(occ.occupation_id AS STRING), ''),
      COALESCE(CAST(nat.nationality_id AS STRING), ''),
      COALESCE(CAST(life.life_status_id AS STRING), ''),
      COALESCE(TRIM(per.PER_TITLE_CD), ''),
      COALESCE(TRIM(per.PER_FIRST_NAME), ''),
      COALESCE(TRIM(per.PER_SURNAME), ''),
      COALESCE(CAST(per.PER_DOB AS STRING), ''),
      COALESCE(per.PER_SEX_CD, ''), COALESCE(per.PER_NI_NO, ''),
      COALESCE(per.PER_MARITAL_STAT_CD, ''),
      COALESCE(per.PER_SMOKER_STATUS, ''),
      COALESCE(CAST(per.PER_DEATH_DATE AS STRING), ''),
      COALESCE(CAST(per.PER_DEATH_NOTIFIED_DATE AS STRING), ''),
      COALESCE(per.PER_PRY_EMP_STAT, ''),
      COALESCE(CAST(per.PER_NET_INCOME AS STRING), ''),
      COALESCE(CAST(per.PER_GROSS_INCOME AS STRING), ''),
      COALESCE(per.PER_INCOME_CURRENCY_CD, '')
    ))) AS hash_key_txt,
    COALESCE(DATE(per.PER_EFF_START_DATE), DATE '0001-01-01') AS eff_from_dt,
    COALESCE(DATE(per.PER_EFF_END_DATE), DATE '9999-12-31') AS eff_to_dt,
    CURRENT_TIMESTAMP() AS rec_ins_ts, CURRENT_TIMESTAMP() AS rec_upd_ts,
    112 AS batch_load_ins_id, 112 AS batch_load_upd_id,
    per.PER_REC_START_DATE,
    per.CURRENT_TS AS per_current_ts, prt.CURRENT_TS AS prt_current_ts,
    prtdtl.CURRENT_TS AS prtdtl_current_ts,
    rolhld.CURRENT_TS AS rolhld_current_ts,
    -- CHANGED: persist the same source ordering timestamp used originally.
    CAST(per.CURRENT_TS AS TIMESTAMP) AS src_current_ts,
    GREATEST(CAST(per.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(prt.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(prtdtl.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(rolhld.ODP_INGEST_TIMESTAMP AS TIMESTAMP)) AS src_odp_ts
  FROM per_latest per
  INNER JOIN prt_latest prt ON prt.IPY_PARTY_ID = per.IPY_PARTY_ID
  JOIN prtdtl_latest prtdtl ON per.IPY_PARTY_ID = prtdtl.IPY_PARTY_ID
    AND per.PER_REC_START_DATE = prtdtl.PDT_REC_START_DATE
  INNER JOIN rolhld_latest rolhld ON per.IPY_PARTY_ID = rolhld.IPY_PARTY_ID
  LEFT JOIN gid_brd_member_fdp.occupation_code occ
    ON per.PER_OCCUPATION_CD = occ.occupation_cd
  LEFT JOIN gid_brd_member_fdp.nationality_code nat
    ON prtdtl.PDT_COL_1 = nat.nationality_cd
  LEFT JOIN gid_brd_member_fdp.member_life_status_code life
    ON prtdtl.PDT_COL_10 = life.life_status_cd
  CROSS JOIN last_run
  WHERE UPPER(TRIM(prt.IPY_PARTY_TYP_CD)) = 'PER'
    -- CHANGED: detect arrival after last execution, not source change time.
    AND GREATEST(CAST(per.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(prt.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(prtdtl.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
      CAST(rolhld.ODP_INGEST_TIMESTAMP AS TIMESTAMP)) > last_run.ts
),
src_final AS (
  SELECT * FROM base
  WHERE NOT EXISTS (
    SELECT 1 FROM customer t
    WHERE t.customer_id = base.customer_id AND t.src_sys_id = base.src_sys_id
      -- CHANGED: same hash at a DIFFERENT source time is valid history.
      AND t.src_current_ts = base.src_current_ts
      AND t.hash_key_txt = base.hash_key_txt
  )
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id, src_sys_id, src_current_ts, hash_key_txt
    ORDER BY src_odp_ts DESC, PER_REC_START_DATE,
      prt_current_ts DESC, prtdtl_current_ts DESC, rolhld_current_ts DESC
  ) = 1
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY customer_id, src_sys_id
    ORDER BY src_current_ts DESC, src_odp_ts DESC,
      prt_current_ts DESC, prtdtl_current_ts DESC, rolhld_current_ts DESC,
      hash_key_txt DESC
  ) AS batch_rn FROM src_final
)
SELECT s.* EXCEPT(batch_rn),
  -- CHANGED: compute the decision BEFORE updating target; reuse for insert.
  s.batch_rn = 1 AND NOT EXISTS (
    SELECT 1 FROM customer t
    WHERE t.customer_id = s.customer_id AND t.src_sys_id = s.src_sys_id
      AND t.latest_rec_ind IS TRUE
      AND (t.src_current_ts > s.src_current_ts
        OR (t.src_current_ts = s.src_current_ts AND t.src_odp_ts >= s.src_odp_ts))
  ) AS latest_rec_ind
FROM ranked s;

ASSERT NOT EXISTS (SELECT 1 FROM src WHERE src_current_ts IS NULL OR src_odp_ts IS NULL)
  AS 'Source timestamps must be populated for version comparison.';

UPDATE customer AS tgt
SET latest_rec_ind = FALSE,
  eff_to_dt = (SELECT s.eff_from_dt FROM src s
    WHERE s.customer_id = tgt.customer_id AND s.src_sys_id = tgt.src_sys_id
      AND s.latest_rec_ind IS TRUE),
  rec_upd_ts = CURRENT_TIMESTAMP(), batch_load_upd_id = 112
WHERE tgt.latest_rec_ind IS TRUE
  AND EXISTS (
    SELECT 1 FROM src s
    WHERE s.customer_id = tgt.customer_id AND s.src_sys_id = tgt.src_sys_id
      AND s.latest_rec_ind IS TRUE
      -- CHANGED: compare SOURCE time with SOURCE time.
      AND (s.src_current_ts > tgt.src_current_ts
        OR (s.src_current_ts = tgt.src_current_ts AND s.src_odp_ts > tgt.src_odp_ts))
  );

INSERT INTO customer (
  customer_key_id, occupation_id, nationality_id, life_status_id, src_sys_id,
  customer_id, customer_internal_ref_num, cust_ref_id, title_cd, given_nm,
  sur_nm, birth_dt, gender_cd, doc_id_typ_txt, marital_status_cd,
  smoker_status_cd, death_dt, death_notified_dt, employment_status_cd,
  net_incm_amt, gross_incm_amt, incm_curncy_cd, hash_key_txt,
  eff_from_dt, eff_to_dt, latest_rec_ind, rec_ins_ts, rec_upd_ts,
  batch_load_ins_id, batch_load_upd_id, src_current_ts, src_odp_ts
)
SELECT s.customer_key_id, s.occupation_id, s.nationality_id, s.life_status_id,
  s.src_sys_id, s.customer_id, s.customer_internal_ref_num, s.cust_ref_id,
  s.title_cd, s.given_nm, s.sur_nm, s.birth_dt, s.gender_cd, s.doc_id_typ_txt,
  s.marital_status_cd, s.smoker_status_cd, s.death_dt, s.death_notified_dt,
  s.employment_status_cd, s.net_incm_amt, s.gross_incm_amt, s.incm_curncy_cd,
  s.hash_key_txt, s.eff_from_dt, s.eff_to_dt, s.latest_rec_ind,
  CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), 112, 112,
  s.src_current_ts, s.src_odp_ts
FROM src s;

MERGE brd_fdp_execution_tracking AS T
USING (SELECT 'customer' AS table_name,
  DATETIME(run_cutoff, 'UTC') AS previous_execution_timestamp) AS S
ON T.table_name = S.table_name
WHEN MATCHED THEN UPDATE SET previous_execution_timestamp = S.previous_execution_timestamp
WHEN NOT MATCHED THEN INSERT (table_name, previous_execution_timestamp)
VALUES (S.table_name, S.previous_execution_timestamp);

COMMIT TRANSACTION;

-- Test output; permanent tables remain unchanged.
SELECT * FROM customer
ORDER BY customer_id, src_current_ts DESC, src_odp_ts DESC;
