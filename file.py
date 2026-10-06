Yes. The problem is clear now, and we can fix it without redesigning your whole query.
The key is to separate arrival time from business/version time:
ODP_INGEST_TIMESTAMP
        ↓
"Did this record arrive after my previous run?"
        ↓
Used for WATERMARK / DELTA detection


CURRENT_TS
        ↓
"Is this version actually newer than what I already have?"
        ↓
Used for LATEST_REC_IND

For your tester's example:
Run 1:
a = 1
CURRENT_TS = Jan-21
ODP_TS     = Jan-22
latest = TRUE

Run 2 late arrival:
a = 2
CURRENT_TS = Jan-20
ODP_TS     = Jan-23

Run 2 must process a=2 because:
Jan-23 ODP_TS > previous run

but:
Jan-20 CURRENT_TS < Jan-21 CURRENT_TS

therefore:
a=1 remains TRUE
a=2 inserted as FALSE

Minimal changes I recommend
There are 4 logical changes. Most of your query remains exactly as it is.
1. Keep your existing CTE ranking
This part is already aligned with Case 1:
QUALIFY ROW_NUMBER()
OVER (
    PARTITION BY PER_PERSON_ID, DATE(ODP_INGEST_TIMESTAMP)
    ORDER BY CURRENT_TS DESC
) = 1

Meaning:
ODP date → group records that arrived together
CURRENT_TS DESC → choose newest business record within that arrival batch

Do the same for the other three CTEs as you already have.
No change required here.
2. Bring ODP_INGEST_TIMESTAMP out of the four CTEs
Currently you're using it inside ROW_NUMBER() but aren't selecting it.
For example change per_latest from:
CURRENT_TS

to:
CURRENT_TS,
ODP_INGEST_TIMESTAMP

Do this in:
per_latest
prt_latest
prtdtl_latest
rolhld_latest

Then in base, carry both sets of timestamps:
per.CURRENT_TS AS per_current_ts,
prt.CURRENT_TS AS prt_current_ts,
prtdtl.CURRENT_TS AS prtdtl_current_ts,
rolhld.CURRENT_TS AS rolhld_current_ts,

per.ODP_INGEST_TIMESTAMP AS per_odp_ts,
prt.ODP_INGEST_TIMESTAMP AS prt_odp_ts,
prtdtl.ODP_INGEST_TIMESTAMP AS prtdtl_odp_ts,
rolhld.ODP_INGEST_TIMESTAMP AS rolhld_odp_ts,

I would also create one timestamp representing the source version:
GREATEST(
    per.CURRENT_TS,
    prt.CURRENT_TS,
    prtdtl.CURRENT_TS,
    rolhld.CURRENT_TS
) AS src_current_ts

and one representing when the joined data arrived:
GREATEST(
    per.ODP_INGEST_TIMESTAMP,
    prt.ODP_INGEST_TIMESTAMP,
    prtdtl.ODP_INGEST_TIMESTAMP,
    rolhld.ODP_INGEST_TIMESTAMP
) AS src_odp_ts

This keeps the subsequent logic much cleaner.
3. Most important: change the watermark condition
This is currently wrong for the tester's late-arrival scenario:
AND GREATEST(
    per.CURRENT_TS,
    prt.CURRENT_TS,
    prtdtl.CURRENT_TS,
    rolhld.CURRENT_TS
) > last_run.ts

Why?
Suppose:
last_run = Jan-22

late record:
CURRENT_TS = Jan-20
ODP_TS     = Jan-23

Your existing condition checks:
Jan-20 > Jan-22

which is FALSE.
So the late record can be completely missed.
Change it to:
AND GREATEST(
    per.ODP_INGEST_TIMESTAMP,
    prt.ODP_INGEST_TIMESTAMP,
    prtdtl.ODP_INGEST_TIMESTAMP,
    rolhld.ODP_INGEST_TIMESTAMP
) > last_run.ts

This is where your lead's instruction to use ODP timestamp is especially important.
Now:
Jan-23 > Jan-22

= TRUE.
So the late record gets processed.
4. Fix latest_rec_ind
This is the other major issue.
You currently have:
CASE
  WHEN ROW_NUMBER() OVER(
      PARTITION BY customer_id
      ORDER BY per_current_ts DESC
  ) = 1
  THEN TRUE
  ELSE FALSE
END AS latest_rec_ind

This only compares records inside the current src.
It doesn't compare the late record against the record already sitting in customer.
That's why Run 2 can incorrectly mark:
a=2 / Jan-20

as latest.
We need to compare against the target
The robust minimal approach is to keep one source timestamp in the target:
src_current_ts

