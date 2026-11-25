# Tasks

## 1. Baseline and test safety

- [x] 1.1 Add `tests/conftest.py` with an autouse fixture that raises if a real `bedrock-runtime` boto3 client, a Strands `BedrockModel`, or an outbound `fal_client` call is created. Verify: `pytest tests -q` shows `test_execute_full_pipeline` failing with the guard error instead of making a live call.
- [x] 1.2 Fix `tests/unit/test_section_generators.py::test_execute_full_pipeline` to patch the Strands `Agent` used by `SectionGenerator`. Verify: `pytest tests -q` passes all 20 tests with no network access.
- [x] 1.3 Delete `lambdas/crosswalk_generator/handler_old.py` and the unused `bedrock_client` imports in `lambdas/t12_generator/handler.py` and `lambdas/qc_validator/handler.py`. Verify: `pytest tests -q` passes, and `grep -r handler_old lambdas` finds nothing.
- [x] 1.4 Pin `strands-agents`, `strands-agents-tools`, `pydantic`, `openpyxl`, `python-docx`, `requests`, and `boto3` to exact versions in `requirements.txt`, `lambdas/requirements-runtime.txt`, and the per-Lambda requirements files. Verify: a fresh venv install followed by `pytest tests -q` passes.
- [x] 1.5 Create `tests/unit/test_cdk_stacks.py`. It synthesizes all stacks with context `aws:cdk:bundling-stacks: []` and dummy env vars, so no Docker is needed. Add `noncurrent_version_expiration=Duration.days(7)` to the bucket lifecycle rule in `cdk/stacks/storage_stack.py`, with an assertion for it. Verify: `pytest tests/unit/test_cdk_stacks.py` passes.

## 2. Crosswalk schema and underwriting engine (spec: crosswalk-schema)

- [x] 2.1 Add Pydantic models to `lambdas/shared/models.py`:
  - `OperatingColumn`: 21 categories plus period dates, with an NRI/EGI/OpEx/NOI/NCF invariant validator
  - `OperatingHistory`: `Year 1`–`Year 3` plus `Underwritten`
  - `Financing`, with nested `SourcesUses`
  - `Sponsorship` and `KeyPrincipal`
  - `ThirdPartyReports`

  Add unit tests for each invariant violation in the spec scenarios. Verify: the tests pass.
- [x] 2.2 Add the tier table to `lambdas/shared/underwriting.py`: Conventional Fixed Tier 2/3/4 (min DSCR, max LTV) plus the Tier 2 rate floors by term. Add a comment marking the values as unverified Form 4660 (Nov 2023 redline). Verify: a unit test confirms Tier 3 sizing uses 1.35 / 65%.
- [x] 2.3 Implement these pure functions in `underwriting.py`:
  - level amortizing debt service
  - DSCR- and LTV-constrained sizing, rounded down to $1,000, returning `binding_constraint`
  - credit metrics: DSCRs, LTVs, debt yield, loan per unit, breakeven occupancy
  - sources & uses, with a balancing cash line

  Verify:
  - The spec example (NCF 1,250,000, DSCR 1.25, 6.00%, 30-year amortization) yields 13,899,000 with `DSCR` binding.
  - Additional tests cover the LTV-binding and cash-out cases.
- [x] 2.4 Implement `build_underwritten_column()` and `derive_prior_years()`:
  - `build_underwritten_column()` applies the Sec 203.01 floors.
  - `derive_prior_years()` de-trends Year 1, with noise seeded from `sha256(job_id)`.

  Verify: unit tests cover each floor, and determinism (the same `job_id` gives identical output).
- [x] 2.5 Add `CrosswalkDraft`: the current schema plus Year 1 categories, `history_assumptions`, financing inputs, `sponsorship`, and `third_party_reports`. Add `finalize_crosswalk(draft) -> CrosswalkData`, which runs the engine, recomputes the `historical_t12` summaries, and validates. Verify: a fixture draft finalizes into a valid `CrosswalkData`, and its `historical_t12["Year 1"]` NOI equals the `operating_history` Year 1 NOI.
- [x] 2.6 Update `crosswalk_generator/handler.py`:
  - Set `structured_output_model=CrosswalkDraft` and `max_tokens=16000`.
  - Extend the schema description and prompt for the new draft fields: fictitious sponsor and third-party-report names, and Year 1 EGI within ±10% of the pro forma EGI.
  - Call `finalize_crosswalk()`.
  - Add a ±10% deviation warning.

  Verify: the updated `tests/unit/test_crosswalk_generator.py` (with the agent mocked to return a draft fixture) persists a valid v2 crosswalk.
