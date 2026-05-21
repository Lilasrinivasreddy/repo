Documentation Structure You Should Create
Based on the complete SOR discussion, your documentation should mainly contain:
1. Overview / Problem Statement
Title
Snapshot-Based SOR CDC Framework for ODP Processing
Description
The source system provides snapshot-based files and does not maintain historical records. The objective is to build a snapshot-based CDC framework where:
ODP acts as the System of Record (SOR)
ODP always reflects the latest source state
Old records from UPDATE and DELETE operations are preserved in OCIDC Audit datasets
Reject records are stored in BigQuery tables
Staging data is retained only for a configurable retention period
2. Architecture Overview
Documentation Section
Components
Component
Purpose
Source Files
Daily snapshot input
Staging Dataset
Temporary raw snapshot storage
Reject Tables
Validation failure storage
ODP Dataset
Current snapshot System of Record
OCIDC Audit Dataset
Old record preservation
DAG/Pipeline
End-to-end orchestration
3. End-to-End Flow
Process Flow
Plain text
1. Source sends daily snapshot files
2. Files loaded into staging dataset
3. Validation performed
4. Reject records stored in reject tables
5. CDC merge logic executed
6. INSERT → ODP
7. UPDATE → old record copied to OCIDC audit → ODP updated
8. DELETE → old record copied to OCIDC audit → record deleted from ODP
9. Retention cleanup executed for staging
4. Dataset Design
A. Staging Dataset
Purpose
Temporary storage for incoming snapshot files.
Characteristics
Contains raw source snapshot data
Retention: 90 days
Used for CDC comparison processing
Additional Columns
ingestion_ts
batch_id
source_file_name
dag_id
B. Reject Dataset
Purpose
Store validation failures instead of flat reject files.
Example Columns
Column
Description
pk
Primary key column
pk_value
Failed record PK
reject_reason
Validation failure
raw_record
Raw failed data
batch_id
Batch identifier
ingestion_ts
Load timestamp
C. ODP Dataset (SOR)
Purpose
Maintain latest snapshot state of source system.
Key Points
Exact replica of latest source state
No historical records
Current active records only
Operations Supported
INSERT
UPDATE
DELETE
D. OCIDC Audit Dataset
Purpose
Preserve old records before UPDATE and DELETE operations.
Key Points
Same schema as ODP
Stores previous values
INSERT operations excluded
Additional Audit Columns
Column
Description
audit_op_type
UPDATE/DELETE
audit_ts
Audit capture timestamp
source_table
Originating table
batch_id
Batch identifier
5. CDC Logic Documentation
INSERT Logic
Condition
Record exists in staging but not in ODP.
Action
Insert directly into ODP.
Audit
No audit entry created.
UPDATE Logic
Condition
Primary key exists but data changed.
Action
Copy old ODP record to OCIDC audit
Update ODP with latest value
DELETE Logic
Condition
Record exists in ODP but missing from latest snapshot.
Action
Copy old ODP record to OCIDC audit
Delete record from ODP
6. Initial Load Handling
Description
Initial snapshot load will be processed using the same CDC framework.
All records will naturally flow as INSERT operations.
Expected Behavior
Records inserted into ODP
No OCIDC audit entries created
7. Retention Logic
Requirement
Staging data should not grow indefinitely.
Current Retention
90 days
Future Retention
Configurable to:
30 days
7 days
Cleanup Logic Example
SQL
DELETE FROM staging_table
WHERE ingestion_ts < CURRENT_TIMESTAMP() - INTERVAL 90 DAY
8. Daily Processing Logic
Important Requirement
Do not process entire 90-day staging dataset.
Process only:
latest ingestion records
current execution snapshot
Filtering Example
SQL
WHERE ingestion_dt = CURRENT_DATE()
9. Merge Logic
High-Level Merge Process
Plain text
STAGING vs ODP
        ↓
Detect:
- INSERT
- UPDATE
- DELETE
        ↓
Apply actions
10. Audit Column Standardization
Common Columns
Column
Purpose
ingestion_ts
Load tracking
current_ts
Record timestamp
batch_id
Batch lineage
dag_id
DAG execution tracking
source_file_name
File traceability
11. JIRA Stories to Create
Story 1
Create ODP Dataset and Snapshot Tables
Story 2
Create OCIDC Audit Dataset and Audit Tables
Story 3
Implement Snapshot-Based CDC Merge Logic
Story 4
Implement UPDATE and DELETE Audit Preservation Logic
Story 5
Implement Initial Load Processing Framework
Story 6
Replace Reject Flat Files with BigQuery Reject Tables
Story 7
Implement Staging Retention Cleanup Logic
Story 8
Add Operational Audit Columns Across Pipeline
Story 9
Integrate CDC Processing into Existing DAG
Story 10
Implement Latest Snapshot Filtering Logic
12. Lead’s Main Expectations
Your lead expects you to:
Understand snapshot-based CDC
Understand SOR concepts
Understand merge processing
Understand audit preservation
Think beyond coding
Design scalable logic for all tables
Ensure ODP always matches source
Avoid duplicate processing
Implement operational auditability
13. One-Line Summary for Documentation
“The solution implements a snapshot-based CDC SOR framework where ODP maintains the latest source state while OCIDC audit datasets preserve old records before UPDATE and DELETE operations to avoid historical data loss.”