Yes — that new constraint changes the solution materially.
If the rule is:
Do not modify any .json schema files. Keep the existing BigQuery target schema unchanged. Fix only SQL/test files using existing columns.

then we should remove the src_current_ts target-column approach. The SQL must not reference a column that does not exist.
The important consequence is this: your target customer table currently does not contain the original source CURRENT_TS. So across two runs, the query cannot directly do this:
incoming.CURRENT_TS > target.src_current_ts

because target.src_current_ts does not exist.
And I would not replace it with:
incoming.CURRENT_TS > target.rec_upd_ts

because that compares two different concepts:
CURRENT_TS  = source/business version time
rec_upd_ts  = FDP processing time

That would recreate the same late-arrival defect in another form.
SQL-only solution
With the schema frozen, the correct SQL-only approach is to reconstruct the source timestamp of the existing target row inside the query, using staging/source history, rather than storing it in customer.
Conceptually:
Existing customer latest row
        ↓
Find the corresponding source/staging version
        ↓
Get its CURRENT_TS
        ↓
Compare against incoming CURRENT_TS

Then:
incoming CURRENT_TS > existing source CURRENT_TS
            ↓
           YES
            ↓
close existing + incoming TRUE

incoming CURRENT_TS <= existing source CURRENT_TS
            ↓
            NO
            ↓
keep existing TRUE + incoming FALSE

For your tester case:
Existing a=1
source CURRENT_TS = Jan-21

Incoming a=2
ODP_TS             = Jan-23   ← makes it eligible
CURRENT_TS         = Jan-20

The SQL evaluates:
Jan-20 > Jan-21

→ FALSE
therefore:
a=1 → latest TRUE
a=2 → latest FALSE

What stays from the previous fix
The watermark change is still absolutely needed.
Your current query has:
AND GREATEST(
    per.CURRENT_TS,
    prt.CURRENT_TS,
    prtdtl.CURRENT_TS,
    rolhld.CURRENT_TS
) > last_run.ts

For late-arrival handling this should use the ingestion timestamps:
AND GREATEST(
    per.ODP_INGEST_TIMESTAMP,
    prt.ODP_INGEST_TIMESTAMP,
    prtdtl.ODP_INGEST_TIMESTAMP,
    rolhld.ODP_INGEST_TIMESTAMP
) > last_run.ts

So:
ODP timestamp → whether to process
CURRENT_TS    → whether it is actually newer

One limitation we need to respect
This SQL-only approach works reliably only if staging/history still contains enough information to identify the source version represented by the current target row.
If the old source version has disappeared from staging and the target doesn't persist CURRENT_TS, then mathematically there is no reliable way to recover it from:
rec_upd_ts
eff_from_dt
customer_key_id
hash_key_txt

unless your project has a defined rule saying one of those columns represents the source version time.
customer_key_id cannot help because FARM_FINGERPRINT() is one-way; we cannot extract CURRENT_TS back from it.
So I agree with the instruction:
NO JSON changes
NO schema migration
NO src_current_ts target column

But then the implementation should be:
1. ODP_INGEST_TIMESTAMP for watermark
2. CURRENT_TS for source ordering
3. Reconstruct existing target's source CURRENT_TS in SQL
4. Compare incoming CURRENT_TS against that value
5. Older late arrival → insert FALSE, don't close target
6. Newer arrival → close old TRUE and insert new TRUE

Do not let the coding model simply remove src_current_ts and fall back to rec_upd_ts; that would not actually solve your tester's scenario.