- [x] 2.7 Update the shared fixture `sample_crosswalk_dict` to the v2 schema, and document the new blocks and invariants in `templates/data_crosswalk.md`. Verify: `pytest tests -q` passes.

## 3. Shared DOCX renderer (design D4)

- [x] 3.1 Move the markdown→DOCX functions from `lambdas/assembler/handler.py` into `lambdas/shared/docx_renderer.py`, adding parameters for cover metadata, optional footer text, and an image map. Switch the assembler to use it. Verify: a unit test renders fixture markdown (headings, list, table, bold) and asserts the paragraph styles, table cell text, and footer text of the resulting `Document`.

## 4. Financial workbooks (spec: financial-workbooks)

- [x] 4.1 Create `lambdas/shared/chart_of_accounts.py`:
  - at least 40 GL accounts (4000/5000/6000 series)
  - for each account: parent category, weight range, and seasonality profile
  - applicability predicates: a cold-climate state list, elevators for mid/high-rise, and non-zero commercial / ground rent
  - a largest-remainder allocator

  Verify:
  - Unit tests confirm allocations sum exactly to their parents.
  - Unit tests confirm snow removal is zero for warm-climate states.
- [x] 4.2 Rewrite `generate_t12()` in `lambdas/t12_generator/handler.py`, keeping the output filenames `t12_year{1,2,3}.xlsx`:
  - month-year column headers taken from the period dates
  - grouped detail rows
  - `=SUM()` subtotals for NRI, Other Income, EGI, each category, Total OpEx, NOI, and NCF, with reserves below NOI
  - Per Unit and % of EGI columns
  - monthly occupancy statistics rows

  Verify with a test that loads each workbook and:
  - recomputes totals from the detail cells and matches them to `operating_history`
  - finds at least 40 detail rows and the correct month headers
  - gets identical output across two runs
- [x] 4.3 Rewrite `generate_rent_roll()`:
  - date taken from `financial_data.effective_date`
  - vacancies scattered using the seeded RNG
  - zero-sum rent jitter within each unit type
  - new columns: move-in, concession, deposit, balance due
  - a summary block by unit type

  Verify with tests for:
  - unit and occupied counts
  - per-type in-place totals
  - the header date
  - vacant units not all trailing

## 5. Property images on Krea 2 Turbo (spec: property-images)

- [x] 5.1 Replace `replicate` with a pinned `fal-client` in `lambdas/image_generator/requirements.txt`, `lambdas/requirements-runtime.txt`, and `requirements.txt`. Verify: `pip install -r requirements.txt` succeeds and `python -c "import fal_client"` works.
- [x] 5.2 Rewrite `generate_single_image()` in `lambdas/image_generator/handler.py` to call `fal_client.run("fal-ai/krea-2/turbo", ...)` with these arguments:
  - `image_size="landscape_4_3"`, `output_format="jpeg"`, `num_images=1`
  - `enable_prompt_expansion=False`, `enable_safety_checker=True`
  - seed = `sha256(job_id + filename)` mod 2³¹

  Download `images[0].url` and store it as `image/jpeg`. Verify with unit tests (`fal_client` mocked) that assert the request arguments, a deterministic seed, and JPEG storage.
- [x] 5.3 Add retry handling to the render path:
  - **Safety flag:** if `has_nsfw_concepts[0]` is true, retry once with `seed + 1`, then mark the shot `failed` with `reason: safety_filter`.
  - **Transient errors:** HTTP 429 or 5xx gets one in-process retry with backoff, then the shot is marked `failed`.

  Verify: unit tests cover flagged-then-clean, flagged-twice, and 429-then-success.
