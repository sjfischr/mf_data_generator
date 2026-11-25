"""Image Generator Lambda — generates property images via fal.ai Krea 2 Turbo."""

import json
import logging
import os
import textwrap
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import fal_client
import requests

from lambdas.shared import bedrock_client, s3_utils
from lambdas.shared.models import CrosswalkData

logger = logging.getLogger(__name__)

FAL_MODEL = "fal-ai/krea-2/turbo"
MAX_WORKERS = 10

# Model used for prompt generation. Sonnet is used instead of Haiku here because
# keeping 30 structured prompts consistent with a single shared architectural
# concept requires stronger instruction-following than Haiku reliably provides.
PROMPT_MODEL = "sonnet"

STRUCTURED_PROMPT_SYSTEM = textwrap.dedent("""\
    You are a prompt generator for the Krea 2 Turbo image generation model. Given
    a shot description and a shared architectural concept for a property, output
    a structured prompt using the following exact section headers, in this exact
    order. Do not add commentary, disclaimers, or any text outside the structure
    below.

    Subject: [one line — the primary subject and setting type]

    Architecture details: [comma-separated list of structural/material features — building materials, window types, rooflines, structural elements]

    Landscaping: [comma-separated list — vegetation, hardscape, terrain, foreground elements]

    Lighting/atmosphere: [comma-separated list — time of day, sky condition, light quality, season indicators]

    Camera: [comma-separated list — angle, height, lens characteristics, composition notes]

    Style tags: [comma-separated list — 4-6 short descriptive tags for overall photographic/artistic style]

    Negative prompt suggestions: [comma-separated list of 4-6 things to avoid — common generation artifacts, distortions, or unwanted elements specific to this image]

    Rules:
    - Never transcribe legible text, signage, logos, or heraldry into the prompt. Describe these generically instead (e.g. "carved wooden sign" not the words on it).
    - Do not identify or name real people. Describe figures only by pose, clothing, and position (e.g. "figure walking away from camera in dark jacket").
    - Do not guess at real-world proper nouns (building names, institution names) unless they are unambiguously visible as printed text you are also declining to transcribe — in that case describe the building type generically.
    - Keep each section to visual, physically observable detail only. No speculation about history, function, or meaning.
    - Every section must be present even if brief.
    - Reuse the SAME architectural materials, colors, rooflines, and landscaping theme given to you in every prompt, so all 30 images clearly depict the same physical property.
    """)


def generate_architectural_concept(crosswalk: CrosswalkData) -> dict:
    """Use Haiku to establish one consistent architectural concept for the property.

    This concept is generated once, up front, and then threaded through every
    one of the 30 structured image prompts so the photo package reads as a
    single consistent property (same materials, colors, rooflines, landscaping)
    rather than 30 unrelated buildings.
    """
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical

    prompt = f"""Establish a single, consistent architectural concept for a commercial
real estate photo package. Every image prompt generated afterward will reference
this concept, so it must be concrete enough to keep the SAME building materials,
color palette, and landscaping style across all 30 photos.

Property details:
- Building type: {phys.building_type}
- Buildings: {phys.total_buildings}, {phys.stories} stories each
- Units: {phys.total_units}
- Year Built: {prop.year_built}
- Location: {prop.city}, {prop.state}
- Site: {phys.site_area_acres} acres
- Amenities: {', '.join(phys.amenities)}

Return a JSON object with these keys:
- "architectural_style": short label (e.g. "contemporary garden-style craftsman" or "modern urban high-rise")
- "exterior_materials": comma-separated list of 3-5 consistent building materials/colors (siding type, brick/stone accents, trim color)
- "roofline": one phrase describing the consistent roof type/pitch (garden-style) or roofline/parapet (high-rise)
- "window_style": one phrase describing the consistent window/balcony style
- "color_palette": comma-separated list of 2-4 consistent exterior colors
- "landscaping_theme": comma-separated list describing consistent landscaping style, plantings, hardscape
- "site_features": comma-separated list of recurring site features (lighting fixtures, signage style, walkway paving, etc.)

Be specific and concrete so an image generation model can reproduce the same look
repeatedly. Keep it realistic for a {phys.building_type} community built in {prop.year_built}.
"""

    return bedrock_client.invoke_model_json(
        prompt=prompt,
        model="haiku",
        system_prompt=(
            "You are an architectural consistency director for a real estate photo "
            "shoot. Return valid JSON only."
        ),
        max_tokens=1024,
    )


