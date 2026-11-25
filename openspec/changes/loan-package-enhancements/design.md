# Design

## Context

See `proposal.md` for motivation; requirements are in `specs/*/spec.md`. Facts observed on 2026-11-25 that shape this design:

- **Crosswalk generation:** Crosswalk runs as a Strands agent on Haiku with arithmetic tools. The handler catches exceptions and *returns* `{"status": "error"}`, which Step Functions treats as success, so the next stages run against a missing crosswalk.
- **Orchestration:**
  - The state machine is Crosswalk → Parallel (12 sections + T-12) → Images (sequential) → QC → Assembler.
  - The state machine timeout is 15 minutes, while the stage timeouts sum to more than 40 minutes.
  - Retries include `States.TaskFailed`, so deterministic failures (including expensive Opus runs) are retried.
- **Image generation:**
  - Sonnet writes 30 seven-part prompts in one call with `max_tokens=8192`, which risks truncation.
  - Renders run on Replicate `krea/krea-2-large` with `creativity: low`.
  - Images are stored as `.jpg` with content type `image/jpeg`, regardless of the format Replicate actually returns.
- **Krea 2 Turbo availability:**
  - Krea 2 Turbo is **not on Replicate**; only `krea-2-large`, `krea-2-medium`, and `krea-3` are.
  - fal.ai serves it as `fal-ai/krea-2/turbo` at $0.008 per megapixel. Its inputs are `prompt`, `seed`, `image_size`, `num_images`, `acceleration`, `enable_prompt_expansion`, `enable_safety_checker`, and `output_format`. Its outputs are `images[].url`, `seed`, and `has_nsfw_concepts[]`.
  - It has no `creativity` or negative-prompt input.
- **Workbooks:**
  - The T-12 has 5 lines, derived from `HistoricalYear`, with an unseeded random monthly spread.
  - The rent roll uses a hard-coded `date(2026, 2, 10)` and lists all vacant units at the end.
- **Downloads:**
  - The assembler writes presigned URLs, with a 7-day expiry, to `download_urls.json`, and the download handler returns those cached URLs.
  - URLs signed with Lambda role session credentials die when that session expires, which happens within hours.
  - The ZIP excludes images and the QC report.
- **Storage:** the S3 bucket is versioned, but its 30-day expiration rule has no noncurrent-version expiration.
- **Tests:**
  - 1 of 20 unit tests fails: `test_execute_full_pipeline` patches the legacy `bedrock_client.invoke_model`, while sections now use Strands. It therefore makes a **live Bedrock call**.
  - Dependencies are unpinned (`strands-agents>=0.1.0`, etc.).
- **Fannie Mae sources (`research.md`):**
  - The Lender Narrative is the **Transaction Approval Memo** (Part I Sec 103); the owner has confirmed this.
  - The ordered outline comes from DUS Exhibit III-2 and Form 4605.
  - The operating categories come from Sec 203.01 and Form 4254.DEF.
  - The tier DSCR/LTV values come from a Nov 2023 Form 4660 redline.

## Goals / Non-Goals

**Goals:**
- Exact arithmetic everywhere. The LLM picks *inputs*; code computes *every* derived figure that appears in any deliverable.
- A TAM and T-12s that a multifamily analyst recognizes: Fannie Mae categories, GL-style sub-accounts, and NOI → NCF.
- Faster, cheaper, consistent photo rendering with Krea 2 Turbo.
- Fix the reliability gaps that cost little and today cause failed or confusing jobs.

**Non-Goals:**
- Changing Bedrock model selection. The existing `haiku`/`sonnet`/`opus` roles and their configuration stay as they are.
- CI/CD workflows or deployment automation. The owner runs and deploys locally, so `.github/workflows/*` are untouched.
- Real DUS Gateway submission formats, Form 6502 delivery folders, or C&D upload.
- Product-specific rules (seniors, student, MAH, Green, small-loan, ARM floors). Only Conventional Fixed tiers are modelled.
- PDF output, user-supplied loan terms (they are synthesized), and full PCA/ESA reports (only summaries).
- API authentication and rate limiting (see Deferred soft spots).

## Decisions

### D1. Two-phase crosswalk: LLM draft → deterministic underwriting engine
- **Draft phase:** the Strands agent fills a new `CrosswalkDraft` model. It is the current schema plus:
  - **Year 1** category amounts for `operating_history`.
  - `history_assumptions`: per-year income and expense growth, plus optional one-off events (for example, an insurance spike in Year 2).
  - Financing *inputs*: purpose, tier, rate, term, amortization, IO, prepayment, and purchase price/date.
  - `sponsorship` and `third_party_reports`.
