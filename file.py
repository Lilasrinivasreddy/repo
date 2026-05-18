Yes, correct. What they are trying to say is:

Before the FTP actual load/process starts, we should first perform the validation activity.

The flow is something like this:

File arrives in landing/transient location
Validation step executes first
Validation checks:
Control file present or not
Expected files count
File naming convention
Record counts
Schema/structure validation
Duplicate/rejected file checks
Only after successful validation → FTP/actual ingestion pipeline kicks off

So in your discussion, they are saying:

Even before FTP starts,
some SQL validation query should run,
and based on that result, proceed further.

The important point from your lead/team discussion is:

They are thinking of maintaining this as a separate “pre-validation framework” or “pre-check feature.”

You can explain it like this to the team:

“Before triggering the FTP ingestion flow, we can introduce a pre-validation layer. This layer executes validation SQLs and performs checks like control file validation, expected file count, schema validation, and duplicate/rejected record verification. Only after validation success, the FTP pipeline or downstream DAG will be triggered.”

The “new day from file concept feature” they mentioned most likely means:

creating a dedicated validation module/service/DAG
which executes validation queries dynamically
probably based on metadata/control configurations
and then triggers the actual FTP processing

A simplified architecture would look like:

Source Files
     ↓
Transient/Landing Bucket
     ↓
Pre-Validation Layer
   • SQL validations
   • Control file check
   • File count validation
   • Schema validation
   • Duplicate checks
     ↓
Validation Success ?
   ↓ Yes
FTP / Main Ingestion DAG
   ↓
BQ / Target Tables

   ↓ No
Reject / Alert / Audit Logs

The benefit of this approach:

Avoids bad data entering pipeline
Prevents unnecessary FTP execution
Early failure detection
Better auditability
Cleaner downstream processing
Easier reconciliation and monitoring

This is similar to the validation-first architecture you discussed earlier for:

ODP/FDP pipelines
CDC/SOR validation
record count reconciliation
control file driven DAG triggering

So your understanding is correct.

This module should only one module which take input parameters to execute different types of JSONs. This is where actually complete the processing happening. This module will take two input parameters. It will take two types of input parameters at the moment. If you do control F and do reference, yeah, see, if daily run mode is reference, then one way of execution happens. And then if daily run mode is another, that is in the other apart from reference, then if the other batching. Okay. So, I think you see that here. Yeah, this is the another value. If run mode is either daily or reference. On line seven, 377, if you see at the end, run mode is equal to daily by reference. Okay, there are two options that we are passing for a run mode. Now, we might need to consider this module in a way that it will accept the third input parameter as a third input parameter might be. I'm just giving this is just a theoretical. Just you analyze, if it is not working, what you do it in a different thing. Okay. But here what I'm expecting is there will be another input parameter where you pass when you call this FDP induction with that third parameter, only your correlation triggers. But reconciliation has still correlation triggers. Yeah, okay. Okay. I understand the process. But instead of going through this process, I think it's better we can create a separate script and call that script in this particular FDP induction. So, script in a sense like the wrapper script only, right? Python script. Yes. Why is you are creating another copy of the Python script? What is my question? There is already a Python script which is executing your SQL queries. Why do you want to duplicate it? Understand, okay. So, yes, it is getting unnecessary. Yeah, correct. You are creating a script. My beat will take more time as well. So, the ideal scenario is this. If you do it like this.

Your lead is actually guiding towards a better architectural approach instead of creating duplicate scripts.

What they are saying is:

There is already one common FDP ingestion module/script.
That module already supports multiple execution modes using input parameters.
Currently it supports:
reference
daily
based on run_mode.

Now the proposal is:

Instead of creating a separate reconciliation Python wrapper script,
extend the existing module itself by adding another parameter or mode.

So the current flow is something like:

FDP_INGESTION.py
    |
    |-- run_mode = reference
    |       → executes reference flow
    |
    |-- run_mode = daily
            → executes daily flow

Now your lead wants something like:

FDP_INGESTION.py
    |
    |-- run_mode = reference
    |       → reference processing
    |
    |-- run_mode = daily
    |       → daily batching
    |
    |-- run_mode = reconciliation
            → reconciliation SQL execution

or

FDP_INGESTION.py
      |
      |-- parameter_3 = reconciliation_flag

Meaning:

