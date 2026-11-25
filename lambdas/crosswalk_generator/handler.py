"""Lambda: Crosswalk Generator.

THE MOST CRITICAL Lambda in the pipeline. Claude (Haiku role) proposes a
realistic draft of the property, market, sponsorship, third-party, and loan
inputs as JSON. A deterministic repair step recomputes every derived figure,
and the underwriting engine builds the operating history, loan sizing, and
credit metrics, so no downstream figure depends on LLM arithmetic.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap

from lambdas.shared import bedrock_client, s3_utils
from lambdas.shared.crosswalk_repair import repair_draft
from lambdas.shared.models import CrosswalkData, CrosswalkDraft
from lambdas.shared.underwriting import finalize_crosswalk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")


class CrosswalkGenerationError(RuntimeError):
    """Raised when a crosswalk cannot be produced or validated."""


SYSTEM_PROMPT = textwrap.dedent("""\
You are a commercial real estate data specialist generating complete, realistic
data for a synthetic multifamily appraisal and Fannie Mae DUS loan package.

Return ONE JSON object only - no prose, no markdown fences, no tool calls.
All dollar amounts are integers (no cents). Percentages are floats (5.25 = 5.25%).
Derived totals are recomputed downstream, so focus on realistic, internally
plausible line items for the specific city and property type. All people and
company names must be fictitious.
""")


def _build_crosswalk_schema_description() -> str:
    """Return the JSON contract the model must follow."""
    return textwrap.dedent("""\
    Top-level keys (use exactly these names):

    property_identification: {property_name, address, city, state (2-letter),
      zip (5 digits), county, legal_description, tax_parcel_numbers [str],
      current_owner, year_built (int), effective_age (int)}

    property_physical: {total_units, total_buildings, building_type
      ("garden-style"|"mid-rise"|"high-rise"), stories, gross_building_area_sf,
      site_area_acres (float), site_area_sf, parking_spaces, parking_ratio (float),
      unit_mix: [{unit_type, count, avg_size_sf, total_sf, bedrooms, bathrooms}],
      amenities [str]}  -- unit_mix counts must sum to total_units

    market_data: {submarket, submarket_vacancy_rate, submarket_rent_growth_yoy,
      comparable_properties: [>=4 {name, address, units, year_built, occupancy,
        avg_rent_per_unit}],
      comparable_sales: [>=3 {property, sale_date, sale_price, units,
        price_per_unit, cap_rate, noi}]}

    financial_data: {effective_date,
      occupancy: {physical_percent, occupied_units, vacant_units},
      market_rents_monthly: {unit_type: int}, in_place_rents_monthly: {unit_type: int},
      pro_forma_income: {potential_gross_rental_income, other_income,
        potential_gross_income, vacancy_collection_loss_percent,
        vacancy_collection_loss_amount, effective_gross_income},
      pro_forma_expenses: {real_estate_taxes, insurance, utilities,
        repairs_maintenance, payroll, management_fee_percent,
        management_fee_amount, marketing, administrative, replacement_reserves,
        total_operating_expenses, expense_per_unit},
      net_operating_income}

    valuation: {sales_comparison_approach: {indicated_value, value_per_unit, value_per_sf},
      income_approach: {stabilized_noi, cap_rate, indicated_value},
      final_value_conclusion: {market_value, value_per_unit, value_per_sf, effective_date}}

    operating_year1: trailing-12 ACTUALS for the most recent year, all POSITIVE
      integers (deductions are positive amounts that get subtracted):
      {gpr, loss_gain_to_lease, vacancy, concessions, bad_debt, non_revenue_units,
       laundry_vending, parking, commercial, other_income, real_estate_taxes,
       insurance, utilities, water_sewer, repairs_maintenance, payroll_benefits,
       general_administrative, marketing, professional_fees, management_fee,
       ground_rent, other_expenses, replacement_reserves}
      Year 1 EGI should be within 10% of the pro forma EGI.

    financing_inputs: {loan_purpose ("Acquisition"|"Refinance"),
      tier ("Tier 2"|"Tier 3"|"Tier 4"), note_rate, term_months (60|84|120|144|180),
      interest_only_months, prepayment_terms, purchase_price}

    sponsorship: {borrower_name, borrower_type,
      key_principals: [{name, role, years_experience, units_owned, net_worth, liquidity}],
      guarantor, property_management: {name, management_fee_percent, on_site_staffing}}

    third_party_reports: {
      appraisal: {firm},
      property_condition_assessment: {firm, immediate_repairs},
      environmental_site_assessment: {firm, finding},
      seismic_applicable (bool), zoning_status}
    """)


def _build_prompt(user_input: dict, job_id: str) -> str:
    """Assemble the full user prompt."""
    return textwrap.dedent(f"""\
    Generate realistic crosswalk data for a synthetic multifamily appraisal and
    DUS loan package for this property:

    Property Name: {user_input.get('property_name') or 'Generate an appropriate professional property name'}
    Property Address: {user_input['address']}
    City: {user_input['city']}
    State: {user_input['state']}
    Total Units: {user_input['units']}
    Year Built: {user_input['year_built']}
    Property Type: {user_input['property_type']}

    {_build_crosswalk_schema_description()}

    Use current market rents, expenses, and cap rates for the
    {user_input['city']}, {user_input['state']} market.
    Return the JSON object only.
    """)


def _parse_agent_json(result) -> dict:
    """Extract a JSON object from a model response (dict, text, or fenced text)."""
    if isinstance(result, dict):
        return result
    raw = str(result).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    return json.loads(raw)


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


def generate_crosswalk(user_input: dict, job_id: str) -> CrosswalkData:
    """Draft with the model, repair deterministically, and finalize underwriting."""
    raw = bedrock_client.invoke_model_json(
        prompt=_build_prompt(user_input, job_id),
        model="haiku",
        system_prompt=SYSTEM_PROMPT,
        max_tokens=16000,
    )
    repaired = repair_draft(_parse_agent_json(raw), user_input, job_id)
    draft = CrosswalkDraft.model_validate(repaired)
    crosswalk = finalize_crosswalk(draft)
    crosswalk.job_id = job_id
    return crosswalk


def handler(event, context):
    """AWS Lambda entry point. Expects ``{"job_id": "<uuid>"}``."""
    job_id = event["job_id"]
    logger.info("Crosswalk generator started for job %s", job_id)

    user_input = s3_utils.read_json(job_id, "input.json")
    logger.info("User input: %s", json.dumps(user_input))

    last_error: Exception | None = None
    crosswalk = None
    for attempt in range(1, 3):
        try:
            crosswalk = generate_crosswalk(user_input, job_id)
            break
        except Exception as exc:  # retry once on malformed model output
            last_error = exc
            logger.exception("Crosswalk attempt %d failed: %s", attempt, exc)
    if crosswalk is None:
        raise CrosswalkGenerationError(f"Crosswalk generation failed: {last_error}") from last_error

    warnings = _validate_crosswalk(crosswalk)
    if warnings:
        logger.warning("Crosswalk warnings: %s", "; ".join(warnings))

    s3_key = s3_utils.write_json(job_id, "crosswalk-data.json", crosswalk.model_dump())
    logger.info("Saved crosswalk data to %s", s3_key)

    return {
        "status": "success",
        "job_id": job_id,
        "s3_key": s3_key,
        "warnings": warnings,
    }