- **Engine phase:** `lambdas/shared/underwriting.py` (pure functions) turns the draft into the final `CrosswalkData`:
  1. Derive Year 2 and Year 3 by de-trending Year 1, with seeded per-category noise.
  2. Build the Underwritten column under the Sec 203.01 floors (see the `crosswalk-schema` spec).
  3. Compute debt service, loan sizing, and credit metrics.
  4. Compute sources & uses, using cash as the balancing line.
  5. Recompute the `historical_t12` summaries.
  6. Validate the result.
- **Why:**
  - The repo already compensates for LLM arithmetic drift (it recomputes `value_per_unit`).
  - Asking the model for 4 columns × 21 categories plus loan math would multiply validation retries.
  - Year-1-only keeps the draft small.
  - The crosswalk keeps using whatever model it uses today. `max_tokens` rises to 16k for the larger draft.
- **Guardrail:** Year 1 EGI should be within ±10% of the appraiser's pro forma EGI. A miss produces a warning, not an error.
- **Appraiser vs. lender treatment of reserves:**
  - The appraiser pro forma keeps reserves above NOI, as appraisals typically present them.
  - The lender Underwritten column puts reserves below NOI.
  - Section 07 is unchanged. The narrative's Appraisal Review section reconciles the two.
- **Determinism:** every seeded RNG derives from `sha256(job_id + purpose)`, never Python's salted `hash()`.
- **Alternatives considered:**
  - LLM emits all columns and the loan math — rejected for the reasons above.
  - History derived purely from the pro forma — rejected; it is flat and has no story.

### D2. Chart of accounts table + largest-remainder allocation for T-12s
- **Account table:** `lambdas/shared/chart_of_accounts.py` is a static table of GL accounts. Each row has:
  - account number, name, parent category, and a weight range
  - a seasonality profile: `level`, `heating`, `cooling`, `growing`, `winter_only`, or `summer_peak`
  - applicability predicates: cold-climate state list, elevators for mid- and high-rise, and non-zero commercial or ground rent
- **Allocation:** category amounts are split into accounts by seeded weights. Account amounts are split into months by seasonality profile. Both splits use largest-remainder rounding, so integer sums are exact.
- **Workbook formulas:** `t12_generator` writes detail values plus `=SUM()` formulas for subtotals, NOI, and NCF.
- **Formula verification:** openpyxl does not evaluate formulas, so QC and the tests recompute totals from detail cells.
- **Rent roll:** uses the same seeded RNG to scatter vacancies, and applies zero-sum ±$25 rent jitter per unit type so per-type in-place totals tie exactly. Lease dates are computed from `effective_date`.

### D3. Lender Narrative (TAM): code-rendered tables + grouped LLM prose with a number guard
- **Runtime:** a new Lambda, `lambdas/lender_narrative_generator`, runs in the producer Parallel state (D6). It reads only `crosswalk-data.json`.
- **Code-built content:**
  - A **fact sheet** of pre-formatted allowed figures, for example `loan_amount: "$13,899,000"` and `uw_dscr: "1.25x"`.
  - All tables, as markdown: loan summary, sources & uses, historical vs. UW, sizing, DSCR sensitivity, refinance projection, and appraisal reconciliation.
- **Prose generation:**
  - Prose uses the existing `opus` role, in about 6 grouped prompts:
    1. summary + recommendation
    2. sponsor + management
    3. property + market + rent roll
    4. operations + appraisal + third-party reports
    5. risks + refinance
    6. waivers + conditions + conclusion
  - The groups run concurrently in a thread pool.
- **Number guard:**
  - Regex-extract `$` amounts, percentages, and `x` ratios from the prose and compare them to the fact sheet, with a tolerance of $1 or 0.01.
  - A group that cites unknown figures is regenerated once, with the offending values listed.
  - If it still fails, QC records a warning.
- **Rendering:**
  - Rendered through the shared DOCX renderer (D4), titled "Lender Narrative — Transaction Approval Memo".
  - The synthetic disclaimer appears on the cover and in the footer.
  - The lender name, "NorthBridge Multifamily Capital", is reused from the appraisal cover.
- **Bedrock calls:** prose needs no tools, so this uses plain `bedrock_client` calls rather than Strands.
- **Alternatives considered:**
  - One monolithic Opus call — rejected: output-length risk and no per-group retry.
  - Reusing the appraisal section markdown — rejected: couples the narrative to LLM prose instead of the crosswalk.

