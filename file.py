BEGIN TRANSACTION;

-- CHANGED: load existing tracking information into a temporary copy.
CREATE TEMP TABLE brd_fdp_execution_tracking AS
SELECT *
FROM gid_brd_audit.brd_fdp_execution_tracking
WHERE table_name = 'customer';

-- CHANGED: load existing customer records into a temporary copy.
CREATE TEMP TABLE customer AS
SELECT *
FROM gid_brd_customer_fdp.customer
WHERE src_sys_id = 2;

-- CHANGED: recover the existing latest customer's source timestamp.
-- This is a temporary lookup; no permanent columns are required.
CREATE TEMP TABLE target_source_version AS
SELECT
  t.customer_id,
  t.src_sys_id,
  t.customer_key_id,
  MIN(CAST(p.CURRENT_TS AS TIMESTAMP)) AS target_current_ts,
  COUNT(
    DISTINCT CAST(p.CURRENT_TS AS TIMESTAMP)
  ) AS matched_version_count
FROM customer t
LEFT JOIN (
  SELECT
    IPY_PARTY_ID,
    CURRENT_TS,
    FARM_FINGERPRINT(
      CONCAT(
        CAST(PER_PERSON_ID AS STRING),
        CAST(IPY_PARTY_ID AS STRING),
        STRING(CURRENT_TS),
        'BANCS'
      )
    ) AS customer_key_id
  FROM gid_brd_staging.ta_prt_person_stg
) p
  ON p.IPY_PARTY_ID = t.customer_id
 AND p.customer_key_id = t.customer_key_id
WHERE t.latest_rec_ind IS TRUE
GROUP BY
  t.customer_id,
  t.src_sys_id,
  t.customer_key_id;

