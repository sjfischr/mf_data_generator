"""Section 10: Assumptions and Limiting Conditions (Haiku)."""

import logging

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)


class Section10Assumptions(SectionGenerator):
    def get_section_name(self) -> str:
        return "section_10_assumptions"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial appraiser writing the Assumptions "
            "and Limiting Conditions section of a multifamily appraisal report. "
            "Use standard USPAP-compliant language. Be thorough and cover all "
            "standard assumptions used in commercial real estate appraisals."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        prop = crosswalk.property_identification
        val = crosswalk.valuation

        return f"""Write Section 10: Assumptions and Limiting Conditions for the appraisal
of {prop.property_name} located at {prop.address}, {prop.city}, {prop.state} {prop.zip}.

Final appraised value: ${val.final_value_conclusion.market_value:,}
Effective date: {val.final_value_conclusion.effective_date}

Include standard assumptions covering:
1. General Assumptions (title, legal, environmental, zoning, physical condition,
   information reliability, competent management, compliance with regulations)
2. General Limiting Conditions (liability limits, report usage, partial value,
   legal matters, engineering matters, survey, environmental hazards,
   Americans with Disabilities Act, competency)
3. Extraordinary Assumptions (if any)
4. Hypothetical Conditions (if any)

Use standard professional appraisal language. Number each assumption and condition.
Output 2-3 pages of content in markdown."""


def handler(event, context):
    return Section10Assumptions(event, context).execute()