def _assemble_structured_prompt(item: dict) -> str:
    """Join the seven structured sections into the final Krea prompt string."""
    return (
        f"Subject: {item['subject']}\n\n"
        f"Architecture details: {item['architecture_details']}\n\n"
        f"Landscaping: {item['landscaping']}\n\n"
        f"Lighting/atmosphere: {item['lighting_atmosphere']}\n\n"
        f"Camera: {item['camera']}\n\n"
        f"Style tags: {item['style_tags']}\n\n"
        f"Negative prompt suggestions: {item['negative_prompt_suggestions']}"
    )


SHOT_BATCHES = [
    ("exterior", "6 exterior views (aerial, street frontage, entrance/signage area, building elevations) "
                 "and 4 amenity views", 10),
    ("interior", "10 unit interior views across the unit types (living, kitchen, bedroom, bath)", 10),
    ("site", "2 more amenity views, 2 more unit interiors, and 6 site/surroundings views "
             "(parking, landscaping, walkways, neighborhood context)", 10),
]
PROMPT_COUNT = sum(count for _, _, count in SHOT_BATCHES)


def _prompt_items(result) -> list[dict]:
    if isinstance(result, dict):
        result = result.get("prompts") or next((v for v in result.values() if isinstance(v, list)), [])
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


def _generate_batch(crosswalk: CrosswalkData, concept: dict, batch: tuple[str, str, int]) -> list[dict]:
    """Generate one batch of structured prompts that all reuse the shared concept."""
    name, shots, count = batch
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical
    unit_sizes = {u.unit_type: u.avg_size_sf for u in phys.unit_mix}
    prompt = f"""Using the shared architectural concept below, generate exactly {count}
structured image prompts for a commercial real estate appraisal photo package:
{shots}. Prefix every filename with "{name}_".

Shared architectural concept (reuse these details consistently in every prompt):
{json.dumps(concept, indent=2)}

Property details:
- Name: {prop.property_name}
- Type: {phys.building_type}
- Location: {prop.city}, {prop.state}
- Buildings: {phys.total_buildings}, {phys.stories} stories each
- Units: {phys.total_units}
- Year Built: {prop.year_built}
- Site: {phys.site_area_acres} acres
- Parking: {phys.parking_spaces} spaces
- Amenities: {', '.join(phys.amenities)}
- Unit sizes: {json.dumps(unit_sizes)}

Return a JSON array of exactly {count} objects. Each object must have:
- "filename": descriptive filename like "{name}_aerial_view.jpg"
- "description": short description for the image manifest
- "subject", "architecture_details", "landscaping", "lighting_atmosphere",
  "camera", "style_tags", "negative_prompt_suggestions": the structured sections
"""
    items: list[dict] = []
    for attempt in range(2):
        result = bedrock_client.invoke_model_json(
            prompt=prompt,
            model=PROMPT_MODEL,
            system_prompt=STRUCTURED_PROMPT_SYSTEM,
            max_tokens=12000,
        )
        items = [i for i in _prompt_items(result) if i.get("filename") and i.get("subject")]
        if len(items) >= count:
            return items[:count]
        logger.warning("Batch %s returned %d prompts (attempt %d); retrying", name, len(items), attempt + 1)
    raise RuntimeError(f"Krea 2 Turbo prompt batch '{name}' returned {len(items)} prompts; expected {count}")


def build_image_prompts(crosswalk: CrosswalkData) -> list[dict]:
    """Generate 30 structured, mutually consistent image prompts.

    One architectural concept is established first and threaded through three
    concurrent prompt batches, keeping every shot visually consistent while
    keeping each model call short.
    """
    concept = generate_architectural_concept(crosswalk)
    logger.info("Architectural concept: %s", json.dumps(concept))

    with ThreadPoolExecutor(max_workers=len(SHOT_BATCHES)) as pool:
        batches = list(pool.map(lambda b: _generate_batch(crosswalk, concept, b), SHOT_BATCHES))

    items: list[dict] = []
    seen: set[str] = set()
    for item in (i for batch in batches for i in batch):
        filename = str(item["filename"]).strip().replace(" ", "_")
        if not filename.lower().endswith((".jpg", ".jpeg")):
            filename += ".jpg"
        while filename in seen:
            filename = filename.replace(".jpg", "_2.jpg")
        seen.add(filename)
        item["filename"] = filename
        for key in ("architecture_details", "landscaping", "lighting_atmosphere", "camera",
                    "style_tags", "negative_prompt_suggestions"):
            item.setdefault(key, "")
        item["prompt"] = _assemble_structured_prompt(item)
        items.append(item)
    return items