This means adding one column to customer.
Then your latest_rec_ind logic can compare incoming against existing target.
Conceptually:
CASE
    WHEN EXISTS (
        SELECT 1
        FROM customer t
        WHERE t.customer_id = base.customer_id
          AND t.src_sys_id = base.src_sys_id
          AND t.latest_rec_ind IS TRUE
          AND t.src_current_ts >= base.src_current_ts
    )
    THEN FALSE
    ELSE TRUE
END

However, because you can potentially have several incoming rows for the same customer in a run, I would keep your source ordering too.
Use:
CASE
    WHEN ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY src_current_ts DESC
    ) <> 1
    THEN FALSE

    WHEN EXISTS (
        SELECT 1
        FROM customer t
        WHERE t.customer_id = src_final.customer_id
          AND t.src_sys_id = src_final.src_sys_id
          AND t.latest_rec_ind IS TRUE
          AND t.src_current_ts >= src_final.src_current_ts
    )
    THEN FALSE

    ELSE TRUE
END AS latest_rec_ind

This handles both:
multiple records in this run
+
existing record from previous runs

Update also needs one small protection
Your existing update is:
UPDATE customer AS tgt
SET
  latest_rec_ind = FALSE,
  ...
WHERE
  tgt.latest_rec_ind = TRUE
  AND EXISTS(
    SELECT 1
    FROM src s
    WHERE
      s.customer_id = tgt.customer_id
      AND s.src_sys_id = tgt.src_sys_id
      AND s.latest_rec_ind is TRUE
      AND s.hash_key_txt != tgt.hash_key_txt
  );

Keep almost everything.
Add the timestamp comparison:
AND s.src_current_ts > tgt.src_current_ts

So it becomes:
UPDATE customer AS tgt
SET
  latest_rec_ind = FALSE,
  eff_to_dt = COALESCE(
    (
      SELECT s.eff_from_dt
      FROM src s
      WHERE s.customer_id = tgt.customer_id
        AND s.src_sys_id = tgt.src_sys_id
        AND s.latest_rec_ind IS TRUE
        AND s.src_current_ts > tgt.src_current_ts
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
    WHERE s.customer_id = tgt.customer_id
      AND s.src_sys_id = tgt.src_sys_id
      AND s.latest_rec_ind IS TRUE
      AND s.hash_key_txt != tgt.hash_key_txt

      -- Important late-arrival protection
      AND s.src_current_ts > tgt.src_current_ts
  );

Now the tester's scenario becomes:
Incoming CURRENT_TS Jan-20
Target   CURRENT_TS Jan-21

Jan-20 > Jan-21 ?
NO

Therefore target is NOT closed.

Exactly what we want.
Insert needs one additional column
Add:
src_current_ts

to:
INSERT INTO customer (...)

and:
s.src_current_ts

to the SELECT.
Optionally, I strongly prefer persisting:
src_odp_ts

too.
So you can clearly distinguish later:
src_current_ts = actual source chronology
src_odp_ts     = actual ingestion/arrival chronology

But for this particular tester issue, src_current_ts is the essential one.
Your final Case 1 logic
Think about the entire solution this way:
               STAGING
                  │
                  ▼
      ODP_INGEST_TIMESTAMP
                  │
         Is it after watermark?
                  │
             YES ─┘
                  │
                  ▼
        Process the record
                  │
                  ▼
             CURRENT_TS
                  │
                  ▼
        Compare with target
         src_current_ts
                  │
        ┌─────────┴──────────┐
        │                    │
Incoming newer          Incoming older
CURRENT_TS              CURRENT_TS
        │                    │
        ▼                    ▼
Close old target        DON'T close target
        │
        ▼                    │
New row TRUE                 ▼
                         Insert history
                         FALSE

For tester case:
Existing:
a=1
CURRENT_TS Jan-21
TRUE

Late incoming:
a=2
ODP_TS Jan-23
CURRENT_TS Jan-20

ODP check:
Jan-23 is new
→ Process it ✅

CURRENT_TS check:
Jan-20 > Jan-21 ?
→ NO

Final:

a=1 Jan-21 TRUE
a=2 Jan-20 FALSE

That's the behavior you need.
One thing I would not do is compare:
incoming.CURRENT_TS > target.rec_upd_ts

because rec_upd_ts is your FDP processing timestamp, while CURRENT_TS is the source timestamp. They represent different clocks and can produce incorrect results.
So the smallest reliable solution is:
1. ODP_TS for watermark
2. CURRENT_TS for ordering
3. Store src_current_ts in customer
4. Compare incoming src_current_ts vs target src_current_ts

Everything else in your query can remain largely unchanged.
