Yes — for the failed cases in the Excel you shared, the updated query is largely on the right track, but I would make one important correction before calling it good.

Your highlighted changes for ROW_NUMBER() and removing CURRENT_TS from FARM_FINGERPRINT are appropriate. The part I would still change is the SCD2 MERGE.

Currently you have essentially:

ON tgt.org_id = s.org_id
AND tgt.src_sys_id = s.src_sys_id
AND tgt.latest_rec_ind = TRUE
AND tgt.hash_key_txt <> s.hash_key_txt

For the validation requirement, change it to:

ON tgt.org_key_id = s.org_key_id
AND tgt.src_sys_id = s.src_sys_id
AND tgt.latest_rec_ind = TRUE

WHEN MATCHED
AND tgt.hash_key_txt <> s.hash_key_txt
THEN
UPDATE SET
    tgt.latest_rec_ind = FALSE,
    tgt.eff_to_dt = s.eff_from_dt,
    tgt.rec_upd_ts = CURRENT_TIMESTAMP(),
    tgt.batch_load_upd_id = 111

And include org_key_id in the USING SELECT:

SELECT
    org_key_id,
    org_id,
    src_sys_id,
    hash_key_txt,
    eff_from_dt
FROM src_c
WHERE rn = 1

So: your query is close, but make this MERGE correction. The org_id NULLABLE → REQUIRED failure is a table-schema change, not something this SQL can fix.

I wouldn't change anything else in the query for the failed cases you showed.
