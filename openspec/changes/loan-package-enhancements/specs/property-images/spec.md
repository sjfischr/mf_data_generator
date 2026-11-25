# Spec Delta

## Purpose

Produces the property photo package: a set of mutually consistent synthetic photographs of the subject property, rendered from structured prompts that share one architectural concept. They are used in the appraisal report and the downloadable package.

## ADDED Requirements

### Requirement: Krea 2 Turbo on fal.ai renders property photos
Each property photo SHALL be rendered by the Krea 2 Turbo model through the fal.ai endpoint `fal-ai/krea-2/turbo`, authenticated with the `FAL_KEY` credential. The image stage SHALL NOT call Replicate.

#### Scenario: Render request targets Krea 2 Turbo
- **WHEN** the image stage renders a shot
- **THEN** the request is sent to `fal-ai/krea-2/turbo` with the assembled structured prompt

#### Scenario: Missing credential
- **WHEN** the image stage starts and `FAL_KEY` is not configured
- **THEN** the stage fails immediately with a message naming `FAL_KEY`, before any prompt generation

### Requirement: Consistent render settings
Every render request SHALL use:
- the same landscape 4:3 image size
- JPEG output
- prompt expansion disabled
- one image per request
- a seed derived deterministically from the job ID and shot filename

#### Scenario: Deterministic seed
- **WHEN** the same job renders the shot `aerial_view.jpg` twice
- **THEN** both requests use the same seed

#### Scenario: Prompt expansion off
- **WHEN** any render request is inspected
- **THEN** `enable_prompt_expansion` is false, so the shared architectural concept is not rewritten

### Requirement: Stored image format matches content
Each stored image SHALL be saved under `images/<filename>.jpg`, with content type `image/jpeg`, and the bytes SHALL be a JPEG.

#### Scenario: JPEG stored
- **WHEN** a render succeeds
- **THEN** the S3 object has content type `image/jpeg`, and its bytes begin with the JPEG signature

### Requirement: Safety-flagged renders are retried
A render that fal.ai flags in `has_nsfw_concepts` SHALL NOT be stored as a successful image. It SHALL be retried once with a different seed, and if it is flagged again it SHALL be recorded as failed in the manifest.

#### Scenario: Flagged render retried
- **WHEN** the first render of a shot returns `has_nsfw_concepts: [true]`
- **THEN** the shot is rendered once more with a different seed
- **AND** if the second render is also flagged, the manifest marks the shot `failed`, with reason `safety_filter`

### Requirement: Structured prompt count validated
Prompt generation SHALL use an output token budget large enough for all 30 structured prompts. It SHALL validate that exactly 30 prompts were parsed before any render starts.

#### Scenario: Short prompt list
- **WHEN** fewer than 30 structured prompts are parsed
- **THEN** prompt generation is retried once, and if it is still short the image stage fails with a message stating the parsed count

### Requirement: Partial render failures tolerated
The image stage SHALL succeed when at least one shot renders. It SHALL fail when no shots render. The manifest SHALL record every shot with status `success` or `failed`, and a reason for each failure.

#### Scenario: Some shots fail
- **WHEN** 27 of 30 shots render successfully
- **THEN** the stage succeeds, and the manifest lists 27 `success` and 3 `failed` entries, each failure with a reason
