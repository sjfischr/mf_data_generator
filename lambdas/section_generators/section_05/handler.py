"""Lambda: Section 05 -- Valuation Methodology.

Generates a brief overview of the valuation approaches used in the
appraisal.  Target: 1 page.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ValuationMethodologyGenerator(SectionGenerator):
    """Generate Section 05 -- Valuation Methodology."""

    def get_section_name(self) -> str:
        return "section_05_valuation_methodology"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You are an expert at "
            "explaining valuation methodology clearly and concisely. "
            "Write in formal, professional appraisal language. "
            "Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        phys = crosswalk.property_physical
        val = crosswalk.valuation

        return textwrap.dedent(f"""\
        Write the VALUATION METHODOLOGY section (Section 5) of a multifamily
        apartment appraisal report.  This section should be approximately
        1 page.

        ## Property Context
        - Property Type: {phys.building_type} multifamily ({phys.total_units} units)
        - Sales Comparison Indicated Value: ${val.sales_comparison_approach.indicated_value:,}
        - Income Approach Indicated Value: ${val.income_approach.indicated_value:,}
        - Income Approach Cap Rate: {val.income_approach.cap_rate}%
        - Final Concluded Value: ${val.final_value_conclusion.market_value:,}

        ## Required Content

        1. **Three Approaches to Value** -- Briefly describe each:
           a. **Sales Comparison Approach** -- Compares the subject to
              recently sold comparable properties with adjustments for
              differences.  State that this approach IS developed.
           b. **Income Capitalization Approach** -- Capitalizes the
              property's net operating income to derive value.  State that
              this approach IS developed and is given primary weight for
              income-producing properties.
           c. **Cost Approach** -- Estimates the cost to reproduce or replace
              the improvements less depreciation plus land value.  State that
              this approach is NOT developed because it is less reliable for
              older income-producing properties and investors do not typically
              use this method.

        2. **Rationale for Approaches Used** -- Explain why the Income
           Capitalization Approach is given primary weight for multifamily
           properties (investors purchase based on income), and why the
           Sales Comparison Approach provides useful support.

        3. **Competency** -- Brief statement that the appraiser has the
           necessary competency for this assignment type.

        Format as professional Markdown with proper headings.
        Write approximately 600-800 words.  Keep this section concise.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = ValuationMethodologyGenerator(event, context)
    return gen.execute()
