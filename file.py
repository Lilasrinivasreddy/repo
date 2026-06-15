Yes, from the changing technique. While you're taking data from staging table, every time you are going into audit, you should audit only the day of, only for the request that you received for that particular day.
Let's say what happens that one day the job got retracted, that is highly volatile, and the job... nobody actually have a solution at the moment. So our phase 5 got rejected and then we got another model. One day the job got fixed. If it is rejected on the next day, you are capturing only for one day, right? Yes. Is this the condition? Yes, okay. So yeah, understand. So that needs to be avoided. So a simple solution would be a tracking table, but if you can think of some other example... Okay, so probably there is a separate table, audit kind of table is required, not audit, where we are going to capture this tracking kind of table. I'm sorry, I'm sorry.
So, what happens when you run the query, run the ODP queries, you update history. Execution tracking table. Yes.
Current text. Take that, I have executed all the records until now repeat. So when you run it the next time, it will take all the records and it will execute for the next time. Current text is in ODP condition type.
Then you have a current date of 15th June 2026, 11.
Yeah, okay. So I think this is the same process we did in the sample. Correct. Yeah, it's for sample theoretical when we are doing a separate tracking table we created and based upon that timestamp, it will, last execution timestamp, it will run. So this logic we implemented already. Similar way, we are going to for all the... We implemented it for sample, right? Or theoretically when we are analyzing it? No, no, theoretical like with the dummy data we tried earlier. So with that... Why it's not implemented or during the panel implementation? No, no, so the next step what we are thinking is, we wanted to create the same tracking last execution timestamp, this one basically. So that is there in the plate. I mean, we had that. After this, you let me know. Yeah, exactly. My only concern here is, you need to do the join before, you need to do the filter before you do the join. Okay, okay. Understood, okay. The filter. Yeah, I will lift that part. Yeah, so that way we might go like this. Okay, select the required columns. Maybe you are doing a subquery, I'm not sure. Or you can do a CT as per your wish. Right? So I think CT would be ideal. So you select the relevant columns from here and apply these conditions. Yeah, I understand. I'm not sure whether this is still significant enough, if you are applying this date filter. Okay, because I think this is also we have taken from the sample, that embark team whatever there. So same process I followed. Yeah, okay, we need to tap at the beginning to understand why they did it. Reach out to that particular person to understand why they did it. If we are achieving the same thing using...
No, no, they are not joining before the filter. They also went in the same way, like two tables they are creating, I mean, one merge query, one insert query, and they are joining in the same way, like after the inner joining. This inner join condition is there, but... This join before filter, and then later point in the filter. That's also, yeah, let's say, yeah, they are joining for all the data. This is, it's not even maintained. Yeah, latest record. This old records, they haven't considered it. I mean, late arrival records, they are not even considered. This is tricky to understand. Yeah, try to understand and let me know why this is relevant and all. Okay? Yeah, okay. Do you have the understanding currently at the moment, or... Yes, okay, I'm having it completely. So we are just joining based upon that ODP and then we are processing it based upon updated and deleted. So still we are doing... Okay, good. This one, last one, it is only for whatever the late arrival records are there, right? So that we are currently making it, we are ignoring it. That's all. So this possibility is not even there, but just we are just putting it in our condition, probably. Late arrival records, we didn't face anything. That's what I got to know from Naveen also. Navin will be off for three days.
His expectation is the cdc audit , merge , delete query and tracking query (4 query all together)
Delete query is already created by my friend so not to worry now
Now can u share me the complete query ...cdc audit, merge etc
here is what gopi changed..
Introduce ODP Execution Tracking Table
He added a new concept:
ODP Execution Tracking Table
table_name        last_execution_ts
rds_qc_dates      15-Jun-2026 11:30 AM
Purpose:
Track the last successfully processed timestamp for each table.
Avoid depending only on data_date.
2. Update Tracking Table After ODP Queries
He mentioned:
Run ODP (3 queries)
→ Update ODP execution tracking with current timestamps
Meaning:
After CDC Audit
After Merge
After Delete
Update the tracking table with the latest processed timestamp.
3.Next Run Should Use Tracking Timestamp
He added:
Next run →
consider records > current_timestamp in ODP execution tracking
for each table
Meaning:
Instead of:
DATE(stg.ODP_INGEST_TIMESTAMP) = {data_date}
Use: stg.CURRENT_TS > last_execution_ts
from tracking table.
4. Filter Before Join
from the discussion:
you need to do the filter before you do the join.
Current flow:
STG
JOIN ODP
THEN FILTER
Expected flow:
FILTER STG
THEN JOIN ODP
Preferably using a CTE/subquery.
5. Handle Job Failures / Re-runs
His concern was:
What if one day the job gets retriggered?
What if one day the job fails?
The tracking table ensures:
No duplicate processing.
No missed records.
Supports reruns safely.
7. Late Arrival Records
He mentioned:
Late arrival records are currently being ignored.
Need to understand whether this condition is still relevant.
So the new tracking approach is intended to help with late-arriving data as well.
In One Line
Gopi did NOT change the CDC Audit join logic. He changed the processing approach from "data_date-based filtering" to "execution tracking timestamp-based filtering" and asked to filter STG records before joining with ODP.
