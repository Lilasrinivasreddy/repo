Complete Understanding – Monthly Full-Load File Processing Optimization

The current process receives approximately 14 GB of data daily from LMP Banks, out of which around 10 GB belongs to a particular BRD/valuation full-load file. The remaining approximately **4 GB is the data that is actually required for regular daily processing.

The BRD/valuation file is being sent as a complete/full refresh every day. Since this data is not required to be refreshed or consumed daily by the downstream process, processing the same large full-load file every day results in unnecessary data processing.

The main objective of this change is to optimize the existing pipeline by processing this file only once a month instead of every day.

Key points from the discussion are:

Current behavior: The source sends the BRD/valuation file as a full load every day. This file alone contributes approximately 10 GB to the total daily incoming data of around 14 GB.
Business usage: The valuation/BRD data does not appear to be required on a daily basis. The downstream/FDP usage of this table should also be cross-checked to confirm that there is no daily dependency.
Monthly processing: Instead of processing this file every day, it should be processed only once per month. The exact monthly processing date needs to be confirmed. One discussion mentioned the 25th of every month, while another referred to the first of the month.
File can still be received: Even if the source continues sending the full-load file every day, our pipeline should identify this specific file and determine whether it is scheduled for processing on that day.
Skip on non-processing days: On all non-scheduled days, the BRD/valuation file should be intentionally skipped. The rest of the daily files should continue through the existing process without any impact.
Do not trigger Dataflow: When this file is intentionally skipped, the corresponding Dataflow job should not be triggered. This is important because starting a Dataflow job only to ignore the file later would still consume resources and incur unnecessary cost.
Tracking/control table handling: Since the existing pipeline tracks received and processed files, the tracking logic needs to handle this file as an expected or intentional skip, rather than treating it as an unprocessed or failed file.
File-count/reconciliation impact: We need to verify any logic that compares received files against processed files. If the BRD file is received but intentionally skipped, it should be excluded from the expected processed-file count. Otherwise, the pipeline could generate a false mismatch.
Error handling: An intentional monthly skip should not be treated as an error. However, on the scheduled monthly processing date, if the BRD/valuation file is expected to run and its processing fails, that should be treated as a genuine pipeline failure.
Cost optimization: This change is primarily a cost and performance optimization. Instead of unnecessarily processing approximately 10 GB of additional full-load data every day, the pipeline will process it only when required.
Code changes: The implementation should mainly be reviewed in the file identification/filtering logic, Dataflow trigger logic, tracking/control-table logic, and reconciliation/file-count validation logic.
Story requirement: A separate development story/ticket should be created for this optimization, covering the monthly processing condition, Dataflow skip logic, tracking changes, reconciliation impact, and testing.
Overall Requirement in One Sentence

Optimize the BRD/valuation full-load processing by identifying and skipping the approximately 10 GB file during regular daily runs and processing it only once per month, without triggering unnecessary Dataflow jobs or causing tracking/reconciliation mismatches, thereby reducing processing time and GCP cost while keeping the remaining daily file processing unchanged.

Before development, the two important things to confirm are the exact file/table name and the exact monthly processing date (1st vs. 25th).
