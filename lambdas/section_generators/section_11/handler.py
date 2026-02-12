"""Section 11: Certification (Haiku)."""

import logging

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)


class Section11Certification(SectionGenerator):
    def get_section_name(self) -> str:
        return "section_11_certification"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial appraiser writing the Certification "
            "section of a multifamily appraisal report. Use standard USPAP certification "
            "language. This is a synthetic/training document."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        prop = crosswalk.property_identification
        val = crosswalk.valuation

        return f"""Write Section 11: Certification for the appraisal of {prop.property_name}
located at {prop.address}, {prop.city}, {prop.state} {prop.zip}.

Final appraised value: ${val.final_value_conclusion.market_value:,}
Effective date: {val.final_value_conclusion.effective_date}
Property type: {crosswalk.property_physical.building_type} multifamily
Total units: {crosswalk.property_physical.total_units}

Include the standard USPAP certification statements:
1. Statements of fact (property inspection, no bias, no undisclosed interest)
2. The analysis and conclusions are the appraiser's own
3. Compliance with USPAP and applicable regulations
4. Identification of anyone providing significant assistance
5. Fee not contingent on value conclusion
6. Prior services disclosure
7. Value conclusion statement with effective date

Use a synthetic appraiser name: "John A. Smith, MAI"
State certification number: "CG-12345"

Output 1-2 pages of content in markdown."""


def handler(event, context):
    return Section11Certification(event, context).execute()
