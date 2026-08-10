Yes, I understand what your team members are showing. This is basically a missing-file / late-arriving-file scenario across different days, and it is exactly why just using ODP_INGEST_TIMESTAMP > last_exec_ts is not enough.

From the picture, I read the two cases like this.

Case 1 — problem with the old/current flow

Day 1

FTP
f1-T1   OPTYPE = I
s1

Normally:

FTP → STG → ODP
s1      s1    s1

But reconciliation fails.

Then on Day 2, a later source version arrives:

f1-T2   OPTYPE = U/D
s2

Here T2 is newer than T1.

The problem is that because the previous processing/file situation was incomplete, the U or D can reach ODP while the corresponding original I is absent.

So you get scenarios such as:

Day 1 expected:
ID=101, Name=Alice, Value=A
I, CURRENT_TS=T1

But Day 1 file/process was missed.

Day 2:
ID=101, Name=Alice, Value=B
U, CURRENT_TS=T2

ODP has no 101.

Your old logic:

WHEN MATCHED AND S.OPTYPE = 'U'

cannot do anything because there is no match.

That is why your new change:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I', 'U')
THEN INSERT

is required.

So Day 2 U can create:

ODP
ID    NAME     VALUE   CURRENT_TS
101   Alice    B       T2

even though the original T1 insert never reached ODP.

That addresses one part of the team's example.

Case 2 — the more important late-file case

This is what the second part of the screenshot is showing.

Day 1

Original file:

f1-T1
I

was missed / failed.

Day 2

A newer event arrives:

f1-T2
U/D

and your fixed code handles it.

For example:

ID=101
T1 = 2026-08-01 10:00
T2 = 2026-08-02 10:00

Suppose Day 2 receives:

101 | Alice | B | U | T2

Since ODP doesn't contain 101, your new logic does:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I','U')
THEN INSERT

So ODP becomes:

101 | Alice | B | T2

Good.

Then Day 3 — the missing old file finally arrives

Now the old Day-1 file f1-T1 arrives late:

101 | Alice | A | I | T1

But remember:

T1 < T2

So we must NOT process T1 simply because it arrived on Day 3.

Arrival order is:

Day 2 → T2
Day 3 → T1

but actual business/source order is:

T1 → T2

Therefore the deciding column must be:

CURRENT_TS

not:

ODP_INGEST_TIMESTAMP
This is how the logic should sort it

Imagine staging contains:

ID    NAME     VALUE    OPTYPE    CURRENT_TS    ODP_INGEST_TIMESTAMP
101   Alice    B        U         T2            Day2
101   Alice    A        I         T1            Day3   ← arrived late

You want:

ROW_NUMBER() OVER (
    PARTITION BY ASM_ADD_SUPP_NO
    ORDER BY CURRENT_TS DESC,
             ODP_INGEST_TIMESTAMP DESC
)

Result:

101 | U | T2 | rn = 1   ← latest actual source event
101 | I | T1 | rn = 2   ← late old event

So T2 wins.

The old T1 should never overwrite/recreate T2.

Very important: where your Copilot logic needs adjustment

Your Copilot currently has:

WHERE ODP_INGEST_TIMESTAMP > last_exec_ts
  AND OPTYPE IN ('I','U','D')

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ASM_ADD_SUPP_NO
    ORDER BY CURRENT_TS DESC,
             ODP_INGEST_TIMESTAMP DESC
) = 1

For your team's Day1 → Day2 → Day3 missing-file example, that's still dangerous because on Day3 it considers only newly ingested rows first.

Instead use the retained staging history to determine the latest business event:

USING
(
    SELECT
        ASM_ADD_SUPP_NO,
        ASM_CSTMR_INSTRN_POS_ID,
        ASM_USER_ID,
        ASM_CSTMR_REF,
        ASM_SUPPORT_CODE,
        ASM_EFFECTIVE_DT,
        ASM_EXPLICIT_CNSNT_REQ,
        ASM_SPCFC_SUPPORT,
        ASM_EXPIRY_DT,
        ASM_STATUS,
        ODP_INGEST_TIMESTAMP,
        OPTYPE,
        SRC_FILENAME,
        CURRENT_TS

    FROM
    (
        SELECT
            ASM_ADD_SUPP_NO,
            ASM_CSTMR_INSTRN_POS_ID,
            ASM_USER_ID,
            ASM_CSTMR_REF,
            ASM_SUPPORT_CODE,
            ASM_EFFECTIVE_DT,
            ASM_EXPLICIT_CNSNT_REQ,
            ASM_SPCFC_SUPPORT,
            ASM_EXPIRY_DT,
            ASM_STATUS,
            ODP_INGEST_TIMESTAMP,
            OPTYPE,
            SRC_FILENAME,
            CURRENT_TS,

            ROW_NUMBER() OVER (
                PARTITION BY ASM_ADD_SUPP_NO
                ORDER BY CURRENT_TS DESC,
                         ODP_INGEST_TIMESTAMP DESC
            ) AS rn

        FROM `{project_id}.gid_mfb_staging.rds_addnl_support_stg`

        WHERE OPTYPE IN ('I', 'U', 'D')
    )

    WHERE rn = 1
      AND ODP_INGEST_TIMESTAMP > last_exec_ts

) AS S

Notice the difference:

WRONG/limited:

new rows after last_exec_ts
        ↓
find latest


BETTER for missing/late files:

all retained staging history
        ↓
find latest CURRENT_TS per ID
        ↓
then see whether that latest event
belongs to the current execution
Now apply it to your team's two cases
Case 1
Day1
T1 I → process fails/missing

Day2
T2 U arrives

Since ODP doesn't have the row:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I','U')
THEN INSERT

Result:

ODP = T2

✅ Correct.

Case 2
Day1
T1 I missing

Day2
T2 U/D processed

Day3
old T1 I finally arrives

Staging history has:

T2
T1

Ranking by:

ORDER BY CURRENT_TS DESC

selects:

T2 = rn 1
T1 = rn 2

Therefore late T1 is ignored.

✅ Correct.

There is one special subcase:

Day2 = D at T2
Day3 = old I at T1

After Day2, ODP may contain no row because T2 deleted it. This is exactly the dangerous case.

But because your staging has retained history, the D T2 is still present there. Ranking across retained staging gives:

D T2 → rn 1
I T1 → rn 2

So the late I T1 never reaches:

WHEN NOT MATCHED ... THEN INSERT

and the deleted row stays deleted.

✅ That's the behavior your team is looking for, as long as the newer event remains within your staging-retention window.