Do not duplicate the Python script.

Because:

duplicate maintenance
duplicate logic
more testing effort
more deployment effort
synchronization issues
longer execution path

Instead:

Reuse the existing execution framework.

Your lead’s core point was:

“There is already a Python script executing SQL queries. Why create another copy?”

That means:

existing framework already has:
DB connection
execution engine
logging
parameter handling
audit handling
orchestration logic
so reconciliation can simply become another execution mode.

So the better architecture is:

Caller / DAG
     ↓
FDP_INGESTION.py
     ↓
Read input parameters
     ↓

IF run_mode = reference
    → reference logic

ELIF run_mode = daily
    → daily ingestion logic

ELIF run_mode = reconciliation
    → reconciliation SQL validation logic

ELSE
    → error handling

The reconciliation mode may:

execute validation SQLs
compare counts
run audit checks
perform delta validation
trigger alerts
stop downstream execution if failed

This is cleaner because:

✅ Single reusable framework
✅ Easier maintenance
✅ Centralized logging
✅ Same audit mechanism
✅ Less code duplication
✅ Easier deployment
✅ Faster enhancement
✅ Standardized execution flow

Your understanding during the discussion was also correct:

Initially you suggested:

create separate wrapper script

But the lead corrected it saying:

unnecessary duplication
existing module already supports parameterized execution
extend the framework instead

So the “ideal scenario” they mentioned is basically:

Convert reconciliation into another configurable execution mode inside the same FDP ingestion framework.

situations following for this application are not, if not, there is another option which can directly trigger a query in as you said in a different module, just to trigger a query. Yes, okay. That will be even easy. So directly to That's your, just have a look at the stack, right? There is already my, so the first reference is this one. Okay. That will be called just because, you know, people are using it for a GB, but it should be maybe named a GB. But at the end of the day, the script is executing your SQL queries. Yes, okay, yeah. This actually doesn't make sense to you, the other person. Or your other person saying that they should be a separate file. Yeah, and one request from my side to Lida, when you are creating these tables in INT and push, add, I have my list in the queue, try to accommodate that changes. Yes, okay, I saw that time. The channel you have posted. Yeah, that I will add whenever I'm trying to push, I will add those things also. Yeah, so I will look this part and

Here the discussion is moving toward a more simplified and practical implementation approach.

What your lead/team is saying is:

If modifying the FDP ingestion framework becomes complicated or does not fit properly, then there is another lightweight option:

Instead of:

creating a completely separate duplicate processing file,

just:

directly trigger the required SQL query from an existing utility/module/script.

Meaning:

There is already an existing generic SQL execution script/module in the framework.

That module:

accepts SQL
connects to DB
executes queries
handles execution flow

So rather than:

building another reconciliation framework,
or duplicating ingestion scripts,

you can simply:

call the existing SQL execution component directly.

The discussion flow was something like:

Option 1:
Enhance FDP ingestion module
   ↓
Add reconciliation mode

Option 2:
Use existing SQL executor module directly
   ↓
Trigger reconciliation query only

Your lead seems more aligned toward:

✅ Reusing existing SQL execution capability
✅ Avoiding duplicate wrapper scripts
✅ Keeping implementation minimal
✅ Faster delivery
✅ Less maintenance

The important sentence was:

“At the end of the day, the script is executing your SQL queries.”

Meaning:

all these frameworks eventually just run SQL
so don’t over-engineer it unnecessarily

So the final simplified architecture becomes:

Validation/Reconciliation Trigger
            ↓
Existing SQL Executor Script
            ↓
Execute Reconciliation SQL
            ↓
Store Result in Audit/Reconciliation Tables
            ↓
Proceed / Fail Based on Validation

Then later discussion shifted to:

INT environment table creation
pushing additional changes
accommodating pending requests from queue/channel.

That part means:

while promoting/deploying tables to INT,
include pending reconciliation/audit table changes also,
instead of creating separate deployment cycles.

So your response in team discussion can be:

“Instead of creating a separate reconciliation wrapper framework, we can reuse the existing SQL execution module already available in FDP ingestion. Since the framework is already parameterized and capable of executing SQL queries, reconciliation logic can either be integrated as another execution mode or directly triggered using the existing query execution component. This reduces duplication and simplifies maintenance.”

This is the main architectural conclusion from the discussion.
