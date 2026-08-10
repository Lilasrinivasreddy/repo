Your Copilot solution is partly correct, but it does not completely solve the Jira story.
From your screenshot, Copilot made these two changes:
WHEN MATCHED
AND S.OPTYPE = 'I'
AND T.CURRENT_TS < S.CURRENT_TS
THEN UPDATE ...
and:
WHEN NOT MATCHED
AND S.OPTYPE IN ('I', 'U')
THEN INSERT ...
Those are useful changes. But the late-arriving Insert after a Delete problem is still not fully handled.
What Copilot fixed correctly
For this Jira case:
OPTYPE I records when there is already record existing in ODP
Copilot added:
WHEN MATCHED
AND S.OPTYPE = 'I'
AND T.CURRENT_TS < S.CURRENT_TS
THEN UPDATE
So if ODP has:
ID    NAME     VALUE   CURRENT_TS
101   Alice    A1      10:05
and staging gets a newer:
ID    NAME     VALUE   OPTYPE   CURRENT_TS
101   Alice2   A2      I        10:10
then it updates ODP.
✅ Correct.
For:
OPTYPE U records when there is NO record existing in ODP
Copilot changed:
WHEN NOT MATCHED AND S.OPTYPE IN ('I')
to:
WHEN NOT MATCHED AND S.OPTYPE IN ('I', 'U')
So:
ODP = no ID 102
Staging:
102   Bob   B1   U   10:05
becomes:
ODP:
102   Bob   B1   10:05
✅ Correct.

For:

OPTYPE D records when there is NO record existing in ODP

No additional clause is required.

A D that does not match ODP simply does nothing.

✅ Correct.

The problem Copilot has not solved

Your Jira also says:

Insert arrived late and update or delete reached ODP first.

Consider this example.

Events are logically:

ID = 101

D   CURRENT_TS = 10:10
I   CURRENT_TS = 10:05   <-- older Insert arrives late

Suppose the D was processed first.

ODP becomes:

ID 101 = DELETED

Later the delayed I arrives.

Now Copilot's MERGE checks:

ON T.ASM_ADD_SUPP_NO = S.ASM_ADD_SUPP_NO

But ID 101 is no longer in ODP because the Delete removed it.

Therefore this condition:

WHEN MATCHED
AND S.OPTYPE = 'I'
AND T.CURRENT_TS < S.CURRENT_TS

cannot execute.

There is no target row.

Instead this executes:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I', 'U')
THEN INSERT

and the old Insert gets inserted again.

Wrong result
10:10 D
    ↓
ODP row deleted

10:05 I arrives late
    ↓
NOT MATCHED
    ↓
INSERT

❌ ID 101 comes back

But because:

10:10 > 10:05

the Delete is actually the latest event.

Correct final ODP state should be:

ID 101 = NOT PRESENT

So the Copilot solution does not fully handle late I after D.

One more important issue

Your current source is roughly:

USING (
    SELECT ...
    FROM staging
    WHERE ODP_INGEST_TIMESTAMP > last_exec_ts
      AND OPTYPE IN ('I', 'U', 'D')
) S

Suppose the same ID has several events in one processing window:

101  I   10:00
101  U   10:05
101  D   10:10

All three source rows can reach the same MERGE.

That is risky. For a BigQuery MERGE involving UPDATE/DELETE, multiple source rows matching one target row can produce a multiple-match runtime error or ambiguous processing rather than giving you a reliable event order.

You should first decide which event is the latest for that primary key.

For example:

ROW_NUMBER() OVER (
    PARTITION BY ASM_ADD_SUPP_NO
    ORDER BY CURRENT_TS DESC,
             ODP_INGEST_TIMESTAMP DESC
) AS rn

and process:

WHERE rn = 1
So compare Copilot vs required solution
Requirement	Copilot	Status
I + existing ODP	Adds MATCHED I → UPDATE	✅
U + missing ODP	Adds U to NOT MATCHED INSERT	✅
D + missing ODP	Naturally ignored	✅
Older I after newer U while row exists	CURRENT_TS protects it	✅
Older I after newer D removed row	Old I becomes NOT MATCHED and inserts	❌
Multiple events same ID in source	No latest-row filtering shown	⚠️

So do not accept the Copilot change exactly as-is yet.

The two changes Copilot made should probably remain:

WHEN MATCHED
AND S.OPTYPE IN ('I', 'U')
AND T.CURRENT_TS < S.CURRENT_TS
THEN UPDATE

and:

WHEN NOT MATCHED
AND S.OPTYPE IN ('I', 'U')
THEN INSERT

But you also need a mechanism to know the latest CURRENT_TS even after a delete has removed the ODP row.

Since your staging has 90-day retention, one relatively simple approach is to derive the latest event per ID from retained staging before the MERGE. If your requirement must handle inserts arriving later than that retention window, then you need a persistent per-key latest-event/tombstone table rather than relying only on ODP.

Also, I would change Copilot's comment:

-- late-arriving insert for a key already updated/deleted-then-recreated in ODP

because that block does not actually solve the deleted-row case. After a true delete, the row isn't present to satisfy WHEN MATCHED.
