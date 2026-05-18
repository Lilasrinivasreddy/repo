read_param = ReadParam(global_filepath=global_param_gcs_uri)

schema = read_param.global_data['audit_dataset']
tablename = read_param.global_data['fdp_audit_tablename']
project_id = read_param.global_data.get("project")
reject_file_path = read_param.global_data.get("fdp_reject_file_path")




project_id = "iw-gid-bld-01-7904"

schema = "gid_mfb_audit"

tablename = "mfb_fdp_batch_run_audit"

reject_file_path = "dummy"

class Dummy:
    dag_run_id = "manual_test_2026-05-18 22:30:00"

read_param = Dummy()



Then directly run
From ~/core:
Bash
python fdp_ingestion.py dummy --run-mode=reconciliation
Why dummy?
Because script still expects:
Python
sys.argv[1]
but now you bypassed actual GCS reading.
What should happen
You should see logs like:
Plain text
Resolved GCP project: iw-gid-bld-01-7904
Run mode: reconciliation
Running reconciliation query: staging:reconciliation_result
Reconciliation query completed successfully
Then validate in BigQuery
Run:
Bash
bq query --use_legacy_sql=false \
"SELECT *
FROM \`iw-gid-bld-01-7904.gid_mfb_audit.mfb_reconciliation_result\`
ORDER BY created_ts DESC
LIMIT 10"
This confirms
✅ JSON loading works
✅ reconciliation mode works
✅ query rendering works
✅ {{PROJECT_ID}} replacement works
✅ BigQuery execution works
✅ query insertion works
without needing actual runtime DAG config.
Important

