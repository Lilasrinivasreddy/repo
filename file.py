CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc`
(
  id STRING,
  value INT64,
  current_ts TIMESTAMP
);



INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc`
(id, value, current_ts)
VALUES
('A', 1, CURRENT_TIMESTAMP()),
('B', 2, CURRENT_TIMESTAMP()),
('C', 3, CURRENT_TIMESTAMP()),
('D', 4, CURRENT_TIMESTAMP()),
('E', 5, CURRENT_TIMESTAMP());



CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.temp_today_poc`
(
  id STRING,
  value INT64,
  load_date DATE,
  batch_id STRING,
  current_ts TIMESTAMP
);


INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.temp_today_poc`
(id, value, load_date, batch_id, current_ts)
VALUES
('A', 1, CURRENT_DATE(), 'BATCH_001', CURRENT_TIMESTAMP()),
('C', 10, CURRENT_DATE(), 'BATCH_001', CURRENT_TIMESTAMP()),
('D', 4, CURRENT_DATE(), 'BATCH_001', CURRENT_TIMESTAMP()),
('E', 5, CURRENT_DATE(), 'BATCH_001', CURRENT_TIMESTAMP()),
('F', 6, CURRENT_DATE(), 'BATCH_001', CURRENT_TIMESTAMP());




CREATE OR REPLACE TABLE `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
(
  id STRING,
  value INT64,
  loadflag STRING,
  batch_id STRING,
  current_ts TIMESTAMP
);


INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
(id, value, loadflag, batch_id, current_ts)
SELECT
  f.id,
  f.value,
  'D' AS loadflag,
  'BATCH_001' AS batch_id,
  CURRENT_TIMESTAMP() AS current_ts
FROM `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc` f
LEFT JOIN `iw-gid-bld-01-7904.gid_mfb_staging.temp_today_poc` t
ON f.id = t.id
AND f.value = t.value
WHERE t.id IS NULL;


INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
(id, value, loadflag, batch_id, current_ts)
SELECT
  t.id,
  t.value,
  'I' AS loadflag,
  'BATCH_001' AS batch_id,
  CURRENT_TIMESTAMP() AS current_ts
FROM `iw-gid-bld-01-7904.gid_mfb_staging.temp_today_poc` t
LEFT JOIN `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc` f
ON t.id = f.id
AND t.value = f.value
WHERE f.id IS NULL;



SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
ORDER BY current_ts;


DELETE FROM `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc`
WHERE id IN (
  SELECT id
  FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
  WHERE loadflag = 'D'
);


INSERT INTO `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc`
(id, value, current_ts)
SELECT
  id,
  value,
  current_ts
FROM `iw-gid-bld-01-7904.gid_mfb_staging.goldengate_delta_poc`
WHERE loadflag = 'I'
ORDER BY current_ts;

SELECT *
FROM `iw-gid-bld-01-7904.gid_mfb_staging.final_sor_poc`
ORDER BY id;
