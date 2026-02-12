"""Lambda: Section 08 -- Cost Approach.

Generates a brief Cost Approach section.  For income-producing multifamily
properties the Cost Approach is typically not developed; this section
explains why and may provide a brief cost estimate.  Target: 1-2 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CostApproachGenerator(SectionGenerator):
    """Generate Section 08 -- Cost Approach."""

    def get_section_name(self) -> str:
        return "section_08_cost_approach"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You understand when the "
            "Cost Approach is and is not applicable to income-producing "
            "properties. Write in formal, professional appraisal language. "
            "Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        val = crosswalk.valuation

        return textwrap.dedent(f"""\
        Write the COST APPROACH section (Section 8) of a multifamily
        apartment appraisal report.  This section should be 1-2 pages.

        ## Property Data
        - Property: {pid.property_name}
        - Location: {pid.city}, {pid.state}
        - Year Built: {pid.year_built}
        - Effective Age: {pid.effective_age} years
        - Total Units: {phys.total_units}
        - GBA: {phys.gross_building_area_sf:,} SF
        - Site Area: {phys.site_area_acres} acres ({phys.site_area_sf:,} SF)
        - Building Type: {phys.building_type}
        - Stories: {phys.stories}
        - Concluded Market Value: ${val.final_value_conclusion.market_value:,}

        ## Required Content

        1. **Cost Approach -- Not Developed** (0.5 page)
           - State clearly that the Cost Approach has NOT been developed
             in this appraisal.
           - Explain the rationale:
             * The subject is an existing {pid.effective_age}-year-old
               income-producing multifamily property
             * Investors in this property type do not typically base
               purchase decisions on replacement cost
             * Accrued depreciation for a property of this age is
               difficult to estimate accurately
             * The Income Capitalization and Sales Comparison Approaches
               provide more reliable indications of value
             * The Cost Approach is most reliable for newer or special-
               purpose properties

        2. **Brief Cost Estimate for Reference** (0.5-1 page)
           Even though not developed, provide a brief indicative cost
           analysis for the reader's reference:
           - Estimated land value (based on comparable land sales,
             express as $/unit or $/SF of land area)
           - Estimated replacement cost new of improvements
             (use Marshall & Swift or similar, express as $/SF of GBA)
           - Less: accrued depreciation
             * Physical deterioration (based on effective age / economic life)
             * Functional obsolescence (if any)
             * External obsolescence (if any)
           - Indicated value via Cost Approach (for reference only)
           - Note that this estimate is provided for informational
             purposes only and is not relied upon in the final
             reconciliation.

        3. **Conclusion** (1-2 sentences)
           - Reiterate that the Cost Approach is not developed and
             not given weight in the final value conclusion.

        Format as professional Markdown with proper headings.
        Write approximately 800-1,200 words.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = CostApproachGenerator(event, context)
    return gen.execute()