### D4. Extract the shared DOCX renderer
- **What moves:** the assembler's markdown → DOCX logic (headings, lists, tables, inline bold/italic, images, cover) moves into `lambdas/shared/docx_renderer.py`.
- **New parameters:** cover metadata, optional footer text, and an image map.
- **Users:** the assembler and the narrative generator both use it.
- **Constraint:** the appraisal DOCX structure stays unchanged.

### D5. Image rendering via fal.ai Krea 2 Turbo
- **Client:** replace `replicate` with `fal-client`.
- **Request:** `fal_client.run("fal-ai/krea-2/turbo", arguments={...})`, with:
  - `image_size: "landscape_4_3"`
  - `output_format: "jpeg"`
  - `num_images: 1`
  - `enable_prompt_expansion: false`
  - `enable_safety_checker: true`
  - `seed` = `int(sha256(job_id + filename))` mod 2³¹
- **Response handling:** download `images[0].url` with `requests`.
- **Safety retry:** if `has_nsfw_concepts[0]` is true, the result is a black image. Retry once with `seed + 1`; otherwise mark the shot failed with `reason: safety_filter`.
- **Why fal.ai:**
  - It is the only hosted API for Turbo besides Krea's own.
  - It is pay-per-megapixel.
  - Its synchronous `run` fits the existing thread-pool design.
- **Consistency without `creativity`:** Turbo has no `creativity` knob. Consistency comes from:
  - the shared architectural concept, which is unchanged
  - prompt expansion turned off, so fal does not rewrite the concept
  - stable per-shot seeds
- **Prompt changes:**
  - The prompt system text changes from "Krea 2 Large" to "Krea 2 Turbo". The 7-section structure stays.
  - Negative-prompt guidance stays inline, since there is no separate negative input — the same as Large.
- **Prompt budget:**
  - Sonnet `max_tokens` rises from 8192 to 32000.
  - The parser requires exactly 30 prompts, with one retry.
- **Configuration:**
  - CDK reads `FAL_KEY` from the local environment at synth time and injects it into ImageGenerator, replacing `REPLICATE_API_TOKEN`.
  - Synth fails fast if `FAL_KEY` is missing (same pattern as today).
  - Worker concurrency stays at 10.
  - The Lambda timeout stays at 10 minutes, because Turbo renders in seconds.
- **Alternatives considered:**
  - Krea native API — rejected by the owner.
  - Keeping a Replicate Large fallback — rejected by the owner; it would also mean two credentials.

### D6. Orchestration changes
- **Parallel branches:**
  - The producer Parallel state gains `GenerateLenderNarrative` and `GenerateImages` branches.
  - The sequential image step is removed.
  - The Parallel state's catch routes to `NotifyError`.
- **Transient errors:**
  - Add a shared `TransientError` (`lambdas/shared/errors.py`).
  - It wraps known transient causes: botocore `ThrottlingException`, `ServiceUnavailableException`, `ModelNotReadyException`, and `InternalServerException`; Strands' model-throttled error; and fal.ai HTTP 429 and 5xx.
- **Retry policy:**
  - Step Functions retries `TransientError` and the four `Lambda.*` service errors up to 3 times (5 s interval, backoff 2.0).
  - It retries `States.Timeout` once.
  - `States.TaskFailed` is removed from the retry list.
- **Crosswalk failures:** the crosswalk raises `CrosswalkGenerationError`, which is not retried.
- **Timeout:** the state machine timeout is computed in CDK as the longest path of `stage_timeout × (1 + max_retries)`, plus a 10% margin.
- **QC status:**
  - `status_checker` reads `qc_report.json` when present and adds `qc: {status, error_count, warning_count, errors[:5]}`.
  - `STEP_PROGRESS` drops the standalone `GenerateImages` step.
- **CDK synth test:** synthesizes with bundling disabled (context `aws:cdk:bundling-stacks: []`), so no Docker is needed. It asserts the branches, retry lists, timeout, and environment.

### D7. Downloads and packaging
- **Download handler:**
  - Lists `outputs/` on every request and signs fresh URLs (`ExpiresIn=3600`).
  - Orders `t12_files` by year and adds `lender_narrative`.
  - The assembler stops writing `download_urls.json`.