def generate_single_image(prompt_data: dict, job_id: str) -> dict:
    """Generate a single image via fal.ai and upload to S3."""
    filename = prompt_data["filename"]
    image_prompt = prompt_data["prompt"]

    seed = int.from_bytes(
        hashlib.sha256(f"{job_id}:{filename}".encode("utf-8")).digest()[:8],
        "big",
    ) % (2**31)

    def render(attempt_seed: int):
        return fal_client.run(
            FAL_MODEL,
            arguments={
                "prompt": image_prompt,
                "seed": attempt_seed,
                "image_size": "landscape_4_3",
                "num_images": 1,
                "acceleration": "none",
                "enable_prompt_expansion": False,
                "enable_safety_checker": True,
                "output_format": "jpeg",
            },
        )

    try:
        output = render(seed)
        nsfw = (output or {}).get("has_nsfw_concepts", [])
        if nsfw and nsfw[0]:
            output = render(seed + 1)
            nsfw = (output or {}).get("has_nsfw_concepts", [])
            if nsfw and nsfw[0]:
                return {
                    "filename": filename,
                    "description": prompt_data.get("description", ""),
                    "status": "failed",
                    "reason": "safety_filter",
                    "error": "fal.ai safety filter flagged the render twice",
                }

        images = (output or {}).get("images", [])
        if not images:
            raise RuntimeError("fal.ai returned no images")
        image_url = images[0]["url"]
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()

        s3_key = s3_utils.write_bytes(
            job_id,
            f"images/{filename}",
            response.content,
            "image/jpeg",
        )
        return {
            "filename": filename,
            "description": prompt_data.get("description", ""),
            "s3_key": s3_key,
            "status": "success",
        }
    except Exception as exc:
        logger.error("Failed to generate image %s: %s", filename, exc)
        return {
            "filename": filename,
            "description": prompt_data.get("description", ""),
            "status": "failed",
            "reason": "render_error",
            "error": str(exc),
        }


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Generating images for job %s", job_id)

    fal_key = os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_TOKEN")
    if not fal_key:
        raise RuntimeError("FAL_KEY or FAL_AI_API_TOKEN is not configured")

    # Load crosswalk data
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    # Generate structured prompts (each batch validates and retries its own count)
    image_prompts = build_image_prompts(crosswalk)
    if len(image_prompts) != PROMPT_COUNT:
        raise RuntimeError(
            f"Krea 2 Turbo prompt generation returned {len(image_prompts)} prompts; expected {PROMPT_COUNT}"
        )
    logger.info("Generated %d image prompts", len(image_prompts))

    # Generate images in parallel
    manifest = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(generate_single_image, p, job_id): p
            for p in image_prompts
        }
        for future in as_completed(futures):
            result = future.result()
            manifest.append(result)

    # Save manifest
    s3_utils.write_json(job_id, "images/manifest.json", manifest)

    succeeded = sum(1 for m in manifest if m["status"] == "success")
    failed = sum(1 for m in manifest if m["status"] == "failed")
    failed_items = [m for m in manifest if m["status"] == "failed"]

    logger.info("Images complete: %d succeeded, %d failed", succeeded, failed)

    if succeeded == 0:
        sample_errors = [item.get("error", "Unknown error") for item in failed_items[:5]]
        raise RuntimeError(
            "Image generation failed for all prompts. "
            f"Failed count={failed}. Sample errors={sample_errors}"
        )

    status = "success" if failed == 0 else "partial_success"

    return {
        "status": status,
        "job_id": job_id,
        "images_generated": succeeded,
        "images_failed": failed,
        "failed_examples": failed_items[:5],
    }
