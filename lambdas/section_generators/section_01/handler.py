"""Lambda: Section 01 -- Introduction.

Generates the introductory section of the appraisal report including
property identification, purpose of the appraisal, intended use,
effective date, and scope of work.  Target length: 2-3 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IntroductionGenerator(SectionGenerator):
    """Generate Section 01 -- Introduction."""

    def get_section_name(self) -> str:
        return "section_01_introduction"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. Write in formal, professional "
            "appraisal language. Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        val = crosswalk.valuation.final_value_conclusion

        return textwrap.dedent(f"""\
        Write the INTRODUCTION section (Section 1) of a multifamily apartment
        appraisal report.  This section should be 2-3 pages and include ALL of
        the following sub-sections with detailed, professional content:

        ## Property Data
        - Property Name: {pid.property_name}
        - Address: {pid.address}, {pid.city}, {pid.state} {pid.zip}
        - County: {pid.county}
        - Legal Description: {pid.legal_description}
        - Tax Parcel Numbers: {', '.join(pid.tax_parcel_numbers)}
        - Current Owner: {pid.current_owner}
        - Year Built: {pid.year_built}
        - Total Units: {phys.total_units}
        - Building Type: {phys.building_type}
        - Effective Date: {val.effective_date}

        ## Required Sub-sections

        1. **Letter of Transmittal** -- Brief cover letter addressed to the
           client summarizing the assignment and concluded value.

        2. **Property Identification** -- Full legal and street address,
           parcel numbers, property type description.

        3. **Purpose of the Appraisal** -- State the purpose is to estimate
           market value as defined by USPAP and federal financial institution
           regulatory agencies.

        4. **Intended Use** -- The intended use is for internal decision-making,
           loan underwriting, and portfolio management.

        5. **Intended Users** -- The client and its successors and assigns.

        6. **Effective Date of Value** -- {val.effective_date}

        7. **Date of Report** -- Same as effective date.

        8. **Scope of Work** -- Describe the scope including: inspection of
           the property and comparables, analysis of market data, application
           of the Income Capitalization and Sales Comparison Approaches,
           interviews with management, and review of historical operating data.

        9. **Market Value Definition** -- Include the standard USPAP/OCC
           definition of market value.

        10. **Extraordinary Assumptions and Hypothetical Conditions** --
            Standard language noting none unless otherwise stated.

        Format as professional Markdown with proper headings (## for main,
        ### for sub-sections).  Do NOT include a title page or table of
        contents.  Write approximately 1,500-2,000 words.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = IntroductionGenerator(event, context)
    return gen.execute()
