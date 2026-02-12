"""Section 9: Reconciliation and Final Value Conclusion (Opus)."""

import logging

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)


class Section09Reconciliation(SectionGenerator):
    def get_section_name(self) -> str:
        return "section_09_reconciliation"

    def get_model_name(self) -> str:
        return "opus"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial appraiser reconciling multiple "
            "value indications to a final conclusion. You must:\n"
            "1. Present the value indication from each approach used\n"
            "2. Discuss the relative reliability and applicability of each approach\n"
            "3. Explain which approach(es) you give most weight to and why\n"
            "4. Arrive at a final value conclusion\n"
            "5. State the conclusion clearly and professionally\n\n"
            "This is the culmination of the entire appraisal. Be thoughtful and thorough."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        val = crosswalk.valuation
        prop = crosswalk.property_identification
        phys = crosswalk.property_physical
        fin = crosswalk.financial_data

        return f"""Write Section 9: Reconciliation and Final Value Conclusion for the appraisal
of {prop.property_name}, a {phys.total_units}-unit {phys.building_type} apartment
community located at {prop.address}, {prop.city}, {prop.state} {prop.zip}.

Value Indications:
- Sales Comparison Approach: ${val.sales_comparison_approach.indicated_value:,}
  (${val.sales_comparison_approach.value_per_unit:,}/unit, ${val.sales_comparison_approach.value_per_sf:.2f}/SF)
- Income Capitalization Approach: ${val.income_approach.indicated_value:,}
  (Stabilized NOI: ${val.income_approach.stabilized_noi:,}, Cap Rate: {val.income_approach.cap_rate}%)

Property Context:
- {phys.total_units} units, built {prop.year_built}
- Current occupancy: {fin.occupancy.physical_percent}%
- Net Operating Income: ${fin.net_operating_income:,}

The section must include:
1. Summary of Value Indications table (markdown table format)
2. Discussion of reliability of Sales Comparison Approach
3. Discussion of reliability of Income Capitalization Approach
4. Reconciliation logic and weighting rationale
5. Final Value Conclusion: **${val.final_value_conclusion.market_value:,}**
   as of {val.final_value_conclusion.effective_date}
6. Any extraordinary assumptions or hypothetical conditions

Format the final value conclusion prominently. Include a reconciliation summary table.
Output 2-3 pages of professional appraisal content in markdown."""


def handler(event, context):
    return Section09Reconciliation(event, context).execute()
