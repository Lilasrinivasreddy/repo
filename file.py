I reviewed the updated query. It is much closer, but I would not merge it exactly as it is yet. The ODP watermark part is correct, but there are 3 small changes I recommend to make Case 1 + the tester's late-arrival scenario safe.
The good part is that Copilot now keeps both timestamps transiently and filters incoming records using src_odp_ts > last_run.ts, which is the correct direction for detecting late arrivals.    Pasted text    Pasted text
1. Don't use GREATEST(CURRENT_TS...) as the customer version timestamp
Right now Copilot created:
GREATEST(
  per.CURRENT_TS,
  prt.CURRENT_TS,
  prtdtl.CURRENT_TS,
  rolhld.CURRENT_TS
) AS src_current_ts

   Pasted text
For your tester's requirement, I would change only this part to:
per.CURRENT_TS AS src_current_ts,

because your original business-version decision was:
ORDER BY per_current_ts DESC

and the customer_key_id is also generated using per.CURRENT_TS.    Pasted text
Keep this exactly as Copilot has it:
GREATEST(
    per.ODP_INGEST_TIMESTAMP,
    prt.ODP_INGEST_TIMESTAMP,
    prtdtl.ODP_INGEST_TIMESTAMP,
    rolhld.ODP_INGEST_TIMESTAMP
) AS src_odp_ts

So the distinction is:
src_odp_ts     → did anything contributing to customer arrive now?
src_current_ts → what is the actual customer/person source version?

Otherwise a role/detail table changing on Jan-25 could accidentally make a Jan-20 person version look newer than a Jan-21 person version.
2. Reconstruct the existing target using customer_key_id, not just the hash
Copilot currently has:
INNER JOIN base b
  ON b.customer_id = tgt.customer_id
  AND b.src_sys_id = tgt.src_sys_id
  AND b.hash_key_txt = tgt.hash_key_txt

   Pasted text
This is potentially ambiguous.
Why? Your hash does not contain CURRENT_TS.    Pasted text
You could theoretically have:
Jan-20 → Name = ABC → hash = XYZ
Jan-21 → Name = ABC → hash = XYZ

Same business values = same hash.
Then this:
MAX(b.src_current_ts)

could associate the target row with the wrong timestamp.
But you already have the perfect identifier:
customer_key_id

because it includes:
PER_PERSON_ID
IPY_PARTY_ID
per.CURRENT_TS
BANCS

   Pasted text
So make this minimal modification:
target_source_version AS (
    SELECT
        tgt.customer_id,
        tgt.src_sys_id,
        MAX(b.src_current_ts) AS target_current_ts
    FROM gid_brd_customer_fdp.customer tgt
    INNER JOIN base b
      ON b.customer_id = tgt.customer_id
      AND b.src_sys_id = tgt.src_sys_id
      AND b.customer_key_id = tgt.customer_key_id
      AND b.hash_key_txt = tgt.hash_key_txt
    WHERE tgt.latest_rec_ind IS TRUE
    GROUP BY
        tgt.customer_id,
        tgt.src_sys_id
)

That gives you a much stronger reconstruction of:
"Which staging version actually created this active target row?"

3. There's one important bug in the current latest_rec_ind CASE
Currently Copilot has:
WHEN EXISTS (
  ...
  AND src_final.target_current_ts IS NOT NULL
  AND src_final.target_current_ts >= src_final.src_current_ts
)
THEN FALSE
ELSE TRUE

   Pasted text
The update is conservative because it refuses to close the target when:
target_current_ts IS NULL

   Pasted text
That's good.
But the INSERT side has a hidden problem.
Suppose:
existing target a=1 → latest TRUE

Copilot cannot reconstruct its CURRENT_TS
target_current_ts = NULL

incoming a=2

The update won't close a=1.
Good.
But the CASE falls into:
ELSE TRUE

So you get:
a=1 → TRUE
a=2 → TRUE   ❌

Two active records.
That's not what we want.
The rule needs to be:
Existing active target + source version unknown
→ preserve existing target
→ incoming row FALSE

while:
No active target at all
→ incoming row can be TRUE

So modify the CASE to something like:
CASE

  -- More than one incoming version:
  -- only newest incoming source version can possibly be latest
  WHEN ROW_NUMBER() OVER (
      PARTITION BY customer_id
      ORDER BY src_current_ts DESC, src_odp_ts DESC
  ) <> 1
  THEN FALSE

  -- Active target exists but we couldn't reconstruct its source timestamp.
  -- Preserve target rather than creating two latest rows.
  WHEN target_current_ts IS NULL
       AND EXISTS (
           SELECT 1
           FROM gid_brd_customer_fdp.customer t
           WHERE t.customer_id = src_final.customer_id
             AND t.src_sys_id = src_final.src_sys_id
             AND t.latest_rec_ind IS TRUE
       )
  THEN FALSE

  -- Existing source version is same/newer than incoming
  WHEN target_current_ts >= src_current_ts
  THEN FALSE

  -- No target or incoming genuinely newer
  ELSE TRUE

END AS latest_rec_ind

That's the minimal safe behavior.
For your tester's exact example, after these changes:
RUN 1

a=1
CURRENT_TS = Jan-21
ODP_TS     = Jan-22

Target:
a=1 → TRUE

Then:
RUN 2

a=2
CURRENT_TS = Jan-20
ODP_TS     = Jan-23

Watermark:
Jan-23 > previous execution
      ↓
PROCESS ✅

Reconstruction:
Existing target a=1
      ↓ customer_key_id
CURRENT_TS = Jan-21

Comparison:
incoming Jan-20 > target Jan-21 ?

NO

Final:
a=1 | CURRENT_TS Jan-21 | latest TRUE
a=2 | CURRENT_TS Jan-20 | latest FALSE

And importantly:
a=1 is NOT closed.

If a genuinely newer record arrives:
a=3
CURRENT_TS Jan-24
ODP_TS Jan-25

then:
Jan-24 > Jan-21

so:
a=1 → FALSE
a=3 → TRUE

So my verdict on Copilot's query
Most of the implementation is correct:
✅ No JSON changes
✅ ODP timestamp used for arrival/watermark
✅ CURRENT timestamp retained transiently
✅ Existing target timestamp reconstructed
✅ No CURRENT_TS vs rec_upd_ts comparison
✅ Late historical rows don't automatically close the target

But I would make these 3 targeted corrections only:
1. src_current_ts = per.CURRENT_TS
   NOT GREATEST(all CURRENT_TS)

2. Reconstruct target using customer_key_id
   in addition to customer/src/hash

3. If active target exists but target_current_ts is NULL,
   incoming latest_rec_ind = FALSE
   instead of ELSE TRUE

After those three changes, the solution matches the late-arrival behavior you and the tester described without changing the BigQuery JSON schema.
