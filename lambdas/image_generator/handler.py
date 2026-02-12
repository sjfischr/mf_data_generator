"""Image Generator Lambda — generates property images via Replicate API."""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import replicate
import requests

from lambdas.shared import bedrock_client, s3_utils
from lambdas.shared.models import CrosswalkData

logger = logging.getLogger(__name__)

REPLICATE_MODEL = "prunaai/z-image-turbo"
MAX_WORKERS = 10


def build_image_prompts(crosswalk: CrosswalkData) -> list[dict]:
    """Use Haiku to generate 30 customized image prompts from the template."""
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical

    unit_sizes = {u.unit_type: u.avg_size_sf for u in phys.unit_mix}

    prompt = f"""Generate exactly 30 image prompts for a commercial real estate appraisal
photo package. Each prompt should describe a professional real estate photograph.

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

Return a JSON array of 30 objects, each with:
- "filename": descriptive filename like "aerial_view.jpg"
- "description": short description for the image manifest
- "prompt": detailed image generation prompt (2-3 sentences)

Categories: 6 exterior views, 6 amenity views, 12 unit interiors, 6 site/surroundings.
"""

    result = bedrock_client.invoke_model_json(
        prompt=prompt,
        model="haiku",
        system_prompt="You are a commercial real estate photographer planning a photo shoot. Return valid JSON only.",
    )

    if isinstance(result, dict) and "prompts" in result:
        return result["prompts"]
    if isinstance(result, list):
        return result
    return result


def generate_single_image(prompt_data: dict, job_id: str) -> dict:
    """Generate a single image via Replicate and upload to S3."""
    filename = prompt_data["filename"]
    image_prompt = prompt_data["prompt"]

    try:
        output = replicate.run(
            REPLICATE_MODEL,
            input={"prompt": image_prompt},
        )

        # Replicate returns a URL or list of URLs
        image_url = output[0] if isinstance(output, list) else output

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
    except Exception as e:
        logger.error("Failed to generate image %s: %s", filename, e)
        return {
            "filename": filename,
            "description": prompt_data.get("description", ""),
            "status": "failed",
            "error": str(e),
        }


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Generating images for job %s", job_id)

    # Load crosswalk data
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    # Generate customized prompts
    image_prompts = build_image_prompts(crosswalk)
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

    logger.info("Images complete: %d succeeded, %d failed", succeeded, failed)

    return {
        "status": "success",
        "job_id": job_id,
        "images_generated": succeeded,
        "images_failed": failed,
    }
