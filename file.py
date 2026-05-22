Description

Create ODP datasets and snapshot-based SOR tables to maintain the latest source snapshot data. ODP tables will act as the System of Record and always contain the current/latest active records from the source system.

2. Implement CDC Merge Logic
Description

Implement snapshot-based CDC merge logic to compare staging data with ODP tables and identify INSERT, UPDATE, and DELETE operations using primary key comparison.

3. Initial Data Load Handling in CDC Pipeline
Description

Implement initial load handling within the CDC framework where all records from the initial snapshot file are treated as INSERT records and loaded directly into ODP tables without audit processing.

4. Staging Table Creation / Retention (90 Days)
Description

Create staging datasets and tables for temporary storage of snapshot files and implement retention cleanup logic to remove records older than 90 days using ingestion timestamp.

5. Create Audit Table Along With Finalizing Columns and Logic
Description

Create OCIDC audit datasets and tables to preserve old records before UPDATE and DELETE operations. Finalize audit table structure, audit columns, and preservation logic for CDC processing.

6. Integrate CDC Merge and Audit Pipeline into Composer DAG
Description

Integrate the complete snapshot CDC processing framework, including merge processing, audit preservation, validation, cleanup, and reconciliation logic into the existing Airflow/Composer DAG orchestration pipeline.

7. Implement CDC Validation and Reconciliation Checks for Processing
Description

Implement validation and reconciliation checks to verify CDC processing accuracy across staging, ODP, and audit datasets, including insert, update, delete, and record count validations.

8. Testing of All Items
Description

Perform end-to-end testing for the complete snapshot-based CDC SOR framework including initial load, CDC merge processing, audit preservation, DAG execution, retention cleanup, reconciliation checks, and reject handling.
