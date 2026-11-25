# Spec Delta

## Purpose

Defines how a generation job moves through its stages, how failures propagate, which errors are retried, and how quality control gates delivery. Together these ensure a job either delivers a consistent package or fails fast with a clear reason.

## ADDED Requirements

### Requirement: Stage ordering
After crosswalk generation, the job SHALL run the following concurrently:
- the 12 appraisal sections
- the T-12 and rent roll workbooks
- the Lender Narrative
- the image package

QC SHALL start only after all of these finish. Assembly SHALL start only after QC passes.

#### Scenario: Images run alongside sections
- **WHEN** crosswalk generation succeeds
- **THEN** image generation starts without waiting for any section generator to finish

#### Scenario: QC waits for all producers
- **WHEN** any producer stage is still running
- **THEN** QC has not started

### Requirement: Stage failures fail the job
A stage that cannot produce its required output SHALL fail its task rather than return a success payload carrying an error status. Crosswalk generation failure in particular SHALL stop the job before any downstream stage starts.

#### Scenario: Crosswalk validation fails
- **WHEN** the crosswalk generator cannot produce a schema-valid crosswalk
- **THEN** the execution fails at the crosswalk stage, and no section, workbook, narrative, or image stage is started

### Requirement: Retry only transient errors
Stage tasks SHALL retry, with exponential backoff, only on transient errors: Lambda service errors, throttling, Bedrock and fal.ai throttling/service-unavailable, and Lambda timeouts. Deterministic failures such as schema validation errors SHALL NOT be retried.

#### Scenario: Validation error not retried
- **WHEN** a stage fails with a schema validation error
- **THEN** the task is not retried, and the execution fails after one attempt

#### Scenario: Throttling retried
- **WHEN** a stage fails with a Bedrock `ThrottlingException`
- **THEN** the task is retried at least twice with increasing delay

### Requirement: Execution time budget
The state machine timeout SHALL be at least the sum of the longest path of configured stage timeouts (validation + crosswalk + slowest parallel producer + QC + assembly), including retries. A job SHALL NOT be cut off by the state machine timeout while a stage is still within its own timeout.

#### Scenario: Budget covers the longest path
- **WHEN** the infrastructure is synthesized
- **THEN** the state machine timeout ≥ the computed longest-path stage budget

### Requirement: QC result surfaced in job status
The status API SHALL include the QC outcome (`PASS`/`FAIL`, error count, warning count) once QC has run. For QC-failed jobs, it SHALL include the first five QC error descriptions as the failure reason.

#### Scenario: QC failure explained
- **WHEN** a job fails because QC reported errors
- **THEN** `GET /api/status/{job_id}` returns `status: failed` with `qc.status: FAIL` and up to five QC error descriptions

### Requirement: QC covers all deliverables
QC SHALL validate the crosswalk invariants, the appraisal sections, the Lender Narrative, and the T-12 workbook annual totals against the crosswalk. The QC report SHALL count the checks it actually performed.

#### Scenario: T-12 total mismatch detected
- **WHEN** `t12_year2.xlsx` annual NOI differs from `operating_history` `Year 2` NOI
- **THEN** QC records an error naming the workbook and the mismatched line

#### Scenario: Accurate check count
- **WHEN** the QC report is written
- **THEN** `checks_performed` equals the number of individual checks executed, not a fixed constant
