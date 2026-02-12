"""Lambda: Crosswalk Generator.

THE MOST CRITICAL Lambda in the pipeline.  It reads the user input,
invokes Haiku to produce the full CrosswalkData JSON, validates the
result with Pydantic, runs additional sanity checks, and persists
the authoritative crosswalk-data.json to S3.
"""

from __future__ import annotations

import json
import logging
import textwrap

from pydantic import ValidationError

from lambdas.shared.models import CrosswalkData, UserInput
from lambdas.shared import bedrock_client, s3_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SYSTEM_PROMPT = (
    "You are a commercial real estate data specialist. Generate complete, "
    "realistic property data for a multifamily apartment property. All "
    "calculations must be accurate. Use market-appropriate values for the "
    "location. Ensure data consistency across all sections."
)

MAX_RETRIES = 3


def _build_crosswalk_schema_description() -> str:
    """Return a human-readable description of every field in CrosswalkData.

    This is embedded in the prompt so the model knows exactly what to produce.
    """
    return textwrap.dedent("""\
    Produce a single JSON object matching this exact schema.  All dollar
    amounts are integers (no cents).  Percentages are floats (e.g. 5.25
    means 5.25%).  Ensure every mathematical relationship holds.

    Top-level keys:
      job_id             - leave as the provided value
      generated_at       - ISO-8601 UTC timestamp string

    property_identification:
      property_name, address, city, state (2-letter), zip (5 or 9 digit),
      county, legal_description, tax_parcel_numbers (list of strings),
      current_owner, year_built (int), effective_age (int)

    property_physical:
      total_units (int), total_buildings (int),
      building_type ("garden-style" | "mid-rise" | "high-rise"),
      stories (int), gross_building_area_sf (int),
      site_area_acres (float), site_area_sf (int),
      parking_spaces (int), parking_ratio (float),
      unit_mix (list of objects):
        unit_type (str e.g. "1BR/1BA"), count (int), avg_size_sf (int),
        total_sf (int = count * avg_size_sf), bedrooms (int), bathrooms (int)
      amenities (list of strings)

      RULE: sum of unit_mix[].count MUST equal total_units

    market_data:
      submarket (str), submarket_vacancy_rate (float 0-100),
      submarket_rent_growth_yoy (float),
      comparable_properties (list, min 1):
        name, address, units (int), year_built (int), occupancy (float 0-100),
        avg_rent_per_unit (float)
      comparable_sales (list, min 1):
        property (str), sale_date (str), sale_price (int), units (int),
        price_per_unit (int = sale_price / units, rounded),
        cap_rate (float 0-100), noi (int)

    financial_data:
      effective_date (str ISO date),
      occupancy:
        physical_percent (float 0-100), occupied_units (int), vacant_units (int)
        RULE: occupied_units + vacant_units = total_units
      market_rents_monthly (dict unit_type -> int)
      in_place_rents_monthly (dict unit_type -> int)
      pro_forma_income:
        potential_gross_rental_income (int), other_income (int),
        potential_gross_income (int = rental + other),
        vacancy_collection_loss_percent (float 0-100),
        vacancy_collection_loss_amount (int),
        effective_gross_income (int = PGI - vacancy_loss)
      pro_forma_expenses:
        real_estate_taxes, insurance, utilities, repairs_maintenance,
        payroll, management_fee_percent (float), management_fee_amount (int),
        marketing, administrative, replacement_reserves,
        total_operating_expenses (int = sum of all line items above),
        expense_per_unit (int)
      net_operating_income (int = EGI - total_operating_expenses)
      historical_t12 (dict year_label -> object):
        rental_income (int), other_income (int), vacancy_loss (int, negative),
        effective_gross_income (int = rental + other + vacancy_loss),
        operating_expenses (int),
        net_operating_income (int = EGI - operating_expenses)
        Provide 3 years of history (e.g. "Year 1", "Year 2", "Year 3")

    valuation:
      sales_comparison_approach:
        indicated_value (int), value_per_unit (int), value_per_sf (float)
      income_approach:
        stabilized_noi (int), cap_rate (float 0-100),
        indicated_value (int)
        RULE: cap_rate approx = (stabilized_noi / indicated_value) * 100
      final_value_conclusion:
        market_value (int), value_per_unit (int = market_value / total_units),
        value_per_sf (float), effective_date (str)

    Double-check ALL math before responding.
    """)


def _build_prompt(user_input: dict, job_id: str) -> str:
    """Assemble the full user prompt."""
    schema = _build_crosswalk_schema_description()

    return textwrap.dedent(f"""\
    Generate complete, realistic crosswalk data for a synthetic multifamily
    appraisal report based on the following user input:

    Property Name: {user_input.get('property_name') or 'Generate an appropriate professional property name'}
    Property Address: {user_input['address']}
    City: {user_input['city']}
    State: {user_input['state']}
    Total Units: {user_input['units']}
    Year Built: {user_input['year_built']}
    Property Type: {user_input['property_type']}

    Use this job_id exactly: {job_id}

    ---
    SCHEMA REQUIREMENTS:
    {schema}
    ---

    Generate at least 4 comparable rental properties and at least 3
    comparable sales.  Make the data realistic for the {user_input['city']},
    {user_input['state']} market.  Use current market cap rates for that MSA.

    Respond with ONLY the JSON object -- no commentary, no markdown fences.
    """)


