# Spec Delta

## Purpose

Defines how users retrieve a finished job's deliverables: the download API, the contents of the complete ZIP package, and how the web UI lists each file. Links must remain usable for the life of the stored outputs.

## ADDED Requirements

### Requirement: Download links signed on request
`GET /api/download/{job_id}` SHALL sign fresh presigned URLs on every request instead of returning URLs persisted at assembly time. Each URL SHALL remain valid for at least 1 hour after the response.

#### Scenario: Links requested days after completion
- **WHEN** a user requests download links 3 days after the job completed
- **THEN** every returned URL downloads its file successfully

### Requirement: Download response contents
For a completed job, the download response SHALL include URLs for:
- `appraisal`
- `lender_narrative`
- `rent_roll`
- `t12_files` (three entries, ordered `Year 1`, `Year 2`, `Year 3`)
- `complete_package`

Missing outputs SHALL be omitted, not returned as broken links.

#### Scenario: Lender narrative link returned
- **WHEN** a completed job's download links are requested
- **THEN** the response contains a `lender_narrative` URL for `outputs/lender_narrative.docx`

#### Scenario: T-12 links ordered
- **WHEN** a completed job's download links are requested
- **THEN** `t12_files[0]`, `[1]`, and `[2]` are the `Year 1`, `Year 2`, and `Year 3` workbooks, respectively

#### Scenario: Job not finished
- **WHEN** download links are requested for a job with no outputs yet
- **THEN** the API responds 404 with `status: not_ready`

### Requirement: Complete package contents
`outputs/loan_package.zip` SHALL contain:
- `appraisal_report.docx`
- `lender_narrative.docx`
- `rent_roll.xlsx`
- `t12_year1.xlsx`, `t12_year2.xlsx`, `t12_year3.xlsx`
- `qc_report.json`
- every successfully generated property photo, under `photos/`

#### Scenario: Photos included
- **WHEN** a job generated 28 successful images
- **THEN** the ZIP contains 28 files under `photos/`

#### Scenario: Narrative included
- **WHEN** the ZIP is listed
- **THEN** it contains `lender_narrative.docx`

### Requirement: Frontend lists every deliverable
The results screen SHALL list:
- Appraisal Report
- Lender Narrative
- Rent Roll
- each T-12, labeled with its year
- Complete Package

Each entry SHALL show its file type. Deliverables absent from the API response SHALL NOT be rendered.

#### Scenario: Lender Narrative shown
- **WHEN** the download response includes `lender_narrative`
- **THEN** the results screen shows a "Lender Narrative" DOCX download entry

#### Scenario: Absent deliverable hidden
- **WHEN** the download response omits `lender_narrative`
- **THEN** no Lender Narrative entry is rendered, and the page does not error