CREATE TEMP TABLE src AS
WITH
  last_run AS (
    SELECT
      COALESCE(
        MAX(CAST(previous_execution_timestamp AS TIMESTAMP)),
        TIMESTAMP '1990-01-01 00:00:00+00'
      ) AS ts
    FROM brd_fdp_execution_tracking
    WHERE table_name = 'customer'
  ),

  per_latest AS (
    SELECT DISTINCT
      PER_PERSON_ID,
      IPY_PARTY_ID,
      PER_TITLE_CD,
      PER_FIRST_NAME,
      PER_SURNAME,
      PER_DOB,
      PER_SEX_CD,
      PER_NI_NO,
      PER_MARITAL_STAT_CD,
      PER_SMOKER_STATUS,
      PER_DEATH_DATE,
      PER_DEATH_NOTIFIED_DATE,
      PER_PRY_EMP_STAT,
      PER_NET_INCOME,
      PER_GROSS_INCOME,
      PER_INCOME_CURRENCY_CD,
      PER_OCCUPATION_CD,
      PER_EFF_START_DATE,
      PER_EFF_END_DATE,
      PER_REC_START_DATE,
      PER_REC_END_DATE,
      CURRENT_TS,
      ODP_INGEST_TIMESTAMP -- CHANGED
    FROM gid_brd_staging.ta_prt_person_stg
    WHERE
      DATE(PER_REC_END_DATE) = DATE '9999-01-01'
      AND COALESCE(
        DATE(PER_EFF_START_DATE),
        DATE '0001-01-01'
      ) < COALESCE(
        DATE(PER_EFF_END_DATE),
        DATE '9999-01-01'
      )
      AND UPPER(TRIM(PER_FIRST_NAME)) NOT IN ('ERASED')
      AND PER_REC_DELETED_BY IS NULL

    -- CHANGED: preserve distinct source versions arriving together.
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY PER_PERSON_ID, CURRENT_TS
      ORDER BY ODP_INGEST_TIMESTAMP DESC
    ) = 1
  ),

  prt_latest AS (
    SELECT DISTINCT
      IPY_PARTY_ID,
      IPY_TMP_CUST_NO,
      IPY_CUST_NO,
      IPY_PARTY_TYP_CD,
      CURRENT_TS,
      ODP_INGEST_TIMESTAMP -- CHANGED
    FROM gid_brd_staging.ta_prt_party_stg

    -- CHANGED
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY IPY_PARTY_ID, CURRENT_TS
      ORDER BY ODP_INGEST_TIMESTAMP DESC
    ) = 1
  ),

  prtdtl_latest AS (
    SELECT
      PDT_PARTY_DTL_ID,
      IPY_PARTY_ID,
      PDT_COL_1,
      PDT_COL_10,
      PDT_REC_START_DATE,
      CURRENT_TS,
      ODP_INGEST_TIMESTAMP -- CHANGED
    FROM gid_brd_staging.ta_prt_party_detail_stg
    WHERE
      DATE(PDT_REC_END_DATE) = DATE '9999-01-01'
      AND PDT_REC_DELETED_BY IS NULL

    -- CHANGED
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY PDT_PARTY_DTL_ID, CURRENT_TS
      ORDER BY ODP_INGEST_TIMESTAMP DESC
    ) = 1
  ),

  rolhld_latest AS (
    SELECT
      IRD_ROL_HDR_PTY_MAP_ID,
      IPY_PARTY_ID,
      IRD_ROLE_CD,
      IRD_REC_END_DATE,
      CURRENT_TS,
      ODP_INGEST_TIMESTAMP -- CHANGED
    FROM gid_brd_staging.ta_poa_role_hdr_pty_map_stg
    WHERE
      DATE(IRD_REC_END_DATE) = DATE '9999-01-01'
      AND IRD_DELETE_FLAG = 'N'

    -- CHANGED
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY IRD_ROL_HDR_PTY_MAP_ID, CURRENT_TS
      ORDER BY ODP_INGEST_TIMESTAMP DESC
    ) = 1
  ),

  base AS (
    SELECT
      FARM_FINGERPRINT(
        CONCAT(
          CAST(per.PER_PERSON_ID AS STRING),
          CAST(per.IPY_PARTY_ID AS STRING),
          STRING(per.CURRENT_TS),
          'BANCS'
        )
      ) AS customer_key_id,

      occ.occupation_id AS occupation_id,
      nat.nationality_id AS nationality_id,
      COALESCE(life.life_status_id, 4) AS life_status_id,
      2 AS src_sys_id,

      prt.IPY_PARTY_ID AS customer_id,
      prt.IPY_TMP_CUST_NO AS customer_internal_ref_num,
      prt.IPY_CUST_NO AS cust_ref_id,

      TRIM(per.PER_TITLE_CD) AS title_cd,
      TRIM(per.PER_FIRST_NAME) AS given_nm,
      TRIM(per.PER_SURNAME) AS sur_nm,
      per.PER_DOB AS birth_dt,

      CASE
        WHEN per.PER_SEX_CD = 'M' THEN 'Male'
        WHEN per.PER_SEX_CD = 'F' THEN 'Female'
        WHEN per.PER_SEX_CD = 'U' THEN 'Unknown'
        ELSE NULL
      END AS gender_cd,

      per.PER_NI_NO AS doc_id_typ_txt,
      per.PER_MARITAL_STAT_CD AS marital_status_cd,
      per.PER_SMOKER_STATUS AS smoker_status_cd,
      per.PER_DEATH_DATE AS death_dt,

      CASE
        WHEN per.PER_DEATH_NOTIFIED_DATE < per.PER_DEATH_DATE
          THEN NULL
        ELSE per.PER_DEATH_NOTIFIED_DATE
      END AS death_notified_dt,

      per.PER_PRY_EMP_STAT AS employment_status_cd,
      per.PER_NET_INCOME AS net_incm_amt,
      per.PER_GROSS_INCOME AS gross_incm_amt,
      per.PER_INCOME_CURRENCY_CD AS incm_curncy_cd,

      TO_HEX(
        SHA256(
          CONCAT(
            COALESCE(CAST(occ.occupation_id AS STRING), ''),
            COALESCE(CAST(nat.nationality_id AS STRING), ''),
            COALESCE(CAST(life.life_status_id AS STRING), ''),
            COALESCE(TRIM(per.PER_TITLE_CD), ''),
            COALESCE(TRIM(per.PER_FIRST_NAME), ''),
            COALESCE(TRIM(per.PER_SURNAME), ''),
            COALESCE(CAST(per.PER_DOB AS STRING), ''),
            COALESCE(per.PER_SEX_CD, ''),
            COALESCE(per.PER_NI_NO, ''),
            COALESCE(per.PER_MARITAL_STAT_CD, ''),
            COALESCE(per.PER_SMOKER_STATUS, ''),
            COALESCE(CAST(per.PER_DEATH_DATE AS STRING), ''),
            COALESCE(
              CAST(per.PER_DEATH_NOTIFIED_DATE AS STRING),
              ''
            ),
            COALESCE(per.PER_PRY_EMP_STAT, ''),
            COALESCE(CAST(per.PER_NET_INCOME AS STRING), ''),
            COALESCE(CAST(per.PER_GROSS_INCOME AS STRING), ''),
            COALESCE(per.PER_INCOME_CURRENCY_CD, '')
          )
        )
      ) AS hash_key_txt,

      COALESCE(
        DATE(per.PER_EFF_START_DATE),
        DATE '0001-01-01'
      ) AS eff_from_dt,

      COALESCE(
        DATE(per.PER_EFF_END_DATE),
        DATE '9999-12-31'
      ) AS eff_to_dt,

      CURRENT_TIMESTAMP() AS rec_ins_ts,
      CURRENT_TIMESTAMP() AS rec_upd_ts,
      112 AS batch_load_ins_id,
      112 AS batch_load_upd_id,

      per.PER_REC_START_DATE,
      per.CURRENT_TS AS per_current_ts,
      prt.CURRENT_TS AS prt_current_ts,
      prtdtl.CURRENT_TS AS prtdtl_current_ts,
      rolhld.CURRENT_TS AS rolhld_current_ts

    FROM per_latest per

    INNER JOIN prt_latest prt
      ON prt.IPY_PARTY_ID = per.IPY_PARTY_ID

    JOIN prtdtl_latest prtdtl
      ON per.IPY_PARTY_ID = prtdtl.IPY_PARTY_ID
     AND per.PER_REC_START_DATE = prtdtl.PDT_REC_START_DATE

    INNER JOIN rolhld_latest rolhld
      ON per.IPY_PARTY_ID = rolhld.IPY_PARTY_ID

    LEFT JOIN gid_brd_member_fdp.occupation_code occ
      ON per.PER_OCCUPATION_CD = occ.occupation_cd

    LEFT JOIN gid_brd_member_fdp.nationality_code nat
      ON prtdtl.PDT_COL_1 = nat.nationality_cd

    LEFT JOIN gid_brd_member_fdp.member_life_status_code life
      ON prtdtl.PDT_COL_10 = life.life_status_cd

    CROSS JOIN last_run

    WHERE
      UPPER(TRIM(prt.IPY_PARTY_TYP_CD)) = 'PER'

      -- CHANGED: use ingestion time to detect late arrivals.
      -- Keep this after the joins so unchanged related rows remain available.
      AND GREATEST(
        CAST(per.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
        CAST(prt.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
        CAST(prtdtl.ODP_INGEST_TIMESTAMP AS TIMESTAMP),
        CAST(rolhld.ODP_INGEST_TIMESTAMP AS TIMESTAMP)
      ) > last_run.ts
  ),

  src_final AS (
    -- Original duplicate handling retained.
    SELECT *
    FROM base
    WHERE NOT EXISTS (
      SELECT 1
      FROM customer t
      WHERE
        t.customer_id = base.customer_id
        AND t.hash_key_txt = base.hash_key_txt
    )
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY
        customer_id,
        hash_key_txt
      ORDER BY PER_REC_START_DATE
    ) = 1
  )

SELECT
  s.*,

  -- CHANGED: latest incoming source version must also be newer
  -- than the existing target's source version.
  -- eff_from_dt and rec_upd_ts are not used for this comparison.
  CASE
    WHEN ROW_NUMBER() OVER (
      PARTITION BY s.customer_id, s.src_sys_id
      ORDER BY
        s.per_current_ts DESC,
        s.hash_key_txt DESC
    ) = 1
    AND NOT EXISTS (
      SELECT 1
      FROM target_source_version t
      WHERE
        t.customer_id = s.customer_id
        AND t.src_sys_id = s.src_sys_id
        AND t.target_current_ts >=
            CAST(s.per_current_ts AS TIMESTAMP)
    )
    THEN TRUE
    ELSE FALSE
  END AS latest_rec_ind

FROM src_final s;

-- CHANGED: stop if an affected existing latest source version
-- cannot be uniquely recovered from staging.
ASSERT NOT EXISTS (
  SELECT 1
  FROM target_source_version t
  WHERE
    t.matched_version_count != 1
    AND EXISTS (
      SELECT 1
      FROM src s
      WHERE
        s.customer_id = t.customer_id
        AND s.src_sys_id = t.src_sys_id
    )
) AS 'Cannot uniquely find the existing latest source version in staging.';

-- Original UPDATE retained.
-- An older late arrival has latest_rec_ind = FALSE,
-- so it does not close the existing latest target row.
UPDATE customer AS tgt
SET
  latest_rec_ind = FALSE,

  eff_to_dt = COALESCE(
    (
      SELECT s.eff_from_dt
      FROM src s
      WHERE
        s.customer_id = tgt.customer_id
        AND s.src_sys_id = tgt.src_sys_id
        AND s.latest_rec_ind IS TRUE
    ),
    CURRENT_DATE()
  ),

  rec_upd_ts = CURRENT_TIMESTAMP(),
  batch_load_upd_id = 112

WHERE
  tgt.latest_rec_ind = TRUE
  AND EXISTS (
    SELECT 1
    FROM src s
    WHERE
      s.customer_id = tgt.customer_id
      AND s.src_sys_id = tgt.src_sys_id
      AND s.latest_rec_ind IS TRUE
      AND s.hash_key_txt != tgt.hash_key_txt
  );

-- Original INSERT retained: no new customer columns.
INSERT INTO customer (
  customer_key_id,
  occupation_id,
  nationality_id,
  life_status_id,
  src_sys_id,
  customer_id,
  customer_internal_ref_num,
  cust_ref_id,
  title_cd,
  given_nm,
  sur_nm,
  birth_dt,
  gender_cd,
  doc_id_typ_txt,
  marital_status_cd,
  smoker_status_cd,
  death_dt,
  death_notified_dt,
  employment_status_cd,
  net_incm_amt,
  gross_incm_amt,
  incm_curncy_cd,
  hash_key_txt,
  eff_from_dt,
  eff_to_dt,
  latest_rec_ind,
  rec_ins_ts,
  rec_upd_ts,
  batch_load_ins_id,
  batch_load_upd_id
)
SELECT
  s.customer_key_id,
  s.occupation_id,
  s.nationality_id,
  s.life_status_id,
  s.src_sys_id,
  s.customer_id,
  s.customer_internal_ref_num,
  s.cust_ref_id,
  s.title_cd,
  s.given_nm,
  s.sur_nm,
  s.birth_dt,
  s.gender_cd,
  s.doc_id_typ_txt,
  s.marital_status_cd,
  s.smoker_status_cd,
  s.death_dt,
  s.death_notified_dt,
  s.employment_status_cd,
  s.net_incm_amt,
  s.gross_incm_amt,
  s.incm_curncy_cd,
  s.hash_key_txt,
  s.eff_from_dt,
  s.eff_to_dt,
  s.latest_rec_ind,
  CURRENT_TIMESTAMP(),
  CURRENT_TIMESTAMP(),
  112,
  112
FROM src s;

-- Original tracking MERGE retained.
MERGE brd_fdp_execution_tracking AS T
USING (
  SELECT
    'customer' AS table_name,
    CURRENT_DATETIME() AS previous_execution_timestamp
) AS S
ON T.table_name = S.table_name

WHEN MATCHED THEN
  UPDATE SET
    T.previous_execution_timestamp = COALESCE(
      S.previous_execution_timestamp,
      T.previous_execution_timestamp
    )

WHEN NOT MATCHED THEN
  INSERT (
    table_name,
    previous_execution_timestamp
  )
  VALUES (
    S.table_name,
    S.previous_execution_timestamp
  );

COMMIT TRANSACTION;
