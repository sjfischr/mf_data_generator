"""Lambda: Section 07 -- Income Capitalization Approach.

CRITICAL SECTION.  Generates the full income capitalization approach
including reconstructed operating statement (pro forma), cap rate
analysis, and direct capitalization to value.  Uses Opus for highest
quality.  Target: 8-10 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IncomeCapitalizationGenerator(SectionGenerator):
    """Generate Section 07 -- Income Capitalization Approach."""

    def get_section_name(self) -> str:
        return "section_07_income_capitalization"

    def get_model_name(self) -> str:
        return "opus"

    def get_tools(self) -> list:
        from lambdas.shared.agent_tools import (
            verify_sum,
            compute_financial_metrics,
            compute_valuation_metrics,
        )
        return [verify_sum, compute_financial_metrics, compute_valuation_metrics]

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You are a recognized expert "
            "in income capitalization analysis, pro forma construction, "
            "capitalization rate derivation, and direct capitalization. "
            "Every financial figure must be internally consistent and "
            "mathematically verifiable. All income and expense items must "
            "reconcile to the stated NOI. Write in formal, professional "
            "appraisal language. Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        mkt = crosswalk.market_data
        fin = crosswalk.financial_data
        val = crosswalk.valuation
        income = fin.pro_forma_income
        expenses = fin.pro_forma_expenses

        # Build unit mix with rent data
        unit_rent_rows = []
        for u in phys.unit_mix:
            market_rent = fin.market_rents_monthly.get(u.unit_type, 0)
            in_place_rent = fin.in_place_rents_monthly.get(u.unit_type, 0)
            annual_market = market_rent * 12 * u.count
            unit_rent_rows.append(
                f"  - {u.unit_type}: {u.count} units x ${market_rent:,}/mo "
                f"(market) | ${in_place_rent:,}/mo (in-place) | "
                f"${annual_market:,} annual potential"
            )
        unit_rent_text = "\n".join(unit_rent_rows)

        # Historical operating summary
        hist_rows = []
        for year_label, hy in fin.historical_t12.items():
            hist_rows.append(
                f"  - {year_label}: EGI ${hy.effective_gross_income:,} | "
                f"Expenses ${hy.operating_expenses:,} | "
                f"NOI ${hy.net_operating_income:,}"
            )
        hist_text = "\n".join(hist_rows)

        # Comparable sales cap rates
        cap_rates = []
        for cs in mkt.comparable_sales:
            cap_rates.append(f"  - {cs.property}: {cs.cap_rate}% cap rate")
        cap_rate_text = "\n".join(cap_rates)

        return textwrap.dedent(f"""\
        Write the INCOME CAPITALIZATION APPROACH section (Section 7) of a
        multifamily apartment appraisal report.  This is the MOST CRITICAL
        section, requiring 8-10 pages of detailed financial analysis.

        ## Subject Property Financial Data

        **Identification:**
        - Property: {pid.property_name}
        - Location: {pid.city}, {pid.state}
        - Total Units: {phys.total_units}
        - GBA: {phys.gross_building_area_sf:,} SF

        **Occupancy:**
        - Physical Occupancy: {fin.occupancy.physical_percent}%
        - Occupied Units: {fin.occupancy.occupied_units}
        - Vacant Units: {fin.occupancy.vacant_units}

        **Unit Mix & Rents:**
        {unit_rent_text}

        **Pro Forma Income:**
        - Potential Gross Rental Income: ${income.potential_gross_rental_income:,}
        - Other Income: ${income.other_income:,}
        - Potential Gross Income: ${income.potential_gross_income:,}
        - Vacancy & Collection Loss: {income.vacancy_collection_loss_percent}% (${income.vacancy_collection_loss_amount:,})
        - Effective Gross Income: ${income.effective_gross_income:,}

        **Pro Forma Expenses:**
        - Real Estate Taxes: ${expenses.real_estate_taxes:,}
        - Insurance: ${expenses.insurance:,}
        - Utilities: ${expenses.utilities:,}
        - Repairs & Maintenance: ${expenses.repairs_maintenance:,}
        - Payroll: ${expenses.payroll:,}
        - Management Fee: {expenses.management_fee_percent}% (${expenses.management_fee_amount:,})
        - Marketing: ${expenses.marketing:,}
        - Administrative: ${expenses.administrative:,}
        - Replacement Reserves: ${expenses.replacement_reserves:,}
        - Total Operating Expenses: ${expenses.total_operating_expenses:,}
        - Expense Per Unit: ${expenses.expense_per_unit:,}

        **Net Operating Income: ${fin.net_operating_income:,}**

        **Historical Performance:**
        {hist_text}

        **Comparable Cap Rates:**
        {cap_rate_text}

        **Target Value Conclusion:**
        - Stabilized NOI: ${val.income_approach.stabilized_noi:,}
        - Capitalization Rate: {val.income_approach.cap_rate}%
        - Indicated Value: ${val.income_approach.indicated_value:,}

        ## Required Sub-sections

        1. **Methodology Overview** (0.5 page)
           - Explain Direct Capitalization: Value = NOI / Cap Rate
           - Briefly mention DCF as an alternative (not developed here)
           - Explain why direct capitalization is appropriate

        2. **Rental Income Analysis** (1.5-2 pages)
           - Market rent analysis by unit type
           - Create Markdown table: Unit Type | Units | SF | Market Rent/Mo | Market Rent/SF | Annual Income
           - Compare in-place rents to market rents
           - Discuss rent loss to lease (if in-place < market)
           - Discuss concessions and free rent in the market
           - Other income analysis (laundry, parking, pet fees, late fees, etc.)
           - Conclude on Potential Gross Income

        3. **Vacancy & Collection Loss** (0.5 page)
           - Subject historical vacancy
           - Market/submarket vacancy rates
           - Structural vs. frictional vacancy
           - Conclude on stabilized vacancy rate of {income.vacancy_collection_loss_percent}%

        4. **Effective Gross Income** (0.25 page)
           - Calculate EGI = PGI - V&C Loss
           - Must equal ${income.effective_gross_income:,}

        5. **Operating Expense Analysis** (2-3 pages)
           - Analyze each expense line item:
             * Real Estate Taxes -- assessed value, tax rate, trend
             * Insurance -- coverage, rate per unit, market comparison
             * Utilities -- which utilities owner pays, trend
             * Repairs & Maintenance -- per unit comparison, age factor
             * Payroll -- staffing levels, market wages
             * Management Fee -- percentage of EGI, market comparison
             * Marketing -- per unit, market conditions
             * Administrative -- per unit
             * Replacement Reserves -- per unit, industry standard
           - Create Markdown table: Expense Category | Amount | Per Unit | % of EGI
           - Compare to historical expenses
           - Compare to industry benchmarks (per unit and % of EGI)
           - Expense ratio analysis

        6. **Reconstructed Operating Statement** (1 page)
           Create a comprehensive Markdown pro forma table showing:
           - Potential Gross Rental Income
           - + Other Income
           - = Potential Gross Income
           - - Vacancy & Collection Loss
           - = Effective Gross Income
           - Each expense line item
           - = Total Operating Expenses
           - = Net Operating Income
           Show amounts, per unit, and % of EGI columns.
           CRITICAL: NOI must equal ${fin.net_operating_income:,}

        7. **Capitalization Rate Analysis** (1-1.5 pages)
           - Market-extracted cap rates from comparable sales
           - Create Markdown table: Sale | Price | NOI | Cap Rate
           - Band of investment technique
           - National investor surveys (ACLI, RealtyRates, PwC)
           - Discussion of risk factors affecting cap rate selection
           - Conclude on {val.income_approach.cap_rate}% overall cap rate

        8. **Direct Capitalization** (0.5 page)
           - NOI / Cap Rate = Value
           - ${val.income_approach.stabilized_noi:,} / {val.income_approach.cap_rate}%
             = ${val.income_approach.indicated_value:,}
           - State the indicated value via the Income Approach

        CRITICAL REQUIREMENTS:
        - Every number must tie: PGI - V&C = EGI, EGI - Expenses = NOI
        - NOI / Cap Rate must equal the indicated value
        - All expense items must sum to total operating expenses
        - Use the EXACT figures provided -- do not round or change them
        - Format all dollar amounts with commas
        - This is the most important section of the entire report

        Format as professional Markdown with proper headings and tables.
        Write approximately 5,000-7,000 words.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = IncomeCapitalizationGenerator(event, context)
    return gen.execute()
