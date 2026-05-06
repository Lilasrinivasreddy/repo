-- =========================================================
-- STEP 1 : CREATE STAGING TABLE (TODAY SNAPSHOT)
-- =========================================================

CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_stg`
(
    id STRING,
    value INT64,
    current_ts TIMESTAMP
);



-- =========================================================
-- STEP 2 : INSERT TODAY DATA INTO STG
-- =========================================================

-- TODAY SNAPSHOT
-- B deleted
-- C updated from 3 -> 10
-- F inserted

INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_stg`
VALUES
('A',1,CURRENT_TIMESTAMP()),
('C',10,CURRENT_TIMESTAMP()),
('D',4,CURRENT_TIMESTAMP()),
('E',5,CURRENT_TIMESTAMP()),
('F',6,CURRENT_TIMESTAMP());



-- =========================================================
-- STEP 3 : CREATE FINAL/SOR TABLE (YESTERDAY SNAPSHOT)
-- =========================================================

CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final`
(
    id STRING,
    value INT64,
    optype STRING,
    current_ts TIMESTAMP
);



-- =========================================================
-- STEP 4 : INSERT YESTERDAY DATA INTO FINAL TABLE
-- =========================================================

INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final`
VALUES
('A',1,'I',CURRENT_TIMESTAMP()),
('B',2,'I',CURRENT_TIMESTAMP()),
('C',3,'I',CURRENT_TIMESTAMP()),
('D',4,'I',CURRENT_TIMESTAMP()),
('E',5,'I',CURRENT_TIMESTAMP());



-- =========================================================
-- STEP 5 : VERIFY STG TABLE
-- =========================================================

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_stg`;



-- =========================================================
-- STEP 6 : VERIFY FINAL TABLE
-- =========================================================

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final`;



-- =========================================================
-- STEP 7 : CREATE GOLDENGATE DELTA TABLE
-- =========================================================

CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
(
    id STRING,
    value INT64,
    loadflag STRING,
    current_ts TIMESTAMP
);



-- =========================================================
-- STEP 8 : FINAL - STG
-- DERIVE DELETE RECORDS
-- =========================================================

INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`

SELECT
    f.id,
    f.value,
    'D' AS loadflag,
    CURRENT_TIMESTAMP() AS current_ts

FROM `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final` f

LEFT JOIN `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_stg` s

ON f.id = s.id
AND f.value = s.value

WHERE s.id IS NULL;



-- =========================================================
-- STEP 9 : STG - FINAL
-- DERIVE INSERT RECORDS
-- =========================================================

INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`

SELECT
    s.id,
    s.value,
    'I' AS loadflag,
    CURRENT_TIMESTAMP() AS current_ts

FROM `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_stg` s

LEFT JOIN `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final` f

ON s.id = f.id
AND s.value = f.value

WHERE f.id IS NULL;



-- =========================================================
-- STEP 10 : VERIFY GOLDENGATE DELTA TABLE
-- =========================================================

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
ORDER BY current_ts;



-- EXPECTED RESULT
--
-- B 2  D
-- C 3  D
-- C 10 I
-- F 6  I



-- =========================================================
-- STEP 11 : APPLY CDC MERGE LOGIC
-- =========================================================

MERGE `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final` T

USING
(
    SELECT *
    FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
) S

ON T.id = S.id


WHEN MATCHED
AND S.loadflag = 'D'

THEN DELETE


WHEN MATCHED
AND S.loadflag = 'I'

THEN
UPDATE SET
    T.value = S.value,
    T.optype = S.loadflag,
    T.current_ts = S.current_ts


WHEN NOT MATCHED
AND S.loadflag = 'I'

THEN
INSERT
(
    id,
    value,
    optype,
    current_ts
)

VALUES
(
    S.id,
    S.value,
    S.loadflag,
    S.current_ts
);



-- =========================================================
-- STEP 12 : VERIFY FINAL SOR TABLE
-- =========================================================

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.mfb_odp_sor_final`
ORDER BY id;



-- EXPECTED FINAL RESULT
--
-- A 1
-- C 10
-- D 4
-- E 5
-- F 6



-- =========================================================
-- STEP 13 : OPTIONAL AUDIT TABLE
-- =========================================================

CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.audit_poc`
(
    batch_id STRING,
    process_name STRING,
    status STRING,
    records_processed INT64,
    process_ts TIMESTAMP
);



INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.audit_poc`

SELECT
    'BATCH_001',
    'SOR_MERGE_PROCESS',
    'SUCCESS',
    COUNT(*),
    CURRENT_TIMESTAMP()

FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`;



-- =========================================================
-- STEP 14 : DUPLICATE / REPROCESS VALIDATION
-- =========================================================

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.audit_poc`
WHERE batch_id = 'BATCH_001'
AND status = 'SUCCESS';


-- IF RECORD EXISTS
-- SKIP REPROCESSING