def _validate_crosswalk(crosswalk: CrosswalkData) -> list[str]:
    """Run additional business-logic validations beyond Pydantic.

    Returns a list of warning messages (empty = all good).
    """
    warnings: list[str] = []

    # Cap rate sanity
    if not crosswalk.validate_cap_rate():
        noi = crosswalk.valuation.income_approach.stabilized_noi
        val = crosswalk.valuation.income_approach.indicated_value
        expected = round((noi / val) * 100, 2)
        actual = crosswalk.valuation.income_approach.cap_rate
        warnings.append(
            f"Cap rate mismatch: stated {actual}% vs calculated {expected}%"
        )

    # Value per unit
    if not crosswalk.validate_value_per_unit():
        mv = crosswalk.valuation.final_value_conclusion.market_value
        units = crosswalk.property_physical.total_units
        expected = round(mv / units)
        actual = crosswalk.valuation.final_value_conclusion.value_per_unit
        warnings.append(
            f"Value per unit mismatch: stated {actual} vs calculated {expected}"
        )

    # Occupancy consistency
    if not crosswalk.validate_occupancy_units():
        occ = crosswalk.financial_data.occupancy
        total = crosswalk.property_physical.total_units
        warnings.append(
            f"Occupancy units mismatch: occupied({occ.occupied_units}) + "
            f"vacant({occ.vacant_units}) != total({total})"
        )

    # Cap rate reasonableness (typical multifamily 3%-12%)
    cap = crosswalk.valuation.income_approach.cap_rate
    if cap < 3.0 or cap > 12.0:
        warnings.append(f"Cap rate {cap}% outside typical 3-12% range")

    # Value per unit reasonableness ($30k-$500k for multifamily)
    vpu = crosswalk.valuation.final_value_conclusion.value_per_unit
    if vpu < 30_000 or vpu > 500_000:
        warnings.append(f"Value per unit ${vpu:,} outside typical range")

    # Occupancy reasonableness (>60%)
    occ_pct = crosswalk.financial_data.occupancy.physical_percent
    if occ_pct < 60.0:
        warnings.append(f"Occupancy {occ_pct}% unusually low")

    return warnings


def handler(event, context):
    """AWS Lambda entry point.

    Expects ``{"job_id": "<uuid>"}``.  Reads ``input.json`` from S3,
    generates crosswalk data via Bedrock Haiku, validates it, and writes
    ``crosswalk-data.json`` back to S3.
    """
    job_id = event["job_id"]
    logger.info("Crosswalk generator started for job %s", job_id)

    # ------------------------------------------------------------------
    # 1. Read user input
    # ------------------------------------------------------------------
    user_input = s3_utils.read_json(job_id, "input.json")
    logger.info("User input: %s", json.dumps(user_input))

    # ------------------------------------------------------------------
    # 2. Generate crosswalk data (with retries)
    # ------------------------------------------------------------------
    prompt = _build_prompt(user_input, job_id)

    last_error: Exception | None = None
    crosswalk: CrosswalkData | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Generation attempt %d/%d", attempt, MAX_RETRIES)
        try:
            raw_text = bedrock_client.invoke_model(
                prompt=prompt,
                model="haiku",
                system_prompt=SYSTEM_PROMPT,
                max_tokens=8192,
                temperature=0.3,
            )

            # Strip markdown fences if the model wrapped the JSON
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                lines = lines[1:]  # remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # remove closing fence
                raw_text = "\n".join(lines)

            data = json.loads(raw_text)

            # Force the correct job_id in case the model changed it
            data["job_id"] = job_id

            # ----------------------------------------------------------
            # 3. Pydantic validation
            # ----------------------------------------------------------
            crosswalk = CrosswalkData.model_validate(data)

            # ----------------------------------------------------------
            # 4. Additional business validations
            # ----------------------------------------------------------
            warnings = _validate_crosswalk(crosswalk)
            if warnings:
                logger.warning(
                    "Crosswalk warnings (attempt %d): %s",
                    attempt,
                    "; ".join(warnings),
                )
                # Warnings are non-fatal -- we accept the data but log them.
                # Only hard Pydantic failures trigger a retry.

            logger.info("Crosswalk validated successfully on attempt %d", attempt)
            break  # success

        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning("Attempt %d failed: %s", attempt, exc)
            # Append feedback to the prompt for the next attempt
            if isinstance(exc, ValidationError):
                prompt += (
                    f"\n\nYour previous response had validation errors:\n"
                    f"{exc}\n\nPlease fix these issues and try again."
                )
            else:
                prompt += (
                    "\n\nYour previous response was not valid JSON. "
                    "Return ONLY a valid JSON object with no other text."
                )

    if crosswalk is None:
        logger.error("All %d attempts failed. Last error: %s", MAX_RETRIES, last_error)
        return {
            "status": "error",
            "job_id": job_id,
            "error": f"Crosswalk generation failed after {MAX_RETRIES} attempts: {last_error}",
        }

    # ------------------------------------------------------------------
    # 5. Persist to S3
    # ------------------------------------------------------------------
    crosswalk_dict = crosswalk.model_dump()
    s3_key = s3_utils.write_json(job_id, "crosswalk-data.json", crosswalk_dict)
    logger.info("Saved crosswalk data to %s", s3_key)

    return {
        "status": "success",
        "job_id": job_id,
        "s3_key": s3_key,
        "warnings": _validate_crosswalk(crosswalk),
    }
