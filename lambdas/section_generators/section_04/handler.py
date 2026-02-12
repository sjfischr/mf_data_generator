"""Lambda: Section 04 -- Highest and Best Use.

Generates the Highest and Best Use analysis including as-if-vacant
and as-improved analyses.  Target: 2 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HighestBestUseGenerator(SectionGenerator):
    """Generate Section 04 -- Highest and Best Use."""

    def get_section_name(self) -> str:
        return "section_04_highest_best_use"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You are an expert at "
            "highest and best use analysis applying the four-part test. "
            "Write in formal, professional appraisal language. "
            "Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        mkt = crosswalk.market_data
        val = crosswalk.valuation

        return textwrap.dedent(f"""\
        Write the HIGHEST AND BEST USE section (Section 4) of a multifamily
        apartment appraisal report.  This section should be approximately
        2 pages.

        ## Property Data
        - Property: {pid.property_name}
        - Location: {pid.address}, {pid.city}, {pid.state} {pid.zip}
        - Site Area: {phys.site_area_acres} acres ({phys.site_area_sf:,} SF)
        - Current Use: {phys.building_type} multifamily ({phys.total_units} units)
        - Year Built: {pid.year_built} (Effective Age: {pid.effective_age} years)
        - Stories: {phys.stories}
        - GBA: {phys.gross_building_area_sf:,} SF
        - Submarket Vacancy: {mkt.submarket_vacancy_rate}%
        - Concluded Value: ${val.final_value_conclusion.market_value:,}
        - NOI: ${val.income_approach.stabilized_noi:,}

        ## Required Sub-sections

        1. **Highest and Best Use Definition** -- Provide the standard
           definition: that use which is legally permissible, physically
           possible, financially feasible, and maximally productive.

        2. **As If Vacant Analysis** -- Apply the four-part test:
           a. **Legally Permissible** -- Discuss zoning classification,
              permitted uses, density limits, setbacks, height restrictions.
              Note that multifamily is a permitted use.
           b. **Physically Possible** -- Discuss site size, shape, topography,
              soil conditions, access, utilities.  The site can physically
              support multifamily development.
           c. **Financially Feasible** -- Given current market conditions,
              strong multifamily demand, and achievable rents, multifamily
              development is financially feasible.
           d. **Maximally Productive** -- Among legally permissible and
              financially feasible uses, multifamily development of similar
              density represents the maximally productive use.
           e. **Conclusion** -- The highest and best use as if vacant is
              development with a multifamily residential project.

        3. **As Improved Analysis** -- Apply the same four-part test to
           the property as it currently exists:
           a. **Legally Permissible** -- Current use conforms to zoning.
           b. **Physically Possible** -- Existing improvements are functional.
           c. **Financially Feasible** -- The property generates positive NOI
              and has value in excess of land value alone.
           d. **Maximally Productive** -- Continued operation as a multifamily
              property is the maximally productive use.
           e. **Conclusion** -- The highest and best use as improved is
              continued use as a multifamily apartment community.

        Format as professional Markdown with proper headings.
        Write approximately 1,200-1,500 words.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = HighestBestUseGenerator(event, context)
    return gen.execute()