- [x] 5.4 Update the prompt pipeline:
  - Change the `STRUCTURED_PROMPT_SYSTEM` text to Krea 2 Turbo.
  - Raise the prompt call `max_tokens` to 32000.
  - Validate that exactly 30 prompts are parsed: retry once, then fail with the parsed count.
  - Check `FAL_KEY` at handler start, replacing the `REPLICATE_API_TOKEN` check.

  Verify: unit tests cover the short-count retry and failure paths, and the missing-`FAL_KEY` failure.
- [x] 5.5 Update `cdk/stacks/lambda_stack.py` to read `FAL_KEY` (synth fails if it is missing) and inject it into ImageGenerator, removing the `REPLICATE_API_TOKEN` requirement. Verify: a `test_cdk_stacks.py` assertion that the ImageGenerator env has `FAL_KEY` and no `REPLICATE_API_TOKEN`.
- [x] 5.6 Update `templates/image_prompts.md`, `README.md` (image section, diagrams, tech stack, prerequisites, configuration), `.github/instructions.md` (image_generator description, env vars), and `.env.example` (`FAL_KEY` replaces `REPLICATE_API_TOKEN`) for Krea 2 Turbo on fal.ai. Verify: `grep -ri "replicate\|krea 2 large" README.md .github/instructions.md templates .env.example lambdas cdk` returns nothing.

## 6. Lender Narrative / Transaction Approval Memo (spec: lender-narrative)

- [x] 6.1 Create `lambdas/lender_narrative_generator/` with:
  - `facts.py`: builds the fact sheet of formatted, allowed figures from `CrosswalkData`
  - `tables.py`: markdown tables for:
    - loan summary
    - sources & uses
    - historical vs. UW, with per-unit, % EGI, and variance columns
    - sizing
    - DSCR sensitivity (+100/+200 bps)
    - refinance projection to maturity (2% income / 3% tax growth, balloon, refi DSCR at note rate + 100 bps)
    - appraisal reconciliation

  Verify with unit tests that:
  - loan-summary values equal the crosswalk values
  - the refinance balloon matches an independent amortization calculation
- [x] 6.2 Implement grouped prose generation in `handler.py`:
  - About 6 `opus`-role prompt groups covering all 17 headings, run concurrently.
  - Each group receives only its relevant facts.
  - Add the number guard: extract `$`/`%`/`x` figures, compare them to the fact sheet within tolerance, regenerate the group once listing the offending figures, then record warnings.

  Verify with unit tests (mocked `bedrock_client`): an unknown figure triggers exactly one regeneration, and a clean group triggers none.
- [x] 6.3 Assemble the narrative markdown in 17-heading order and render it with `docx_renderer`:
  - title "Lender Narrative — Transaction Approval Memo"
  - cover with lender name and property
  - synthetic disclaimer on the cover and in the footer

  Write `outputs/lender_narrative.docx` and `sections/lender_narrative_warnings.json`. Verify: a test confirms the DOCX contains the 17 headings in order and the footer disclaimer.
- [x] 6.4 Register a `LenderNarrativeGenerator` Lambda (1024 MB, 10 min) in `cdk/stacks/lambda_stack.py` and expose it to `StepFunctionsStack`. Verify: a `test_cdk_stacks.py` assertion that the function exists with those settings.

## 7. Pipeline orchestration (spec: pipeline-orchestration)

- [x] 7.1 Add `lambdas/shared/errors.py` with `TransientError` and a `wrap_transient()` helper. It maps these to `TransientError`:
  - botocore `ThrottlingException`, `ServiceUnavailableException`, `ModelNotReadyException`, and `InternalServerException`
  - Strands' model-throttled error
  - fal.ai HTTP 429 and 5xx

  Apply it in `bedrock_client`, `SectionGenerator.generate_content`, and the crosswalk, image, and narrative handlers. Verify with unit tests: a mocked throttling `ClientError` surfaces as `TransientError`, and a `ValidationException` does not.
- [x] 7.2 Make `crosswalk_generator.handler` raise `CrosswalkGenerationError` on failure instead of returning `status: error`. Verify: a unit test with a failing mocked agent raises.
- [x] 7.3 Restructure `cdk/stacks/stepfunctions_stack.py`:
  - Add `GenerateLenderNarrative` and `GenerateImages` as branches of the producer Parallel state, and remove the sequential image step.
  - Retry `TransientError` plus the four `Lambda.*` errors: 3 attempts, 5 s interval, backoff 2.0.
  - Retry `States.Timeout` once. Do not retry `States.TaskFailed`.
  - Compute the longest-path timeout with a 10% margin.

  Verify with `test_cdk_stacks.py` assertions:
  - The Parallel branches include the sections, T-12, narrative, and images.
  - No retry list contains `States.TaskFailed`.
  - The timeout is at least the longest-path budget.
