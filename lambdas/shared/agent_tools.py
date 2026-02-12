"""Custom Strands tools for the appraisal generation pipeline.

These tools give agents access to S3 data and arithmetic verification,
turning what was procedural Lambda code into agentic capabilities.
"""

from __future__ import annotations

import json
import logging

from strands import tool

from lambdas.shared import s3_utils

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# S3 data tools
# ---------------------------------------------------------------------------

@tool
def read_crosswalk(job_id: str) -> str:
    """Read the crosswalk-data.json for a job from S3.

    Args:
        job_id: The UUID job identifier.

    Returns:
        The full crosswalk JSON as a string.
    """
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    return json.dumps(data, indent=2)


@tool
def read_user_input(job_id: str) -> str:
    """Read the user input.json for a job from S3.

    Args:
        job_id: The UUID job identifier.

    Returns:
        The user input JSON as a string.
    """
    data = s3_utils.read_json(job_id, "input.json")
    return json.dumps(data, indent=2)


@tool
def save_section_markdown(job_id: str, section_name: str, content: str) -> str:
    """Save generated markdown content for a report section to S3.

    Args:
        job_id: The UUID job identifier.
        section_name: The section slug (e.g. 'section_01_introduction').
        content: The markdown content to save.

    Returns:
        The S3 key where the file was saved.
    """
    filename = f"sections/{section_name}.md"
    key = s3_utils.write_text(job_id, filename, content)
    logger.info("Saved section %s to %s", section_name, key)
    return key


@tool
def save_crosswalk_json(job_id: str, crosswalk_json: str) -> str:
    """Save validated crosswalk data to S3.

    Args:
        job_id: The UUID job identifier.
        crosswalk_json: The complete crosswalk JSON string.

    Returns:
        The S3 key where the file was saved.
    """
    data = json.loads(crosswalk_json)
    key = s3_utils.write_json(job_id, "crosswalk-data.json", data)
    logger.info("Saved crosswalk data to %s", key)
    return key


# ---------------------------------------------------------------------------
# Arithmetic verification tools
# ---------------------------------------------------------------------------

@tool
def verify_sum(values: list[int], expected_total: int) -> str:
    """Verify that a list of integers sums to an expected total.

    Use this to double-check financial calculations before finalizing data.

    Args:
        values: List of integer values to sum.
        expected_total: The expected total.

    Returns:
        A string indicating whether the sum matches, and what the actual sum is.
    """
    actual = sum(values)
    if actual == expected_total:
        return f"CORRECT: sum({values}) = {actual} matches expected {expected_total}"
    else:
        return (
            f"MISMATCH: sum({values}) = {actual}, but expected {expected_total}. "
            f"Difference: {actual - expected_total}"
        )


@tool
def compute_financial_metrics(
    rental_income: int,
    other_income: int,
    vacancy_loss_amount: int,
    real_estate_taxes: int,
    insurance: int,
    utilities: int,
    repairs_maintenance: int,
    payroll: int,
    management_fee_amount: int,
    marketing: int,
    administrative: int,
    replacement_reserves: int,
) -> str:
    """Compute all derived financial metrics from line items.

    Use this tool to calculate PGI, EGI, total expenses, and NOI
    from the individual line items, ensuring perfect arithmetic.

    Args:
        rental_income: Annual potential gross rental income.
        other_income: Annual other income (laundry, parking, etc.).
        vacancy_loss_amount: Dollar amount of vacancy/collection loss (positive number).
        real_estate_taxes: Annual real estate tax expense.
        insurance: Annual insurance expense.
        utilities: Annual utilities expense.
        repairs_maintenance: Annual repairs and maintenance expense.
        payroll: Annual payroll expense.
        management_fee_amount: Annual management fee dollar amount.
        marketing: Annual marketing expense.
        administrative: Annual administrative expense.
        replacement_reserves: Annual replacement reserves.

    Returns:
        JSON with all computed totals: PGI, EGI, total_expenses, NOI.
    """
    pgi = rental_income + other_income
    egi = pgi - vacancy_loss_amount
    total_expenses = (
        real_estate_taxes + insurance + utilities + repairs_maintenance
        + payroll + management_fee_amount + marketing + administrative
        + replacement_reserves
    )
    noi = egi - total_expenses

    result = {
        "potential_gross_income": pgi,
        "effective_gross_income": egi,
        "total_operating_expenses": total_expenses,
        "net_operating_income": noi,
        "breakdown": {
            "rental_income": rental_income,
            "other_income": other_income,
            "pgi_formula": f"{rental_income} + {other_income} = {pgi}",
            "vacancy_loss_amount": vacancy_loss_amount,
            "egi_formula": f"{pgi} - {vacancy_loss_amount} = {egi}",
            "expense_line_items": [
                real_estate_taxes, insurance, utilities, repairs_maintenance,
                payroll, management_fee_amount, marketing, administrative,
                replacement_reserves,
            ],
            "expenses_formula": (
                f"{real_estate_taxes} + {insurance} + {utilities} + "
                f"{repairs_maintenance} + {payroll} + {management_fee_amount} + "
                f"{marketing} + {administrative} + {replacement_reserves} = "
                f"{total_expenses}"
            ),
            "noi_formula": f"{egi} - {total_expenses} = {noi}",
        },
    }
    return json.dumps(result, indent=2)


@tool
def compute_valuation_metrics(
    noi: int,
    cap_rate_percent: float,
    total_units: int,
    gross_building_area_sf: int,
) -> str:
    """Compute valuation metrics from NOI and cap rate.

    Args:
        noi: Net operating income (annual).
        cap_rate_percent: Capitalization rate as a percentage (e.g. 5.5 means 5.5%).
        total_units: Total number of units.
        gross_building_area_sf: Total gross building area in square feet.

    Returns:
        JSON with indicated_value, value_per_unit, value_per_sf.
    """
    indicated_value = round(noi / (cap_rate_percent / 100))
    value_per_unit = round(indicated_value / total_units)
    value_per_sf = round(indicated_value / gross_building_area_sf, 2)

    result = {
        "indicated_value": indicated_value,
        "value_per_unit": value_per_unit,
        "value_per_sf": value_per_sf,
        "formulas": {
            "value": f"{noi} / ({cap_rate_percent}% / 100) = {indicated_value}",
            "per_unit": f"{indicated_value} / {total_units} = {value_per_unit}",
            "per_sf": f"{indicated_value} / {gross_building_area_sf} = {value_per_sf}",
        },
    }
    return json.dumps(result, indent=2)


@tool
def compute_price_per_unit(sale_price: int, units: int) -> str:
    """Compute price per unit from a sale price.

    Args:
        sale_price: Total sale price.
        units: Number of units.

    Returns:
        The computed price per unit (rounded).
    """
    ppu = round(sale_price / units)
    return json.dumps({
        "price_per_unit": ppu,
        "formula": f"{sale_price} / {units} = {ppu}",
    })


@tool
def compute_unit_mix_total_sf(count: int, avg_size_sf: int) -> str:
    """Compute total square footage for a unit mix row.

    Args:
        count: Number of units of this type.
        avg_size_sf: Average size in square feet.

    Returns:
        The computed total SF.
    """
    total = count * avg_size_sf
    return json.dumps({
        "total_sf": total,
        "formula": f"{count} * {avg_size_sf} = {total}",
    })
