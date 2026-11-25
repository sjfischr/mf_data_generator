"""Build the exact, allowed fact sheet for lender-narrative prose."""

from __future__ import annotations

from lambdas.shared.models import CrosswalkData


def fmt_dollar(value: int | float) -> str:
    return f"${round(value):,}"


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def build_fact_sheet(crosswalk: CrosswalkData) -> dict[str, str]:
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical
    fin = crosswalk.financial_data
    financing = crosswalk.financing
    uw = (
        crosswalk.operating_history.underwritten
        if crosswalk.operating_history
        else None
    )

    facts: dict[str, str] = {
        "property_name": prop.property_name,
        "address": ", ".join(
            [prop.address, prop.city, prop.state, prop.zip]
        ),
        "units": str(phys.total_units),
        "occupancy": fmt_pct(fin.occupancy.physical_percent),
        "appraised_value": fmt_dollar(
            crosswalk.valuation.final_value_conclusion.market_value
        ),
    }

    if financing:
        facts.update(
            {
                "loan_amount": fmt_dollar(financing.loan_amount),
                "loan_per_unit": fmt_dollar(financing.loan_per_unit),
                "note_rate": fmt_pct(financing.note_rate),
                "underwriting_rate": fmt_pct(financing.underwriting_rate_basis),
                "underwriting_value": fmt_dollar(financing.underwriting_value),
                "ltv_underwriting": fmt_pct(financing.ltv_underwriting_value),
                "ltv_appraised": fmt_pct(financing.ltv_appraised_value),
                "underwritten_dscr": f"{financing.underwritten_dscr:.2f}x",
                "actual_dscr": f"{financing.actual_dscr:.2f}x",
                "debt_yield": fmt_pct(financing.debt_yield),
                "breakeven": fmt_pct(financing.breakeven_occupancy),
                "binding_constraint": financing.binding_constraint,
            }
        )
    if uw:
        facts.update(
            {
                "uw_ncf": fmt_dollar(uw.ncf),
                "uw_noi": fmt_dollar(uw.noi),
                "uw_egi": fmt_dollar(uw.effective_gross_income),
                "replacement_reserve_per_unit": fmt_dollar(
                    uw.replacement_reserves / phys.total_units
                ),
            }
        )
    return facts
