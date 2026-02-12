"""Lucky Generator Lambda.

Generates believable multifamily starter data using Claude Haiku for
an "I'm Feeling Lucky" input flow.
"""

from __future__ import annotations

import json
import logging

from lambdas.shared import bedrock_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ALLOWED_PROPERTY_TYPES = {"garden-style", "mid-rise", "high-rise"}


def _api_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }


def _normalize(payload: dict) -> dict:
    units = int(payload.get("units", 120))
    units = max(10, min(500, units))

    year_built = int(payload.get("year_built", 2005))
    year_built = max(1950, min(2026, year_built))

    property_type = str(payload.get("property_type", "garden-style")).strip()
    if property_type not in ALLOWED_PROPERTY_TYPES:
        property_type = "garden-style"

    return {
        "property_name": str(payload.get("property_name", "Smaug Residences")).strip(),
        "address": str(payload.get("address", "1000 Ember Lane")).strip(),
        "city": str(payload.get("city", "Austin")).strip(),
        "state": str(payload.get("state", "TX")).strip()[:2].upper(),
        "units": units,
        "year_built": year_built,
        "property_type": property_type,
    }


def handler(event, context):
    http_method = event.get("httpMethod", "POST")
    if http_method == "OPTIONS":
        return _api_response(200, {"ok": True})

    prompt = (
        "Generate one realistic multifamily property starter record in the US. "
        "Return JSON with keys: property_name, address, city, state, units, year_built, property_type. "
        "Constraints: units integer 10-500, year_built integer 1950-2026, "
        "property_type one of garden-style|mid-rise|high-rise, state is 2-letter code."
    )

    try:
        raw = bedrock_client.invoke_model_json(
            prompt=prompt,
            model="haiku",
            system_prompt=(
                "You generate concise, believable multifamily property seed data. "
                "Return valid JSON only."
            ),
            max_tokens=512,
        )

        if isinstance(raw, dict) and "property" in raw and isinstance(raw["property"], dict):
            raw = raw["property"]

        payload = _normalize(raw if isinstance(raw, dict) else {})
        return _api_response(200, payload)

    except Exception as exc:
        logger.exception("Lucky generation failed: %s", exc)
        fallback = {
            "property_name": "Smaug Court Apartments",
            "address": "7429 Copper Peak Drive",
            "city": "Phoenix",
            "state": "AZ",
            "units": 164,
            "year_built": 2008,
            "property_type": "garden-style",
        }
        return _api_response(200, fallback)
