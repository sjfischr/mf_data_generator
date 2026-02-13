"""Lambda: Crosswalk Generator — Strands Agentic Version.

THE MOST CRITICAL Lambda in the pipeline.  Uses a Strands agent with
calculator/arithmetic tools to generate the CrosswalkData JSON.  The agent
can verify its own math via tools before producing the final output.  Strands'
structured_output_model auto-validates against the Pydantic schema and retries
on validation failure.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap

from strands import Agent
from strands.models.bedrock import BedrockModel

from lambdas.shared.models import CrosswalkData
from lambdas.shared import s3_utils
from lambdas.shared.agent_tools import (
    compute_financial_metrics,
    compute_valuation_metrics,
    compute_price_per_unit,
    compute_unit_mix_total_sf,
    verify_sum,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = textwrap.dedent("""\
You are a commercial real estate data specialist generating complete, realistic
property data for a multifamily apartment appraisal.

CRITICAL WORKFLOW:
1. First, decide on reasonable market values for all line items.
2. BEFORE assembling the final JSON, use your arithmetic tools to compute
   every derived total:
   - Use compute_financial_metrics to get PGI, EGI, total_expenses, NOI
   - Use compute_valuation_metrics to get indicated_value, value_per_unit, value_per_sf
   - Use compute_price_per_unit for each comparable sale
   - Use compute_unit_mix_total_sf for each unit mix row
   - Use verify_sum to double-check any totals
3. Use the EXACT computed values from the tools in your final output.
   Never estimate or round differently than what the tools return.

