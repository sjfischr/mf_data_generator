# Proposal

## Why

The synthetic loan package is incomplete for multifamily lending workflows:
- It has no lender-side document. A DUS loan file centers on the lender's **Transaction Approval Memo (TAM)**, also called the Lender Narrative.
- The T-12s are too thin. Each has five summary lines and a single "Operating Expenses" row, where a real T-12 follows Fannie Mae's operating-statement categories (Guide Sec 203.01, Form 4254.DEF).
- The review also found several low-cost reliability gaps: silent stage failures, download links that expire within hours, and a stale test that calls Bedrock live.
- We also want faster, cheaper image rendering, using Krea 2 Turbo.

## What Changes

- **Crosswalk schema** (**BREAKING** for `crosswalk-data.json` consumers):
  - Add `financing` (loan terms and deterministic loan sizing), `sponsorship`, and `third_party_reports` blocks.
  - Add a detailed `operating_history`: 3 historical years plus an Underwritten column, in Fannie Mae categories.
  - The lender Underwritten column places replacement reserves below NOI (NOI → NCF), per Sec 203.01.
  - The appraiser pro forma keeps its current shape, and the narrative reconciles the two.
  - `historical_t12` remains as a summary derived from the detail, for backward compatibility.
- **Lender Narrative / Transaction Approval Memo** (new deliverable):
  - Generate `lender_narrative.docx`, following the TAM topics (Guide Part I Sec 103) and the DUS Exhibit III-2 / Form 4605 outline.
  - Code computes every table and metric. The LLM writes only prose around the fixed figures.
- **Detailed T-12s:**
  - Keep the three T-12 files, now with a full chart of accounts, sub-accounts, monthly seasonality, occupancy statistics, subtotals, NOI, and NCF. Each ties exactly to the crosswalk.
  - Make the rent roll consistent with the crosswalk effective date and occupancy.
- **Image rendering — Krea 2 Turbo on fal.ai:**
  - Replace Replicate (Krea 2 Large) with `fal-ai/krea-2/turbo`, using a `FAL_KEY` credential.
  - Use deterministic per-shot seeds and JPEG output, and retry safety-flagged renders once.
  - Validate the structured prompt count before rendering.
- **Pipeline reliability (low-hanging fruit):**
  - The crosswalk stage fails the execution on error instead of returning `status: error`.
  - Retry only transient errors.
  - Images run in parallel with sections, and the state machine timeout matches the Lambda budgets.
  - QC covers the new deliverables, and QC results are surfaced through the status API.
- **Downloads:**
  - Presigned URLs are generated on request. Today, cached URLs signed with Lambda session credentials expire within hours.
  - The ZIP package includes the Lender Narrative, the QC report, and the photo set.
  - The frontend lists the new deliverable.
- **Engineering hygiene:**
  - Fix stale unit tests (one currently makes a live Bedrock call) and add a guard that blocks live AWS calls in unit tests.
  - Remove dead code.
  - Pin dependencies.
  - Expire noncurrent S3 object versions.

**Out of scope:** Bedrock model selection (current models stay as-is), CI/CD workflows, and deployment automation. The owner runs and deploys locally.

## Capabilities

### New Capabilities

- `crosswalk-schema`: The master data contract — financing, sponsorship, third-party reports, the detailed operating history — and the deterministic invariants every downstream stage relies on.
- `lender-narrative`: Generation of the Lender Narrative / Transaction Approval Memo DOCX deliverable.
- `financial-workbooks`: The T-12 operating statement and rent roll Excel deliverables.
- `property-images`: Rendering of the consistent property photo package (Krea 2 Turbo via fal.ai).
- `pipeline-orchestration`: Stage ordering, failure propagation, retries, timeouts, and QC gating of a generation job.
- `deliverable-downloads`: How finished deliverables are packaged and exposed to users (API, ZIP, frontend).

### Modified Capabilities

None. No specs exist yet in `openspec/specs/`.

## Impact

- **Code:**
  - `lambdas/shared/`: `models.py`, `s3_utils.py`, a new underwriting engine, chart of accounts, DOCX renderer, and errors module.
  - Lambdas: `crosswalk_generator`, `t12_generator`, `image_generator`, `qc_validator`, `assembler`, `download_handler`, `status_checker`.
  - New `lambdas/lender_narrative_generator`.
- **Infra:**
  - `cdk/stacks/lambda_stack.py`: new Lambda; `FAL_KEY` replaces `REPLICATE_API_TOKEN` for ImageGenerator; assembler storage.
  - `cdk/stacks/stepfunctions_stack.py`: new parallel branches, retry policy, timeout.
  - `cdk/stacks/storage_stack.py`: noncurrent-version expiration.
- **Dependencies:** add `fal-client`; remove `replicate`.
- **Frontend:** `services/api.ts`, `DownloadLinks.tsx`, and the QC failure display.
- **Data contract:** `crosswalk-data.json` gains required blocks. Jobs started before the change are not compatible (jobs are short-lived).
- **Credentials:** a fal.ai API key (`FAL_KEY`) must be present in the local environment used for `cdk deploy`. `REPLICATE_API_TOKEN` is no longer needed.
- **Docs:** `README.md`, `.github/instructions.md`, `templates/data_crosswalk.md`, `templates/image_prompts.md`, `.env.example`.
- **Reference:** `research.md` in this change folder (sourced Fannie Mae research).
