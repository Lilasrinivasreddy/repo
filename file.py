I reviewed this final query carefully. The late-arrival logic itself is now in the right shape, including the temp snapshots, ODP-based watermark, per.CURRENT_TS ordering, target reconstruction, and protection against older late arrivals.    Pasted text    Pasted text
However, I would make one concrete syntax correction before running it.
In prt_latest, you currently have:
CURRENT_TS,
ODP_INGEST_TIMESTAMP,

FROM gid_brd_staging.ta_prt_party_stg

That trailing comma after ODP_INGEST_TIMESTAMP should be removed.    Pasted text
It should be:
CURRENT_TS,
ODP_INGEST_TIMESTAMP
FROM gid_brd_staging.ta_prt_party_stg

The same issue exists in prtdtl_latest:
CURRENT_TS,
ODP_INGEST_TIMESTAMP,

FROM gid_brd_staging.ta_prt_party_detail_stg

   Pasted text
Change it to:
CURRENT_TS,
ODP_INGEST_TIMESTAMP
FROM gid_brd_staging.ta_prt_party_detail_stg

Apart from those syntax commas, the important logic is correct:
TEMP tracking snapshot
        ↓
previous watermark

TEMP customer snapshot
        ↓
existing target state

ODP_INGEST_TIMESTAMP
        ↓
Did this arrive after previous run?

per.CURRENT_TS
        ↓
Is this really newer than existing customer?

The reconstruction is also correct now:
b.customer_key_id = tgt.customer_key_id
AND b.hash_key_txt = tgt.hash_key_txt

so it identifies the source version represented by the existing active target.    Pasted text
And your tester scenario is correctly protected by:
target_current_ts >= src_current_ts

which makes the older incoming row historical.    Pasted text
The update additionally requires:
s.src_current_ts > s.target_current_ts

before closing the existing active row, so Jan-20 cannot close an existing Jan-21 record.    Pasted text
So my status is:
Late-arrival design          ✅
ODP watermark                ✅
CURRENT_TS version ordering  ✅
Temp snapshots               ✅
No JSON/schema change        ✅
Older late-arrival handling  ✅
Newer-row closeout           ✅

SQL syntax                   ⚠️ remove 2 trailing commas

One last thing to verify rather than change blindly: make sure ODP_INGEST_TIMESTAMP and previous_execution_timestamp are compatible BigQuery types. Your comparison is:
b.src_odp_ts > last_run.ts

   Pasted text
If one is TIMESTAMP and the other is DATETIME, cast one explicitly. If they are already the same type in your tables, leave it exactly as it is.
So: do not change the late-arrival logic anymore. Fix the two trailing commas, verify the timestamp datatype, then test the three scenarios we discussed.