All dollar amounts are integers (no cents). Percentages are floats (e.g. 5.25).
Ensure data consistency across all sections and every mathematical relationship holds.
""")


def _build_crosswalk_schema_description() -> str:
    """Return a human-readable description of every field in CrosswalkData."""
    return textwrap.dedent("""\
    Produce a single JSON object matching this exact schema.

    Top-level keys:
      job_id             - use the provided value exactly
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
        unit_type (str), count (int), avg_size_sf (int),
        total_sf (int = count * avg_size_sf), bedrooms (int), bathrooms (int)
        USE compute_unit_mix_total_sf for each row!
      amenities (list of strings)
      RULE: sum of unit_mix[].count MUST equal total_units

    market_data:
      submarket (str), submarket_vacancy_rate (float 0-100),
      submarket_rent_growth_yoy (float),
      comparable_properties (list, min 4):
        name, address, units (int), year_built (int), occupancy (float 0-100),
        avg_rent_per_unit (float)
      comparable_sales (list, min 3):
        property (str), sale_date (str), sale_price (int), units (int),
        price_per_unit (int), cap_rate (float 0-100), noi (int)
        USE compute_price_per_unit for each sale!

    financial_data:
      effective_date (str ISO date),
      occupancy:
        physical_percent (float 0-100), occupied_units (int), vacant_units (int)
        RULE: occupied_units + vacant_units = total_units
      market_rents_monthly (dict unit_type -> int)
      in_place_rents_monthly (dict unit_type -> int)
      pro_forma_income:
        potential_gross_rental_income (int), other_income (int),
        potential_gross_income (int), vacancy_collection_loss_percent (float),
        vacancy_collection_loss_amount (int), effective_gross_income (int)
        USE compute_financial_metrics to derive PGI and EGI!
      pro_forma_expenses:
        real_estate_taxes, insurance, utilities, repairs_maintenance,
        payroll, management_fee_percent (float), management_fee_amount (int),
        marketing, administrative, replacement_reserves,
        total_operating_expenses (int), expense_per_unit (int)
        USE compute_financial_metrics to derive total_operating_expenses!
      net_operating_income (int)
        USE the NOI value from compute_financial_metrics!
      historical_t12 (dict year_label -> object):
        rental_income (int), other_income (int), vacancy_loss (int, negative),
        effective_gross_income (int), operating_expenses (int),
        net_operating_income (int)
        Provide 3 years ("Year 1", "Year 2", "Year 3")

    valuation:
      sales_comparison_approach:
        indicated_value (int), value_per_unit (int), value_per_sf (float)
      income_approach:
        stabilized_noi (int), cap_rate (float 0-100), indicated_value (int)
        USE compute_valuation_metrics for this!
      final_value_conclusion:
        market_value (int), value_per_unit (int), value_per_sf (float),
        effective_date (str)
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

    IMPORTANT: Before producing the final JSON, you MUST use the arithmetic
    tools to compute every derived value. Do NOT guess at totals.

    Steps:
    1. Decide on realistic line-item values for the {user_input['city']}, {user_input['state']} market.
    2. Call compute_unit_mix_total_sf for each unit type.
    3. Call compute_price_per_unit for each comparable sale.
    4. Call compute_financial_metrics with all income/expense line items.
    5. Call compute_valuation_metrics with the NOI and your chosen cap rate.
    6. Use verify_sum to confirm unit_mix counts sum to total_units.
    7. Assemble the final JSON using ONLY the values returned by the tools.

    Generate at least 4 comparable rental properties and at least 3
    comparable sales.  Use current market cap rates for that MSA.
    """)


def _validate_crosswalk(crosswalk: CrosswalkData) -> list[str]:
    """Run additional business-logic validations beyond Pydantic."""
    warnings: list[str] = []

    if not crosswalk.validate_cap_rate():
        noi = crosswalk.valuation.income_approach.stabilized_noi
        val = crosswalk.valuation.income_approach.indicated_value
        expected = round((noi / val) * 100, 2)
        actual = crosswalk.valuation.income_approach.cap_rate
        warnings.append(
            f"Cap rate mismatch: stated {actual}% vs calculated {expected}%"
        )

    if not crosswalk.validate_value_per_unit():
        mv = crosswalk.valuation.final_value_conclusion.market_value
        units = crosswalk.property_physical.total_units
        expected = round(mv / units)
        actual = crosswalk.valuation.final_value_conclusion.value_per_unit
        warnings.append(
            f"Value per unit mismatch: stated {actual} vs calculated {expected}"
        )

    if not crosswalk.validate_occupancy_units():
        occ = crosswalk.financial_data.occupancy
        total = crosswalk.property_physical.total_units
        warnings.append(
            f"Occupancy units mismatch: occupied({occ.occupied_units}) + "
            f"vacant({occ.vacant_units}) != total({total})"
        )

    cap = crosswalk.valuation.income_approach.cap_rate
    if cap < 3.0 or cap > 12.0:
        warnings.append(f"Cap rate {cap}% outside typical 3-12% range")

    vpu = crosswalk.valuation.final_value_conclusion.value_per_unit
    if vpu < 30_000 or vpu > 500_000:
        warnings.append(f"Value per unit ${vpu:,} outside typical range")

    occ_pct = crosswalk.financial_data.occupancy.physical_percent
    if occ_pct < 60.0:
        warnings.append(f"Occupancy {occ_pct}% unusually low")

    return warnings


def _create_crosswalk_agent() -> Agent:
    """Create the Strands agent for crosswalk generation."""
    model = BedrockModel(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name=REGION,
        max_tokens=8192,
        temperature=0.3,
    )

    return Agent(
        name="crosswalk_generator",
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            compute_financial_metrics,
            compute_valuation_metrics,
            compute_price_per_unit,
            compute_unit_mix_total_sf,
            verify_sum,
        ],
    )


def handler(event, context):
    """AWS Lambda entry point.

    Expects ``{"job_id": "<uuid>"}``.  Reads ``input.json`` from S3,
    generates crosswalk data via a Strands agent backed by Bedrock Haiku
    with arithmetic tools, validates with Pydantic, and writes
    ``crosswalk-data.json`` back to S3.
    """
    job_id = event["job_id"]
    logger.info("Crosswalk generator (agentic) started for job %s", job_id)

    # ------------------------------------------------------------------
    # 1. Read user input
    # ------------------------------------------------------------------
    user_input = s3_utils.read_json(job_id, "input.json")
    logger.info("User input: %s", json.dumps(user_input))

    # ------------------------------------------------------------------
    # 2. Generate crosswalk data via Strands agent
    # ------------------------------------------------------------------
    prompt = _build_prompt(user_input, job_id)
    agent = _create_crosswalk_agent()

    try:
        # Strands structured_output_model handles:
        #   - Pydantic schema → tool spec conversion
        #   - JSON extraction from agent response
        #   - Pydantic validation with auto-retry on failure
        result = agent(prompt, structured_output_model=CrosswalkData)
        crosswalk = CrosswalkData.model_validate(
            result.structured_output.model_dump()  # type: ignore[union-attr]
        )

        # Force the correct job_id in case the model changed it
        crosswalk.job_id = job_id

        logger.info("Crosswalk generated and validated successfully")

    except Exception as exc:
        logger.error("Crosswalk generation failed: %s", exc)
        return {
            "status": "error",
            "job_id": job_id,
            "error": f"Crosswalk generation failed: {exc}",
        }

    # ------------------------------------------------------------------
    # 3. Business-logic warnings (non-fatal)
    # ------------------------------------------------------------------
    warnings = _validate_crosswalk(crosswalk)
    if warnings:
        logger.warning("Crosswalk warnings: %s", "; ".join(warnings))

    # ------------------------------------------------------------------
    # 4. Persist to S3
    # ------------------------------------------------------------------
    crosswalk_dict = crosswalk.model_dump()
    s3_key = s3_utils.write_json(job_id, "crosswalk-data.json", crosswalk_dict)
    logger.info("Saved crosswalk data to %s", s3_key)

    return {
        "status": "success",
        "job_id": job_id,
        "s3_key": s3_key,
        "warnings": warnings,
    }