- [x] 7.4 Extend `qc_validator` with these checks, and count `checks_performed` from the checks actually executed:
  - **Narrative:**
    - the narrative exists
    - it has all 17 headings
    - the formatted loan amount, UW DSCR, LTV, and UW NCF are present
    - a missing narrative or missing loan amount is an error
  - **T-12 totals:** annual EGI, OpEx, NOI, and NCF recomputed from detail cells vs. `operating_history`; a mismatch is an error.
  - **Tier:** the tier-constraint check.
  - **Warnings:** the narrative's number-guard warnings and the image manifest failures are added as warnings.

  Verify: unit tests cover each new error path and the check count.
- [x] 7.5 Update `status_checker`:
  - Read `qc_report.json` when present, and return `qc: {status, error_count, warning_count, errors[:5]}`.
  - Drop the standalone `GenerateImages` from `STEP_PROGRESS`.

  Verify: a unit test (mocked S3 and SFN responses) covers a QC-failed job.
- [x] 7.6 Update `frontend/src/services/api.ts` (`StatusResponse.qc`) and `GenerationProgress.tsx` to show QC failure reasons on failed jobs. Verify: `npm run build` succeeds in `frontend/`.

## 8. Deliverable downloads (spec: deliverable-downloads)

- [x] 8.1 Rewrite `download_handler`:
  - Always list `outputs/` and sign fresh 1-hour URLs.
  - Add `lender_narrative`.
  - Order `t12_files` by year.
  - Omit missing outputs.
  - Keep the 404 `not_ready` response.

  Also remove the `download_urls.json` write from the assembler. Verify: unit tests (mocked S3) cover ordering, omission, and not-ready.
- [x] 8.2 Update the assembler ZIP:
  - Build it in `/tmp`.
  - Add `lender_narrative.docx`, `qc_report.json`, and `photos/<filename>` for each successful image.
  - Set the assembler's ephemeral storage to 2048 MB and memory to 1024 MB in CDK.

  Verify:
  - A unit test (mocked S3) checks the ZIP entries for a fixture job with 3 images.
  - A `test_cdk_stacks.py` assertion checks the assembler sizing.
- [x] 8.3 Update `frontend/src/services/api.ts` and `DownloadLinks.tsx`:
  - In `api.ts`, make the `DownloadResponse.urls` fields optional and add `lender_narrative`.
  - In `DownloadLinks.tsx`, render only the keys present, add a "Lender Narrative" DOCX entry, and label T-12s "T-12 — Year N".

  Verify: `npm run build` succeeds, and with mocked responses the dev server shows or hides the narrative entry accordingly.

## 9. Documentation and integration verification

- [x] 9.1 Update `README.md` and `.github/instructions.md`:
  - architecture diagrams: images and the Lender Narrative in the parallel fan-out
  - pipeline stage table
  - deliverables list
  - ZIP contents
  - T-12 description

  Verify: the Mermaid blocks render in a Markdown preview.
- [x] 9.2 Run `openspec validate loan-package-enhancements --strict` and `pytest tests -q`. Verify: both pass.
- [ ] 9.3 After deploying locally (`cdk deploy --all`, with `FAL_KEY` set), run one end-to-end job from the UI. Verify:
  - every download link works
  - the ZIP contains the narrative, the 3 T-12s, the rent roll, `qc_report.json`, and `photos/`
  - the status response shows a `qc` block
  - the `t12_year1.xlsx` NOI equals the narrative's Year 1 NOI
  - the narrative loan amount equals `financing.loan_amount`
  - the photos visibly depict one consistent property

## Workflow follow-up

- Create a fal.ai API key and add `FAL_KEY` to the local `.env` before deploying. Remove `REPLICATE_API_TOKEN` after the smoke run passes.
- Archive this change after review and a successful end-to-end run.