- **ZIP package:**
  - The assembler builds the ZIP in a `/tmp` file and uploads it with `upload_file`.
  - It adds `lender_narrative.docx`, `qc_report.json`, and `photos/<filename>`.
  - Assembler resources: 2048 MB ephemeral storage, 1024 MB memory.
- **Frontend:**
  - `DownloadResponse.urls` fields become optional, plus a new `lender_narrative`.
  - `DownloadLinks.tsx` renders only the keys present and labels T-12s "T-12 — Year N".

### D8. Hygiene
- **Unit-test guard:** a `tests/conftest.py` autouse fixture makes constructing a real `bedrock-runtime` client, a Strands `BedrockModel`, or an outbound fal.ai call raise.
- **Test fixes:** `test_execute_full_pipeline` is fixed to patch the Strands `Agent`.
- **Dead code:** delete `crosswalk_generator/handler_old.py` and the unused `bedrock_client` imports.
- **Dependencies:** pin the Python dependencies in `requirements.txt`, `lambdas/requirements-runtime.txt`, and the per-Lambda files.
- **Storage:** add `noncurrent_version_expiration=7 days` to the bucket lifecycle.

## Risks / Trade-offs

- **[Risk] Turbo images look less consistent than Large at `creativity: low`.**
  - **Mitigation:** stable per-shot seeds, prompt expansion off, and the shared concept in every prompt.
  - **Check:** the smoke run (task 9.3) inspects the 30 images for visual consistency.
  - **Fallback:** if consistency is poor, strengthen the concept block in each structured prompt, for example by repeating materials and palette verbatim in the Subject line. The model choice itself is fixed by the owner.
- **[Risk] fal.ai rate-limits 10 concurrent requests.** 429s become `TransientError` inside the per-shot call, with one in-process retry with backoff. A shot still failing after that is recorded as failed. The stage only fails if all 30 shots fail.
- **[Risk] The larger crosswalk draft raises structured-output retries and latency.** Mitigations: Year-1-only draft, 16k `max_tokens`, and the 10-minute timeout is retained.
- **[Risk] Opus prose cites numbers not in the fact sheet.** Mitigations: the number guard, one regeneration, then a QC warning. Tables, which carry every key figure, are never LLM-generated.
- **[Risk] Old `crosswalk-data.json` files fail the new schema (BREAKING).** Jobs are single-run and nothing re-reads old jobs. Deploy when no executions are `RUNNING`.
- **[Risk] Tier thresholds are out of date (Nov 2023 Form 4660 redline).** They live in one configurable table, labelled unverified in code and in a narrative footnote.
- **[Trade-off] Images move into the Parallel state.** Image and section spend now happen concurrently even if one of them fails. In exchange, wall-clock time drops substantially.
- **[Trade-off] Download URLs live 1 hour.** That is shorter but honest, and the UI re-fetches the links on page load.

## Migration Plan

1. Create a fal.ai API key and set `FAL_KEY` in the local environment (`.env`) used for `cdk deploy`. Leave `REPLICATE_API_TOKEN` in place until the deploy succeeds, then remove it.
2. Confirm no Step Functions executions are `RUNNING`. Run `pytest tests -q`, then deploy locally with `cdk deploy --all`.
3. Smoke test with one job from the UI:
   - All download links work.
   - The ZIP lists the narrative, photos, and QC report.
   - `qc` appears in the status response.
   - The `t12_year1.xlsx` NOI equals the narrative's Year 1 NOI.
   - The photos look like one property.
4. Rollback: check out the previous commit and redeploy. This needs `REPLICATE_API_TOKEN` again, so keep it until step 3 passes.

## Deferred soft spots (recorded, not in this change)

- **Unprotected API.** The API is public, unauthenticated, and unthrottled. Each `/api/generate` call spends Opus plus 30 renders. Recommended follow-up: API Gateway stage throttling with a usage plan or API key.
- **Loose S3 CORS.** S3 CORS allows `PUT`, `POST`, and `DELETE` from `*`. Tighten it to `GET` and `HEAD`.
- **CI deploy workflows.** These have failed since 2026-07-27 and still reference `REPLICATE_API_TOKEN`. They are out of scope while deploys are local.
- **Status checker fallback.** It scans `list_executions` across statuses. That is fine at current volume.
- **Deprecated datetime call.** `models.py` still uses `datetime.utcnow()`.

## Open Questions

- What refinance-rate assumption should the Refinance Risk section use? The default is the note rate + 100 bps; only the narrative's input value changes.
- Exact pinned dependency versions will be chosen during implementation, from what passes the tests locally.
