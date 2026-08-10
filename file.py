Give Copilot these steps exactly, in this order:

Do not rewrite the whole SQL file. Only update the CDC MERGE logic in rds_addnl_support_sor.sql.
In the USING (...) AS S source query, keep the existing filter:
WHERE ODP_INGEST_TIMESTAMP > last_exec_ts
  AND OPTYPE IN ('I', 'U', 'D')
Add this immediately after that filter so only the latest event for each primary key is used in the current execution:
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ASM_ADD_SUPP_NO
    ORDER BY CURRENT_TS DESC,
             ODP_INGEST_TIMESTAMP DESC
) = 1
Keep the existing delete clause unchanged:
WHEN MATCHED
AND S.OPTYPE = 'D'
AND T.CURRENT_TS <= S.CURRENT_TS
THEN DELETE
Change the existing update clause from:
WHEN MATCHED
AND S.OPTYPE = 'U'
AND T.CURRENT_TS < S.CURRENT_TS
THEN UPDATE

to:

WHEN MATCHED
AND S.OPTYPE IN ('I', 'U')
AND T.CURRENT_TS < S.CURRENT_TS
THEN UPDATE
Do not create a separate duplicate WHEN MATCHED ... OPTYPE='I' UPDATE block. Reuse the existing update block for both I and U.
Change the existing insert clause from:
WHEN NOT MATCHED
AND S.OPTYPE IN ('I')
THEN INSERT

to:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I', 'U')
THEN INSERT
Do not add any WHEN NOT MATCHED clause for D. If a delete arrives and the key is not in ODP, it should be a no-op.
Do not change CDC audit logic, 90-day retention logic, or execution tracking logic for this minimal fix.
Ask Copilot to preserve all existing field mappings exactly and only make the three functional changes above.

You can paste this prompt directly into Copilot:

Update only the CDC MERGE logic in rds_addnl_support_sor.sql with minimal changes. Keep all existing columns, audit logic, retention logic, and tracking logic unchanged. In the MERGE source, after WHERE ODP_INGEST_TIMESTAMP > last_exec_ts AND OPTYPE IN ('I','U','D'), add QUALIFY ROW_NUMBER() OVER (PARTITION BY ASM_ADD_SUPP_NO ORDER BY CURRENT_TS DESC, ODP_INGEST_TIMESTAMP DESC) = 1. Change the existing matched update condition from S.OPTYPE = 'U' to S.OPTYPE IN ('I','U'). Change the existing not-matched insert condition from S.OPTYPE IN ('I') to S.OPTYPE IN ('I','U'). Do not add a separate duplicate matched-I update block. Keep unmatched D as no-op. Show me only the diff.
